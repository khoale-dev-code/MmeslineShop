"""Supabase persistence for customer broadcast notifications."""

from __future__ import annotations

from app.utils.supabase_client import get_supabase_admin


class BroadcastNotificationRepository:
    def __init__(self, client=None) -> None:
        self._client = client or get_supabase_admin()

    def list_all(self) -> list[dict]:
        result = self._client.table("notifications").select("*").order("created_at", desc=True).execute()
        return result.data or []

    def get(self, notification_id: str) -> dict | None:
        result = self._client.table("notifications").select("*").eq("id", notification_id).limit(1).execute()
        return result.data[0] if result.data else None

    def create(self, payload: dict) -> dict | None:
        result = self._client.table("notifications").insert(payload).execute()
        return result.data[0] if result.data else None

    def update(self, notification_id: str, payload: dict) -> bool:
        result = self._client.table("notifications").update(payload).eq("id", notification_id).execute()
        return bool(result.data)

    def delete(self, notification_id: str) -> bool:
        self._client.table("user_notifications").delete().eq("notification_id", notification_id).execute()
        self._client.table("notifications").delete().eq("id", notification_id).execute()
        return True

    def existing_user_ids(self, notification_id: str) -> set[str]:
        ids: set[str] = set()
        offset = 0
        while True:
            result = (
                self._client.table("user_notifications")
                .select("user_id")
                .eq("notification_id", notification_id)
                .range(offset, offset + 999)
                .execute()
            )
            rows = result.data or []
            ids.update(str(row["user_id"]) for row in rows if row.get("user_id"))
            if len(rows) < 1000:
                return ids
            offset += 1000

    def customer_ids(self) -> list[str]:
        ids: list[str] = []
        offset = 0
        while True:
            result = self._client.table("users").select("id").eq("role", "customer").range(offset, offset + 999).execute()
            rows = result.data or []
            ids.extend(str(row["id"]) for row in rows if row.get("id"))
            if len(rows) < 1000:
                return ids
            offset += 1000

    def insert_user_notifications(self, rows: list[dict]) -> int:
        total = 0
        for start in range(0, len(rows), 500):
            batch = rows[start:start + 500]
            self._client.table("user_notifications").insert(batch).execute()
            total += len(batch)
        return total
