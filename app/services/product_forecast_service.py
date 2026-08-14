"""Conservative product forecasting and opportunity segmentation."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from statistics import median
from typing import Any, Iterable

from app.models.report_models import ReportFilters


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _integer(value: Any, default: int = 0) -> int:
    return int(round(_number(value, float(default))))


def _minmax(value: float, values: Iterable[float]) -> float:
    candidates = list(values)
    if not candidates:
        return 0.0
    low = min(candidates)
    high = max(candidates)
    if high <= low:
        return 1.0 if value > 0 else 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


class ProductForecastService:
    """Forecasts are gated by history volume and always include confidence."""

    @staticmethod
    def forecast_product(filters: ReportFilters, history: dict[str, Any]) -> dict[str, Any]:
        daily_units: dict[date, int] = history.get("daily_units") or {}
        if not daily_units:
            return ProductForecastService._insufficient_product()

        first_day = min(daily_units)
        history_days = (filters.end_date - first_day).days + 1
        active_days = sum(1 for value in daily_units.values() if value > 0)
        total_units = sum(daily_units.values())
        if history_days < 56 or active_days < 4 or total_units < 8:
            return ProductForecastService._insufficient_product()

        recent_start = filters.end_date - timedelta(days=13)
        prior_start = filters.end_date - timedelta(days=41)
        prior_end = filters.end_date - timedelta(days=14)
        recent_units = sum(value for day, value in daily_units.items() if recent_start <= day <= filters.end_date)
        prior_units = sum(value for day, value in daily_units.items() if prior_start <= day <= prior_end)
        daily_rate = (recent_units / 14) * 0.65 + (prior_units / 28) * 0.35
        projected = max(0, round(daily_rate * 30))
        confidence = min(92, round(35 + min(history_days, 120) / 120 * 35 + min(active_days, 30) / 30 * 22))
        spread = max(0.12, 0.36 - (confidence / 100) * 0.22)
        return {
            "forecast": projected,
            "low": max(0, round(projected * (1 - spread))),
            "high": round(projected * (1 + spread)),
            "confidence": confidence,
            "status": "ready",
        }

    @staticmethod
    def _insufficient_product() -> dict[str, Any]:
        return {
            "forecast": None,
            "low": None,
            "high": None,
            "confidence": 0,
            "status": "insufficient",
        }

    @staticmethod
    def forecast_total(
        filters: ReportFilters,
        history: dict[str, Any],
        current: dict[str, Any],
    ) -> dict[str, Any]:
        daily_units: dict[date, int] = defaultdict(int)
        for metric in history["product_metrics"].values():
            for day, units in (metric.get("daily_units") or {}).items():
                daily_units[day] += units
        if not daily_units or (filters.end_date - min(daily_units)).days + 1 < 56 or sum(daily_units.values()) < 12:
            return {
                "status": "insufficient",
                "units_30d": None,
                "revenue_30d": None,
                "confidence": 0,
                "message": "Cần tối thiểu 8 tuần và 12 sản phẩm bán ra để bật dự báo tổng.",
                "points": [],
            }

        recent_start = filters.end_date - timedelta(days=13)
        prior_start = filters.end_date - timedelta(days=41)
        prior_end = filters.end_date - timedelta(days=14)
        recent = sum(value for day, value in daily_units.items() if recent_start <= day <= filters.end_date)
        prior = sum(value for day, value in daily_units.items() if prior_start <= day <= prior_end)
        rate = (recent / 14) * 0.65 + (prior / 28) * 0.35
        units_30d = max(0, round(rate * 30))
        average_unit_revenue = current["total_revenue"] / current["total_units"] if current["total_units"] else 0.0
        confidence = min(90, round(50 + min(len(daily_units), 40)))
        points = []
        for week in range(1, 5):
            units = rate * 7
            points.append({
                "label": f"Tuần +{week}",
                "units": round(units),
                "revenue": round(units * average_unit_revenue, 2),
                "low": round(units * average_unit_revenue * 0.78, 2),
                "high": round(units * average_unit_revenue * 1.22, 2),
            })
        return {
            "status": "ready",
            "units_30d": units_30d,
            "revenue_30d": round(units_30d * average_unit_revenue, 2),
            "confidence": confidence,
            "message": "Dự báo trọng số 14/28 ngày; luôn xem cùng khoảng thấp–cao.",
            "points": points,
        }

    @staticmethod
    def score_and_segment(rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        units_values = [row["sold_units"] for row in rows]
        growth_values = [max(-100.0, min(300.0, row["growth_pct"] or 0.0)) for row in rows]
        interest_values = [(row["wishlists"] or 0) + (row["carts"] or 0) for row in rows]
        margin_values = [row["gross_margin"] or 0.0 for row in rows]
        positive_units = sorted(value for value in units_values if value > 0)
        bestseller_cutoff = positive_units[max(0, math.floor(len(positive_units) * 0.75) - 1)] if positive_units else 1
        view_values = [row["views"] or 0 for row in rows if row["views"]]
        median_views = median(view_values) if view_values else 0

        for row in rows:
            components = [
                (35.0, _minmax(row["sold_units"], units_values)),
                (25.0, _minmax(max(-100.0, min(300.0, row["growth_pct"] or 0.0)), growth_values)),
                (20.0, _minmax((row["wishlists"] or 0) + (row["carts"] or 0), interest_values)),
            ]
            if row["gross_margin"] is not None:
                components.append((20.0, _minmax(row["gross_margin"], margin_values)))
            weight = sum(item[0] for item in components)
            row["opportunity_score"] = round(sum(w * score for w, score in components) / weight * 100, 1)

            ProductForecastService._assign_segment(row, bestseller_cutoff, median_views)

    @staticmethod
    def _assign_segment(row: dict[str, Any], bestseller_cutoff: int, median_views: float) -> None:
        if row["forecast_30d"] is not None and row["forecast_30d"] > 0 and row["stock"] < row["forecast_30d"] * 0.4:
            row["segment"] = "stock_risk"
            row["reasons"].append("Tồn kho thấp hơn 40% nhu cầu dự báo 30 ngày.")
        elif row["sold_units"] >= 3 and row["growth_pct"] is not None and row["growth_pct"] >= 25:
            row["segment"] = "accelerating"
            row["reasons"].append("Số lượng bán tăng ít nhất 25% so với kỳ trước.")
        elif row["sold_units"] >= bestseller_cutoff and row["sold_units"] > 0:
            row["segment"] = "bestseller"
            row["reasons"].append("Thuộc nhóm 25% sản phẩm bán nhiều nhất trong kỳ.")
        elif median_views and (row["views"] or 0) >= median_views and ((row["wishlists"] or 0) + (row["carts"] or 0)) > 0 and (row["conversion"] or 0) < 3:
            row["segment"] = "potential"
            row["reasons"].append("Tín hiệu quan tâm tốt nhưng tỷ lệ mua còn thấp.")
        elif row["stock"] > 0 and row["sold_units"] == 0:
            row["segment"] = "slow"
            row["reasons"].append("Có tồn kho nhưng chưa phát sinh bán trong kỳ.")
        else:
            row["reasons"].append("Hiệu suất ổn định trong dữ liệu hiện có.")

        if row["gross_margin"] is None:
            row["reasons"].append("Chưa đủ giá vốn để xác nhận biên lợi nhuận.")
        if row["forecast_30d"] is None:
            row["reasons"].append("Cần tối thiểu 8 tuần dữ liệu để bật dự báo.")

