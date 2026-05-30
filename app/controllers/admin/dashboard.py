"""
app/controllers/admin/dashboard.py
"""

import logging
from datetime import datetime

from flask import render_template, current_app

from app.models.product_model import ProductModel
from app.models.order_model import OrderModel
from app.models.user_model import UserModel          # ← thêm dòng này
from app.middleware.auth_required import admin_required
from app.utils.supabase_client import get_supabase
from ._blueprint import admin_bp
from ._helpers import handle_errors

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────


def _fetch_logistics_stats() -> dict:
    """Tính delivery_success, return_rate, avg_time từ bảng shipments."""
    db = get_supabase()
    shipments = (
        db.table("shipments")
        .select("status, created_at, shipped_at, delivered_at, shipping_fee, actual_shipping_fee")
        .execute()
        .data or []
    )

    total = len(shipments)
    delivered = sum(1 for s in shipments if s["status"] == "delivered")
    returned = sum(1 for s in shipments if s["status"] in ("returned", "failed", "cancelled"))

    delivery_success_rate = round(delivered / total * 100, 1) if total else 0
    return_rate = round(returned / total * 100, 1) if total else 0

    total_days, valid = 0, 0
    for s in shipments:
        if s["status"] == "delivered" and s.get("shipped_at") and s.get("delivered_at"):
            try:
                start = datetime.fromisoformat(s["shipped_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(s["delivered_at"].replace("Z", "+00:00"))
                total_days += (end - start).days
                valid += 1
            except Exception:
                pass

    return {
        "delivery_success": delivery_success_rate,
        "return_rate": return_rate,
        "avg_time": round(total_days / valid, 1) if valid else 0,
    }


# ── Routes ───────────────────────────────────────────────────────


@admin_bp.route("/")
@admin_required
@handle_errors("Lỗi tải dashboard.")
def dashboard():
    stats = OrderModel.get_stats()
    user_count = UserModel.get_user_count()           # ← giờ dùng đúng model
    prod_total = ProductModel.get_all(page=1, per_page=1, admin_mode=True).get("total", 0)

    try:
        stats.update(_fetch_logistics_stats())
    except Exception as e:
        current_app.logger.error(f"[Dashboard] Lỗi query logistics: {e}")
        stats.update({"delivery_success": 0, "return_rate": 0, "avg_time": 0})

    try:
        recent_result = OrderModel.get_all(page=1, per_page=10)
        recent_orders = recent_result.get("items", [])
    except Exception as e:
        current_app.logger.error(f"[Dashboard] Lỗi query recent orders: {e}")
        recent_orders = []

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        user_count=user_count,
        prod_count=prod_total,
        recent_orders=recent_orders,
    )