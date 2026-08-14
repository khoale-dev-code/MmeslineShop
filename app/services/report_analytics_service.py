"""Pure analytics and conservative forecasting for GUAMAISON reports."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

from app.models.report_models import ANALYTICS_VERSION, ReportFilters, ReportSnapshot
from app.repositories.report_repository import ReportRepository
from app.services.product_forecast_service import ProductForecastService


VALID_STATUSES = {"delivered", "completed"}
INVALID_STATUSES = {"cancelled", "canceled", "refunded", "failed"}
MARKETPLACE_PROVIDERS = ("shopee", "lazada", "tiktok_shop")
CHANNEL_ALIASES = {
    "website": "web",
    "online": "web",
    "store": "pos",
    "offline": "pos",
    "tiktok": "tiktok_shop",
    "tik_tok": "tiktok_shop",
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _integer(value: Any, default: int = 0) -> int:
    return int(round(_number(value, float(default))))


def _channel(value: Any) -> str:
    normalized = str(value or "web").strip().lower().replace("-", "_")
    return CHANNEL_ALIASES.get(normalized, normalized or "web")


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def _row_date(row: dict[str, Any]) -> date | None:
    for key in ("event_date", "recorded_date", "metric_date", "date", "created_at", "updated_at"):
        parsed = _datetime(row.get(key))
        if parsed:
            return parsed.date()
    return None


def _percent_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round(((current - previous) / abs(previous)) * 100, 1)


def _safe_rate(numerator: float, denominator: float) -> float | None:
    if denominator <= 0 or numerator < 0 or numerator > denominator:
        return None
    return round((numerator / denominator) * 100, 1)


class ReportAnalyticsService:
    """Business rules only; no Flask and no direct database calls."""

    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    def build(self, filters: ReportFilters) -> dict[str, Any]:
        return self.build_from_snapshot(filters, self._repository.load_snapshot(filters))

    def build_from_snapshot(
        self,
        filters: ReportFilters,
        snapshot: ReportSnapshot,
    ) -> dict[str, Any]:
        active_connections = [
            row for row in snapshot.marketplace_connections
            if str(row.get("status") or "").lower() in {"active", "connected"}
        ]
        connected_providers = {_channel(row.get("provider")) for row in active_connections}
        connected_shops = {
            (_channel(row.get("provider")), str(row.get("shop_id") or ""))
            for row in active_connections
        }
        internal_orders = [self._normalize_order(row) for row in snapshot.orders]
        # Once a marketplace connector is active, its normalized external facts
        # are authoritative for that channel and replace manually imported rows.
        internal_orders = [
            row for row in internal_orders
            if row["channel"] not in connected_providers
        ]
        external_order_rows = [
            row for row in snapshot.external_orders
            if (_channel(row.get("provider")), str(row.get("shop_id") or "")) in connected_shops
        ]
        external_orders = [self._normalize_external_order(row) for row in external_order_rows]
        orders = [row for row in internal_orders + external_orders if row["id"] and self._is_valid_order(row)]
        order_items = [self._normalize_item(row) for row in snapshot.order_items]
        external_context = {
            str(row.get("id")): row
            for row in external_order_rows
            if row.get("id")
        }
        order_items.extend(
            self._normalize_external_items(
                snapshot.external_order_items,
                external_context,
                snapshot.product_channel_mappings,
            )
        )
        unmapped_external_items = sum(
            1 for row in order_items
            if row.get("is_external") and not row.get("product_id") and row.get("quantity", 0) > 0
        )
        products = {
            str(row.get("id")): self._normalize_product(row)
            for row in snapshot.products
            if row.get("id")
        }

        current_orders = self._orders_in_range(
            orders,
            filters.start_date,
            filters.end_date,
            filters.channels,
        )
        previous_orders = self._orders_in_range(
            orders,
            filters.previous_start_date,
            filters.previous_end_date,
            filters.channels,
        ) if filters.compare_previous else []
        history_orders = self._orders_in_range(
            orders,
            filters.history_start_date,
            filters.end_date,
            filters.channels,
        )

        items_by_order: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in order_items:
            if item["order_id"]:
                items_by_order[item["order_id"]].append(item)

        current_sales = self._aggregate_sales(current_orders, items_by_order, products)
        previous_sales = self._aggregate_sales(previous_orders, items_by_order, products)
        history_sales = self._aggregate_sales(history_orders, items_by_order, products)

        analytics_rows, undated_analytics = self._filter_analytics(snapshot.analytics, filters)
        analytics_by_product, analytics_by_channel = self._aggregate_analytics(analytics_rows)

        funnel, funnel_issues = self._build_funnel(
            current_sales["units_by_channel"],
            analytics_by_channel,
        )
        product_rows = self._build_product_rows(
            filters,
            products,
            current_sales,
            previous_sales,
            history_sales,
            analytics_by_product,
        )
        channel_rows = self._build_channel_rows(current_sales, previous_sales, funnel)
        trend = self._build_trend(filters, current_orders)
        forecast = ProductForecastService.forecast_total(filters, history_sales, current_sales)
        marketplaces = self._build_marketplace_status(snapshot.marketplace_connections)

        data_quality = self._build_data_quality(
            snapshot=snapshot,
            current_sales=current_sales,
            products=products,
            analytics_rows=analytics_rows,
            undated_analytics=undated_analytics,
            funnel_issues=funnel_issues,
            product_rows=product_rows,
            marketplaces=marketplaces,
            unmapped_external_items=unmapped_external_items,
        )
        kpis = self._build_kpis(
            current_sales,
            previous_sales,
            funnel,
            data_quality["score"],
        )

        return {
            "version": ANALYTICS_VERSION,
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "filters": filters.as_dict(),
                "tracking_is_realtime": False,
                "data_scope": "Đơn hoàn tất/đã thanh toán; loại đơn hủy và hoàn tiền toàn phần.",
            },
            "kpis": kpis,
            "trend": trend,
            "forecast": forecast,
            "channels": channel_rows,
            "funnel": funnel,
            "products": product_rows,
            "marketplaces": marketplaces,
            "data_quality": data_quality,
            "summary": {
                "bestsellers": sum(row["segment"] == "bestseller" for row in product_rows),
                "accelerating": sum(row["segment"] == "accelerating" for row in product_rows),
                "potential": sum(row["segment"] == "potential" for row in product_rows),
                "stock_risk": sum(row["segment"] == "stock_risk" for row in product_rows),
                "forecast_ready": sum(row["forecast_30d"] is not None for row in product_rows),
            },
        }

    @staticmethod
    def _normalize_order(row: dict[str, Any]) -> dict[str, Any]:
        status = str(row.get("status") or "").strip().lower()
        payment = str(row.get("payment_status") or "").strip().lower()
        total = max(0.0, _number(row.get("total_amount")))
        shipping = max(0.0, _number(row.get("shipping_fee")))
        refunded = max(0.0, _number(row.get("refunded_amount")))
        return {
            "id": str(row.get("id") or ""),
            "created_at": _datetime(row.get("created_at")),
            "status": status,
            "payment_status": payment,
            "channel": _channel(row.get("sales_channel")),
            "total": total,
            "shipping": shipping,
            "refunded": refunded,
            "net_revenue": max(0.0, total - shipping - refunded),
        }

    @staticmethod
    def _normalize_external_order(row: dict[str, Any]) -> dict[str, Any]:
        status = str(row.get("order_status") or "").strip().lower()
        payment = str(row.get("payment_status") or "").strip().lower()
        net_amount = max(0.0, _number(row.get("net_amount")))
        return {
            "id": "market:" + str(row.get("id") or ""),
            "created_at": _datetime(row.get("ordered_at") or row.get("completed_at")),
            "status": status,
            "payment_status": payment,
            "channel": _channel(row.get("provider")),
            "total": net_amount,
            "shipping": 0.0,
            "refunded": max(0.0, _number(row.get("refund_amount"))),
            "net_revenue": net_amount,
            "is_external": True,
        }

    @staticmethod
    def _normalize_item(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "order_id": str(row.get("order_id") or ""),
            "product_id": str(row.get("product_id") or ""),
            "variant_id": str(row.get("variant_id") or ""),
            "quantity": max(0, _integer(row.get("quantity"))),
            "unit_price": max(0.0, _number(row.get("unit_price"))),
            "size": str(row.get("size") or "").strip(),
            "is_external": False,
        }

    @staticmethod
    def _normalize_external_items(
        rows: list[dict[str, Any]],
        order_context: dict[str, dict[str, Any]],
        mappings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        mapping_index: dict[tuple[str, str, str, str], str] = {}
        seller_sku_index: dict[tuple[str, str, str], str] = {}
        for mapping in mappings:
            provider = _channel(mapping.get("provider"))
            shop_id = str(mapping.get("shop_id") or "")
            product_id = str(mapping.get("product_id") or "")
            if not product_id:
                continue
            external_product = str(mapping.get("external_product_id") or "")
            external_sku = str(mapping.get("external_sku_id") or "")
            seller_sku = str(mapping.get("seller_sku") or "")
            mapping_index[(provider, shop_id, external_product, external_sku)] = product_id
            if seller_sku:
                seller_sku_index[(provider, shop_id, seller_sku)] = product_id

        normalized = []
        for row in rows:
            order_pk = str(row.get("external_order_pk") or "")
            order = order_context.get(order_pk) or {}
            provider = _channel(order.get("provider"))
            shop_id = str(order.get("shop_id") or "")
            external_product = str(row.get("external_product_id") or "")
            external_sku = str(row.get("external_sku_id") or "")
            seller_sku = str(row.get("seller_sku") or "")
            product_id = (
                mapping_index.get((provider, shop_id, external_product, external_sku))
                or mapping_index.get((provider, shop_id, external_product, ""))
                or seller_sku_index.get((provider, shop_id, seller_sku))
                or ""
            )
            quantity = max(
                0,
                _integer(row.get("quantity")) - _integer(row.get("returned_quantity")),
            )
            normalized.append({
                "order_id": "market:" + order_pk,
                "product_id": product_id,
                "variant_id": "",
                "quantity": quantity,
                "unit_price": max(0.0, _number(row.get("unit_price")) - _number(row.get("item_discount"))),
                "size": str(row.get("variant_name") or "").strip(),
                "is_external": True,
            })
        return normalized

    @staticmethod
    def _normalize_product(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row.get("id") or ""),
            "name": str(row.get("name") or "Sản phẩm chưa đặt tên").strip(),
            "sku": str(row.get("sku") or "").strip(),
            "thumbnail_url": str(row.get("thumbnail_url") or "").strip(),
            "stock": max(0, _integer(row.get("stock"))),
            "price": max(0.0, _number(row.get("price"))),
            "cost_price": max(0.0, _number(row.get("cost_price"))),
        }

    @staticmethod
    def _is_valid_order(order: dict[str, Any]) -> bool:
        if order["status"] in INVALID_STATUSES:
            return False
        return order["status"] in VALID_STATUSES or order["payment_status"] == "paid"

    @staticmethod
    def _orders_in_range(
        orders: list[dict[str, Any]],
        start: date,
        end: date,
        channels: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        selected_channels = {_channel(value) for value in channels}
        return [
            order
            for order in orders
            if order["created_at"]
            and start <= order["created_at"].date() <= end
            and (not selected_channels or order["channel"] in selected_channels)
        ]

    def _aggregate_sales(
        self,
        orders: list[dict[str, Any]],
        items_by_order: dict[str, list[dict[str, Any]]],
        products: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        product_metrics: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "units": 0,
                "revenue": 0.0,
                "cogs": 0.0,
                "costed_units": 0,
                "daily_units": defaultdict(int),
            }
        )
        revenue_by_channel: dict[str, float] = defaultdict(float)
        units_by_channel: dict[str, int] = defaultdict(int)
        total_units = 0
        total_revenue = 0.0

        for order in orders:
            total_revenue += order["net_revenue"]
            revenue_by_channel[order["channel"]] += order["net_revenue"]
            items = items_by_order.get(order["id"], [])
            gross_items = sum(item["unit_price"] * item["quantity"] for item in items)
            allocation = order["net_revenue"] / gross_items if gross_items > 0 else 1.0

            for item in items:
                product_id = item["product_id"]
                if item["quantity"] <= 0:
                    continue
                quantity = item["quantity"]
                allocated_revenue = item["unit_price"] * quantity * allocation
                units_by_channel[order["channel"]] += quantity
                total_units += quantity
                if not product_id:
                    continue
                product = products.get(product_id, {})
                cost_price = _number(product.get("cost_price"))

                metric = product_metrics[product_id]
                metric["units"] += quantity
                metric["revenue"] += allocated_revenue
                if cost_price > 0:
                    metric["cogs"] += cost_price * quantity
                    metric["costed_units"] += quantity
                metric["daily_units"][order["created_at"].date()] += quantity

        return {
            "orders": orders,
            "order_count": len(orders),
            "total_revenue": round(total_revenue, 2),
            "total_units": total_units,
            "average_order_value": round(total_revenue / len(orders), 2) if orders else 0.0,
            "product_metrics": product_metrics,
            "revenue_by_channel": dict(revenue_by_channel),
            "units_by_channel": dict(units_by_channel),
        }

    def _filter_analytics(
        self,
        rows: list[dict[str, Any]],
        filters: ReportFilters,
    ) -> tuple[list[dict[str, Any]], int]:
        channels = {_channel(value) for value in filters.channels}
        result: list[dict[str, Any]] = []
        undated = 0
        for row in rows:
            channel = _channel(row.get("channel"))
            if channels and channel not in channels:
                continue
            recorded = _row_date(row)
            if recorded is None:
                undated += 1
                result.append(row)
            elif filters.start_date <= recorded <= filters.end_date:
                result.append(row)
        return result, undated

    @staticmethod
    def _aggregate_analytics(
        rows: list[dict[str, Any]],
    ) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]]:
        by_product: dict[str, dict[str, int]] = defaultdict(
            lambda: {"views": 0, "carts": 0, "wishlists": 0}
        )
        by_channel: dict[str, dict[str, int]] = defaultdict(
            lambda: {"views": 0, "carts": 0, "wishlists": 0}
        )
        for row in rows:
            product_id = str(row.get("product_id") or "")
            channel = _channel(row.get("channel"))
            values = {
                "views": max(0, _integer(row.get("views"))),
                "carts": max(0, _integer(row.get("add_to_carts"))),
                "wishlists": max(0, _integer(row.get("wishlist_count"))),
            }
            for key, value in values.items():
                if product_id:
                    by_product[product_id][key] += value
                by_channel[channel][key] += value
        return by_product, by_channel

    @staticmethod
    def _build_funnel(
        units_by_channel: dict[str, int],
        analytics_by_channel: dict[str, dict[str, int]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        channels = sorted(set(units_by_channel) | set(analytics_by_channel))
        rows: list[dict[str, Any]] = []
        issues: list[str] = []
        for channel in channels:
            tracked = analytics_by_channel.get(channel, {})
            views = max(0, _integer(tracked.get("views")))
            carts = max(0, _integer(tracked.get("carts")))
            sold = max(0, _integer(units_by_channel.get(channel)))
            consistent = not ((carts and carts > views) or (views and sold > views))
            if not consistent:
                issues.append(
                    f"Funnel {channel} không đồng nhất giữa tracking và đơn hàng; tỷ lệ được ẩn."
                )
            rows.append({
                "channel": channel,
                "views": views if views > 0 else None,
                "carts": carts if views > 0 else None,
                "sold": sold,
                "view_to_cart": _safe_rate(carts, views) if consistent else None,
                "cart_to_order": _safe_rate(sold, carts) if consistent else None,
                "conversion": _safe_rate(sold, views) if consistent else None,
                "tracking_complete": views > 0,
                "consistent": consistent,
            })
        return rows, issues

    def _build_product_rows(
        self,
        filters: ReportFilters,
        products: dict[str, dict[str, Any]],
        current_sales: dict[str, Any],
        previous_sales: dict[str, Any],
        history_sales: dict[str, Any],
        analytics_by_product: dict[str, dict[str, int]],
    ) -> list[dict[str, Any]]:
        product_ids = set(products) | set(current_sales["product_metrics"]) | set(analytics_by_product)
        rows: list[dict[str, Any]] = []

        for product_id in product_ids:
            product = products.get(product_id) or {
                "id": product_id,
                "name": "Sản phẩm không còn trong danh mục",
                "sku": "",
                "thumbnail_url": "",
                "stock": 0,
                "price": 0.0,
                "cost_price": 0.0,
            }
            current = current_sales["product_metrics"].get(product_id, {})
            previous = previous_sales["product_metrics"].get(product_id, {})
            history = history_sales["product_metrics"].get(product_id, {})
            engagement = analytics_by_product.get(product_id, {})

            units = _integer(current.get("units"))
            prior_units = _integer(previous.get("units"))
            revenue = round(_number(current.get("revenue")), 2)
            cogs = round(_number(current.get("cogs")), 2)
            costed_units = _integer(current.get("costed_units"))
            gross_profit = round(revenue - cogs, 2) if units and costed_units == units else None
            margin = round((gross_profit / revenue) * 100, 1) if gross_profit is not None and revenue else None
            growth = _percent_change(units, prior_units)
            forecast = ProductForecastService.forecast_product(filters, history)
            stock = product["stock"]
            views = _integer(engagement.get("views"))
            carts = _integer(engagement.get("carts"))
            wishlists = _integer(engagement.get("wishlists"))
            conversion = _safe_rate(units, views)

            row = {
                "product_id": product_id,
                "name": product["name"],
                "sku": product["sku"] or product_id[:8].upper(),
                "thumbnail_url": product["thumbnail_url"],
                "sold_units": units,
                "previous_units": prior_units,
                "net_revenue": revenue,
                "gross_profit": gross_profit,
                "gross_margin": margin,
                "growth_pct": growth,
                "sales_velocity": round(units / max(filters.day_count, 1), 2),
                "views": views if views > 0 else None,
                "carts": carts if views > 0 else None,
                "wishlists": wishlists,
                "conversion": conversion,
                "stock": stock,
                "forecast_30d": forecast["forecast"],
                "forecast_low": forecast["low"],
                "forecast_high": forecast["high"],
                "forecast_confidence": forecast["confidence"],
                "forecast_status": forecast["status"],
                "reorder_qty": max(0, _integer((forecast["forecast"] or 0) - stock)),
                "segment": "stable",
                "opportunity_score": 0.0,
                "reasons": [],
            }
            rows.append(row)

        ProductForecastService.score_and_segment(rows)
        rows.sort(
            key=lambda row: (
                row["segment"] == "stock_risk",
                row["opportunity_score"],
                row["net_revenue"],
            ),
            reverse=True,
        )
        return rows[:300]

    @staticmethod
    def _build_channel_rows(
        current: dict[str, Any],
        previous: dict[str, Any],
        funnel: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        funnel_map = {row["channel"]: row for row in funnel}
        channels = sorted(set(current["revenue_by_channel"]) | set(previous["revenue_by_channel"]) | set(funnel_map))
        result = []
        for channel in channels:
            revenue = _number(current["revenue_by_channel"].get(channel))
            previous_revenue = _number(previous["revenue_by_channel"].get(channel))
            result.append({
                "channel": channel,
                "net_revenue": round(revenue, 2),
                "revenue_share": round(revenue / current["total_revenue"] * 100, 1) if current["total_revenue"] else 0.0,
                "growth_pct": _percent_change(revenue, previous_revenue),
                "sold_units": _integer(current["units_by_channel"].get(channel)),
                "conversion": (funnel_map.get(channel) or {}).get("conversion"),
                "tracking_complete": (funnel_map.get(channel) or {}).get("tracking_complete", False),
            })
        result.sort(key=lambda row: row["net_revenue"], reverse=True)
        return result

    @staticmethod
    def _build_trend(filters: ReportFilters, orders: list[dict[str, Any]]) -> dict[str, Any]:
        buckets: dict[str, float] = defaultdict(float)
        if filters.day_count <= 45:
            period = "day"
            for order in orders:
                buckets[order["created_at"].date().isoformat()] += order["net_revenue"]
        elif filters.day_count <= 180:
            period = "week"
            for order in orders:
                year, week, _ = order["created_at"].date().isocalendar()
                buckets[f"{year}-W{week:02d}"] += order["net_revenue"]
        else:
            period = "month"
            for order in orders:
                buckets[order["created_at"].strftime("%Y-%m")] += order["net_revenue"]
        return {
            "period": period,
            "points": [
                {"label": label, "revenue": round(value, 2)}
                for label, value in sorted(buckets.items())
            ],
        }

    @staticmethod
    def _build_marketplace_status(connections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for row in connections:
            provider = _channel(row.get("provider"))
            if provider in MARKETPLACE_PROVIDERS:
                latest[provider] = row
        labels = {"shopee": "Shopee", "lazada": "Lazada", "tiktok_shop": "TikTok Shop"}
        return [{
            "provider": provider,
            "label": labels[provider],
            "status": str((latest.get(provider) or {}).get("status") or "not_connected"),
            "shop_name": str((latest.get(provider) or {}).get("shop_name") or ""),
            "last_synced_at": (latest.get(provider) or {}).get("last_synced_at"),
            "connected": str((latest.get(provider) or {}).get("status") or "") in {"active", "connected"},
        } for provider in MARKETPLACE_PROVIDERS]

    @staticmethod
    def _build_data_quality(
        *,
        snapshot: ReportSnapshot,
        current_sales: dict[str, Any],
        products: dict[str, dict[str, Any]],
        analytics_rows: list[dict[str, Any]],
        undated_analytics: int,
        funnel_issues: list[str],
        product_rows: list[dict[str, Any]],
        marketplaces: list[dict[str, Any]],
        unmapped_external_items: int,
    ) -> dict[str, Any]:
        issues = list(snapshot.repository_issues) + list(funnel_issues)
        order_score = 35 if current_sales["order_count"] else 10
        tracking_score = 25 if analytics_rows and not funnel_issues else (12 if analytics_rows else 0)
        sold_units = current_sales["total_units"]
        costed_units = sum(
            _integer(metric.get("costed_units"))
            for metric in current_sales["product_metrics"].values()
        )
        cost_coverage = round(costed_units / sold_units * 100, 1) if sold_units else 0.0
        cost_score = round(min(25, cost_coverage * 0.25)) if sold_units else 5
        catalog_score = 10 if products else 0
        marketplace_score = 5 if any(row["connected"] for row in marketplaces) else 0
        score = max(0, min(100, order_score + tracking_score + cost_score + catalog_score + marketplace_score))

        if undated_analytics:
            issues.append(
                f"{undated_analytics:,} dòng tracking không có ngày; không thể so sánh chính xác theo kỳ."
            )
        if sold_units and cost_coverage < 80:
            issues.append(
                f"Giá vốn mới phủ {cost_coverage:.1f}% số lượng bán; lợi nhuận được hiển thị N/A khi chưa đủ."
            )
        if snapshot.truncated_sources:
            issues.append("Một số nguồn đạt giới hạn dòng; báo cáo có thể chưa đầy đủ.")
        if not analytics_rows:
            issues.append("Chưa có tracking lượt xem/thêm giỏ; funnel hiển thị N/A thay vì số giả.")
        if not any(row["connected"] for row in marketplaces):
            issues.append("Chưa có sàn nào kết nối qua API chính thức.")
        if unmapped_external_items:
            issues.append(
                f"{unmapped_external_items:,} dòng sản phẩm từ sàn chưa map với SKU nội bộ; "
                "doanh thu kênh vẫn được tính nhưng chưa phân bổ vào bảng sản phẩm."
            )

        return {
            "score": score,
            "label": "Tốt" if score >= 80 else ("Cần bổ sung" if score >= 55 else "Thiếu dữ liệu"),
            "cost_coverage": cost_coverage,
            "tracking_rows": len(analytics_rows),
            "order_rows": current_sales["order_count"],
            "product_rows": len(product_rows),
            "issues": list(dict.fromkeys(issues))[:12],
            "truncated_sources": snapshot.truncated_sources,
        }

    @staticmethod
    def _build_kpis(
        current: dict[str, Any],
        previous: dict[str, Any],
        funnel: list[dict[str, Any]],
        data_score: int,
    ) -> dict[str, Any]:
        sold_units = current["total_units"]
        costed_units = sum(_integer(row.get("costed_units")) for row in current["product_metrics"].values())
        cogs = sum(_number(row.get("cogs")) for row in current["product_metrics"].values())
        gross_profit = current["total_revenue"] - cogs if sold_units and costed_units == sold_units else None
        margin = gross_profit / current["total_revenue"] * 100 if gross_profit is not None and current["total_revenue"] else None
        valid_funnel = [row for row in funnel if row["tracking_complete"] and row["consistent"]]
        total_views = sum(row["views"] or 0 for row in valid_funnel)
        total_sold = sum(row["sold"] for row in valid_funnel)
        conversion = _safe_rate(total_sold, total_views)
        return {
            "net_revenue": {
                "value": current["total_revenue"],
                "change_pct": _percent_change(current["total_revenue"], previous["total_revenue"]),
            },
            "orders": {
                "value": current["order_count"],
                "change_pct": _percent_change(current["order_count"], previous["order_count"]),
            },
            "sold_units": {
                "value": sold_units,
                "change_pct": _percent_change(sold_units, previous["total_units"]),
            },
            "average_order_value": {
                "value": current["average_order_value"],
                "change_pct": _percent_change(current["average_order_value"], previous["average_order_value"]),
            },
            "gross_profit": {"value": round(gross_profit, 2) if gross_profit is not None else None},
            "gross_margin": {"value": round(margin, 1) if margin is not None else None},
            "conversion": {"value": conversion},
            "data_quality": {"value": data_score},
        }
