"""
app/models/setting_model.py
=========================
Quản lý Cấu hình hệ thống toàn cục (Global Store Settings) cho GUA Maison.

Phiên bản 6.1 (Lazy Smart Cache Edition):
- ĐỒNG BỘ: Áp dụng cơ chế Lazy Initialization phân tách an toàn cổng kết nối Database.
- Ép các hàm ghi và khôi phục dữ liệu (update_section, _initialize_defaults) chạy qua admin client để bypass RLS.
- TTL Cache 60 giây kết hợp Thread-safe với threading.Lock bảo vệ tài nguyên trên Vercel Serverless.
"""
import copy
import logging
import threading
import time

from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)


class SettingModel:

    # ═══════════════════════════════════════════════════════════════
    #  CACHE NỘI BỘ (TTL 60 giây, thread-safe)
    # ═══════════════════════════════════════════════════════════════
    _cache: dict = {}
    _cache_ts: float = 0.0
    _cache_ttl: int = 60          # Giây — giữ cấu hình RAM tránh hit mạng liên tục
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
            # GUAMAISON-home-editorial-v21-defaults
            "latest_arrivals_enabled": "true",
            # GUAMAISON-home-editorial-v21-latest-products-defaults
            "latest_arrivals_eyebrow": "Bộ sưu tập mới · 2026",
            # GUAMAISON-home-editorial-v21-whats-hot-default
            "latest_arrivals_title": "WHATS' HOT",
            "latest_arrivals_description": "Những thiết kế mới được GUAMAISON tuyển chọn, sẵn sàng đồng hành cùng nhịp sống mỗi ngày.",
            "latest_arrivals_product_ids": [],
            "instagram_section_enabled": "true",
            "instagram_section_title": "Instagram",
            "instagram_handle": "@GUAMAISON",
            "instagram_profile_url": "",
            "instagram_media_1_url": "",
            "instagram_media_2_url": "",
            "instagram_media_3_url": "",
            "instagram_media_4_url": "",
            "instagram_media_5_url": "",
            "instagram_media_6_url": "",
            # GUAMAISON-home-editorial-v21-instagram-link-defaults
            "instagram_link_1_url": "",
            "instagram_link_2_url": "",
            "instagram_link_3_url": "",
            "instagram_link_4_url": "",
            "instagram_link_5_url": "",
            "instagram_link_6_url": "",
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
        "size_charts": {
            "items": [],
        },
        "navigation": {
            "navbar": {
                "brand_label": "GUAMAISON",
                "transparent_home": True,
                "items": [
                    {"id": "shop", "label": "Shop", "url": "/shop", "kind": "products", "enabled": True, "new_tab": False},
                    {"id": "collections", "label": "Collection", "url": "/collections", "kind": "collections", "enabled": True, "new_tab": False},
                    {"id": "vouchers", "label": "Voucher", "url": "/vouchers", "kind": "link", "enabled": True, "new_tab": False},
                    {"id": "contact", "label": "Contact", "url": "/contact", "kind": "link", "enabled": True, "new_tab": False},
                    {"id": "about", "label": "About", "url": "/about", "kind": "link", "enabled": True, "new_tab": False},
                ],
            },
            "product_menu": {
                "heading": "Shop",
                "show_new_arrivals": True,
                "new_arrivals_label": "New Arrival",
                "new_arrivals_url": "/shop?sort=new",
                "show_all_products": True,
                "all_products_label": "All Products",
                "all_products_url": "/shop",
                "show_categories": True,
                "category_mode": "automatic",
                "category_limit": 12,
                "selected_category_ids": [],
            },
            "footer": {
                "kicker": "Official Online Store",
                "seal": "Curated Fashion / Vietnam",
                "brand_name": "GUAMAISON",
                "description": "GUAMAISON mang đến những thiết kế thời trang chọn lọc, tối giản và hiện đại, dành cho phong cách sống tinh tế mỗi ngày.",
                "newsletter_enabled": True,
                "newsletter_placeholder": "Địa chỉ email",
                "newsletter_button_label": "Đăng ký",
                "columns": [
                    {
                        "id": "column-1",
                        "title": "Mua sắm",
                        "links": [
                            {"id": "shopping-products", "label": "Sản phẩm", "url": "/shop", "new_tab": False},
                            {"id": "shopping-new", "label": "Hàng mới", "url": "/shop?sort=new", "new_tab": False},
                            {"id": "shopping-collections", "label": "Bộ sưu tập", "url": "/collections", "new_tab": False},
                            {"id": "shopping-favorites", "label": "Yêu thích", "url": "/profile/favorites", "new_tab": False},
                        ],
                    },
                    {
                        "id": "column-2",
                        "title": "Hỗ trợ",
                        "links": [
                            {"id": "support-contact", "label": "Liên hệ", "url": "/contact", "new_tab": False},
                            {"id": "support-shipping", "label": "Vận chuyển", "url": "#", "new_tab": False},
                            {"id": "support-returns", "label": "Đổi trả", "url": "#", "new_tab": False},
                            {"id": "support-privacy", "label": "Bảo mật", "url": "#", "new_tab": False},
                        ],
                    },
                ],
                "contact_title": "Thông tin",
                "contact_text": "GUAMAISON\nOfficial Online Store\nVietnam",
                "contact_email": "support@guamaison.vn",
                "socials": {
                    "instagram": "#",
                    "facebook": "#",
                    "tiktok": "#",
                    "youtube": "#",
                    "pinterest": "#",
                },
                "copyright": "© 2026 GUAMAISON. All Rights Reserved.",
                "bottom_links": [
                    {"id": "terms", "label": "Terms", "url": "#", "new_tab": False},
                    {"id": "privacy", "label": "Privacy", "url": "#", "new_tab": False},
                    {"id": "cookies", "label": "Cookies", "url": "#", "new_tab": False},
                ],
            },
        },
    }

    # Danh sách section hợp lệ — chặn đứng mã độc phá hoại payload cấu trúc bảng
    VALID_SECTIONS: list = [
        "general",
        "storefront",
        "integrations",
        "shipping_rules",
        "language",
        "admin_ui",
        "size_charts",
        "navigation",
    ]

    # ═══════════════════════════════════════════════════════════════
    #  A. ĐỌC CẤU HÌNH (READ - TẬN DỤNG CACHE NỘI BỘ TRÁNH LỆ TRANG)
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    def get_settings(cls, force_reload: bool = False) -> dict:
        """
        Trả về toàn bộ cấu hình hệ thống (Có tích hợp an toàn Thread-safe).
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

        # Cache miss hoặc force_reload → thực hiện quét trực tiếp dữ liệu từ DB
        logger.debug(
            "[SettingModel] Cache MISS%s — đang tiến hành đọc cấu hình DB...",
            " (force_reload)" if force_reload else "",
        )
        settings = cls._fetch_from_db()

        # Cập nhật bộ đệm cache RAM (thread-safe)
        with cls._lock:
            cls._cache = settings
            cls._cache_ts = time.monotonic()

        return copy.deepcopy(settings)

    @classmethod
    def get_section(cls, section_name: str) -> dict:
        """
        Trích xuất nhanh một section cấu hình cụ thể.
        """
        settings = cls.get_settings()
        return settings.get(section_name) or copy.deepcopy(
            cls.DEFAULT_SETTINGS.get(section_name, {})
        )

    @classmethod
    def invalidate_cache(cls) -> None:
        """
        Xóa cache thủ công trên RAM để giải phóng phiên làm việc.
        """
        with cls._lock:
            cls._cache = {}
            cls._cache_ts = 0.0
        logger.debug("[SettingModel] Cache bộ đệm cấu hình đã xóa dọn sạch.")

    # ═══════════════════════════════════════════════════════════════
    #  B. GHI CẤU HÌNH (WRITE - ÉP DÙNG ADMIN CLIENT BYPASS RLS)
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    def update_section(cls, section_name: str, new_data: dict) -> bool:
        """
        Cập nhật một section cấu hình vào DB (Sử dụng Admin Client để bảo toàn luồng ghi).
        """
        if section_name not in cls.VALID_SECTIONS:
            logger.warning(
                "[SettingModel] Từ chối thực thi: section '%s' không hợp lệ.", section_name
            )
            return False

        try:
            # ✅ ĐÃ SỬA: Lazy Initialization chuyển hẳn sang admin client để tránh lỗi chặn RLS dữ liệu rác
            db = get_supabase_admin()

            # Deep merge: Giữ nguyên các giá trị cấu hình cũ không nằm trong diện chỉnh sửa lần này
            current_section = cls.get_section(section_name)
            merged_data = {**current_section, **new_data}

            db.table("store_settings").upsert(
                {"setting_key": section_name, "setting_value": merged_data}
            ).execute()

            # Giải phóng RAM lập tức để nạp ngay cấu hình tươi ngoài trang bán hàng công khai
            cls.invalidate_cache()

            logger.info("[SettingModel] Đã cập nhật thành công section cấu hình '%s'.", section_name)
            return True

        except Exception as e:
            logger.error(
                "[SettingModel] Ghi đè cập nhật section '%s' thất bại. Lỗi hệ thống: %s",
                section_name,
                e,
            )
            return False

    # ═══════════════════════════════════════════════════════════════
    #  C. INTERNAL HELPERS (MÁY QUÉT NỘI BỘ)
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    def _fetch_from_db(cls) -> dict:
        """
        Đọc thông tin từ bảng store_settings.
        Sử dụng public client kết hợp self-healing an toàn.
        """
        try:
            # Khởi tạo lười khi hàm được triệu gọi thực tế ngoài controller
            db = get_supabase()
            res = db.table("store_settings").select("*").execute()

            # Khởi hành luồng deep copy từ cấu trúc defaults
            settings: dict = copy.deepcopy(cls.DEFAULT_SETTINGS)

            if res.data:
                for row in res.data:
                    key = row.get("setting_key")
                    val = row.get("setting_value")
                    if key in settings and isinstance(val, dict):
                        settings[key].update(val)
            else:
                logger.warning(
                    "[SettingModel] Bảng store_settings đang bị trống — Kích hoạt khôi phục dữ liệu nền..."
                )
                cls._initialize_defaults()

            return settings

        except Exception as e:
            logger.error(
                "[SettingModel] Mất kết nối DB hoặc bị nghẽn mạng Vercel — Dùng cấu hình mặc định. Lỗi: %s", e
            )
            return copy.deepcopy(cls.DEFAULT_SETTINGS)

    @classmethod
    def _initialize_defaults(cls) -> None:
        """
        Self-Healing: Đẩy đồng bộ cấu trúc DEFAULT_SETTINGS vào Supabase (Dùng Admin Client).
        """
        try:
            # ✅ ĐÃ SỬA: Khởi tạo lười qua admin client để bypass RLS khi thực hiện chèn dữ liệu nền tự động
            db = get_supabase_admin()
            upsert_data = [
                {"setting_key": key, "setting_value": value}
                for key, value in cls.DEFAULT_SETTINGS.items()
            ]
            db.table("store_settings").upsert(upsert_data).execute()
            logger.info("[SettingModel] Khởi tạo dữ liệu khôi phục nền Self-Healing thành công.")
        except Exception as e:
            logger.error(
                "[SettingModel] Luồng xử lý khôi phục tự động Self-Healing thất bại. Lỗi: %s", e
            )