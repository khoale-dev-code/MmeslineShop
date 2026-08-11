"""The only Supabase access layer for coupons and their eligibility data."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from app.models.coupon_model import CouponScope
from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CouponRepositoryError(RuntimeError):
    pass


class CouponRepositoryUnavailable(CouponRepositoryError):
    pass


class CouponRepository:
    """Small, retry-aware repository. Controllers and services never query Supabase."""

    def __init__(self, client: Any, retries: int = 2) -> None:
        self._client = client
        self._retries = max(0, retries)

    @classmethod
    def admin(cls) -> "CouponRepository":
        return cls(get_supabase_admin())

    @classmethod
    def public(cls) -> "CouponRepository":
        return cls(get_supabase())

    @staticmethod
    def _is_transient(exc: Exception) -> bool:
        name = exc.__class__.__name__.lower()
        message = str(exc).lower()
        signals = (
            "transport", "timeout", "connect", "protocol", "disconnect",
            "temporarily", "connection reset", "server disconnected", "502", "503", "504",
        )
        return any(signal in name or signal in message for signal in signals)

    def _run(self, operation: Callable[[], T], label: str) -> T:
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                return operation()
            except Exception as exc:  # Supabase/PostgREST expose several exception classes.
                last_error = exc
                if attempt >= self._retries or not self._is_transient(exc):
                    break
                time.sleep(0.12 * (attempt + 1))

        logger.warning("[CouponRepository] %s failed: %s", label, last_error)
        raise CouponRepositoryUnavailable(label) from last_error

    def list_admin(self, page: int, per_page: int, filter_mode: str, now_iso: str) -> tuple[list[dict], int]:
        offset = (page - 1) * per_page

        def query():
            builder = self._client.table("coupons").select("*", count="exact").order("created_at", desc=True)
            if filter_mode == "active":
                builder = builder.eq("is_active", True).or_(f"expires_at.is.null,expires_at.gt.{now_iso}")
            elif filter_mode == "expired":
                builder = builder.lt("expires_at", now_iso)
            elif filter_mode in {"percent", "fixed", "free_shipping"}:
                builder = builder.eq("discount_type", filter_mode)
            return builder.range(offset, offset + per_page - 1).execute()

        response = self._run(query, "list_admin")
        return response.data or [], int(response.count or 0)

    def list_public_candidates(self, now_iso: str) -> list[dict]:
        def query():
            return (
                self._client.table("coupons")
                .select("*")
                .eq("is_active", True)
                .or_(f"expires_at.is.null,expires_at.gt.{now_iso}")
                .order("created_at", desc=True)
                .execute()
            )

        return self._run(query, "list_public_candidates").data or []

    def get_by_id(self, coupon_id: str) -> dict | None:
        response = self._run(
            lambda: self._client.table("coupons").select("*").eq("id", coupon_id).limit(1).execute(),
            "get_by_id",
        )
        rows = response.data or []
        return rows[0] if rows else None

    def get_by_code(self, code: str) -> dict | None:
        response = self._run(
            lambda: self._client.table("coupons").select("*").eq("code", code).limit(1).execute(),
            "get_by_code",
        )
        rows = response.data or []
        return rows[0] if rows else None

    def create(self, payload: dict) -> dict:
        response = self._run(lambda: self._client.table("coupons").insert(payload).execute(), "create")
        rows = response.data or []
        if not rows:
            raise CouponRepositoryError("coupon_insert_returned_no_row")
        return rows[0]

    def update(self, coupon_id: str, payload: dict) -> dict:
        response = self._run(
            lambda: self._client.table("coupons").update(payload).eq("id", coupon_id).execute(),
            "update",
        )
        rows = response.data or []
        return rows[0] if rows else {"id": coupon_id, **payload}

    def delete(self, coupon_id: str) -> None:
        self._run(lambda: self._client.table("coupons").delete().eq("id", coupon_id).execute(), "delete")

    def set_active(self, coupon_id: str, active: bool) -> None:
        self.update(coupon_id, {"is_active": bool(active)})

    def list_categories(self) -> list[dict]:
        response = self._run(
            lambda: self._client.table("categories").select("id,name,slug,is_active").eq("is_active", True).order("name").execute(),
            "list_categories",
        )
        return response.data or []

    def list_products(self) -> list[dict]:
        response = self._run(
            lambda: self._client.table("products").select("id,name,thumbnail_url,price,is_active,deleted_at").eq("is_active", True).is_("deleted_at", "null").order("name").limit(1000).execute(),
            "list_products",
        )
        return response.data or []

    def scope_for(self, coupon_id: str) -> CouponScope:
        categories = self._run(
            lambda: self._client.table("coupon_categories").select("category_id").eq("coupon_id", coupon_id).execute(),
            "scope_categories",
        ).data or []
        products = self._run(
            lambda: self._client.table("coupon_products").select("product_id").eq("coupon_id", coupon_id).execute(),
            "scope_products",
        ).data or []
        if categories:
            return CouponScope("category", tuple(str(row["category_id"]) for row in categories))
        if products:
            return CouponScope("product", tuple(str(row["product_id"]) for row in products))
        return CouponScope()

    def scopes_for_many(self, coupon_ids: list[str]) -> dict[str, CouponScope]:
        scopes = {str(coupon_id): CouponScope() for coupon_id in coupon_ids}
        if not coupon_ids:
            return scopes
        categories = self._run(
            lambda: self._client.table("coupon_categories").select("coupon_id,category_id").in_("coupon_id", coupon_ids).execute(),
            "scopes_categories",
        ).data or []
        products = self._run(
            lambda: self._client.table("coupon_products").select("coupon_id,product_id").in_("coupon_id", coupon_ids).execute(),
            "scopes_products",
        ).data or []
        grouped_categories: dict[str, list[str]] = {}
        grouped_products: dict[str, list[str]] = {}
        for row in categories:
            grouped_categories.setdefault(str(row["coupon_id"]), []).append(str(row["category_id"]))
        for row in products:
            grouped_products.setdefault(str(row["coupon_id"]), []).append(str(row["product_id"]))
        for coupon_id in scopes:
            if grouped_categories.get(coupon_id):
                scopes[coupon_id] = CouponScope("category", tuple(grouped_categories[coupon_id]))
            elif grouped_products.get(coupon_id):
                scopes[coupon_id] = CouponScope("product", tuple(grouped_products[coupon_id]))
        return scopes

    def replace_scope(self, coupon_id: str, scope: CouponScope) -> None:
        self._run(lambda: self._client.table("coupon_categories").delete().eq("coupon_id", coupon_id).execute(), "clear_category_scope")
        self._run(lambda: self._client.table("coupon_products").delete().eq("coupon_id", coupon_id).execute(), "clear_product_scope")
        if scope.kind == "category" and scope.ids:
            rows = [{"coupon_id": coupon_id, "category_id": item_id} for item_id in scope.ids]
            self._run(lambda: self._client.table("coupon_categories").upsert(rows, on_conflict="coupon_id,category_id").execute(), "save_category_scope")
        elif scope.kind == "product" and scope.ids:
            rows = [{"coupon_id": coupon_id, "product_id": item_id} for item_id in scope.ids]
            self._run(lambda: self._client.table("coupon_products").upsert(rows, on_conflict="coupon_id,product_id").execute(), "save_product_scope")

    def usage_counts(self, coupon_ids: list[str]) -> dict[str, int]:
        counts = {str(coupon_id): 0 for coupon_id in coupon_ids}
        if not coupon_ids:
            return counts
        response = self._run(
            lambda: self._client.table("coupon_usages").select("coupon_id").in_("coupon_id", coupon_ids).execute(),
            "usage_counts",
        )
        for row in response.data or []:
            coupon_id = str(row.get("coupon_id") or "")
            if coupon_id in counts:
                counts[coupon_id] += 1
        return counts

    def count_usages(self, coupon_id: str, user_id: str | None = None, used_after: str | None = None) -> int:
        def query():
            builder = self._client.table("coupon_usages").select("id", count="exact").eq("coupon_id", coupon_id)
            if user_id:
                builder = builder.eq("user_id", user_id)
            if used_after:
                builder = builder.gte("used_at", used_after)
            return builder.limit(1).execute()

        response = self._run(query, "count_usages")
        return int(response.count or 0)

    def user_points(self, user_id: str) -> int:
        response = self._run(
            lambda: self._client.table("users").select("points").eq("id", user_id).limit(1).execute(),
            "user_points",
        )
        rows = response.data or []
        return int(float((rows[0] if rows else {}).get("points") or 0))

    def order_count(self, user_id: str) -> int:
        response = self._run(
            lambda: self._client.table("orders").select("id", count="exact").eq("user_id", user_id).limit(1).execute(),
            "order_count",
        )
        return int(response.count or 0)

    def product_category_map(self, product_ids: list[str]) -> dict[str, set[str]]:
        result = {str(product_id): set() for product_id in product_ids}
        if not product_ids:
            return result
        response = self._run(
            lambda: self._client.table("product_categories").select("product_id,category_id").in_("product_id", product_ids).execute(),
            "product_category_map",
        )
        for row in response.data or []:
            product_id = str(row.get("product_id") or "")
            if product_id in result:
                result[product_id].add(str(row.get("category_id") or ""))
        return result

    def usages(self, coupon_id: str) -> list[dict]:
        response = self._run(
            lambda: self._client.table("coupon_usages").select("*,users(full_name,email),orders(id,total_amount,created_at)").eq("coupon_id", coupon_id).order("used_at", desc=True).execute(),
            "usages",
        )
        return response.data or []

