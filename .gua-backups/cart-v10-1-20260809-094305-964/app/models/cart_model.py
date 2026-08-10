"""Data objects for the GUAMAISON cart domain.

This module deliberately has no database or Flask dependencies.  Cart reads and
writes live in ``CartRepository`` while cart rules live in ``CartService``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import ceil
from typing import Any, Literal


SelectionMode = Literal["explicit", "all"]


@dataclass(frozen=True)
class CartSelection:
    """A compact selection that can represent two lines or the whole cart."""

    mode: SelectionMode = "explicit"
    item_ids: tuple[str, ...] = field(default_factory=tuple)
    excluded_ids: tuple[str, ...] = field(default_factory=tuple)

    def to_record(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "item_ids": list(self.item_ids),
            "excluded_ids": list(self.excluded_ids),
        }

    @classmethod
    def from_record(cls, value: dict[str, Any] | None) -> "CartSelection":
        value = value or {}
        mode: SelectionMode = "all" if value.get("mode") == "all" else "explicit"
        return cls(
            mode=mode,
            item_ids=tuple(str(item) for item in (value.get("item_ids") or [])),
            excluded_ids=tuple(str(item) for item in (value.get("excluded_ids") or [])),
        )


@dataclass(frozen=True)
class CartPage:
    items: tuple[dict[str, Any], ...]
    page: int
    per_page: int
    total_lines: int
    query: str = ""

    @property
    def total_pages(self) -> int:
        return max(1, ceil(self.total_lines / self.per_page))

    @property
    def first_position(self) -> int:
        return 0 if not self.items else (self.page - 1) * self.per_page + 1

    @property
    def last_position(self) -> int:
        return min(self.total_lines, (self.page - 1) * self.per_page + len(self.items))

    def to_template(self) -> dict[str, Any]:
        value = asdict(self)
        value.update(
            total_pages=self.total_pages,
            first_position=self.first_position,
            last_position=self.last_position,
        )
        return value


@dataclass(frozen=True)
class CartSummary:
    line_count: int = 0
    quantity: int = 0
    total: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CartMutation:
    success: bool
    message: str
    affected: int = 0
    item: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
