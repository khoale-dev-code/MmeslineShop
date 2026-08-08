"""Kiểu dữ liệu bảng size dùng ở storefront."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class SizeChart:
    id: str
    name: str
    image_url: str
    is_active: bool = True
    sort_order: int = 0

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SizeChart":
        return cls(
            id=str(value.get("id") or "").strip(),
            name=str(value.get("name") or "").strip(),
            image_url=str(value.get("image_url") or "").strip(),
            is_active=bool(value.get("is_active", True)),
            sort_order=int(value.get("sort_order") or 0),
        )