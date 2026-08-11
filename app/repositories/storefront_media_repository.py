"""Supabase adapter for Media Studio; no HTTP or business rules live here."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.utils.supabase_client import get_supabase_admin


class StorefrontMediaRepositoryError(RuntimeError):
    pass


class StorefrontMediaRepository:
    BUCKET = "store-assets"
    SETTING_KEY = "storefront"

    def __init__(self, client: Any | None = None) -> None:
        self._client = client or get_supabase_admin()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def upload(
        self,
        *,
        path: str,
        content: bytes,
        content_type: str,
        cache_control: str = "31536000",
    ) -> str:
        storage = self._client.storage.from_(self.BUCKET)
        primary_options = {
            "content-type": content_type,
            "cache-control": cache_control,
            "upsert": "false",
        }
        alternate_options = {
            "contentType": content_type,
            "cacheControl": cache_control,
            "upsert": "false",
        }
        try:
            try:
                storage.upload(path, content, primary_options)
            except Exception:
                storage.upload(path, content, alternate_options)
            public_url = storage.get_public_url(path)
            if not public_url:
                raise StorefrontMediaRepositoryError(
                    "Supabase Storage không trả về public URL."
                )
            return str(public_url)
        except StorefrontMediaRepositoryError:
            raise
        except Exception as exc:
            raise StorefrontMediaRepositoryError(str(exc)) from exc

    def get_settings(self) -> dict[str, Any]:
        try:
            response = (
                self._client.table("store_settings")
                .select("setting_value,updated_at")
                .eq("setting_key", self.SETTING_KEY)
                .limit(1)
                .execute()
            )
            row = (response.data or [{}])[0]
            value = row.get("setting_value")
            return dict(value) if isinstance(value, dict) else {}
        except Exception as exc:
            raise StorefrontMediaRepositoryError(str(exc)) from exc

    def save_settings(self, changes: dict[str, str]) -> tuple[dict[str, Any], str]:
        current = self.get_settings()
        merged = {**current, **changes}
        updated_at = self._now_iso()
        payload = {
            "setting_key": self.SETTING_KEY,
            "setting_value": merged,
            "updated_at": updated_at,
        }
        try:
            response = (
                self._client.table("store_settings")
                .upsert(payload, on_conflict="setting_key")
                .execute()
            )
            row = (response.data or [payload])[0]
            saved = row.get("setting_value")
            return (dict(saved) if isinstance(saved, dict) else merged, updated_at)
        except Exception as exc:
            raise StorefrontMediaRepositoryError(str(exc)) from exc

