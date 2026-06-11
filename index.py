import os
import time
import copy
import logging
import threading
from typing import Any, Dict, List, Optional

# ═══════════════════════════════════════════════════════════════
# 1. NẠP BIẾN MÔI TRƯỜNG LOCAL
# ═══════════════════════════════════════════════════════════════
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from flask import request, jsonify
from app import create_app
from app.models.setting_model import SettingModel
from app.utils.supabase_client import get_supabase

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 2. KHỞI TẠO ỨNG DỤNG FLASK
# ═══════════════════════════════════════════════════════════════
app = create_app()

# Nâng hạn mức upload lên 50MB.
# Lưu ý: Vercel vẫn có giới hạn request riêng khoảng 4.5MB,
# nên video/ảnh lớn vẫn nên upload trực tiếp lên Supabase Storage.
app.config["MAX_CONTENT_LENGTH"] = int(
    os.environ.get("MAX_CONTENT_LENGTH", 50 * 1024 * 1024)
)


# ═══════════════════════════════════════════════════════════════
# 3. HELPER ENV
# ═══════════════════════════════════════════════════════════════
def _env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)

    if value is None:
        return default

    return str(value).strip().lower() in ("1", "true", "t", "yes", "y", "on")


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except Exception:
        return default


IS_DEBUG = _env_bool("FLASK_DEBUG", False)


# ═══════════════════════════════════════════════════════════════
# 4. IN-MEMORY GLOBAL CONTEXT CACHE
# ═══════════════════════════════════════════════════════════════
_SETTINGS_CACHE: Optional[Dict[str, Any]] = None
_LAST_FETCH_TIME: float = 0.0
_CACHE_TIMEOUT = _env_int("GLOBAL_CACHE_TIMEOUT", 300)

_CACHE_LOCK = threading.RLock()


def invalidate_global_context_cache() -> None:
    """
    Xoá cache global của index.py.

    Quan trọng:
    - SettingModel.invalidate_cache() chỉ xoá cache ở model.
    - index.py còn cache riêng _SETTINGS_CACHE.
    - Sau khi admin lưu storefront, cần gọi hàm này để ảnh/banner mới hiện ngay.
    """
    global _SETTINGS_CACHE, _LAST_FETCH_TIME

    with _CACHE_LOCK:
        _SETTINGS_CACHE = None
        _LAST_FETCH_TIME = 0.0

    try:
        SettingModel.invalidate_cache()
    except Exception as e:
        logger.debug("[GLOBAL CONTEXT] Không xoá được SettingModel cache: %s", e)

    logger.info("[GLOBAL CONTEXT] Đã xoá cache global context.")


def _cache_is_valid() -> bool:
    if _SETTINGS_CACHE is None:
        return False

    if _CACHE_TIMEOUT <= 0:
        return False

    return (time.time() - _LAST_FETCH_TIME) < _CACHE_TIMEOUT


# ═══════════════════════════════════════════════════════════════
# 5. HELPER FETCH DATA AN TOÀN
# ═══════════════════════════════════════════════════════════════
def _safe_list(data: Any) -> List[Dict[str, Any]]:
    """
    Đảm bảo dữ liệu Supabase trả về luôn là list[dict].
    """
    if not isinstance(data, list):
        return []

    return [item for item in data if isinstance(item, dict)]


def _safe_settings(data: Any) -> Dict[str, Any]:
    """
    Trả về settings hợp lệ, không mutate DEFAULT_SETTINGS gốc.
    """
    defaults = copy.deepcopy(SettingModel.DEFAULT_SETTINGS)

    if not isinstance(data, dict):
        return defaults

    merged = copy.deepcopy(defaults)

    for key, value in data.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value

    return merged


def _fetch_categories(db) -> List[Dict[str, Any]]:
    """
    Lấy danh mục cho navbar.
    Ưu tiên sort_order, fallback sang name nếu schema không có sort_order.
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


def _build_default_context() -> Dict[str, Any]:
    """
    Context fallback khi Supabase hoặc settings lỗi.
    """
    defaults = copy.deepcopy(SettingModel.DEFAULT_SETTINGS)

    return {
        "system_settings": defaults,
        "global_settings": defaults.get("general", {}),
        "global_storefront": defaults.get("storefront", {}),
        "global_categories": [],
        "global_collections": [],
    }


def _build_global_context(force_reload: bool = False) -> Dict[str, Any]:
    """
    Tạo dữ liệu global cho mọi template:
    - system_settings
    - global_settings
    - global_storefront
    - global_categories
    - global_collections
    """
    context = _build_default_context()

    try:
        db = get_supabase()

        try:
            all_settings = SettingModel.get_settings(force_reload=force_reload)
        except TypeError:
            # Fallback nếu SettingModel.get_settings() bản cũ chưa nhận force_reload.
            all_settings = SettingModel.get_settings()

        all_settings = _safe_settings(all_settings)

        context["system_settings"] = all_settings
        context["global_settings"] = all_settings.get("general", {})
        context["global_storefront"] = all_settings.get("storefront", {})
        context["global_categories"] = _fetch_categories(db)
        context["global_collections"] = _fetch_collections(db)

        return context

    except Exception as e:
        logger.exception("[GLOBAL CONTEXT] Lỗi build global context: %s", e)
        return context


def _should_force_context_reload() -> bool:
    """
    Cho phép ép reload context trong vài trường hợp:
    - Debug bằng ?fresh=1 hoặc ?no_cache=1.
    - Trang admin settings nên ưu tiên dữ liệu mới.
    """
    try:
        if request.args.get("fresh") in ("1", "true", "yes"):
            return True

        if request.args.get("no_cache") in ("1", "true", "yes"):
            return True

        if request.path.startswith("/admin/settings"):
            return True

    except RuntimeError:
        return False

    return False


# ═══════════════════════════════════════════════════════════════
# 6. GLOBAL CONTEXT PROCESSOR
# ═══════════════════════════════════════════════════════════════
@app.context_processor
def inject_global_settings():
    """
    Inject dữ liệu global cho toàn bộ template.

    Fix:
    - Tránh lỗi global_collections undefined.
    - Navbar có global_categories/global_collections.
    - Storefront lấy được global_storefront.
    - Có cache để không gọi Supabase liên tục.
    - Có cơ chế force reload sau khi admin cập nhật ảnh/banner.
    """
    global _SETTINGS_CACHE, _LAST_FETCH_TIME

    force_reload = _should_force_context_reload()

    if not force_reload:
        with _CACHE_LOCK:
            if _cache_is_valid():
                return copy.deepcopy(_SETTINGS_CACHE)

    try:
        fresh_context = _build_global_context(force_reload=force_reload)

        with _CACHE_LOCK:
            _SETTINGS_CACHE = copy.deepcopy(fresh_context)
            _LAST_FETCH_TIME = time.time()

        return fresh_context

    except Exception as e:
        logger.exception("[GLOBAL CONTEXT] Lỗi context processor: %s", e)
        return _build_default_context()


# ═══════════════════════════════════════════════════════════════
# 7. OPTIONAL DEBUG ROUTES
# ═══════════════════════════════════════════════════════════════
@app.route("/__clear-global-cache")
def clear_global_cache():
    """
    Dùng khi debug local:
    http://127.0.0.1:5000/__clear-global-cache

    Chỉ cho chạy khi FLASK_DEBUG=true.
    Không public route này ở production.
    """
    if not IS_DEBUG:
        return "Not allowed", 403

    invalidate_global_context_cache()

    return jsonify({
        "success": True,
        "message": "Global cache cleared",
        "cache_timeout": _CACHE_TIMEOUT,
    })


@app.route("/__global-cache-status")
def global_cache_status():
    """
    Kiểm tra trạng thái cache khi debug local.
    """
    if not IS_DEBUG:
        return "Not allowed", 403

    with _CACHE_LOCK:
        age = time.time() - _LAST_FETCH_TIME if _LAST_FETCH_TIME else None

        return jsonify({
            "success": True,
            "has_cache": _SETTINGS_CACHE is not None,
            "cache_timeout": _CACHE_TIMEOUT,
            "cache_age_seconds": round(age, 2) if age is not None else None,
            "is_valid": _cache_is_valid(),
        })


# ═══════════════════════════════════════════════════════════════
# 8. LOCAL DEVELOPMENT SERVER
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = _env_int("PORT", 5000)

    print("=" * 60)
    print("🚀 GUAMAISON 2026 - SERVER IS STARTING...")
    print(f"🌍 Truy cập tại     : http://127.0.0.1:{port}")
    print(f"🛠️  Chế độ Debug    : {'BẬT (Development)' if IS_DEBUG else 'TẮT (Production)'}")
    print(f"⚡ Global Cache     : {_CACHE_TIMEOUT}s")
    print(f"📦 Upload Limit     : {app.config['MAX_CONTENT_LENGTH'] / 1024 / 1024:.0f}MB")
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=port,
        debug=IS_DEBUG,
    )