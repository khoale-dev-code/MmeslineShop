"""
app/context_processors.py
=========================
Inject biến toàn cục vào mọi template.

PERF FIX (v2) — dựa trên schema thực tế:
────────────────────────────────────────────────────────────────────────────
VẤN ĐỀ CŨ:
  inject_globals() gọi 3–4 DB round-trips TUẦN TỰ trên mọi request:
    1. settings    (~300ms)
    2. categories  (~300ms)
    3. collections (~300ms)
    4. cart_count  (~200ms)     ← chỉ khi đã login
    5. unread_count (~300ms+)   ← chỉ khi đã login, load toàn bộ rows
    6. pending_returns (~200ms) ← chỉ khi admin
  Tổng: 1–2s thuần DB mỗi trang, chưa tính render.

CÁC FIX:
  1. Cache shared data (settings/categories/collections) TTL 15 phút — như cũ,
     nhưng dùng time.monotonic() thay time.time() (không bị ảnh hưởng NTP drift).

  2. Cache user-level data (cart_count, unread_count) TTL 30 giây PER USER KEY.
     → 95%+ request không chạm DB; badge lag tối đa 30s (UX chấp nhận được).
     → Sau khi add-to-cart hoặc đọc notification, gọi invalidate_user_cache()
       để badge cập nhật tức thì không cần chờ TTL hết.

  3. pending_returns ĐÃ BỎ khỏi context_processor toàn cục.
     Lý do: chạy 1 DB call thêm trên MỌI trang kể cả trang khách hàng.
     Giá trị chỉ hiển thị ở admin sidebar → fetch riêng (xem hướng dẫn cuối file).

LƯU Ý VỀ VERCEL / SERVERLESS:
  _GLOBAL_CACHE là dict trong RAM — bị reset sau mỗi cold start.
  Nếu deploy Vercel, cache có thể không hoạt động ổn định.
  Giải pháp lâu dài: dùng Upstash Redis (free tier) hoặc Supabase edge functions.
  Trước mắt: ngay cả khi cache miss, codebase vẫn nhanh hơn nhờ fix #3 ở trên.
────────────────────────────────────────────────────────────────────────────
"""

import logging
import time
from flask import session
from app.models.cart_model import CartModel
from app.models.category_model import CategoryModel
from app.models.collection_model import CollectionModel
from app.models.setting_model import SettingModel
from app.models.navigation_model import NavigationModel

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
#  IN-MEMORY TTL CACHE
# ─────────────────────────────────────────────────────────────────
_CACHE: dict = {}

_TTL_SHARED = 900  # 15 phút: settings, categories, collections
_TTL_USER   = 30   # 30 giây: cart_count, unread_count (per user)


def _cache_get(key: str, fetch_func, ttl: int):
    """
    Lấy giá trị từ cache nếu còn hạn, ngược lại gọi fetch_func().
    Dùng time.monotonic() — không bị lệch bởi NTP sync hay DST.
    Nếu fetch_func() ném exception, trả về dữ liệu cũ (stale-while-error).
    """
    now = time.monotonic()
    entry = _CACHE.get(key)
    if entry and (now - entry["ts"] < ttl):
        return entry["data"]
    try:
        data = fetch_func()
        _CACHE[key] = {"data": data, "ts": now}
        return data
    except Exception as e:
        logger.warning(f"[context_processor] fetch thất bại, dùng stale — key='{key}': {e}")
        return entry["data"] if entry else None


def invalidate_user_cache(user_id: str) -> None:
    """
    Xóa cache của một user khỏi bộ nhớ ngay lập tức.

    Gọi hàm này sau các action làm thay đổi cart hoặc notification để badge
    cập nhật tức thì thay vì chờ TTL 30 giây hết.

    VÍ DỤ — trong cart_controller.py, sau khi add/remove item:
        from app.context_processors import invalidate_user_cache
        invalidate_user_cache(session["user_id"])

    VÍ DỤ — trong notification_controller.py, sau khi mark as read:
        from app.context_processors import invalidate_user_cache
        invalidate_user_cache(session["user_id"])
    """
    _CACHE.pop(f"cart_{user_id}", None)
    _CACHE.pop(f"unread_{user_id}", None)
    logger.debug(f"[context_processor] Đã xóa cache cho user {user_id}")


def invalidate_shared_cache() -> None:
    """
    Xóa cache shared (settings/categories/collections).
    Gọi sau khi admin cập nhật danh mục, setting, collection để
    thay đổi hiển thị ngay mà không cần chờ 15 phút.

    VÍ DỤ — trong admin/categories.py, sau khi update:
        from app.context_processors import invalidate_shared_cache
        invalidate_shared_cache()
    """
    for key in ("settings", "categories", "collections"):
        _CACHE.pop(key, None)
    logger.info("[context_processor] Đã xóa shared cache")


# ─────────────────────────────────────────────────────────────────
#  CONTEXT PROCESSOR CHÍNH
# ─────────────────────────────────────────────────────────────────

def inject_globals() -> dict:
    user_id = session.get("user_id")
    role    = session.get("role")

    # ── 1. Shared data — cache 15 phút, dùng chung mọi user ──────
    system_settings = _cache_get(
        "settings",
        SettingModel.get_settings,
        _TTL_SHARED
    ) or {}

    categories = _cache_get(
        "categories",
        CategoryModel.get_all,
        _TTL_SHARED
    ) or []

    collections = _cache_get(
        "collections",
        lambda: CollectionModel.get_all(admin_mode=False),
        _TTL_SHARED
    ) or []

    navigation_config = NavigationModel.normalize_config(system_settings.get("navigation"))
    menu_product_categories = NavigationModel.select_product_categories(
        navigation_config, categories
    )

    # ── 2. User data — cache 30 giây, mỗi user một key riêng ─────
    cart_count               = 0
    unread_notification_count = 0

    if user_id:
        cart_count = _cache_get(
            f"cart_{user_id}",
            lambda: CartModel.get_count(user_id),
            _TTL_USER
        ) or 0

        try:
            from app.models.notification_model import NotificationModel
            unread_notification_count = _cache_get(
                f"unread_{user_id}",
                lambda: NotificationModel.get_unread_count(user_id),
                _TTL_USER
            ) or 0
        except Exception as e:
            logger.warning(f"[context_processor] unread_count thất bại: {e}")

    # ── 3. pending_returns ĐÃ BỎ — xem hướng dẫn bên dưới ───────
    # Giữ lại key với giá trị 0 để template admin không bị KeyError
    # trong lúc bạn chưa kịp chuyển sang giải pháp thay thế.

    return {
        "current_user": {
            "id":              user_id,
            "email":           session.get("email"),
            "full_name":       session.get("full_name"),
            "role":            role,
            "admin_role_slug": session.get("admin_role_slug"),
        },
        "cart_count":                cart_count,
        "global_categories":         categories,
        "global_collections":        collections,
        "system_settings":           system_settings,
        "site_navigation":           navigation_config,
        "menu_product_categories":   menu_product_categories,
        "unread_notification_count": unread_notification_count,
        "pending_returns":           0,  # xem hướng dẫn bên dưới
    }


# ═══════════════════════════════════════════════════════════════
#  HƯỚNG DẪN: thay thế pending_returns
# ═══════════════════════════════════════════════════════════════
#
# CÁCH 1 — Admin blueprint context_processor riêng (khuyên dùng):
# Trong app/controllers/admin/_blueprint.py, thêm:
#
#     from app.utils.supabase_client import get_supabase
#
#     @admin_bp.context_processor
#     def admin_inject_globals():
#         try:
#             r = (get_supabase()
#                  .table("return_requests")
#                  .select("id", count="exact")
#                  .eq("status", "pending")
#                  .execute())
#             return {"pending_returns": r.count or 0}
#         except Exception:
#             return {"pending_returns": 0}
#
# → Chỉ chạy khi vào trang /admin/*, không ảnh hưởng trang khách hàng.
#
# CÁCH 2 — AJAX lazy-load trong admin_base.html:
#
#     <span id="pending-badge"
#           hx-get="/admin/api/pending-returns-count"
#           hx-trigger="load"
#           hx-swap="innerHTML">…</span>
#
# Rồi tạo endpoint trong admin orders controller:
#     @admin_bp.route("/api/pending-returns-count")
#     @admin_required
#     def api_pending_returns_count():
#         r = get_supabase().table("return_requests")
#             .select("id", count="exact").eq("status","pending").execute()
#         return str(r.count or 0)
#
# → Trang admin load ngay, badge hiện sau ~100ms không block render.