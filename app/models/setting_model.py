"""
app/models/setting_model.py
Quản lý Cấu hình hệ thống toàn cục (Global Store Settings).

Phiên bản 6.0 (Smart Cache Edition):
- Hỗ trợ tham số force_reload=True để bỏ qua cache khi cần (tương thích cart_controller).
- TTL Cache 60 giây: giảm tải DB mà vẫn đảm bảo gần-thực-thời-gian.
- Thread-safe với threading.Lock để tránh race condition khi nhiều request đồng thời.
- Deep copy khi trả về để bảo vệ cache khỏi bị mutate từ bên ngoài.
- Self-Healing: tự khôi phục defaults nếu bảng store_settings trống.
- Tương thích ngược 100%: mọi nơi gọi get_settings() không cần thay đổi gì.
"""
import copy
import logging
import threading
import time

from app.utils.supabase_client import get_supabase

logger = logging.getLogger(__name__)


class SettingModel:

    # ═══════════════════════════════════════════════════════════════
    #  CACHE NỘI BỘ (TTL 60 giây, thread-safe)
    # ═══════════════════════════════════════════════════════════════
    _cache: dict = {}
    _cache_ts: float = 0.0
    _cache_ttl: int = 60          # Giây — có thể tăng lên 120 nếu cần
    _lock = threading.Lock()

    # ═══════════════════════════════════════════════════════════════
    #  CẤU HÌNH MẶC ĐỊNH (Fallback an toàn khi DB không có dữ liệu)
    # ═══════════════════════════════════════════════════════════════
    DEFAULT_SETTINGS: dict = {
        "general": {
            "shop_name": "GUA Maison",
            "hotline": "",
            "email": "",
            "timezone": "Asia/Ho_Chi_Minh",
            "warehouse_address": "",
        },
        "storefront": {
            "topbar_active": "false",
            "topbar_text": "",
            "banner_desktop_url": "",
            "hero_banner_url": "",
            "banner2_url": "",        # Banner full-width (Giao diện 3)
            "split_left_url": "",     # Split banner bên trái (Nam)
            "split_right_url": "",    # Split banner bên phải (Nữ)
            "banner4_video_url": "",  # Video nền phần Best Sellers
        },
        "integrations": {
            "vnpay_tmncode": "",
            "vnpay_hashsecret": "",
            "ghn_api_token": "",
            "ghn_shop_id": "",
        },
        "shipping_rules": {
            "rules": [],
        },
        "language": {
            "admin_lang": "vi",
            "date_format": "DD/MM/YYYY",
            "time_format": "24h",
        },
        "admin_ui": {
            "logo_url": "",
            "banner_url": "",
        },
    }

    # Danh sách section hợp lệ — chặn payload độc hại
    VALID_SECTIONS: list = [
        "general",
        "storefront",
        "integrations",
        "shipping_rules",
        "language",
        "admin_ui",
    ]

    # ═══════════════════════════════════════════════════════════════
    #  A. ĐỌC CẤU HÌNH (READ)
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    def get_settings(cls, force_reload: bool = False) -> dict:
        """
        Trả về toàn bộ cấu hình hệ thống.

        Tham số:
            force_reload (bool): Nếu True, bỏ qua cache và kéo thẳng từ DB.
                                  Dùng khi cần dữ liệu tươi tuyệt đối (vd: checkout, admin save).

        Chiến lược cache:
            - Lần đầu hoặc cache hết hạn (> TTL): query DB, lưu vào cache.
            - Các lần tiếp theo trong TTL: trả về bản sao cache (không tốn DB round-trip).
            - force_reload=True: luôn query DB và làm mới cache.

        Trả về:
            dict: Toàn bộ cấu hình đã được merge với DEFAULT_SETTINGS.
                  Luôn là deep copy — caller có thể mutate tự do mà không ảnh hưởng cache.
        """
        now = time.monotonic()

        # Kiểm tra cache (thread-safe)
        with cls._lock:
            cache_valid = (
                not force_reload
                and bool(cls._cache)
                and (now - cls._cache_ts) < cls._cache_ttl
            )
            if cache_valid:
                logger.debug("[SettingModel] Cache HIT — trả về từ RAM.")
                return copy.deepcopy(cls._cache)

        # Cache miss hoặc force_reload → query DB
        logger.debug(
            "[SettingModel] Cache MISS%s — đang query DB...",
            " (force_reload)" if force_reload else "",
        )
        settings = cls._fetch_from_db()

        # Cập nhật cache (thread-safe)
        with cls._lock:
            cls._cache = settings
            cls._cache_ts = time.monotonic()

        return copy.deepcopy(settings)

    @classmethod
    def get_section(cls, section_name: str) -> dict:
        """
        Trích xuất nhanh một section (vd: 'general', 'shipping_rules').
        Trả về dict rỗng nếu section không hợp lệ.
        """
        settings = cls.get_settings()
        return settings.get(section_name) or copy.deepcopy(
            cls.DEFAULT_SETTINGS.get(section_name, {})
        )

    @classmethod
    def invalidate_cache(cls) -> None:
        """
        Xóa cache thủ công. Gọi sau khi update_section() để đảm bảo
        lần đọc tiếp theo luôn lấy dữ liệu mới nhất từ DB.
        """
        with cls._lock:
            cls._cache = {}
            cls._cache_ts = 0.0
        logger.debug("[SettingModel] Cache đã được xóa thủ công.")

    # ═══════════════════════════════════════════════════════════════
    #  B. GHI CẤU HÌNH (WRITE)
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    def update_section(cls, section_name: str, new_data: dict) -> bool:
        """
        Cập nhật một section cấu hình vào DB (deep merge với dữ liệu cũ).
        Tự động xóa cache sau khi ghi thành công.

        Trả về:
            bool: True nếu thành công, False nếu thất bại.
        """
        if section_name not in cls.VALID_SECTIONS:
            logger.warning(
                "[SettingModel] Từ chối: section '%s' không hợp lệ.", section_name
            )
            return False

        try:
            db = get_supabase()

            # Deep merge: giữ nguyên các key cũ không được gửi lên
            current_section = cls.get_section(section_name)
            merged_data = {**current_section, **new_data}

            db.table("store_settings").upsert(
                {"setting_key": section_name, "setting_value": merged_data}
            ).execute()

            # Xóa cache để lần đọc tiếp theo lấy dữ liệu mới
            cls.invalidate_cache()

            logger.info("[SettingModel] Đã cập nhật section '%s'.", section_name)
            return True

        except Exception as e:
            logger.error(
                "[SettingModel] Cập nhật section '%s' thất bại. Lỗi: %s",
                section_name,
                e,
            )
            return False

    # ═══════════════════════════════════════════════════════════════
    #  C. INTERNAL HELPERS (private)
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    def _fetch_from_db(cls) -> dict:
        """
        Query bảng store_settings và merge vào DEFAULT_SETTINGS.
        Kích hoạt Self-Healing nếu bảng trống.
        Trả về DEFAULT_SETTINGS nếu mất kết nối DB.
        """
        try:
            db = get_supabase()
            res = db.table("store_settings").select("*").execute()

            # Bắt đầu từ bản sao deep của defaults (đảm bảo mọi key luôn tồn tại)
            settings: dict = copy.deepcopy(cls.DEFAULT_SETTINGS)

            if res.data:
                for row in res.data:
                    key = row.get("setting_key")
                    val = row.get("setting_value")
                    if key in settings and isinstance(val, dict):
                        settings[key].update(val)
            else:
                logger.warning(
                    "[SettingModel] Bảng store_settings trống — kích hoạt Self-Healing..."
                )
                cls._initialize_defaults()

            return settings

        except Exception as e:
            logger.error(
                "[SettingModel] Mất kết nối DB — dùng DEFAULT_SETTINGS tạm thời. Lỗi: %s", e
            )
            return copy.deepcopy(cls.DEFAULT_SETTINGS)

    @classmethod
    def _initialize_defaults(cls) -> None:
        """
        Self-Healing: chèn toàn bộ DEFAULT_SETTINGS vào DB nếu bảng trống.
        """
        try:
            db = get_supabase()
            upsert_data = [
                {"setting_key": key, "setting_value": value}
                for key, value in cls.DEFAULT_SETTINGS.items()
            ]
            db.table("store_settings").upsert(upsert_data).execute()
            logger.info("[SettingModel] Self-Healing: đã khởi tạo defaults thành công.")
        except Exception as e:
            logger.error(
                "[SettingModel] Self-Healing thất bại. Lỗi: %s", e
            )