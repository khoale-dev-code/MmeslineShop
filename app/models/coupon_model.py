"""Data contracts for the GUAMAISON promotion domain."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CouponScope:
    kind: str = "all"
    ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CouponDraft:
    code: str
    description: str
    discount_type: str
    discount_value: float
    max_discount: float | None
    min_order_value: float
    usage_limit: int | None
    usage_per_user: int | None
    starts_at: str | None
    expires_at: str | None
    is_stackable: bool
    is_active: bool
    is_first_order_only: bool
    max_usage_per_day: int | None
    image_url: str | None
    applicable_channel: str
    min_loyalty_points: int
    scope: CouponScope = field(default_factory=CouponScope)


@dataclass(frozen=True)
class CouponApplication:
    valid: bool = False
    coupon_id: str | None = None
    code: str = ""
    discount_amount: float = 0.0
    free_shipping: bool = False
    applicable_subtotal: float = 0.0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["discount"] = data["discount_amount"]
        return data


@dataclass(frozen=True)
class CouponFormOptions:
    categories: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    products: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    warning: str = ""

