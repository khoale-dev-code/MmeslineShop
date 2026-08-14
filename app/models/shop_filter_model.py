"""Data-only models for configurable storefront filters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ShopFilterOption:
    id: str | None
    group_id: str
    value: str
    label: str
    color_hex: str | None = None
    sort_order: int = 0
    is_active: bool = True

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ShopFilterOption":
        return cls(
            id=str(row.get("id")) if row.get("id") else None,
            group_id=str(row.get("group_id") or ""),
            value=str(row.get("value") or ""),
            label=str(row.get("label") or ""),
            color_hex=str(row.get("color_hex")) if row.get("color_hex") else None,
            sort_order=int(row.get("sort_order") or 0),
            is_active=bool(row.get("is_active", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ShopFilterGroup:
    id: str | None
    key: str
    label: str
    display_type: str = "chips"
    sort_order: int = 0
    is_active: bool = True
    is_system: bool = False
    options: list[ShopFilterOption] = field(default_factory=list)

    @classmethod
    def from_row(
        cls,
        row: dict[str, Any],
        options: list[ShopFilterOption] | None = None,
    ) -> "ShopFilterGroup":
        return cls(
            id=str(row.get("id")) if row.get("id") else None,
            key=str(row.get("key") or ""),
            label=str(row.get("label") or ""),
            display_type=str(row.get("display_type") or "chips"),
            sort_order=int(row.get("sort_order") or 0),
            is_active=bool(row.get("is_active", True)),
            is_system=bool(row.get("is_system", False)),
            options=options or [],
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["options"] = [option.to_dict() for option in self.options]
        return data
