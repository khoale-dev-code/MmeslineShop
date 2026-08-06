"""Quy tắc Nhóm sản phẩm kiểu Haravan, không yêu cầu migration database.

Thông tin cơ bản/SEO tiếp tục nằm trong bảng ``collections``. Kiểu chọn sản
phẩm và các điều kiện tự động được lưu trong ``store_settings`` với key
``product_group_rules``. Bảng nối ``collection_products`` vẫn là nguồn dữ
liệu duy nhất cho storefront, vì vậy các trang shop cũ tiếp tục hoạt động.
"""

from __future__ import annotations

import copy
import logging
import re
import threading
import time
from typing import Any

from app.utils.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)


class ProductGroupModel:
    SETTING_KEY = "product_group_rules"
    SCHEMA_VERSION = 1
    MAX_GROUPS = 300
    MAX_RULES = 12
    MAX_PRODUCTS = 20000
    CACHE_TTL = 30

    ALLOWED_FIELDS = {
        "name", "sku", "barcode", "brand", "gender", "tag",
        "price", "stock", "status", "category",
    }
    TEXT_OPERATORS = {
        "equals", "not_equals", "contains", "not_contains",
        "starts_with", "ends_with",
    }
    NUMBER_OPERATORS = {"equals", "not_equals", "gt", "gte", "lt", "lte"}
    ALLOWED_TEMPLATES = {"collection", "collection-grid", "collection-lookbook"}

    _cache: dict[str, Any] = {}
    _cache_at = 0.0
    _lock = threading.Lock()

    @staticmethod
    def _db():
        return get_supabase_admin()

    @staticmethod
    def _text(value: Any, max_length: int = 180) -> str:
        text = str(value or "")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text).strip()
        return text[:max_length]

    @classmethod
    def _normalize_rule(cls, raw: Any) -> dict[str, str] | None:
        if not isinstance(raw, dict):
            return None

        field = cls._text(raw.get("field"), 24).lower()
        if field not in cls.ALLOWED_FIELDS:
            return None

        allowed_operators = cls.NUMBER_OPERATORS if field in {"price", "stock"} else cls.TEXT_OPERATORS
        operator = cls._text(raw.get("operator"), 24).lower()
        if operator not in allowed_operators:
            operator = "equals"

        value = cls._text(raw.get("value"), 180)
        if not value:
            return None

        return {"field": field, "operator": operator, "value": value}

    @classmethod
    def normalize_group(cls, raw: Any) -> dict[str, Any]:
        source = raw if isinstance(raw, dict) else {}
        selection_mode = cls._text(source.get("selection_mode"), 20).lower()
        if selection_mode not in {"manual", "automatic"}:
            selection_mode = "manual"

        match_mode = cls._text(source.get("match_mode"), 12).lower()
        if match_mode not in {"all", "any"}:
            match_mode = "all"

        template = cls._text(source.get("template"), 40).lower()
        if template not in cls.ALLOWED_TEMPLATES:
            template = "collection"

        rules: list[dict[str, str]] = []
        for raw_rule in source.get("rules") or []:
            rule = cls._normalize_rule(raw_rule)
            if rule:
                rules.append(rule)
            if len(rules) >= cls.MAX_RULES:
                break

        return {
            "selection_mode": selection_mode,
            "match_mode": match_mode,
            "rules": rules,
            "template": template,
        }

    @classmethod
    def _normalize_config(cls, raw: Any) -> dict[str, Any]:
        source = raw if isinstance(raw, dict) else {}
        raw_groups = source.get("groups") if isinstance(source.get("groups"), dict) else {}
        groups: dict[str, dict[str, Any]] = {}

        for collection_id, raw_group in list(raw_groups.items())[: cls.MAX_GROUPS]:
            safe_id = cls._text(collection_id, 100)
            if safe_id:
                groups[safe_id] = cls.normalize_group(raw_group)

        return {"schema_version": cls.SCHEMA_VERSION, "groups": groups}

    @classmethod
    def invalidate_cache(cls) -> None:
        with cls._lock:
            cls._cache = {}
            cls._cache_at = 0.0

    @classmethod
    def get_config(cls, force_reload: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        with cls._lock:
            if not force_reload and cls._cache and now - cls._cache_at < cls.CACHE_TTL:
                return copy.deepcopy(cls._cache)

        config: dict[str, Any] = {"schema_version": cls.SCHEMA_VERSION, "groups": {}}
        try:
            result = (
                cls._db().table("store_settings").select("setting_value")
                .eq("setting_key", cls.SETTING_KEY).limit(1).execute()
            )
            if result.data:
                config = cls._normalize_config(result.data[0].get("setting_value"))
        except Exception as exc:
            logger.warning("[ProductGroupModel] Không đọc được quy tắc nhóm: %s", exc)

        with cls._lock:
            cls._cache = copy.deepcopy(config)
            cls._cache_at = time.monotonic()
        return config

    @classmethod
    def _save_config(cls, config: dict[str, Any]) -> bool:
        normalized = cls._normalize_config(config)
        try:
            cls._db().table("store_settings").upsert({
                "setting_key": cls.SETTING_KEY,
                "setting_value": normalized,
            }).execute()
            cls.invalidate_cache()
            return True
        except Exception as exc:
            logger.error("[ProductGroupModel] Không lưu được quy tắc nhóm: %s", exc, exc_info=True)
            return False

    @classmethod
    def get_group(cls, collection_id: Any) -> dict[str, Any]:
        collection_id = cls._text(collection_id, 100)
        return copy.deepcopy(
            cls.get_config().get("groups", {}).get(collection_id)
            or cls.normalize_group({})
        )

    @classmethod
    def save_group(cls, collection_id: Any, raw: Any) -> tuple[bool, dict[str, Any]]:
        collection_id = cls._text(collection_id, 100)
        normalized = cls.normalize_group(raw)
        if not collection_id:
            return False, normalized

        config = cls.get_config(force_reload=True)
        groups = config.setdefault("groups", {})
        if collection_id not in groups and len(groups) >= cls.MAX_GROUPS:
            return False, normalized
        groups[collection_id] = normalized
        return cls._save_config(config), normalized

    @classmethod
    def delete_group(cls, collection_id: Any) -> bool:
        collection_id = cls._text(collection_id, 100)
        config = cls.get_config(force_reload=True)
        config.setdefault("groups", {}).pop(collection_id, None)
        return cls._save_config(config)

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _fold(value: Any) -> str:
        return " ".join(str(value or "").casefold().split())

    @classmethod
    def _text_match(cls, candidates: list[Any], operator: str, expected: Any) -> bool:
        expected_text = cls._fold(expected)
        values = [cls._fold(value) for value in candidates]

        if operator == "equals":
            return any(value == expected_text for value in values)
        if operator == "not_equals":
            return all(value != expected_text for value in values)
        if operator == "contains":
            return any(expected_text in value for value in values)
        if operator == "not_contains":
            return all(expected_text not in value for value in values)
        if operator == "starts_with":
            return any(value.startswith(expected_text) for value in values)
        if operator == "ends_with":
            return any(value.endswith(expected_text) for value in values)
        return False

    @classmethod
    def _rule_matches(
        cls,
        product: dict[str, Any],
        categories: list[str],
        rule: dict[str, str],
    ) -> bool:
        field = rule["field"]
        operator = rule["operator"]
        expected = rule["value"]

        if field in {"price", "stock"}:
            actual_number = cls._number(product.get(field))
            # Giá/tồn kho của shop là số nguyên; chấp nhận cả "200.000 đ".
            expected_number = cls._number(re.sub(r"[^\d]", "", expected))
            return {
                "equals": actual_number == expected_number,
                "not_equals": actual_number != expected_number,
                "gt": actual_number > expected_number,
                "gte": actual_number >= expected_number,
                "lt": actual_number < expected_number,
                "lte": actual_number <= expected_number,
            }.get(operator, False)

        if field == "tag":
            raw_tags = product.get("tags") or []
            candidates = raw_tags if isinstance(raw_tags, list) else re.split(r"[,|;]+", str(raw_tags))
        elif field == "category":
            candidates = categories
        elif field == "status":
            if product.get("deleted_at"):
                candidates = ["deleted", "đã xóa"]
            elif product.get("is_active") is False or product.get("product_status") in {"draft", "hidden"}:
                candidates = ["hidden", "draft", "ẩn"]
            else:
                candidates = ["active", "đang bán"]
        else:
            candidates = [product.get(field)]

        return cls._text_match(candidates, operator, expected)

    @classmethod
    def matches_group(
        cls,
        product: dict[str, Any],
        categories: list[str],
        group: dict[str, Any],
    ) -> bool:
        rules = group.get("rules") or []
        if not rules or product.get("deleted_at"):
            return False
        results = [cls._rule_matches(product, categories, rule) for rule in rules]
        return any(results) if group.get("match_mode") == "any" else all(results)

    @classmethod
    def _categories_by_product(cls, product_ids: list[str]) -> dict[str, list[str]]:
        output: dict[str, list[str]] = {str(product_id): [] for product_id in product_ids}
        if not product_ids:
            return output

        try:
            for start in range(0, len(product_ids), 200):
                chunk = product_ids[start:start + 200]
                rows = (
                    cls._db().table("product_categories")
                    .select("product_id,categories(name,slug)")
                    .in_("product_id", chunk).execute().data or []
                )
                for row in rows:
                    product_id = str(row.get("product_id") or "")
                    category = row.get("categories") or {}
                    if isinstance(category, dict):
                        output.setdefault(product_id, []).extend(
                            value for value in (category.get("name"), category.get("slug")) if value
                        )
        except Exception as exc:
            logger.warning("[ProductGroupModel] Không tải được danh mục sản phẩm: %s", exc)
        return output

    @classmethod
    def sync_collection(cls, collection_id: Any) -> int:
        """Tính lại toàn bộ thành viên cho một nhóm tự động và trả về số sản phẩm."""
        collection_id = cls._text(collection_id, 100)
        group = cls.get_group(collection_id)
        if not collection_id or group.get("selection_mode") != "automatic":
            return 0

        db = cls._db()
        products: list[dict[str, Any]] = []
        select_fields = "id,name,sku,barcode,brand,gender,tags,price,stock,is_active,product_status,deleted_at"
        for start in range(0, cls.MAX_PRODUCTS, 1000):
            batch = (
                db.table("products").select(select_fields)
                .range(start, start + 999).execute().data or []
            )
            products.extend(batch)
            if len(batch) < 1000:
                break
        product_ids = [str(product.get("id")) for product in products if product.get("id")]
        category_map = cls._categories_by_product(product_ids)
        matched = {
            str(product["id"])
            for product in products
            if product.get("id") and cls.matches_group(
                product, category_map.get(str(product["id"]), []), group
            )
        }

        current_rows = (
            db.table("collection_products").select("product_id")
            .eq("collection_id", collection_id).execute().data or []
        )
        current = {str(row.get("product_id")) for row in current_rows if row.get("product_id")}

        to_remove = sorted(current - matched)
        to_add = sorted(matched - current)
        for start in range(0, len(to_remove), 200):
            db.table("collection_products").delete().eq("collection_id", collection_id).in_(
                "product_id", to_remove[start:start + 200]
            ).execute()
        for start in range(0, len(to_add), 200):
            db.table("collection_products").upsert([
                {"collection_id": collection_id, "product_id": product_id}
                for product_id in to_add[start:start + 200]
            ]).execute()
        return len(matched)

    @classmethod
    def sync_automatic_for_product(cls, product_id: Any) -> int:
        """Cập nhật các nhóm tự động ngay sau khi một sản phẩm được lưu."""
        product_id = cls._text(product_id, 100)
        if not product_id:
            return 0

        groups = cls.get_config().get("groups", {})
        automatic = {
            collection_id: group
            for collection_id, group in groups.items()
            if group.get("selection_mode") == "automatic"
        }
        if not automatic:
            return 0

        db = cls._db()
        rows = (
            db.table("products")
            .select("id,name,sku,barcode,brand,gender,tags,price,stock,is_active,product_status,deleted_at")
            .eq("id", product_id).limit(1).execute().data or []
        )
        product = rows[0] if rows else {"id": product_id, "deleted_at": True}
        categories = cls._categories_by_product([product_id]).get(product_id, [])
        matched = {
            collection_id
            for collection_id, group in automatic.items()
            if cls.matches_group(product, categories, group)
        }
        current_rows = (
            db.table("collection_products").select("collection_id")
            .eq("product_id", product_id).in_("collection_id", list(automatic)).execute().data or []
        )
        current = {str(row.get("collection_id")) for row in current_rows if row.get("collection_id")}
        to_add = sorted(matched - current)
        to_remove = sorted(current - matched)
        if to_add:
            db.table("collection_products").upsert([
                {"collection_id": collection_id, "product_id": product_id}
                for collection_id in to_add
            ]).execute()
        if to_remove:
            db.table("collection_products").delete().eq("product_id", product_id).in_(
                "collection_id", to_remove
            ).execute()
        return len(matched)

    @classmethod
    def enrich_collections(
        cls,
        collections: list[dict[str, Any]],
        include_counts: bool = True,
    ) -> list[dict[str, Any]]:
        """Gắn mode và số thành viên để màn hình danh sách không phải query N+1."""
        groups = cls.get_config().get("groups", {})
        counts: dict[str, int] = {}
        if include_counts:
            try:
                for start in range(0, 50000, 1000):
                    rows = (
                        cls._db().table("collection_products").select("collection_id")
                        .range(start, start + 999).execute().data or []
                    )
                    for row in rows:
                        collection_id = str(row.get("collection_id") or "")
                        if collection_id:
                            counts[collection_id] = counts.get(collection_id, 0) + 1
                    if len(rows) < 1000:
                        break
            except Exception as exc:
                logger.warning("[ProductGroupModel] Không đếm được thành viên nhóm: %s", exc)

        for collection in collections:
            collection_id = str(collection.get("id") or "")
            config = groups.get(collection_id) or cls.normalize_group({})
            collection["selection_mode"] = config["selection_mode"]
            collection["group_rule_count"] = len(config.get("rules") or [])
            collection["product_count"] = counts.get(collection_id, 0)
            collection["template"] = config.get("template", "collection")
        return collections
