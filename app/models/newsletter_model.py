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


@dataclass(frozen=True)
class NewsletterCampaign:
    id: str
    admin_user_id: Optional[str]
    name: str
    subject: str
    body_text: str
    action_label: str
    action_url: str
    target_mode: str
    status: str
    target_count: int
    pending_count: int
    processing_count: int
    sent_count: int
    failed_count: int
    skipped_count: int
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    updated_at: Optional[str]

    @classmethod
    def from_record(cls, record: dict[str, Any] | None) -> "NewsletterCampaign | None":
        if not record or not record.get("id"):
            return None
        return cls(
            id=str(record["id"]),
            admin_user_id=(str(record["admin_user_id"]) if record.get("admin_user_id") else None),
            name=str(record.get("name") or ""),
            subject=str(record.get("subject") or ""),
            body_text=str(record.get("body_text") or ""),
            action_label=str(record.get("action_label") or ""),
            action_url=str(record.get("action_url") or ""),
            target_mode=str(record.get("target_mode") or "all_active"),
            status=str(record.get("status") or "draft"),
            target_count=int(record.get("target_count") or 0),
            pending_count=int(record.get("pending_count") or 0),
            processing_count=int(record.get("processing_count") or 0),
            sent_count=int(record.get("sent_count") or 0),
            failed_count=int(record.get("failed_count") or 0),
            skipped_count=int(record.get("skipped_count") or 0),
            created_at=record.get("created_at"),
            started_at=record.get("started_at"),
            completed_at=record.get("completed_at"),
            updated_at=record.get("updated_at"),
        )

    @property
    def finished_count(self) -> int:
        return self.sent_count + self.failed_count + self.skipped_count

    @property
    def progress_percent(self) -> int:
        if self.target_count <= 0:
            return 0
        return min(100, round((self.finished_count / self.target_count) * 100))


@dataclass(frozen=True)
class NewsletterCampaignRecipient:
    id: str
    campaign_id: str
    subscriber_id: str
    email: str
    full_name: str
    unsubscribe_token: Optional[str]
    status: str
    attempt_count: int
    error_message: Optional[str]
    sent_at: Optional[str]
    created_at: Optional[str]

    @classmethod
    def from_record(
        cls, record: dict[str, Any] | None
    ) -> "NewsletterCampaignRecipient | None":
        if not record or not record.get("id"):
            return None
        return cls(
            id=str(record["id"]),
            campaign_id=str(record.get("campaign_id") or ""),
            subscriber_id=str(record.get("subscriber_id") or ""),
            email=str(record.get("email") or ""),
            full_name=str(record.get("full_name") or ""),
            unsubscribe_token=(
                str(record["unsubscribe_token"])
                if record.get("unsubscribe_token")
                else None
            ),
            status=str(record.get("status") or "pending"),
            attempt_count=int(record.get("attempt_count") or 0),
            error_message=(str(record["error_message"]) if record.get("error_message") else None),
            sent_at=record.get("sent_at"),
            created_at=record.get("created_at"),
        )


@dataclass(frozen=True)
class NewsletterCampaignPage:
    rows: tuple[NewsletterCampaign, ...]
    page: int
    per_page: int
    total: int
    total_pages: int


@dataclass(frozen=True)
class CampaignBatchResult:
    campaign: NewsletterCampaign
    claimed: int
    sent: int
    failed: int
    skipped: int
    daily_sent: int
    daily_limit: int
    stop_reason: Optional[str] = None
