"""The only application layer that accesses ``admin_events`` in Supabase."""

from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import Any

from app.models.admin_event_model import AdminEvent, AdminEventPage
from app.utils.supabase_client import get_supabase_admin


class AdminEventMigrationRequired(RuntimeError):
    pass


class AdminEventRepository:
    TABLE = "admin_events"

    def __init__(self, client=None) -> None:
        self._client = client or get_supabase_admin()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _raise_known(exc: Exception) -> None:
        text = str(exc).lower()
        if ("admin_events" in text or "admin_event_" in text) and any(
            code in text for code in ("pgrst202", "pgrst205", "42p01", "not found", "schema cache")
        ):
            raise AdminEventMigrationRequired(
                "Chưa chạy migration Admin Action Inbox v18."
            ) from exc
        raise exc

    def list_events(
        self,
        *,
        page: int,
        per_page: int,
        status: str,
        category: str,
        priority: str,
        query_text: str,
    ) -> AdminEventPage:
        offset = (page - 1) * per_page
        try:
            query = self._client.table(self.TABLE).select("*", count="exact")
            if status:
                query = query.eq("status", status)
            if category:
                query = query.eq("category", category)
            if priority:
                query = query.eq("priority", priority)
            if query_text:
                pattern = f"%{query_text}%"
                query = query.or_(
                    f"title.ilike.{pattern},message.ilike.{pattern},"
                    f"actor_name.ilike.{pattern},actor_email.ilike.{pattern}"
                )
            result = (
                query.order("occurred_at", desc=True)
                .range(offset, offset + per_page - 1)
                .execute()
            )
            total = int(result.count or 0)
            return AdminEventPage(
                items=tuple(AdminEvent.from_record(row) for row in (result.data or [])),
                total=total,
                page=page,
                per_page=per_page,
                total_pages=max(1, ceil(total / per_page)),
            )
        except Exception as exc:
            self._raise_known(exc)

    def get(self, event_id: str) -> AdminEvent | None:
        try:
            result = (
                self._client.table(self.TABLE)
                .select("*")
                .eq("id", event_id)
                .limit(1)
                .execute()
            )
            return AdminEvent.from_record(result.data[0]) if result.data else None
        except Exception as exc:
            self._raise_known(exc)

    def stats(self) -> dict[str, int]:
        try:
            result = self._client.rpc("admin_event_stats_v18").execute()
            row: dict[str, Any] = {}
            if isinstance(result.data, list) and result.data:
                row = result.data[0] or {}
            elif isinstance(result.data, dict):
                row = result.data
            return {
                "unread": int(row.get("unread") or 0),
                "high_priority": int(row.get("high_priority") or 0),
                "open_work": int(row.get("open_work") or 0),
                "resolved_today": int(row.get("resolved_today") or 0),
                "total": int(row.get("total") or 0),
            }
        except Exception as exc:
            self._raise_known(exc)

    def unread_count(self) -> int:
        try:
            result = self._client.rpc("admin_event_unread_count_v18").execute()
            data = result.data
            if isinstance(data, list):
                data = data[0] if data else 0
            if isinstance(data, dict):
                data = next(iter(data.values()), 0)
            return max(0, int(data or 0))
        except Exception as exc:
            self._raise_known(exc)

    def set_status(self, event_id: str, *, status: str, admin_user_id: str | None) -> bool:
        now = self._now()
        payload: dict[str, Any] = {"status": status, "updated_at": now}
        if status == "unread":
            payload.update({"read_at": None, "read_by": None, "resolved_at": None, "resolved_by": None})
        elif status == "read":
            payload.update({"read_at": now, "read_by": admin_user_id, "resolved_at": None, "resolved_by": None})
        elif status == "resolved":
            payload.update({
                "read_at": now,
                "read_by": admin_user_id,
                "resolved_at": now,
                "resolved_by": admin_user_id,
            })
        try:
            result = (
                self._client.table(self.TABLE)
                .update(payload)
                .eq("id", event_id)
                .execute()
            )
            return bool(result.data)
        except Exception as exc:
            self._raise_known(exc)

    def mark_all_read(self, *, admin_user_id: str | None) -> int:
        try:
            result = self._client.rpc(
                "admin_event_mark_all_read_v18",
                {"p_admin_user_id": admin_user_id},
            ).execute()
            data = result.data
            if isinstance(data, list):
                data = data[0] if data else 0
            if isinstance(data, dict):
                data = next(iter(data.values()), 0)
            return max(0, int(data or 0))
        except Exception as exc:
            self._raise_known(exc)
