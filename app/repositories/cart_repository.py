"""Supabase access for carts.  No HTTP or business rules live here."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from app.models.cart_model import CartSelection
from app.utils.supabase_client import get_supabase_admin


logger = logging.getLogger(__name__)

_CART_SELECT = (
    "id,user_id,product_id,variant_id,quantity,size,color,created_at,"
    "products!inner(id,name,sku,price,thumbnail_url,stock,slug,is_active,deleted_at),"
    "product_variants!inner(id,product_id,size,color_name,color_hex,sku,price_override,stock)"
)


def _chunks(values: Iterable[str], size: int = 150):
    values = list(values)
    for index in range(0, len(values), size):
        yield values[index:index + size]


class CartRepository:
    def _db(self):
        return get_supabase_admin()

    @staticmethod
    def _rows(result) -> list[dict[str, Any]]:
        return list(getattr(result, "data", None) or [])

    def get_page(self, user_id: str, page: int, per_page: int, query: str = "") -> tuple[list, int]:
        offset = (page - 1) * per_page
        request = (
            self._db()
            .table("cart_items")
            .select(_CART_SELECT, count="exact")
            .eq("user_id", user_id)
        )
        if query:
            product_ids, variant_ids = self._search_cart_refs(query)
            if not product_ids and not variant_ids:
                return [], 0
            if product_ids and variant_ids:
                request = request.or_(
                    "product_id.in.({0}),variant_id.in.({1})".format(
                        ",".join(product_ids),
                        ",".join(variant_ids),
                    )
                )
            elif product_ids:
                request = request.in_("product_id", product_ids)
            else:
                request = request.in_("variant_id", variant_ids)

        response = (
            request
            .order("created_at", desc=False)
            .range(offset, offset + per_page - 1)
            .execute()
        )
        return self._rows(response), int(getattr(response, "count", 0) or 0)

    def _search_cart_refs(self, query: str) -> tuple[list[str], list[str]]:
        """Resolve product/variant ids first to stay compatible with supabase-py 2.3+."""
        product_ids: set[str] = set()
        variant_ids: set[str] = set()
        pattern = f"%{query}%"

        for column in ("name", "sku"):
            try:
                response = (
                    self._db()
                    .table("products")
                    .select("id")
                    .ilike(column, pattern)
                    .limit(300)
                    .execute()
                )
                product_ids.update(str(row["id"]) for row in self._rows(response) if row.get("id"))
            except Exception as exc:
                logger.debug("Cart search skipped products.%s: %s", column, exc)

        try:
            response = (
                self._db()
                .table("product_variants")
                .select("id")
                .ilike("sku", pattern)
                .limit(300)
                .execute()
            )
            variant_ids.update(str(row["id"]) for row in self._rows(response) if row.get("id"))
        except Exception as exc:
            logger.debug("Cart search skipped product_variants.sku: %s", exc)

        return sorted(product_ids), sorted(variant_ids)

    def get_line_count(self, user_id: str) -> int:
        response = (
            self._db()
            .table("cart_items")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return int(getattr(response, "count", 0) or 0)

    def get_item(self, user_id: str, item_id: str, with_relations: bool = True) -> dict | None:
        fields = _CART_SELECT if with_relations else "*"
        response = (
            self._db()
            .table("cart_items")
            .select(fields)
            .eq("user_id", user_id)
            .eq("id", item_id)
            .limit(1)
            .execute()
        )
        rows = self._rows(response)
        return rows[0] if rows else None

    def get_item_by_variant(self, user_id: str, variant_id: str) -> dict | None:
        response = (
            self._db()
            .table("cart_items")
            .select("*")
            .eq("user_id", user_id)
            .eq("variant_id", variant_id)
            .limit(1)
            .execute()
        )
        rows = self._rows(response)
        return rows[0] if rows else None

    def get_items_by_ids(self, user_id: str, item_ids: Iterable[str]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for batch in _chunks(dict.fromkeys(item_ids)):
            if not batch:
                continue
            response = (
                self._db()
                .table("cart_items")
                .select(_CART_SELECT)
                .eq("user_id", user_id)
                .in_("id", batch)
                .order("created_at", desc=False)
                .execute()
            )
            items.extend(self._rows(response))
        return items

    def list_all_items(self, user_id: str, excluded_ids: Iterable[str] = ()) -> list[dict[str, Any]]:
        excluded = set(excluded_ids)
        items: list[dict[str, Any]] = []
        page_size = 500
        offset = 0
        while True:
            response = (
                self._db()
                .table("cart_items")
                .select(_CART_SELECT)
                .eq("user_id", user_id)
                .order("created_at", desc=False)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            rows = self._rows(response)
            items.extend(item for item in rows if str(item.get("id")) not in excluded)
            if len(rows) < page_size:
                break
            offset += page_size
        return items

    def list_all_ids(self, user_id: str) -> list[str]:
        ids: list[str] = []
        page_size = 500
        offset = 0
        while True:
            response = (
                self._db()
                .table("cart_items")
                .select("id")
                .eq("user_id", user_id)
                .order("created_at", desc=False)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            rows = self._rows(response)
            ids.extend(str(row["id"]) for row in rows if row.get("id"))
            if len(rows) < page_size:
                break
            offset += page_size
        return ids

    def get_product_variants(self, product_id: str) -> list[dict[str, Any]]:
        response = (
            self._db()
            .table("product_variants")
            .select("id,product_id,size,color_name,color_hex,sku,price_override,stock,sort_order")
            .eq("product_id", product_id)
            .order("sort_order", desc=False)
            .order("color_name", desc=False)
            .execute()
        )
        return self._rows(response)

    def get_variant(self, variant_id: str) -> dict | None:
        response = (
            self._db()
            .table("product_variants")
            .select("id,product_id,size,color_name,color_hex,sku,price_override,stock,sort_order")
            .eq("id", variant_id)
            .limit(1)
            .execute()
        )
        rows = self._rows(response)
        return rows[0] if rows else None

    def insert_item(self, values: dict[str, Any]) -> dict | None:
        response = self._db().table("cart_items").insert(values).execute()
        rows = self._rows(response)
        return rows[0] if rows else None

    def update_item(self, user_id: str, item_id: str, values: dict[str, Any]) -> dict | None:
        response = (
            self._db()
            .table("cart_items")
            .update(values)
            .eq("user_id", user_id)
            .eq("id", item_id)
            .execute()
        )
        rows = self._rows(response)
        return rows[0] if rows else None

    def delete_item(self, user_id: str, item_id: str) -> bool:
        response = (
            self._db()
            .table("cart_items")
            .delete()
            .eq("user_id", user_id)
            .eq("id", item_id)
            .execute()
        )
        return bool(self._rows(response))

    def delete_ids(self, user_id: str, item_ids: Iterable[str]) -> int:
        affected = 0
        for batch in _chunks(dict.fromkeys(item_ids)):
            if not batch:
                continue
            response = (
                self._db()
                .table("cart_items")
                .delete()
                .eq("user_id", user_id)
                .in_("id", batch)
                .execute()
            )
            affected += len(self._rows(response))
        return affected

    def clear_cart(self, user_id: str) -> int:
        response = self._db().table("cart_items").delete().eq("user_id", user_id).execute()
        return len(self._rows(response))

    def create_checkout_selection(self, user_id: str, selection: CartSelection) -> str | None:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        values = {
            "user_id": user_id,
            "mode": selection.mode,
            "item_ids": list(selection.item_ids),
            "excluded_ids": list(selection.excluded_ids),
            "expires_at": expires_at.isoformat(),
        }
        try:
            response = self._db().table("cart_checkout_selections").insert(values).execute()
            rows = self._rows(response)
            return str(rows[0]["id"]) if rows else None
        except Exception as exc:
            logger.warning("Cart v10 selection table unavailable; using session fallback: %s", exc)
            return None

    def get_checkout_selection(self, user_id: str, selection_id: str) -> CartSelection | None:
        try:
            response = (
                self._db()
                .table("cart_checkout_selections")
                .select("mode,item_ids,excluded_ids,expires_at")
                .eq("id", selection_id)
                .eq("user_id", user_id)
                .gt("expires_at", datetime.now(timezone.utc).isoformat())
                .limit(1)
                .execute()
            )
            rows = self._rows(response)
            return CartSelection.from_record(rows[0]) if rows else None
        except Exception as exc:
            logger.warning("Cannot load Cart v10 selection %s: %s", selection_id, exc)
            return None

    def delete_checkout_selection(self, user_id: str, selection_id: str | None) -> None:
        if not selection_id:
            return
        try:
            (
                self._db()
                .table("cart_checkout_selections")
                .delete()
                .eq("id", selection_id)
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as exc:
            logger.debug("Could not clean Cart v10 selection: %s", exc)

    def selection_summary_rpc(self, user_id: str, selection: CartSelection) -> dict[str, Any] | None:
        try:
            response = self._db().rpc("cart_selection_summary_v10", {
                "p_user_id": user_id,
                "p_mode": selection.mode,
                "p_item_ids": list(selection.item_ids),
                "p_excluded_ids": list(selection.excluded_ids),
            }).execute()
            data = getattr(response, "data", None)
            if isinstance(data, dict):
                return data
            if isinstance(data, list) and data and isinstance(data[0], dict):
                return data[0]
        except Exception as exc:
            logger.debug("Cart v10 summary RPC unavailable: %s", exc)
        return None

    def delete_selection_rpc(self, user_id: str, selection: CartSelection) -> int | None:
        try:
            response = self._db().rpc("cart_delete_selection_v10", {
                "p_user_id": user_id,
                "p_mode": selection.mode,
                "p_item_ids": list(selection.item_ids),
                "p_excluded_ids": list(selection.excluded_ids),
            }).execute()
            data = getattr(response, "data", None)
            if isinstance(data, int):
                return data
            if isinstance(data, list) and data:
                value = data[0]
                if isinstance(value, int):
                    return value
                if isinstance(value, dict):
                    return int(next(iter(value.values()), 0) or 0)
        except Exception as exc:
            logger.debug("Cart v10 delete RPC unavailable: %s", exc)
        return None

    def change_variant_rpc(self, user_id: str, item_id: str, variant_id: str) -> dict | None:
        try:
            response = self._db().rpc("cart_change_variant_v10", {
                "p_user_id": user_id,
                "p_item_id": item_id,
                "p_variant_id": variant_id,
            }).execute()
            data = getattr(response, "data", None)
            if isinstance(data, dict):
                return data
            if isinstance(data, list) and data and isinstance(data[0], dict):
                return data[0]
        except Exception as exc:
            logger.debug("Cart v10 variant RPC unavailable: %s", exc)
        return None
