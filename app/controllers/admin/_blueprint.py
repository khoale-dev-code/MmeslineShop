"""
app/controllers/admin/_blueprint.py
===================================
Định nghĩa Blueprint duy nhất cho khu vực Admin.

Lưu ý:
- File này không import các controller con.
- Các controller con import admin_bp từ đây.
- Admin context processor dùng service_role để đọc số liệu nội bộ.
- Không dùng anon client vì sẽ bị RLS chặn.
- Có cache ngắn hạn để chuyển trang admin nhanh hơn.
"""

import logging
import time
from typing import Any

from flask import Blueprint, g

from app.utils.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ═══════════════════════════════════════════════════════════════
# CACHE CONFIG
# ═══════════════════════════════════════════════════════════════

_ADMIN_CONTEXT_TTL = 30  # giây

_ADMIN_CONTEXT_CACHE: dict[str, dict[str, Any]] = {
    "pending_returns": {
        "value": 0,
        "expires_at": 0.0,
    },
    "admin_notification_count": {
        "value": 0,
        "expires_at": 0.0,
    },
}


# ═══════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_cached_value(key: str) -> int | None:
    item = _ADMIN_CONTEXT_CACHE.get(key)
    if not item:
        return None

    now = time.time()
    if now < float(item.get("expires_at") or 0):
        return int(item.get("value") or 0)

    return None


def _set_cached_value(key: str, value: int, ttl: int = _ADMIN_CONTEXT_TTL) -> int:
    _ADMIN_CONTEXT_CACHE[key] = {
        "value": int(value or 0),
        "expires_at": time.time() + ttl,
    }
    return int(value or 0)


def _safe_count(
    table: str,
    filters: dict[str, Any] | None = None,
    cache_key: str | None = None,
    ttl: int = _ADMIN_CONTEXT_TTL,
) -> int:
    """
    Count an toàn cho admin context.

    Dùng service_role vì đây là số liệu nội bộ admin.
    Có cache để tránh mỗi page admin lại query Supabase.
    """
    if cache_key:
        cached = _get_cached_value(cache_key)
        if cached is not None:
            return cached

    try:
        db = get_supabase_admin()

        query = db.table(table).select("id", count="exact")

        for col, value in (filters or {}).items():
            query = query.eq(col, value)

        res = query.execute()
        count = int(res.count or 0)

        if cache_key:
            return _set_cached_value(cache_key, count, ttl)

        return count

    except Exception as e:
        logger.warning(
            "[admin_context] Không đếm được table=%s filters=%s error=%s",
            table,
            filters,
            e,
        )

        if cache_key:
            fallback = _ADMIN_CONTEXT_CACHE.get(cache_key, {}).get("value", 0)
            return int(fallback or 0)

        return 0


def _get_pending_returns_count() -> int:
    """
    Đếm số yêu cầu đổi/trả đang pending.

    Dùng service_role vì:
    - Đây là số liệu nội bộ admin.
    - return_requests có RLS user-owned.
    - Không nên mở SELECT toàn bảng return_requests cho anon/authenticated.
    """
    return _safe_count(
        table="return_requests",
        filters={"status": "pending"},
        cache_key="pending_returns",
        ttl=_ADMIN_CONTEXT_TTL,
    )


def _get_admin_notification_count() -> int:
    """Äáº¿m viá»‡c chÆ°a Ä‘á»c trong shared Admin action inbox."""
    cached = _get_cached_value("admin_notification_count")
    if cached is not None:
        return cached
    try:
        from app.services.admin_event_service import AdminEventMigrationRequired, AdminEventService

        return _set_cached_value(
            "admin_notification_count",
            AdminEventService().unread_count(),
            _ADMIN_CONTEXT_TTL,
        )
    except AdminEventMigrationRequired:
        return _set_cached_value("admin_notification_count", 0, _ADMIN_CONTEXT_TTL)
    except Exception as exc:
        logger.warning("[admin_context] KhÃ´ng Ä‘áº¿m Ä‘Æ°á»£c Admin action inbox: %s", exc)
        return int(_ADMIN_CONTEXT_CACHE.get("admin_notification_count", {}).get("value", 0) or 0)

def clear_admin_context_cache() -> None:
    """
    Optional helper.

    Có thể gọi sau khi tạo/sửa/xóa notification hoặc return_request
    nếu bạn muốn badge cập nhật ngay lập tức thay vì đợi TTL 30 giây.
    """
    for key in _ADMIN_CONTEXT_CACHE:
        _ADMIN_CONTEXT_CACHE[key]["expires_at"] = 0.0


# ═══════════════════════════════════════════════════════════════
# CONTEXT PROCESSOR
# ═══════════════════════════════════════════════════════════════

@admin_bp.context_processor
def admin_inject_globals():
    """
    Inject biến dành riêng cho admin — chỉ chạy khi render template admin.

    Biến inject:
    - pending_returns: badge Đổi / Trả hàng.
    - admin_notification_count: badge Thông báo admin.
    """
    try:
        if hasattr(g, "_admin_context_globals"):
            return g._admin_context_globals

        context = {
            "pending_returns": _get_pending_returns_count(),
            "admin_notification_count": _get_admin_notification_count(),
            "newsletter_unread_count": _get_newsletter_unread_count(),
            "contact_unread_count": _get_contact_unread_count(),
        }

        g._admin_context_globals = context
        return context

    except Exception as e:
        logger.warning(f"[admin_context] fallback context error: {e}")

        return {
            "pending_returns": 0,
            "admin_notification_count": 0,
            "newsletter_unread_count": 0,
            "contact_unread_count": 0,
        }