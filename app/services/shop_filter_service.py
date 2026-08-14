"""Business rules for admin-configured, tag-backed shop filters."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable

from app.models.shop_filter_model import ShopFilterGroup, ShopFilterOption
from app.repositories.shop_filter_repository import ShopFilterRepository


class ShopFilterValidationError(ValueError):
    pass


class ShopFilterService:
    DISPLAY_TYPES = {"chips", "checkbox", "color"}
    SYSTEM_KEYS = {"color", "chatlieu", "loai"}
    KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
    HEX_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

    def __init__(
        self,
        *,
        admin: bool = False,
        repository_factory: Callable[..., ShopFilterRepository] = ShopFilterRepository,
    ) -> None:
        self._repository = repository_factory(admin=admin)

    @staticmethod
    def slugify(value: Any, *, fallback: str = "") -> str:
        text = str(value or "").strip().lower().replace("đ", "d")
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
        return text or fallback

    @classmethod
    def normalize_key(cls, value: Any) -> str:
        key = cls.slugify(value).replace("-", "_")
        if not cls.KEY_PATTERN.fullmatch(key):
            raise ShopFilterValidationError(
                "Mã bộ lọc phải bắt đầu bằng chữ, chỉ gồm a-z, 0-9 hoặc dấu gạch dưới."
            )
        return key

    @classmethod
    def build_token(cls, key: Any, value: Any) -> str:
        normalized_key = cls.normalize_key(key)
        normalized_value = cls.slugify(value)
        if not normalized_value or len(normalized_value) > 48:
            raise ShopFilterValidationError("Giá trị bộ lọc không hợp lệ.")
        return f"{normalized_key}:{normalized_value}"

    @staticmethod
    def _clean_label(value: Any, *, max_length: int = 80) -> str:
        label = " ".join(str(value or "").strip().split())[:max_length]
        if not label:
            raise ShopFilterValidationError("Nhãn hiển thị không được để trống.")
        return label

    def configuration(self, *, include_inactive: bool = False) -> dict[str, Any]:
        try:
            group_rows = self._repository.list_groups(include_inactive=include_inactive)
            option_rows = self._repository.list_options(include_inactive=include_inactive)
        except Exception:
            return {"ready": False, "groups": []}

        options_by_group: dict[str, list[ShopFilterOption]] = {}
        for row in option_rows:
            option = ShopFilterOption.from_row(row)
            options_by_group.setdefault(option.group_id, []).append(option)

        groups = [
            ShopFilterGroup.from_row(
                row,
                options=options_by_group.get(str(row.get("id") or ""), []),
            ).to_dict()
            for row in group_rows
        ]
        return {"ready": True, "groups": groups}

    def save_group(self, data: dict[str, Any]) -> dict[str, Any]:
        group_id = str(data.get("id") or "").strip() or None
        existing = self._repository.get_group(group_id) if group_id else None
        key = str(existing.get("key")) if existing else self.normalize_key(data.get("key"))
        display_type = str(data.get("display_type") or "chips").strip().lower()
        if display_type not in self.DISPLAY_TYPES:
            raise ShopFilterValidationError("Kiểu hiển thị bộ lọc không hợp lệ.")
        payload = {
            "id": group_id,
            "key": key,
            "label": self._clean_label(data.get("label")),
            "display_type": display_type,
            "sort_order": max(0, min(int(data.get("sort_order") or 0), 9999)),
            "is_active": bool(data.get("is_active", True)),
            "is_system": bool(existing.get("is_system")) if existing else key in self.SYSTEM_KEYS,
        }
        return self._repository.upsert_group(payload)

    def save_option(self, data: dict[str, Any]) -> dict[str, Any]:
        group_id = str(data.get("group_id") or "").strip()
        group = self._repository.get_group(group_id)
        if not group:
            raise ShopFilterValidationError("Không tìm thấy bộ lọc cha.")
        label = self._clean_label(data.get("label"))
        value = self.slugify(data.get("value") or label)
        if not value or len(value) > 48:
            raise ShopFilterValidationError("Mã giá trị bộ lọc không hợp lệ.")
        color_hex = str(data.get("color_hex") or "").strip() or None
        if str(group.get("key")) == "color":
            color_hex = color_hex or "#d6b88d"
            if not self.HEX_PATTERN.fullmatch(color_hex):
                raise ShopFilterValidationError("Mã màu phải có dạng #RRGGBB.")
        else:
            color_hex = None
        payload = {
            "id": str(data.get("id") or "").strip() or None,
            "group_id": group_id,
            "value": value,
            "label": label,
            "color_hex": color_hex,
            "sort_order": max(0, min(int(data.get("sort_order") or 0), 9999)),
            "is_active": bool(data.get("is_active", True)),
        }
        saved = self._repository.upsert_option(payload)
        saved["token"] = self.build_token(group.get("key"), value)
        return saved

    def set_group_active(self, group_id: str, is_active: bool) -> None:
        if not self._repository.get_group(group_id):
            raise ShopFilterValidationError("Không tìm thấy bộ lọc.")
        self._repository.set_group_active(group_id, is_active)

    def set_option_active(self, option_id: str, is_active: bool) -> None:
        self._repository.set_option_active(option_id, is_active)

    def normalize_selected_tokens(
        self,
        values: list[Any],
        *,
        config: dict[str, Any] | None = None,
    ) -> list[str]:
        config = config or self.configuration(include_inactive=False)
        allowed = {
            self.build_token(group["key"], option["value"])
            for group in config["groups"]
            for option in group["options"]
            if group.get("is_active") and option.get("is_active")
        }
        output: list[str] = []
        for value in values or []:
            token = str(value or "").strip().lower()
            if token in allowed and token not in output:
                output.append(token)
        return output[:40]

    def find_matching_product_ids(
        self,
        values: list[Any],
        *,
        normalized: bool = False,
        config: dict[str, Any] | None = None,
    ) -> list[str] | None:
        if normalized:
            tokens = list(dict.fromkeys(
                str(value or "").strip().lower()
                for value in values or []
                if str(value or "").strip()
            ))[:40]
        else:
            tokens = self.normalize_selected_tokens(values, config=config)
        if not tokens:
            return None
        try:
            return self._repository.matching_product_ids(tokens)
        except Exception:
            return []

    def merge_product_tags(
        self,
        existing_tags: list[Any],
        selected_filter_tags: list[Any],
        *,
        replace_configured: bool,
    ) -> list[str]:
        existing = [str(tag).strip() for tag in existing_tags or [] if str(tag).strip()]
        if not replace_configured:
            return list(dict.fromkeys(existing))

        config = self.configuration(include_inactive=True)
        if not config["ready"]:
            return list(dict.fromkeys(existing))

        keys = {str(group["key"]).lower() for group in config["groups"]}
        allowed = {
            self.build_token(group["key"], option["value"])
            for group in config["groups"]
            for option in group["options"]
            if option.get("is_active")
        }
        kept = [
            tag for tag in existing
            if ":" not in tag or tag.split(":", 1)[0].strip().lower() not in keys
        ]
        selected = []
        for value in selected_filter_tags or []:
            token = str(value or "").strip().lower()
            if token in allowed and token not in selected:
                selected.append(token)
        return list(dict.fromkeys(kept + selected))
