import os
import time
import logging
from typing import Any, Dict, List

# 1. NẠP BIẾN MÔI TRƯỜNG LOCAL
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from app import create_app
from app.models.setting_model import SettingModel
from app.utils.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# 2. KHỞI TẠO ỨNG DỤNG FLASK
app = create_app()

# Nâng hạn mức upload lên 50MB
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


# ═══════════════════════════════════════════════════════════════
# IN-MEMORY CACHE
# ═══════════════════════════════════════════════════════════════
_SETTINGS_CACHE: Dict[str, Any] | None = None
_CACHE_TIMEOUT = int(os.environ.get("GLOBAL_CACHE_TIMEOUT", 300))
_LAST_FETCH_TIME = 0


# ═══════════════════════════════════════════════════════════════
# HELPER FETCH DATA AN TOÀN
# ═══════════════════════════════════════════════════════════════
def _safe_list(data: Any) -> List[Dict[str, Any]]:
    """Đảm bảo dữ liệu trả về luôn là list."""
    return data if isinstance(data, list) else []


def _fetch_categories(db) -> List[Dict[str, Any]]:
    """
    Lấy danh mục cho navbar.
    Ưu tiên sort_order, fallback sang name nếu bảng/schema có khác biệt.
    """
    try:
        res = (
            db.table("categories")
            .select("id,name,slug,description,parent_id,is_active,sort_order,created_at")
            .eq("is_active", True)
            .order("sort_order", desc=False)
            .order("name", desc=False)
            .execute()
        )
        return _safe_list(res.data)

    except Exception as e:
        logger.warning("[GLOBAL NAV] Không lấy được categories theo sort_order: %s", e)

        try:
            res = (
                db.table("categories")
                .select("id,name,slug,description,parent_id,is_active,created_at")
                .eq("is_active", True)
                .order("name", desc=False)
                .execute()
            )
            return _safe_list(res.data)

        except Exception as err:
            logger.error("[GLOBAL NAV] Lỗi lấy categories fallback: %s", err)
            return []


def _fetch_collections(db) -> List[Dict[str, Any]]:
    """
    Lấy bộ sưu tập cho navbar.
    Có fallback nếu bảng collections không có sort_order.
    """
    try:
        res = (
            db.table("collections")
            .select("id,name,slug,description,is_active,sort_order,created_at")
            .eq("is_active", True)
            .order("sort_order", desc=False)
            .order("name", desc=False)
            .execute()
        )
        return _safe_list(res.data)

    except Exception as e:
        logger.warning("[GLOBAL NAV] Không lấy được collections theo sort_order: %s", e)

        try:
            res = (
                db.table("collections")
                .select("id,name,slug,description,is_active,created_at")
                .eq("is_active", True)
                .order("name", desc=False)
                .execute()
            )
            return _safe_list(res.data)

        except Exception as err:
            logger.error("[GLOBAL NAV] Lỗi lấy collections fallback: %s", err)
            return []


def _build_global_context() -> Dict[str, Any]:
    """
    Tạo dữ liệu global cho mọi template:
    - system_settings
    - global_settings
    - global_categories
    - global_collections

    Navbar sẽ dùng global_categories/global_collections.
    """
    defaults = SettingModel.DEFAULT_SETTINGS

    context = {
        "system_settings": defaults,
        "global_settings": defaults.get("general", {}),
        "global_categories": [],
        "global_collections": [],
    }

    try:
        db = get_supabase()

        all_settings = SettingModel.get_settings() or defaults

        context["system_settings"] = all_settings
        context["global_settings"] = all_settings.get("general", {})
        context["global_categories"] = _fetch_categories(db)
        context["global_collections"] = _fetch_collections(db)

        return context

    except Exception as e:
        logger.exception("[GLOBAL CONTEXT] Lỗi build global context: %s", e)
        return context


# ═══════════════════════════════════════════════════════════════
# GLOBAL CONTEXT PROCESSOR
# ═══════════════════════════════════════════════════════════════
@app.context_processor
def inject_global_settings():
    """
    Inject dữ liệu global cho toàn bộ template.

    Sửa lỗi:
    - navbar.html bị lỗi global_collections undefined
    - collection menu không hiện vì chưa truyền global_collections
    - tránh gọi Supabase liên tục khi render nhiều template
    """
    global _SETTINGS_CACHE, _LAST_FETCH_TIME

    current_time = time.time()

    if _SETTINGS_CACHE and (current_time - _LAST_FETCH_TIME < _CACHE_TIMEOUT):
        return _SETTINGS_CACHE

    try:
        _SETTINGS_CACHE = _build_global_context()
        _LAST_FETCH_TIME = current_time
        return _SETTINGS_CACHE

    except Exception as e:
        logger.exception("[GLOBAL CONTEXT] Lỗi context processor: %s", e)

        defaults = SettingModel.DEFAULT_SETTINGS

        return {
            "system_settings": defaults,
            "global_settings": defaults.get("general", {}),
            "global_categories": [],
            "global_collections": [],
        }


# ═══════════════════════════════════════════════════════════════
# OPTIONAL: ROUTE XÓA CACHE KHI CẦN DEBUG LOCAL
# ═══════════════════════════════════════════════════════════════
@app.route("/__clear-global-cache")
def clear_global_cache():
    """
    Dùng khi debug local:
    http://127.0.0.1:5000/__clear-global-cache

    Không nên public route này ở production nếu không cần.
    """
    global _SETTINGS_CACHE, _LAST_FETCH_TIME

    if os.environ.get("FLASK_DEBUG", "False").lower() not in ("true", "1", "t"):
        return "Not allowed", 403

    _SETTINGS_CACHE = None
    _LAST_FETCH_TIME = 0

    return {
        "success": True,
        "message": "Global cache cleared",
    }


# ═══════════════════════════════════════════════════════════════
# LOCAL DEVELOPMENT SERVER
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    is_debug = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "t")

    print("=" * 60)
    print("🚀 MMÉSTLINE 2026 - SERVER IS STARTING...")
    print(f"🌍 Truy cập tại     : http://127.0.0.1:{port}")
    print(f"🛠️  Chế độ Debug    : {'BẬT (Development)' if is_debug else 'TẮT (Production)'}")
    print(f"⚡ Global Cache     : {_CACHE_TIMEOUT}s")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=is_debug,
    )