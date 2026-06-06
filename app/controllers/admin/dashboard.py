"""
app/controllers/admin/dashboard.py
==================================
Dashboard tổng quan cho Admin.

Fix / cải thiện:
- Dùng service_role cho số liệu nội bộ admin.
- Không query shipments bằng anon client vì sẽ bị RLS chặn.
- Tách helper an toàn, có fallback khi lỗi.
- Parse datetime chắc hơn.
- Giới hạn dữ liệu logistics để tránh dashboard load quá nặng.
- Không để một lỗi nhỏ làm sập toàn bộ dashboard.
"""

import logging
from datetime import datetime
from typing import Any

from flask import render_template, current_app

from app.models.product_model import ProductModel
from app.models.order_model import OrderModel
from app.models.user_model import UserModel
from app.middleware.auth_required import admin_required
from app.utils.supabase_client import get_supabase_admin

from ._blueprint import admin_bp
from ._helpers import handle_errors

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

LOGISTICS_LIMIT = 1000

DEFAULT_LOGISTICS_STATS = {
    "delivery_success": 0,
    "return_rate": 0,
    "avg_time": 0,
}


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _safe_parse_datetime(value: str | None) -> datetime | None:
    """
    Parse datetime từ Supabase.

    Supabase thường trả ISO string dạng:
      2026-06-05T10:00:00+00:00
      2026-06-05T10:00:00Z
    """
    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0

    try:
        return round((numerator / denominator) * 100, 1)
    except Exception:
        return 0


def _fetch_logistics_stats() -> dict:
    """
    Tính delivery_success, return_rate, avg_time từ bảng shipments.

    Dùng service_role vì:
    - Đây là số liệu nội bộ admin.
    - shipments không nên mở SELECT cho anon/authenticated.
    - Dashboard admin cần xem tổng quan toàn hệ thống.
    """
    db = get_supabase_admin()

    res = (
        db.table("shipments")
        .select(
            "status, created_at, shipped_at, delivered_at, "
            "shipping_fee, actual_shipping_fee"
        )
        .order("created_at", desc=True)
        .limit(LOGISTICS_LIMIT)
        .execute()
    )

    shipments = res.data or []

    total = len(shipments)
    if total == 0:
        return dict(DEFAULT_LOGISTICS_STATS)

    delivered = 0
    returned_or_failed = 0

    total_days = 0.0
    valid_delivery_time_count = 0

    for shipment in shipments:
        status = shipment.get("status")

        if status == "delivered":
            delivered += 1

            shipped_at = _safe_parse_datetime(shipment.get("shipped_at"))
            delivered_at = _safe_parse_datetime(shipment.get("delivered_at"))

            if shipped_at and delivered_at and delivered_at >= shipped_at:
                delta = delivered_at - shipped_at
                total_days += delta.total_seconds() / 86400
                valid_delivery_time_count += 1

        elif status in {"returned", "failed", "cancelled"}:
            returned_or_failed += 1

    avg_time = (
        round(total_days / valid_delivery_time_count, 1)
        if valid_delivery_time_count
        else 0
    )

    return {
        "delivery_success": _safe_ratio(delivered, total),
        "return_rate": _safe_ratio(returned_or_failed, total),
        "avg_time": avg_time,
    }


def _safe_get_order_stats() -> dict:
    try:
        stats = OrderModel.get_stats()
        return stats or {}
    except Exception as e:
        current_app.logger.error("[Dashboard] Lỗi lấy order stats: %s", e, exc_info=True)
        return {}


def _safe_get_user_count() -> int:
    try:
        return int(UserModel.get_user_count() or 0)
    except Exception as e:
        current_app.logger.error("[Dashboard] Lỗi lấy user count: %s", e, exc_info=True)
        return 0


def _safe_get_product_count() -> int:
    try:
        result = ProductModel.get_all(
            page=1,
            per_page=1,
            admin_mode=True,
        )
        return int((result or {}).get("total", 0) or 0)
    except Exception as e:
        current_app.logger.error("[Dashboard] Lỗi lấy product count: %s", e, exc_info=True)
        return 0


def _safe_get_recent_orders() -> list[dict[str, Any]]:
    try:
        result = OrderModel.get_all(
            page=1,
            per_page=10,
        )
        return (result or {}).get("items", []) or []
    except Exception as e:
        current_app.logger.error("[Dashboard] Lỗi lấy recent orders: %s", e, exc_info=True)
        return []


def _safe_get_logistics_stats() -> dict:
    try:
        return _fetch_logistics_stats()
    except Exception as e:
        current_app.logger.error("[Dashboard] Lỗi query logistics: %s", e, exc_info=True)
        return dict(DEFAULT_LOGISTICS_STATS)


# ═══════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/")
@admin_required
@handle_errors("Lỗi tải dashboard.")
def dashboard():
    stats = _safe_get_order_stats()

    # Bổ sung logistics vào stats nhưng không để lỗi logistics làm sập dashboard.
    stats.update(_safe_get_logistics_stats())

    user_count = _safe_get_user_count()
    prod_total = _safe_get_product_count()
    recent_orders = _safe_get_recent_orders()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        user_count=user_count,
        prod_count=prod_total,
        recent_orders=recent_orders,
    )