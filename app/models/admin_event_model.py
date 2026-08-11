"""Pure data objects for the shared Admin action inbox."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AdminEvent:
    id: str
    event_key: str
    event_type: str
    category: str
    priority: str
    title: str
    message: str
    entity_type: str
    entity_id: str
    action_url: str
    action_label: str
    actor_id: str | None
    actor_name: str
    actor_email: str
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "unread"
    occurred_at: str = ""
    read_at: str | None = None
    read_by: str | None = None
    resolved_at: str | None = None
    resolved_by: str | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "AdminEvent":
        return cls(
            id=str(record.get("id") or ""),
            event_key=str(record.get("event_key") or ""),
            event_type=str(record.get("event_type") or "system.info"),
            category=str(record.get("category") or "system"),
            priority=str(record.get("priority") or "normal"),
            title=str(record.get("title") or "Thông báo mới"),
            message=str(record.get("message") or ""),
            entity_type=str(record.get("entity_type") or ""),
            entity_id=str(record.get("entity_id") or ""),
            action_url=str(record.get("action_url") or "/admin/notifications"),
            action_label=str(record.get("action_label") or "Xem chi tiết"),
            actor_id=(str(record["actor_id"]) if record.get("actor_id") else None),
            actor_name=str(record.get("actor_name") or "Khách hàng"),
            actor_email=str(record.get("actor_email") or ""),
            metadata=record.get("metadata") if isinstance(record.get("metadata"), dict) else {},
            status=str(record.get("status") or "unread"),
            occurred_at=str(record.get("occurred_at") or record.get("created_at") or ""),
            read_at=record.get("read_at"),
            read_by=(str(record["read_by"]) if record.get("read_by") else None),
            resolved_at=record.get("resolved_at"),
            resolved_by=(str(record["resolved_by"]) if record.get("resolved_by") else None),
        )


@dataclass(frozen=True)
class AdminEventPage:
    items: tuple[AdminEvent, ...]
    total: int
    page: int
    per_page: int
    total_pages: int

