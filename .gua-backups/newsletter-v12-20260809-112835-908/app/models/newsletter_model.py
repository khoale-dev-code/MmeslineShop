"""Pure data models for the GUAMAISON newsletter feature."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class NewsletterSubscriber:
    id: str
    email: str
    full_name: str
    status: str
    source: str
    locale: str
    consent_version: str
    is_unread: bool
    created_at: Optional[str]
    last_subscribed_at: Optional[str]
    unsubscribed_at: Optional[str]
    last_replied_at: Optional[str]
    unsubscribe_token: Optional[str]

    @classmethod
    def from_record(cls, record: dict[str, Any] | None) -> "NewsletterSubscriber | None":
        if not record or not record.get("id"):
            return None
        return cls(
            id=str(record["id"]),
            email=str(record.get("email") or ""),
            full_name=str(record.get("full_name") or ""),
            status=str(record.get("status") or "active"),
            source=str(record.get("source") or "storefront"),
            locale=str(record.get("locale") or "vi"),
            consent_version=str(record.get("consent_version") or "v1"),
            is_unread=bool(record.get("is_unread")),
            created_at=record.get("created_at"),
            last_subscribed_at=record.get("last_subscribed_at"),
            unsubscribed_at=record.get("unsubscribed_at"),
            last_replied_at=record.get("last_replied_at"),
            unsubscribe_token=(
                str(record.get("unsubscribe_token"))
                if record.get("unsubscribe_token")
                else None
            ),
        )


@dataclass(frozen=True)
class NewsletterMessage:
    id: str
    subscriber_id: str
    admin_user_id: Optional[str]
    subject: str
    body_text: str
    status: str
    error_message: Optional[str]
    created_at: Optional[str]
    sent_at: Optional[str]

    @classmethod
    def from_record(cls, record: dict[str, Any] | None) -> "NewsletterMessage | None":
        if not record or not record.get("id"):
            return None
        return cls(
            id=str(record["id"]),
            subscriber_id=str(record.get("subscriber_id") or ""),
            admin_user_id=(str(record["admin_user_id"]) if record.get("admin_user_id") else None),
            subject=str(record.get("subject") or ""),
            body_text=str(record.get("body_text") or ""),
            status=str(record.get("status") or "pending"),
            error_message=(str(record["error_message"]) if record.get("error_message") else None),
            created_at=record.get("created_at"),
            sent_at=record.get("sent_at"),
        )


@dataclass(frozen=True)
class SubscriptionResult:
    code: str
    subscriber_id: Optional[str]
    status: Optional[str]


@dataclass(frozen=True)
class NewsletterPage:
    rows: tuple[NewsletterSubscriber, ...]
    page: int
    per_page: int
    total: int
    total_pages: int

