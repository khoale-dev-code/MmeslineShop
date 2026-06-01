"""
app/controllers/admin/_blueprint.py
Định nghĩa Blueprint duy nhất — không import gì từ nội bộ package.
Các sub-module import từ đây thay vì từ __init__.py.
"""

from flask import Blueprint
from app.utils.supabase_client import get_supabase

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.context_processor
def admin_inject_globals():
    """
    Inject biến dành riêng cho admin — chỉ chạy khi vào /admin/*.
    Không ảnh hưởng đến trang khách hàng.
    """
    try:
        r = (
            get_supabase()
            .table("return_requests")
            .select("id", count="exact")
            .eq("status", "pending")
            .execute()
        )
        return {"pending_returns": r.count or 0}
    except Exception:
        return {"pending_returns": 0}