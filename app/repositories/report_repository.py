"""Supabase access for analytics reports.

Only this layer knows how data is stored. Services receive plain rows through
``ReportSnapshot`` and never import a Supabase client.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from app.models.report_models import ReportFilters, ReportSnapshot
from app.utils.supabase_client import get_supabase_admin


logger = logging.getLogger(__name__)


class ReportRepository:
    PAGE_SIZE = 1000
    MAX_ROWS_PER_SOURCE = 20_000
    ORDER_ID_BATCH = 180

    def __init__(self, db_factory: Callable[[], Any] = get_supabase_admin) -> None:
        self._db_factory = db_factory
        self._issues: list[str] = []
        self._truncated: list[str] = []

    def load_snapshot(self, filters: ReportFilters) -> ReportSnapshot:
        self._issues = []
        self._truncated = []
        db = self._db_factory()

        connections = self._load_marketplace_connections(db)
        orders = self._load_orders(db, filters)
        order_ids = [str(row.get("id")) for row in orders if row.get("id")]
        order_items = self._load_order_items(db, order_ids)

        products = self._load_products(db)
        analytics = self._load_analytics(db)
        has_active_connection = any(
            str(row.get("status") or "").lower() in {"active", "connected"}
            for row in connections
        )
        external_orders = self._load_external_orders(db, filters, has_active_connection)
        external_order_ids = [str(row.get("id")) for row in external_orders if row.get("id")]
        external_items = self._load_external_order_items(db, external_order_ids)
        mappings = self._load_product_channel_mappings(db, bool(external_orders))

        return ReportSnapshot(
            orders=orders,
            order_items=order_items,
            products=products,
            analytics=analytics,
            marketplace_connections=connections,
            external_orders=external_orders,
            external_order_items=external_items,
            product_channel_mappings=mappings,
            repository_issues=list(dict.fromkeys(self._issues)),
            truncated_sources=list(dict.fromkeys(self._truncated)),
        )

    def _execute(self, label: str, query_factory: Callable[[], Any]) -> Any | None:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return query_factory().execute()
            except Exception as exc:  # Supabase/PostgREST exposes several error classes.
                last_error = exc
                message = str(exc).lower()
                retryable = any(
                    token in message
                    for token in (
                        "server disconnected",
                        "timeout",
                        "connection reset",
                        "temporarily unavailable",
                        "remoteprotocolerror",
                    )
                )
                if not retryable or attempt == 2:
                    break
                time.sleep(0.2 * (attempt + 1))

        logger.warning("[analytics_repository] %s failed: %s", label, last_error)
        self._issues.append(f"Không đọc được nguồn dữ liệu: {label}.")
        return None

    def _fetch_pages(
        self,
        label: str,
        query_factory: Callable[[int, int], Any],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0

        while offset < self.MAX_ROWS_PER_SOURCE:
            response = self._execute(
                label,
                lambda: query_factory(offset, offset + self.PAGE_SIZE - 1),
            )
            if response is None:
                break

            page = list(getattr(response, "data", None) or [])
            rows.extend(page)
            if len(page) < self.PAGE_SIZE:
                break
            offset += self.PAGE_SIZE

        if len(rows) >= self.MAX_ROWS_PER_SOURCE:
            self._truncated.append(label)
            self._issues.append(
                f"Nguồn {label} đã đạt giới hạn {self.MAX_ROWS_PER_SOURCE:,} dòng; "
                "nên dùng bảng tổng hợp theo ngày."
            )
        return rows[: self.MAX_ROWS_PER_SOURCE]

    def _load_orders(self, db: Any, filters: ReportFilters) -> list[dict[str, Any]]:
        expanded_fields = (
            "id,total_amount,shipping_fee,discount_amount,refunded_amount,"
            "sales_channel,created_at,status,payment_status"
        )
        stable_fields = (
            "id,total_amount,shipping_fee,sales_channel,created_at,status,payment_status"
        )

        def factory(fields: str) -> Callable[[int, int], Any]:
            return lambda start, end: (
                db.table("orders")
                .select(fields)
                .gte("created_at", filters.history_start_iso)
                .lte("created_at", filters.end_iso)
                .order("created_at", desc=False)
                .range(start, end)
            )

        rows = self._fetch_pages("orders", factory(expanded_fields))
        if rows or not any("orders" in issue for issue in self._issues):
            return rows

        self._issues = [issue for issue in self._issues if "orders" not in issue]
        return self._fetch_pages("orders", factory(stable_fields))

    def _load_order_items(self, db: Any, order_ids: list[str]) -> list[dict[str, Any]]:
        if not order_ids:
            return []

        fields = "order_id,product_id,variant_id,quantity,unit_price,size"
        result: list[dict[str, Any]] = []

        for index in range(0, len(order_ids), self.ORDER_ID_BATCH):
            ids = order_ids[index : index + self.ORDER_ID_BATCH]
            batch_rows = self._fetch_pages(
                "order_items",
                lambda start, end, ids=ids: (
                    db.table("order_items")
                    .select(fields)
                    .in_("order_id", ids)
                    .range(start, end)
                ),
            )
            result.extend(batch_rows)
        return result

    def _load_products(self, db: Any) -> list[dict[str, Any]]:
        fields = "id,name,sku,thumbnail_url,stock,price,cost_price"
        return self._fetch_pages(
            "products",
            lambda start, end: (
                db.table("products")
                .select(fields)
                .eq("is_active", True)
                .is_("deleted_at", "null")
                .order("name", desc=False)
                .range(start, end)
            ),
        )

    def _load_analytics(self, db: Any) -> list[dict[str, Any]]:
        # Legacy installations use different date column names. Fetch rows once;
        # the service filters a row when a supported timestamp is present.
        return self._fetch_pages(
            "product_analytics",
            lambda start, end: (
                db.table("product_analytics")
                .select("*")
                .range(start, end)
            ),
        )

    def _load_marketplace_connections(self, db: Any) -> list[dict[str, Any]]:
        response = self._execute(
            "marketplace_connections",
            lambda: (
                db.table("marketplace_connections")
                .select(
                    "id,provider,shop_id,shop_name,status,last_synced_at,"
                    "token_expires_at,updated_at"
                )
                .order("provider", desc=False)
            ),
        )
        if response is None:
            # This table is optional until the marketplace migration is run.
            self._issues = [
                issue
                for issue in self._issues
                if "marketplace_connections" not in issue
            ]
            return []
        return list(response.data or [])

    def _load_external_orders(
        self,
        db: Any,
        filters: ReportFilters,
        marketplace_enabled: bool,
    ) -> list[dict[str, Any]]:
        if not marketplace_enabled:
            return []
        return self._fetch_pages(
            "external_orders",
            lambda start, end: (
                db.table("external_orders")
                .select(
                    "id,provider,shop_id,external_order_id,order_status,payment_status,"
                    "gross_amount,discount_amount,refund_amount,marketplace_fee,"
                    "shipping_fee,net_amount,ordered_at,completed_at"
                )
                .gte("ordered_at", filters.history_start_iso)
                .lte("ordered_at", filters.end_iso)
                .order("ordered_at", desc=False)
                .range(start, end)
            ),
        )

    def _load_external_order_items(self, db: Any, order_ids: list[str]) -> list[dict[str, Any]]:
        if not order_ids:
            return []
        result: list[dict[str, Any]] = []
        fields = (
            "external_order_pk,external_line_item_id,external_product_id,"
            "external_sku_id,seller_sku,product_name,variant_name,quantity,"
            "returned_quantity,unit_price,item_discount"
        )
        for index in range(0, len(order_ids), self.ORDER_ID_BATCH):
            batch = order_ids[index : index + self.ORDER_ID_BATCH]
            result.extend(self._fetch_pages(
                "external_order_items",
                lambda start, end, batch=batch: (
                    db.table("external_order_items")
                    .select(fields)
                    .in_("external_order_pk", batch)
                    .range(start, end)
                ),
            ))
        return result

    def _load_product_channel_mappings(self, db: Any, enabled: bool) -> list[dict[str, Any]]:
        if not enabled:
            return []
        return self._fetch_pages(
            "product_channel_mappings",
            lambda start, end: (
                db.table("product_channel_mappings")
                .select(
                    "product_id,variant_id,provider,shop_id,external_product_id,"
                    "external_sku_id,seller_sku,is_active"
                )
                .eq("is_active", True)
                .range(start, end)
            ),
        )
