"""Mô hình menu storefront kiểu Haravan, lưu bằng JSONB trong store_settings."""

from __future__ import annotations

import copy
import re
import threading
import time
from typing import Any
from urllib.parse import urlparse

from app.models.setting_model import SettingModel
from app.utils.supabase_client import get_supabase_admin


class NavigationModel:
    SCHEMA_VERSION = 3
    MAX_MENUS = 30
    MAX_ITEMS_PER_MENU = 120
    MAX_DEPTH = 3
    MAX_SELECTED_CATEGORIES = 48
    MAX_FOOTER_LINKS = 12
    MAX_BOTTOM_LINKS = 6

    ALLOWED_KINDS = {"link", "products", "collections", "mega"}
    ALLOWED_LINK_TYPES = {
        "url", "home", "page", "product", "category", "collection", "search", "none"
    }
    ALLOWED_SOCIALS = {"instagram", "facebook", "tiktok", "youtube", "pinterest"}
    _target_cache: dict[Any, Any] = {}
    _target_cache_lock = threading.Lock()
    _target_cache_ttl = 30

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
        identifier = cls._text(value, fallback, 100).lower()
        identifier = re.sub(r"[^a-z0-9_-]+", "-", identifier).strip("-")
        return identifier or fallback

    @classmethod
    def _url(cls, value: Any, default: str = "#") -> str:
        url = cls._text(value, default, 500)
        if not url:
            return default
        lowered = url.lower().replace("\n", "").replace("\r", "")
        if lowered.startswith(("javascript:", "data:", "vbscript:")):
            return default
        if url.startswith(("/", "#", "?")):
            return url
        parsed = urlparse(url)
        return url if parsed.scheme.lower() in {"http", "https", "mailto", "tel"} else default

    @classmethod
    def _normalize_menu_item(
        cls,
        raw: Any,
        fallback_id: str,
        depth: int,
        state: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not isinstance(raw, dict) or depth > cls.MAX_DEPTH:
            return None
        if state["count"] >= cls.MAX_ITEMS_PER_MENU:
            return None

        label = cls._text(raw.get("label"), "", 100)
        if not label:
            return None

        item_id = cls._identifier(raw.get("id"), fallback_id)
        base_id = item_id
        suffix = 2
        while item_id in state["ids"]:
            item_id = f"{base_id}-{suffix}"
            suffix += 1
        state["ids"].add(item_id)
        state["count"] += 1

        link_type = cls._text(raw.get("link_type"), "url", 24).lower()
        if link_type not in cls.ALLOWED_LINK_TYPES:
            link_type = "url"

        kind = cls._text(raw.get("kind"), "link", 24).lower()
        if kind not in cls.ALLOWED_KINDS:
            kind = "link"

        children: list[dict[str, Any]] = []
        source_children = raw.get("children")
        if isinstance(source_children, list) and depth < cls.MAX_DEPTH:
            for index, child in enumerate(source_children):
                normalized = cls._normalize_menu_item(
                    child, f"{item_id}-{index + 1}", depth + 1, state
                )
                if normalized:
                    children.append(normalized)

        return {
            "id": item_id,
            "label": label,
            "link_type": link_type,
            "target_id": cls._text(raw.get("target_id"), "", 100),
            "url": cls._url(raw.get("url"), "#"),
            "kind": kind,
            "enabled": cls._bool(raw.get("enabled"), True),
            "new_tab": cls._bool(raw.get("new_tab"), False),
            "children": children,
        }

    @classmethod
    def _normalize_menu(cls, raw: Any, index: int, used_handles: set[str]) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None
        title = cls._text(raw.get("title"), "", 100)
        if not title:
            return None

        handle = cls._identifier(raw.get("handle"), f"menu-{index + 1}")
        base = handle
        suffix = 2
        while handle in used_handles:
            handle = f"{base}-{suffix}"
            suffix += 1
        used_handles.add(handle)

        state: dict[str, Any] = {"count": 0, "ids": set()}
        items: list[dict[str, Any]] = []
        raw_items = raw.get("items")
        if isinstance(raw_items, list):
            for item_index, item in enumerate(raw_items):
                normalized = cls._normalize_menu_item(
                    item, f"{handle}-{item_index + 1}", 1, state
                )
                if normalized:
                    items.append(normalized)

        return {
            "id": cls._identifier(raw.get("id"), handle),
            "title": title,
            "handle": handle,
            "items": items,
        }

    @classmethod
    def _legacy_library(cls, source: dict[str, Any], defaults: dict[str, Any]) -> list[dict[str, Any]]:
        navbar = source.get("navbar") if isinstance(source.get("navbar"), dict) else defaults["navbar"]
        footer = source.get("footer") if isinstance(source.get("footer"), dict) else defaults["footer"]
        columns = footer.get("columns") if isinstance(footer.get("columns"), list) else []

        menus: list[dict[str, Any]] = [{
            "id": "main-menu",
            "title": "Menu chính",
            "handle": "main-menu",
            "items": copy.deepcopy(navbar.get("items") or []),
        }]
        for index in range(2):
            column = columns[index] if index < len(columns) and isinstance(columns[index], dict) else {}
            menus.append({
                "id": f"footer-{index + 1}",
                "title": cls._text(column.get("title"), f"Footer {index + 1}", 100),
                "handle": f"footer-{index + 1}",
                "items": copy.deepcopy(column.get("links") or []),
            })
        return menus

    @classmethod
    def _normalize_menus(cls, source: dict[str, Any], defaults: dict[str, Any]) -> list[dict[str, Any]]:
        raw_menus = source.get("menus")
        if not isinstance(raw_menus, list) or not raw_menus:
            raw_menus = cls._legacy_library(source, defaults)

        menus: list[dict[str, Any]] = []
        used_handles: set[str] = set()
        for index, raw_menu in enumerate(raw_menus[: cls.MAX_MENUS]):
            menu = cls._normalize_menu(raw_menu, index, used_handles)
            if menu:
                menus.append(menu)

        if not menus:
            menus = cls._normalize_menus({}, defaults)
        return menus

    @classmethod
    def _normalize_placements(cls, raw: Any, menus: list[dict[str, Any]]) -> dict[str, str]:
        source = raw if isinstance(raw, dict) else {}
        handles = {menu["handle"] for menu in menus}
        first = menus[0]["handle"]
        footer_handles = [menu["handle"] for menu in menus[1:3]]
        while len(footer_handles) < 2:
            footer_handles.append(first)

        def pick(key: str, fallback: str) -> str:
            value = cls._identifier(source.get(key), fallback)
            return value if value in handles else fallback

        return {
            "navbar": pick("navbar", first),
            "product_mega": pick("product_mega", first),
            "footer_1": pick("footer_1", footer_handles[0]),
            "footer_2": pick("footer_2", footer_handles[1]),
        }

    @classmethod
    def _normalize_navbar(cls, raw: Any, defaults: dict[str, Any]) -> dict[str, Any]:
        source = raw if isinstance(raw, dict) else {}
        return {
            "brand_label": cls._text(source.get("brand_label"), defaults.get("brand_label", "GUAMAISON"), 80),
            "transparent_home": cls._bool(source.get("transparent_home"), defaults.get("transparent_home", True)),
            "items": [],
        }

    @classmethod
    def _normalize_product_menu(cls, raw: Any, defaults: dict[str, Any]) -> dict[str, Any]:
        source = raw if isinstance(raw, dict) else {}
        mode = cls._text(source.get("category_mode"), "automatic", 20).lower()
        if mode not in {"automatic", "selected"}:
            mode = "automatic"
        selected: list[str] = []
        for value in source.get("selected_category_ids") or []:
            value = cls._text(value, "", 80)
            if value and value not in selected:
                selected.append(value)
            if len(selected) >= cls.MAX_SELECTED_CATEGORIES:
                break
        return {
            "heading": cls._text(source.get("heading"), defaults.get("heading", "Shop"), 80),
            "show_new_arrivals": cls._bool(source.get("show_new_arrivals"), defaults.get("show_new_arrivals", True)),
            "new_arrivals_label": cls._text(source.get("new_arrivals_label"), defaults.get("new_arrivals_label", "New Arrival"), 80),
            "new_arrivals_url": cls._url(source.get("new_arrivals_url"), defaults.get("new_arrivals_url", "/shop?sort=new")),
            "show_all_products": cls._bool(source.get("show_all_products"), defaults.get("show_all_products", True)),
            "all_products_label": cls._text(source.get("all_products_label"), defaults.get("all_products_label", "All Products"), 80),
            "all_products_url": cls._url(source.get("all_products_url"), defaults.get("all_products_url", "/shop")),
            "show_categories": cls._bool(source.get("show_categories"), defaults.get("show_categories", True)),
            "category_mode": mode,
            "category_limit": cls._int(source.get("category_limit"), 12, 1, 24),
            "selected_category_ids": selected,
        }

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
    def _normalize_footer(cls, raw: Any, defaults: dict[str, Any]) -> dict[str, Any]:
        source = raw if isinstance(raw, dict) else {}
        socials_source = source.get("socials") if isinstance(source.get("socials"), dict) else {}
        default_socials = defaults.get("socials", {})
        bottom_links: list[dict[str, Any]] = []
        raw_bottom = source.get("bottom_links") if isinstance(source.get("bottom_links"), list) else defaults.get("bottom_links", [])
        for index, raw_link in enumerate(raw_bottom[: cls.MAX_BOTTOM_LINKS]):
            link = cls._normalize_link(raw_link, f"bottom-{index + 1}")
            if link:
                bottom_links.append(link)
        return {
            "kicker": cls._text(source.get("kicker"), defaults.get("kicker", "Official Online Store"), 100),
            "seal": cls._text(source.get("seal"), defaults.get("seal", "Curated Fashion / Vietnam"), 120),
            "brand_name": cls._text(source.get("brand_name"), defaults.get("brand_name", "GUAMAISON"), 80),
            "description": cls._text(source.get("description"), defaults.get("description", ""), 600),
            "newsletter_enabled": cls._bool(source.get("newsletter_enabled"), defaults.get("newsletter_enabled", True)),
            "newsletter_placeholder": cls._text(source.get("newsletter_placeholder"), defaults.get("newsletter_placeholder", "Địa chỉ email"), 100),
            "newsletter_button_label": cls._text(source.get("newsletter_button_label"), defaults.get("newsletter_button_label", "Đăng ký"), 60),
            "columns": [],
            "contact_title": cls._text(source.get("contact_title"), defaults.get("contact_title", "Thông tin"), 80),
            "contact_text": cls._text(source.get("contact_text"), defaults.get("contact_text", ""), 400),
            "contact_email": cls._text(source.get("contact_email"), defaults.get("contact_email", ""), 160),
            "socials": {platform: cls._url(socials_source.get(platform), default_socials.get(platform, "#")) for platform in cls.ALLOWED_SOCIALS},
            "copyright": cls._text(source.get("copyright"), defaults.get("copyright", ""), 180),
            "bottom_links": bottom_links,
        }

    @classmethod
    def _walk_items(cls, items: Any):
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            yield item
            yield from cls._walk_items(item.get("children"))

    @classmethod
    def _load_target_catalog(cls, config: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
        wanted: dict[str, set[str]] = {"product": set(), "category": set(), "collection": set()}
        for menu in config.get("menus") or []:
            for item in cls._walk_items(menu.get("items")):
                link_type = item.get("link_type")
                target_id = cls._text(item.get("target_id"), "", 100)
                if link_type in wanted and target_id:
                    wanted[link_type].add(target_id)

        signature = tuple((kind, tuple(sorted(ids))) for kind, ids in wanted.items())
        now = time.monotonic()
        with cls._target_cache_lock:
            cached = cls._target_cache.get(signature)
            if cached and cached[0] > now:
                return copy.deepcopy(cached[1])

        catalog: dict[str, dict[str, dict[str, Any]]] = {
            "product": {}, "category": {}, "collection": {},
        }
        table_map = {
            "product": "products",
            "category": "categories",
            "collection": "collections",
        }
        select_map = {
            "product": "id,name,slug,is_active,deleted_at",
            "category": "id,name,slug,is_active",
            "collection": "id,name,slug,is_active",
        }
        try:
            db = get_supabase_admin()
            for kind, ids in wanted.items():
                if not ids:
                    continue
                rows = (
                    db.table(table_map[kind]).select(select_map[kind])
                    .in_("id", list(ids)).execute().data or []
                )
                catalog[kind] = {
                    str(row.get("id")): row
                    for row in rows
                    if row.get("id") and row.get("slug") and not row.get("deleted_at")
                }
        except Exception:
            # Khi DB tạm lỗi, giữ URL dự phòng đã lưu thay vì làm hỏng toàn bộ navbar.
            return catalog

        with cls._target_cache_lock:
            if len(cls._target_cache) > 32:
                cls._target_cache.clear()
            cls._target_cache[signature] = (now + cls._target_cache_ttl, copy.deepcopy(catalog))
        return catalog

    @classmethod
    def _resolve_target_urls(cls, config: dict[str, Any]) -> dict[str, Any]:
        catalog = cls._load_target_catalog(config)
        for menu in config.get("menus") or []:
            for item in cls._walk_items(menu.get("items")):
                kind = item.get("link_type")
                target_id = str(item.get("target_id") or "")
                if kind not in catalog or not target_id:
                    item["target_missing"] = False
                    continue

                target = catalog[kind].get(target_id)
                if not target:
                    item["target_missing"] = True
                    continue

                slug = cls._identifier(target.get("slug"), "")
                if not slug:
                    item["target_missing"] = True
                    continue

                if kind == "product":
                    item["url"] = f"/product/{slug}"
                elif kind == "category":
                    item["url"] = f"/shop?category={slug}"
                else:
                    item["url"] = f"/collections/{slug}"
                item["target_missing"] = False
                item["target_inactive"] = target.get("is_active") is False
                item["target_label"] = cls._text(target.get("name"), item.get("label", ""), 100)
        return config

    @classmethod
    def _materialize(cls, config: dict[str, Any]) -> dict[str, Any]:
        menu_map = {menu["handle"]: menu for menu in config["menus"]}
        placements = config["placements"]
        main_menu = menu_map.get(placements["navbar"], config["menus"][0])
        config["navbar"]["items"] = copy.deepcopy(main_menu.get("items") or [])
        product_mega = menu_map.get(placements.get("product_mega", ""))
        if product_mega and product_mega.get("handle") != main_menu.get("handle"):
            for item in config["navbar"]["items"]:
                if item.get("kind") == "products" and product_mega.get("items"):
                    item["children"] = copy.deepcopy(product_mega["items"])
                    item["kind"] = "mega"

        columns = []
        for index, key in enumerate(("footer_1", "footer_2"), 1):
            menu = menu_map.get(placements[key], config["menus"][0])
            links = []
            for item in (menu.get("items") or [])[: cls.MAX_FOOTER_LINKS]:
                if item.get("enabled", True):
                    links.append({
                        "id": item["id"], "label": item["label"], "url": item["url"],
                        "new_tab": item.get("new_tab", False),
                    })
            columns.append({"id": f"column-{index}", "title": menu["title"], "links": links})
        config["footer"]["columns"] = columns
        return config

    @classmethod
    def normalize_config(cls, raw: Any) -> dict[str, Any]:
        defaults = copy.deepcopy(SettingModel.DEFAULT_SETTINGS["navigation"])
        source = raw if isinstance(raw, dict) else {}
        menus = cls._normalize_menus(source, defaults)
        config = {
            "schema_version": cls.SCHEMA_VERSION,
            "menus": menus,
            "placements": cls._normalize_placements(source.get("placements"), menus),
            "navbar": cls._normalize_navbar(source.get("navbar"), defaults["navbar"]),
            "product_menu": cls._normalize_product_menu(source.get("product_menu"), defaults["product_menu"]),
            "footer": cls._normalize_footer(source.get("footer"), defaults["footer"]),
        }
        return cls._materialize(cls._resolve_target_urls(config))

    @classmethod
    def get_config(cls, force_reload: bool = False) -> dict[str, Any]:
        settings = SettingModel.get_settings(force_reload=force_reload)
        return cls.normalize_config(settings.get("navigation"))

    @classmethod
    def save_config(cls, raw: Any) -> tuple[bool, dict[str, Any]]:
        normalized = cls.normalize_config(raw)
        success = SettingModel.update_section("navigation", normalized)
        if success:
            with cls._target_cache_lock:
                cls._target_cache.clear()
        return success, normalized

    @classmethod
    def find_target_usage(
        cls,
        config: dict[str, Any],
        link_type: str,
        target_id: str,
    ) -> list[dict[str, str]]:
        usage: list[dict[str, str]] = []
        target_id = str(target_id or "")
        if not target_id:
            return usage
        for menu in config.get("menus") or []:
            for item in cls._walk_items(menu.get("items")):
                if item.get("link_type") == link_type and str(item.get("target_id") or "") == target_id:
                    usage.append({
                        "menu_title": cls._text(menu.get("title"), "Menu", 100),
                        "menu_handle": cls._text(menu.get("handle"), "", 100),
                        "item_label": cls._text(item.get("label"), "", 100),
                    })
        return usage

    @classmethod
    def upsert_target_link(
        cls,
        *,
        menu_handle: str,
        link_type: str,
        target_id: str,
        label: str,
        parent_id: str = "",
    ) -> bool:
        if link_type not in {"product", "category", "collection"}:
            return False
        config = cls.get_config(force_reload=True)
        menu = next(
            (item for item in config.get("menus") or [] if item.get("handle") == menu_handle),
            None,
        )
        if not menu or not target_id:
            return False

        for item in cls._walk_items(menu.get("items")):
            if item.get("link_type") == link_type and str(item.get("target_id") or "") == str(target_id):
                item["label"] = cls._text(label, item.get("label", "Liên kết"), 100)
                item["enabled"] = True
                return cls.save_config(config)[0]

        new_item = {
            "id": cls._identifier(f"{link_type}-{target_id}", f"{link_type}-link"),
            "label": cls._text(label, "Liên kết", 100),
            "link_type": link_type,
            "target_id": cls._text(target_id, "", 100),
            "url": "#",
            "kind": "link",
            "enabled": True,
            "new_tab": False,
            "children": [],
        }
        container = menu.setdefault("items", [])
        if parent_id:
            for item in cls._walk_items(menu.get("items")):
                if item.get("id") == parent_id:
                    item.setdefault("children", []).append(new_item)
                    break
            else:
                container.append(new_item)
        else:
            container.append(new_item)
        return cls.save_config(config)[0]

    @classmethod
    def remove_target_links(cls, link_type: str, target_id: str) -> bool:
        """Dọn liên kết đích đã xóa và đưa menu con của nó lên cùng cấp."""
        config = cls.get_config(force_reload=True)
        target_id = str(target_id or "")
        changed = False

        def prune(items: Any) -> list[dict[str, Any]]:
            nonlocal changed
            output: list[dict[str, Any]] = []
            for item in items if isinstance(items, list) else []:
                children = prune(item.get("children"))
                if item.get("link_type") == link_type and str(item.get("target_id") or "") == target_id:
                    output.extend(children)
                    changed = True
                    continue
                item["children"] = children
                output.append(item)
            return output

        for menu in config.get("menus") or []:
            menu["items"] = prune(menu.get("items"))
        return cls.save_config(config)[0] if changed else True

    @classmethod
    def select_product_categories(cls, config: dict[str, Any], categories: Any) -> list[dict[str, Any]]:
        if not isinstance(categories, list):
            return []
        product_menu = (config or {}).get("product_menu") or {}
        if not product_menu.get("show_categories", True):
            return []
        selected = {str(item) for item in product_menu.get("selected_category_ids", [])}
        selected_mode = product_menu.get("category_mode") == "selected" and bool(selected)
        output = [category for category in categories if isinstance(category, dict) and category.get("is_active", True) and (not selected_mode or str(category.get("id")) in selected)]
        return output[: cls._int(product_menu.get("category_limit"), 12, 1, 24)]
