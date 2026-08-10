"""The only newsletter layer allowed to call Supabase."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.models.newsletter_model import (
    NewsletterCampaign,
    NewsletterCampaignPage,
    NewsletterCampaignRecipient,
    NewsletterMessage,
    NewsletterPage,
    NewsletterSubscriber,
    SubscriptionResult,
)
from app.utils.supabase_client import get_supabase_admin


class NewsletterRepositoryError(RuntimeError):
    pass


class NewsletterMigrationRequired(NewsletterRepositoryError):
    pass


class NewsletterRepository:
    def __init__(self, client: Any | None = None) -> None:
        self._client = client or get_supabase_admin()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _clean_search(value: str) -> str:
        value = re.sub(r"[,().%*'\"]+", " ", str(value or ""))
        return " ".join(value.split())[:120]

    @staticmethod
    def _raise(exc: Exception) -> None:
        message = str(exc)
        if any(
            marker in message
            for marker in (
                "newsletter_subscribers",
                "newsletter_messages",
                "newsletter_rate_limits",
                "newsletter_subscribe_v11",
                "newsletter_unsubscribe_v11",
                "newsletter_campaigns",
                "newsletter_campaign_recipients",
                "newsletter_prepare_campaign_v12",
                "newsletter_claim_campaign_batch_v12",
                "newsletter_refresh_campaign_v12",
            )
        ):
            raise NewsletterMigrationRequired(
                "Chưa chạy đầy đủ migration Newsletter v11/v12 trên Supabase."
            ) from exc
        raise NewsletterRepositoryError(message) from exc

    def subscribe(
        self,
        *,
        email: str,
        full_name: str,
        source: str,
        locale: str,
        consent_version: str,
        fingerprint: str,
    ) -> SubscriptionResult:
        try:
            response = self._client.rpc(
                "newsletter_subscribe_v11",
                {
                    "p_email": email,
                    "p_full_name": full_name or None,
                    "p_source": source,
                    "p_locale": locale,
                    "p_consent_version": consent_version,
                    "p_fingerprint": fingerprint or None,
                },
            ).execute()
            row = (response.data or [{}])[0]
            return SubscriptionResult(
                code=str(row.get("result_code") or "error"),
                subscriber_id=(str(row["subscription_id"]) if row.get("subscription_id") else None),
                status=(str(row["subscription_status"]) if row.get("subscription_status") else None),
            )
        except Exception as exc:
            self._raise(exc)

    def unsubscribe(self, token: str) -> bool:
        try:
            response = self._client.rpc(
                "newsletter_unsubscribe_v11", {"p_token": token}
            ).execute()
            row = (response.data or [{}])[0]
            return bool(row.get("unsubscribed"))
        except Exception as exc:
            self._raise(exc)

    def count_unread(self) -> int:
        try:
            response = (
                self._client.table("newsletter_subscribers")
                .select("id", count="exact")
                .eq("is_unread", True)
                .execute()
            )
            return int(response.count or 0)
        except Exception as exc:
            self._raise(exc)

    def stats(self) -> dict[str, int]:
        def count(filters: dict[str, Any]) -> int:
            query = self._client.table("newsletter_subscribers").select("id", count="exact")
            for key, value in filters.items():
                query = query.eq(key, value)
            result = query.execute()
            return int(result.count or 0)

        try:
            direct_sent = (
                self._client.table("newsletter_messages")
                .select("id", count="exact")
                .eq("status", "sent")
                .execute()
            )
            campaign_sent = (
                self._client.table("newsletter_campaign_recipients")
                .select("id", count="exact")
                .eq("status", "sent")
                .execute()
            )
            return {
                "active": count({"status": "active"}),
                "unread": count({"is_unread": True}),
                "unsubscribed": count({"status": "unsubscribed"}),
                "sent": int(direct_sent.count or 0) + int(campaign_sent.count or 0),
            }
        except Exception as exc:
            self._raise(exc)

    def list_subscribers(
        self,
        *,
        page: int,
        per_page: int,
        query_text: str = "",
        status: str = "",
        unread_only: bool = False,
    ) -> NewsletterPage:
        start = (page - 1) * per_page
        end = start + per_page - 1
        try:
            query = self._client.table("newsletter_subscribers").select("*", count="exact")
            cleaned = self._clean_search(query_text)
            if cleaned:
                query = query.or_(f"email.ilike.%{cleaned}%,full_name.ilike.%{cleaned}%")
            if status in {"active", "unsubscribed", "blocked"}:
                query = query.eq("status", status)
            if unread_only:
                query = query.eq("is_unread", True)
            response = query.order("created_at", desc=True).range(start, end).execute()
            rows = tuple(
                model
                for model in (NewsletterSubscriber.from_record(row) for row in (response.data or []))
                if model is not None
            )
            total = int(response.count or 0)
            return NewsletterPage(
                rows=rows,
                page=page,
                per_page=per_page,
                total=total,
                total_pages=max(1, (total + per_page - 1) // per_page),
            )
        except Exception as exc:
            self._raise(exc)

    def get_subscriber(self, subscriber_id: str) -> NewsletterSubscriber | None:
        try:
            response = (
                self._client.table("newsletter_subscribers")
                .select("*")
                .eq("id", subscriber_id)
                .limit(1)
                .execute()
            )
            return NewsletterSubscriber.from_record(response.data[0]) if response.data else None
        except Exception as exc:
            self._raise(exc)

    def mark_read(self, subscriber_id: str) -> None:
        try:
            (
                self._client.table("newsletter_subscribers")
                .update({"is_unread": False, "last_viewed_at": self._now_iso(), "updated_at": self._now_iso()})
                .eq("id", subscriber_id)
                .execute()
            )
        except Exception as exc:
            self._raise(exc)

    def list_messages(self, subscriber_id: str) -> tuple[NewsletterMessage, ...]:
        try:
            response = (
                self._client.table("newsletter_messages")
                .select("*")
                .eq("subscriber_id", subscriber_id)
                .order("created_at", desc=True)
                .limit(50)
                .execute()
            )
            return tuple(
                model
                for model in (NewsletterMessage.from_record(row) for row in (response.data or []))
                if model is not None
            )
        except Exception as exc:
            self._raise(exc)

    def create_message(
        self,
        *,
        subscriber_id: str,
        admin_user_id: str | None,
        subject: str,
        body_text: str,
    ) -> NewsletterMessage:
        try:
            response = self._client.table("newsletter_messages").insert(
                {
                    "subscriber_id": subscriber_id,
                    "admin_user_id": admin_user_id,
                    "subject": subject,
                    "body_text": body_text,
                    "status": "processing",
                }
            ).execute()
            model = NewsletterMessage.from_record((response.data or [{}])[0])
            if model is None:
                raise NewsletterRepositoryError("Không tạo được lịch sử email.")
            return model
        except NewsletterRepositoryError:
            raise
        except Exception as exc:
            self._raise(exc)

    def finish_message(self, message_id: str, *, sent: bool, error_message: str | None = None) -> None:
        now = self._now_iso()
        data = {
            "status": "sent" if sent else "failed",
            "sent_at": now if sent else None,
            "error_message": None if sent else str(error_message or "Không gửi được email.")[:500],
            "updated_at": now,
        }
        try:
            self._client.table("newsletter_messages").update(data).eq("id", message_id).execute()
            if sent:
                message = (
                    self._client.table("newsletter_messages")
                    .select("subscriber_id")
                    .eq("id", message_id)
                    .limit(1)
                    .execute()
                )
                if message.data:
                    self._client.table("newsletter_subscribers").update(
                        {"last_replied_at": now, "updated_at": now}
                    ).eq("id", message.data[0]["subscriber_id"]).execute()
        except Exception as exc:
            self._raise(exc)

    def create_campaign(
        self,
        *,
        admin_user_id: str | None,
        name: str,
        subject: str,
        body_text: str,
        action_label: str,
        action_url: str,
        target_mode: str,
        subscriber_ids: list[str],
    ) -> NewsletterCampaign:
        try:
            response = self._client.table("newsletter_campaigns").insert(
                {
                    "admin_user_id": admin_user_id,
                    "name": name,
                    "subject": subject,
                    "body_text": body_text,
                    "action_label": action_label or None,
                    "action_url": action_url or None,
                    "target_mode": target_mode,
                    "status": "draft",
                }
            ).execute()
            campaign = NewsletterCampaign.from_record((response.data or [{}])[0])
            if campaign is None:
                raise NewsletterRepositoryError("Không tạo được chiến dịch email.")

            self._client.rpc(
                "newsletter_prepare_campaign_v12",
                {
                    "p_campaign_id": campaign.id,
                    "p_target_mode": target_mode,
                    "p_subscriber_ids": subscriber_ids or None,
                },
            ).execute()
            refreshed = self.get_campaign(campaign.id)
            if refreshed is None:
                raise NewsletterRepositoryError("Không đọc lại được chiến dịch email.")
            return refreshed
        except NewsletterRepositoryError:
            raise
        except Exception as exc:
            self._raise(exc)

    def list_campaigns(self, *, page: int, per_page: int) -> NewsletterCampaignPage:
        start = (page - 1) * per_page
        end = start + per_page - 1
        try:
            response = (
                self._client.table("newsletter_campaigns")
                .select("*", count="exact")
                .order("created_at", desc=True)
                .range(start, end)
                .execute()
            )
            rows = tuple(
                model
                for model in (
                    NewsletterCampaign.from_record(row) for row in (response.data or [])
                )
                if model is not None
            )
            total = int(response.count or 0)
            return NewsletterCampaignPage(
                rows=rows,
                page=page,
                per_page=per_page,
                total=total,
                total_pages=max(1, (total + per_page - 1) // per_page),
            )
        except Exception as exc:
            self._raise(exc)

    def get_campaign(self, campaign_id: str) -> NewsletterCampaign | None:
        try:
            response = (
                self._client.table("newsletter_campaigns")
                .select("*")
                .eq("id", campaign_id)
                .limit(1)
                .execute()
            )
            return NewsletterCampaign.from_record(response.data[0]) if response.data else None
        except Exception as exc:
            self._raise(exc)

    def list_campaign_recipients(
        self, campaign_id: str, *, limit: int = 100
    ) -> tuple[NewsletterCampaignRecipient, ...]:
        try:
            response = (
                self._client.table("newsletter_campaign_recipients")
                .select("*")
                .eq("campaign_id", campaign_id)
                .order("created_at", desc=False)
                .limit(min(200, max(1, int(limit))))
                .execute()
            )
            return tuple(
                model
                for model in (
                    NewsletterCampaignRecipient.from_record(row)
                    for row in (response.data or [])
                )
                if model is not None
            )
        except Exception as exc:
            self._raise(exc)

    def set_campaign_status(self, campaign_id: str, status: str) -> None:
        try:
            data: dict[str, Any] = {"status": status, "updated_at": self._now_iso()}
            if status == "sending":
                data["started_at"] = self._now_iso()
            (
                self._client.table("newsletter_campaigns")
                .update(data)
                .eq("id", campaign_id)
                .in_("status", ["ready", "sending", "paused"])
                .execute()
            )
        except Exception as exc:
            self._raise(exc)

    def claim_campaign_batch(
        self, campaign_id: str, *, limit: int
    ) -> tuple[NewsletterCampaignRecipient, ...]:
        try:
            response = self._client.rpc(
                "newsletter_claim_campaign_batch_v12",
                {"p_campaign_id": campaign_id, "p_limit": limit},
            ).execute()
            return tuple(
                model
                for model in (
                    NewsletterCampaignRecipient.from_record(row)
                    for row in (response.data or [])
                )
                if model is not None
            )
        except Exception as exc:
            self._raise(exc)

    def finish_campaign_recipient(
        self,
        recipient_id: str,
        *,
        sent: bool,
        error_message: str | None = None,
    ) -> None:
        now = self._now_iso()
        data = {
            "status": "sent" if sent else "failed",
            "sent_at": now if sent else None,
            "error_message": None if sent else str(error_message or "SMTP không gửi được email.")[:500],
            "updated_at": now,
        }
        try:
            (
                self._client.table("newsletter_campaign_recipients")
                .update(data)
                .eq("id", recipient_id)
                .eq("status", "processing")
                .execute()
            )
        except Exception as exc:
            self._raise(exc)

    def refresh_campaign(self, campaign_id: str) -> NewsletterCampaign:
        try:
            response = self._client.rpc(
                "newsletter_refresh_campaign_v12", {"p_campaign_id": campaign_id}
            ).execute()
            row = (response.data or [{}])[0]
            campaign = NewsletterCampaign.from_record(row)
            if campaign is None:
                campaign = self.get_campaign(campaign_id)
            if campaign is None:
                raise NewsletterRepositoryError("Không tìm thấy chiến dịch email.")
            return campaign
        except NewsletterRepositoryError:
            raise
        except Exception as exc:
            self._raise(exc)

    def count_campaign_sent_since(self, since_iso: str) -> int:
        try:
            response = (
                self._client.table("newsletter_campaign_recipients")
                .select("id", count="exact")
                .eq("status", "sent")
                .gte("sent_at", since_iso)
                .execute()
            )
            return int(response.count or 0)
        except Exception as exc:
            self._raise(exc)

    def retry_failed_campaign(self, campaign_id: str) -> NewsletterCampaign:
        try:
            self._client.rpc(
                "newsletter_retry_failed_v12", {"p_campaign_id": campaign_id}
            ).execute()
            return self.refresh_campaign(campaign_id)
        except Exception as exc:
            self._raise(exc)

    def cancel_campaign(self, campaign_id: str) -> NewsletterCampaign:
        try:
            self._client.rpc(
                "newsletter_cancel_campaign_v12", {"p_campaign_id": campaign_id}
            ).execute()
            return self.refresh_campaign(campaign_id)
        except Exception as exc:
            self._raise(exc)
