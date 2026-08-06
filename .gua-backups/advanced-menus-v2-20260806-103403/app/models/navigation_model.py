"""
Quản lý cấu hình menu giao diện (navbar, mega menu sản phẩm và footer).

Dữ liệu được lưu trong ``store_settings`` với ``setting_key = navigation``.
Model này chịu trách nhiệm chuẩn hóa toàn bộ payload trước khi ghi để template
không phải tin tưởng dữ liệu JSON do trình duyệt gửi lên.
"""

from __future__ import annotations

import copy
import re
from typing import Any
from urllib.parse import urlparse

from app.models.setting_model import SettingModel


class NavigationModel:
    MAX_NAV_ITEMS = 12
    MAX_FOOTER_LINKS = 12
    MAX_BOTTOM_LINKS = 6
    MAX_SELECTED_CATEGORIES = 48

    ALLOWED_KINDS = {"link", "products", "collections"}
    ALLOWED_SOCIALS = {"instagram", "facebook", "tiktok", "youtube", "pinterest"}

    @staticmethod
    def _text(value: Any, default: str = "", max_length: int = 160) -> str:
        text = str(value if value is not None else default)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text).strip()
        return text[:max_length]

    @staticmethod
    def _bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _int(value: Any, default: int, minimum: int, maximum: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = default
        return max(minimum, min(maximum, number))

    @classmethod
    def _identifier(cls, value: Any, fallback: str) -> str:
        identifier = cls._text(value, fallback, 80).lower()
        identifier = re.sub(r"[^a-z0-9_-]+", "-", identifier).strip("-")
        return identifier or fallback

    @classmethod
    def _url(cls, value: Any, default: str = "#") -> str:
        """Chỉ cho phép URL tương đối, anchor, http(s), mailto và tel."""
        url = cls._text(value, default, 500)
        if not url:
            return default

        lowered = url.lower().replace("\n", "").replace("\r", "")
        if lowered.startswith(("javascript:", "data:", "vbscript:")):
            return default

        if url.startswith(("/", "#", "?")):
            return url

        parsed = urlparse(url)
        if parsed.scheme.lower() in {"http", "https", "mailto", "tel"}:
            return url

        return default

    @classmethod
    def _normalize_link(cls, raw: Any, fallback_id: str) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None

        label = cls._text(raw.get("label"), "", 80)
        if not label:
            return None

        return {
            "id": cls._identifier(raw.get("id"), fallback_id),
            "label": label,
            "url": cls._url(raw.get("url"), "#"),
            "new_tab": cls._bool(raw.get("new_tab"), False),
        }

    @classmethod
    def _normalize_navbar(cls, raw: Any, defaults: dict[str, Any]) -> dict[str, Any]:
        source = raw if isinstance(raw, dict) else {}
        items_source = source.get("items")
        if not isinstance(items_source, list):
            items_source = defaults.get("items", [])

        items: list[dict[str, Any]] = []
        used_ids: set[str] = set()
        used_special_kinds: set[str] = set()

        for index, item in enumerate(items_source[: cls.MAX_NAV_ITEMS]):
            if not isinstance(item, dict):
                continue

            label = cls._text(item.get("label"), "", 80)
            if not label:
                continue

            kind = cls._text(item.get("kind"), "link", 24).lower()
            if kind not in cls.ALLOWED_KINDS:
                kind = "link"

            # Chỉ một mega menu sản phẩm và một mega menu bộ sưu tập.
            if kind in {"products", "collections"}:
                if kind in used_special_kinds:
                    kind = "link"
                else:
                    used_special_kinds.add(kind)

            fallback_id = f"nav-{index + 1}"
            item_id = cls._identifier(item.get("id"), fallback_id)
            while item_id in used_ids:
                item_id = f"{item_id}-{index + 1}"
            used_ids.add(item_id)

            default_url = "/shop" if kind == "products" else "/collections" if kind == "collections" else "#"
            items.append({
                "id": item_id,
                "label": label,
                "url": cls._url(item.get("url"), default_url),
                "kind": kind,
                "enabled": cls._bool(item.get("enabled"), True),
                "new_tab": cls._bool(item.get("new_tab"), False),
            })

        return {
            "brand_label": cls._text(
                source.get("brand_label"), defaults.get("brand_label", "GUAMAISON"), 80
            ),
            "transparent_home": cls._bool(
                source.get("transparent_home"), defaults.get("transparent_home", True)
            ),
            "items": items,
        }

    @classmethod
    def _normalize_product_menu(cls, raw: Any, defaults: dict[str, Any]) -> dict[str, Any]:
        source = raw if isinstance(raw, dict) else {}
        category_mode = cls._text(source.get("category_mode"), "automatic", 20).lower()
        if category_mode not in {"automatic", "selected"}:
            category_mode = "automatic"

        selected_ids: list[str] = []
        raw_ids = source.get("selected_category_ids")
        if isinstance(raw_ids, list):
            for value in raw_ids[: cls.MAX_SELECTED_CATEGORIES]:
                item_id = cls._text(value, "", 80)
                if item_id and item_id not in selected_ids:
                    selected_ids.append(item_id)

        return {
            "heading": cls._text(source.get("heading"), defaults.get("heading", "Shop"), 80),
            "show_new_arrivals": cls._bool(
                source.get("show_new_arrivals"), defaults.get("show_new_arrivals", True)
            ),
            "new_arrivals_label": cls._text(
                source.get("new_arrivals_label"), defaults.get("new_arrivals_label", "New Arrival"), 80
            ),
            "new_arrivals_url": cls._url(
                source.get("new_arrivals_url"), defaults.get("new_arrivals_url", "/shop?sort=new")
            ),
            "show_all_products": cls._bool(
                source.get("show_all_products"), defaults.get("show_all_products", True)
            ),
            "all_products_label": cls._text(
                source.get("all_products_label"), defaults.get("all_products_label", "All Products"), 80
            ),
            "all_products_url": cls._url(
                source.get("all_products_url"), defaults.get("all_products_url", "/shop")
            ),
            "show_categories": cls._bool(
                source.get("show_categories"), defaults.get("show_categories", True)
            ),
            "category_mode": category_mode,
            "category_limit": cls._int(source.get("category_limit"), 12, 1, 24),
            "selected_category_ids": selected_ids,
        }

    @classmethod
    def _normalize_footer_column(
        cls, raw: Any, default: dict[str, Any], column_index: int
    ) -> dict[str, Any]:
        source = raw if isinstance(raw, dict) else default
        links_source = source.get("links") if isinstance(source.get("links"), list) else default.get("links", [])
        links: list[dict[str, Any]] = []

        for index, raw_link in enumerate(links_source[: cls.MAX_FOOTER_LINKS]):
            link = cls._normalize_link(raw_link, f"footer-{column_index + 1}-{index + 1}")
            if link:
                links.append(link)

        return {
            "id": f"column-{column_index + 1}",
            "title": cls._text(source.get("title"), default.get("title", "Menu"), 80),
            "links": links,
        }

    @classmethod
    def _normalize_footer(cls, raw: Any, defaults: dict[str, Any]) -> dict[str, Any]:
        source = raw if isinstance(raw, dict) else {}
        columns_source = source.get("columns") if isinstance(source.get("columns"), list) else []
        default_columns = defaults.get("columns", [])
        columns: list[dict[str, Any]] = []

        # Giao diện footer hiện có hai cột link để giữ bố cục bốn cột cân đối.
        for index in range(2):
            default_column = default_columns[index] if index < len(default_columns) else {"title": "Menu", "links": []}
            raw_column = columns_source[index] if index < len(columns_source) else default_column
            columns.append(cls._normalize_footer_column(raw_column, default_column, index))

        bottom_source = source.get("bottom_links")
        if not isinstance(bottom_source, list):
            bottom_source = defaults.get("bottom_links", [])
        bottom_links: list[dict[str, Any]] = []
        for index, raw_link in enumerate(bottom_source[: cls.MAX_BOTTOM_LINKS]):
            link = cls._normalize_link(raw_link, f"bottom-{index + 1}")
            if link:
                bottom_links.append(link)

        socials_source = source.get("socials") if isinstance(source.get("socials"), dict) else {}
        default_socials = defaults.get("socials", {})
        socials = {
            platform: cls._url(socials_source.get(platform), default_socials.get(platform, "#"))
            for platform in cls.ALLOWED_SOCIALS
        }

        return {
            "kicker": cls._text(source.get("kicker"), defaults.get("kicker", "Official Online Store"), 100),
            "seal": cls._text(source.get("seal"), defaults.get("seal", "Curated Fashion / Vietnam"), 120),
            "brand_name": cls._text(source.get("brand_name"), defaults.get("brand_name", "GUAMAISON"), 80),
            "description": cls._text(source.get("description"), defaults.get("description", ""), 600),
            "newsletter_enabled": cls._bool(
                source.get("newsletter_enabled"), defaults.get("newsletter_enabled", True)
            ),
            "newsletter_placeholder": cls._text(
                source.get("newsletter_placeholder"), defaults.get("newsletter_placeholder", "Địa chỉ email"), 100
            ),
            "newsletter_button_label": cls._text(
                source.get("newsletter_button_label"), defaults.get("newsletter_button_label", "Đăng ký"), 60
            ),
            "columns": columns,
            "contact_title": cls._text(source.get("contact_title"), defaults.get("contact_title", "Thông tin"), 80),
            "contact_text": cls._text(source.get("contact_text"), defaults.get("contact_text", ""), 400),
            "contact_email": cls._text(source.get("contact_email"), defaults.get("contact_email", ""), 160),
            "socials": socials,
            "copyright": cls._text(source.get("copyright"), defaults.get("copyright", ""), 180),
            "bottom_links": bottom_links,
        }

    @classmethod
    def normalize_config(cls, raw: Any) -> dict[str, Any]:
        defaults = copy.deepcopy(SettingModel.DEFAULT_SETTINGS["navigation"])
        source = raw if isinstance(raw, dict) else {}

        return {
            "navbar": cls._normalize_navbar(source.get("navbar"), defaults["navbar"]),
            "product_menu": cls._normalize_product_menu(
                source.get("product_menu"), defaults["product_menu"]
            ),
            "footer": cls._normalize_footer(source.get("footer"), defaults["footer"]),
        }

    @classmethod
    def get_config(cls, force_reload: bool = False) -> dict[str, Any]:
        settings = SettingModel.get_settings(force_reload=force_reload)
        return cls.normalize_config(settings.get("navigation"))

    @classmethod
    def save_config(cls, raw: Any) -> tuple[bool, dict[str, Any]]:
        normalized = cls.normalize_config(raw)
        return SettingModel.update_section("navigation", normalized), normalized

    @classmethod
    def select_product_categories(
        cls, config: dict[str, Any], categories: Any
    ) -> list[dict[str, Any]]:
        """Lọc và giới hạn danh mục hiển thị trong mega menu sản phẩm."""
        if not isinstance(categories, list):
            return []

        product_menu = (config or {}).get("product_menu") or {}
        if not product_menu.get("show_categories", True):
            return []

        selected_ids = {str(item) for item in product_menu.get("selected_category_ids", [])}
        selected_mode = product_menu.get("category_mode") == "selected" and bool(selected_ids)

        output: list[dict[str, Any]] = []
        for category in categories:
            if not isinstance(category, dict) or not category.get("is_active", True):
                continue
            if selected_mode and str(category.get("id")) not in selected_ids:
                continue
            output.append(category)

        limit = cls._int(product_menu.get("category_limit"), 12, 1, 24)
        return output[:limit]
