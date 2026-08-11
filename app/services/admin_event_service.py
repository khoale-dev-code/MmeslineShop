"""Business rules for the shared Admin action inbox; no Flask/Supabase imports."""

from __future__ import annotations

import re

from app.models.admin_event_model import AdminEventPage
from app.repositories.admin_event_repository import AdminEventMigrationRequired, AdminEventRepository


class AdminEventValidationError(ValueError):
    pass


class AdminEventService:
    STATUSES = {"", "unread", "read", "resolved"}
    CATEGORIES = {"", "order", "payment", "return", "contact", "marketing", "system"}
    PRIORITIES = {"", "info", "normal", "high", "urgent"}

    def __init__(self, repository: AdminEventRepository | None = None) -> None:
        self.repository = repository or AdminEventRepository()

    @staticmethod
    def _clean_query(value: str) -> str:
        return re.sub(r"[^\w\s@.+-]", " ", str(value or ""), flags=re.UNICODE).strip()[:100]

    def inbox(
        self,
        *,
        page: int,
        per_page: int,
        status: str,
        category: str,
        priority: str,
        query_text: str,
    ) -> tuple[AdminEventPage, dict[str, int]]:
        status = status if status in self.STATUSES else ""
        category = category if category in self.CATEGORIES else ""
        priority = priority if priority in self.PRIORITIES else ""
        page = max(1, int(page or 1))
        per_page = min(50, max(10, int(per_page or 20)))
        return (
            self.repository.list_events(
                page=page,
                per_page=per_page,
                status=status,
                category=category,
                priority=priority,
                query_text=self._clean_query(query_text),
            ),
            self.repository.stats(),
        )

    def mark_read(self, event_id: str, *, admin_user_id: str | None) -> bool:
        event = self.repository.get(str(event_id))
        if event is None:
            raise AdminEventValidationError("Không tìm thấy thông báo.")
        if event.status != "unread":
            return True
        return self.repository.set_status(event.id, status="read", admin_user_id=admin_user_id)

    def resolve(self, event_id: str, *, admin_user_id: str | None) -> bool:
        event = self.repository.get(str(event_id))
        if event is None:
            raise AdminEventValidationError("Không tìm thấy thông báo.")
        if event.status == "resolved":
            return True
        return self.repository.set_status(event.id, status="resolved", admin_user_id=admin_user_id)

    def reopen(self, event_id: str, *, admin_user_id: str | None) -> bool:
        event = self.repository.get(str(event_id))
        if event is None:
            raise AdminEventValidationError("Không tìm thấy thông báo.")
        return self.repository.set_status(event.id, status="unread", admin_user_id=admin_user_id)

    def open_action(self, event_id: str, *, admin_user_id: str | None) -> str:
        event = self.repository.get(str(event_id))
        if event is None:
            raise AdminEventValidationError("Không tìm thấy thông báo.")
        if event.status == "unread":
            self.repository.set_status(event.id, status="read", admin_user_id=admin_user_id)
        url = event.action_url.strip()
        return url if url.startswith("/admin/") and not url.startswith("//") else "/admin/notifications"

    def mark_all_read(self, *, admin_user_id: str | None) -> int:
        return self.repository.mark_all_read(admin_user_id=admin_user_id)

    def unread_count(self) -> int:
        return self.repository.unread_count()
