"""Supabase persistence for shop filters. No business rules live here."""

from __future__ import annotations

from typing import Any

from app.utils.supabase_client import get_supabase, get_supabase_admin


class ShopFilterRepository:
    def __init__(self, *, admin: bool = False) -> None:
        self._db = get_supabase_admin() if admin else get_supabase()

    def list_groups(self, *, include_inactive: bool = False) -> list[dict[str, Any]]:
        query = self._db.table("shop_filter_groups").select("*")
        if not include_inactive:
            query = query.eq("is_active", True)
        return query.order("sort_order").order("created_at").execute().data or []

    def list_options(self, *, include_inactive: bool = False) -> list[dict[str, Any]]:
        query = self._db.table("shop_filter_options").select("*")
        if not include_inactive:
            query = query.eq("is_active", True)
        return query.order("sort_order").order("created_at").execute().data or []

    def get_group(self, group_id: str) -> dict[str, Any] | None:
        rows = (
            self._db.table("shop_filter_groups")
            .select("*")
            .eq("id", group_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None

    def upsert_group(self, payload: dict[str, Any]) -> dict[str, Any]:
        group_id = payload.pop("id", None)
        query = self._db.table("shop_filter_groups")
        if group_id:
            rows = query.update(payload).eq("id", group_id).execute().data or []
        else:
            rows = query.insert(payload).execute().data or []
        return rows[0] if rows else {**payload, "id": group_id}

    def upsert_option(self, payload: dict[str, Any]) -> dict[str, Any]:
        option_id = payload.pop("id", None)
        query = self._db.table("shop_filter_options")
        if option_id:
            rows = query.update(payload).eq("id", option_id).execute().data or []
        else:
            rows = (
                query.upsert(payload, on_conflict="group_id,value")
                .execute()
                .data
                or []
            )
        return rows[0] if rows else {**payload, "id": option_id}

    def set_group_active(self, group_id: str, is_active: bool) -> None:
        self._db.table("shop_filter_groups").update(
            {"is_active": is_active}
        ).eq("id", group_id).execute()

    def set_option_active(self, option_id: str, is_active: bool) -> None:
        self._db.table("shop_filter_options").update(
            {"is_active": is_active}
        ).eq("id", option_id).execute()

    def matching_product_ids(self, tokens: list[str]) -> list[str]:
        rows = self._db.rpc(
            "filter_storefront_product_ids",
            {"p_tokens": tokens},
        ).execute().data or []
        return [str(row["product_id"]) for row in rows if row.get("product_id")]
