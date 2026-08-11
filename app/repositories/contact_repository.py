"""The only Contact Center layer allowed to access Supabase."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.models.contact_model import (
    ContactMessage,
    ContactMessagePage,
    ContactPageSettings,
    ContactReply,
    ContactSubmissionResult,
)
from app.utils.supabase_client import get_supabase_admin


class ContactRepositoryError(RuntimeError):
    pass


class ContactMigrationRequired(ContactRepositoryError):
    pass


class ContactRepository:
    def __init__(self, client: Any | None = None) -> None:
        self._client = client or get_supabase_admin()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _clean_search(value: str) -> str:
        value = re.sub(r"[^\w\s@+.-]+", " ", str(value or ""), flags=re.UNICODE)
        return " ".join(value.split())[:120]

    @staticmethod
    def _raise(exc: Exception) -> None:
        message = str(exc)
        if any(
            marker in message
            for marker in (
                "contact_page_settings",
                "contact_messages",
                "contact_replies",
                "contact_submit_message_v13",
            )
        ):
            raise ContactMigrationRequired(
                "Chưa chạy migration Contact Center v13 trên Supabase."
            ) from exc
        raise ContactRepositoryError(message) from exc

    def get_settings(self) -> ContactPageSettings:
        try:
            response = (
                self._client.table("contact_page_settings")
                .select("*")
                .eq("id", "primary")
                .limit(1)
                .execute()
            )
            return ContactPageSettings.from_record(
                response.data[0] if response.data else None
            )
        except Exception as exc:
            self._raise(exc)

    def save_settings(
        self, data: dict[str, Any], *, admin_user_id: str | None
    ) -> ContactPageSettings:
        payload = dict(data)
        payload.update(
            {
                "id": "primary",
                "updated_by": admin_user_id,
                "updated_at": self._now_iso(),
            }
        )
        try:
            response = (
                self._client.table("contact_page_settings")
                .upsert(payload, on_conflict="id")
                .execute()
            )
            return ContactPageSettings.from_record(
                (response.data or [payload])[0]
            )
        except Exception as exc:
            self._raise(exc)

    def submit_message(
        self,
        *,
        full_name: str,
        email: str,
        phone: str,
        topic: str,
        message: str,
        fingerprint: str,
    ) -> ContactSubmissionResult:
        try:
            response = self._client.rpc(
                "contact_submit_message_v13",
                {
                    "p_full_name": full_name,
                    "p_email": email,
                    "p_phone": phone or None,
                    "p_topic": topic,
                    "p_message": message,
                    "p_fingerprint": fingerprint,
                },
            ).execute()
            row = (response.data or [{}])[0]
            return ContactSubmissionResult(
                code=str(row.get("result_code") or "error"),
                message_id=(str(row["contact_message_id"]) if row.get("contact_message_id") else None),
            )
        except Exception as exc:
            self._raise(exc)

    def count_unread(self) -> int:
        try:
            response = (
                self._client.table("contact_messages")
                .select("id", count="exact")
                .eq("is_unread", True)
                .neq("status", "spam")
                .execute()
            )
            return int(response.count or 0)
        except Exception as exc:
            self._raise(exc)

    def stats(self) -> dict[str, int]:
        def count(filters: dict[str, Any]) -> int:
            query = self._client.table("contact_messages").select("id", count="exact")
            for key, value in filters.items():
                query = query.eq(key, value)
            result = query.execute()
            return int(result.count or 0)

        try:
            total = self._client.table("contact_messages").select("id", count="exact").execute()
            unread = (
                self._client.table("contact_messages")
                .select("id", count="exact")
                .eq("is_unread", True)
                .neq("status", "spam")
                .execute()
            )
            return {
                "total": int(total.count or 0),
                "unread": int(unread.count or 0),
                "new": count({"status": "new"}),
                "open": count({"status": "open"}),
                "replied": count({"status": "replied"}),
                "closed": count({"status": "closed"}),
            }
        except Exception as exc:
            self._raise(exc)

    def list_messages(
        self,
        *,
        page: int,
        per_page: int,
        query_text: str = "",
        status: str = "",
        topic: str = "",
        unread_only: bool = False,
    ) -> ContactMessagePage:
        start = (page - 1) * per_page
        end = start + per_page - 1
        try:
            query = self._client.table("contact_messages").select("*", count="exact")
            cleaned = self._clean_search(query_text)
            if cleaned:
                query = query.or_(
                    "full_name.ilike.%{0}%,email.ilike.%{0}%,phone.ilike.%{0}%,message.ilike.%{0}%".format(cleaned)
                )
            if status in {"new", "open", "replied", "closed", "spam"}:
                query = query.eq("status", status)
            if topic:
                query = query.eq("topic", str(topic)[:120])
            if unread_only:
                query = query.eq("is_unread", True)
            response = query.order("created_at", desc=True).range(start, end).execute()
            rows = tuple(
                model
                for model in (ContactMessage.from_record(row) for row in (response.data or []))
                if model is not None
            )
            total = int(response.count or 0)
            return ContactMessagePage(
                rows=rows,
                page=page,
                per_page=per_page,
                total=total,
                total_pages=max(1, (total + per_page - 1) // per_page),
            )
        except Exception as exc:
            self._raise(exc)

    def get_message(self, message_id: str) -> ContactMessage | None:
        try:
            response = (
                self._client.table("contact_messages")
                .select("*")
                .eq("id", message_id)
                .limit(1)
                .execute()
            )
            return ContactMessage.from_record(response.data[0]) if response.data else None
        except Exception as exc:
            self._raise(exc)

    def mark_read(self, message_id: str) -> None:
        now = self._now_iso()
        try:
            (
                self._client.table("contact_messages")
                .update({"is_unread": False, "last_viewed_at": now, "updated_at": now})
                .eq("id", message_id)
                .execute()
            )
        except Exception as exc:
            self._raise(exc)

    def update_message(
        self, message_id: str, *, status: str, admin_note: str
    ) -> ContactMessage | None:
        try:
            response = (
                self._client.table("contact_messages")
                .update(
                    {
                        "status": status,
                        "admin_note": admin_note or "",
                        "is_unread": False,
                        "updated_at": self._now_iso(),
                    }
                )
                .eq("id", message_id)
                .execute()
            )
            return ContactMessage.from_record(response.data[0]) if response.data else None
        except Exception as exc:
            self._raise(exc)

    def list_replies(self, message_id: str) -> tuple[ContactReply, ...]:
        try:
            response = (
                self._client.table("contact_replies")
                .select("*")
                .eq("contact_message_id", message_id)
                .order("created_at", desc=True)
                .limit(50)
                .execute()
            )
            return tuple(
                model
                for model in (ContactReply.from_record(row) for row in (response.data or []))
                if model is not None
            )
        except Exception as exc:
            self._raise(exc)

    def create_reply(
        self,
        *,
        message_id: str,
        admin_user_id: str | None,
        subject: str,
        body_text: str,
    ) -> ContactReply:
        try:
            response = self._client.table("contact_replies").insert(
                {
                    "contact_message_id": message_id,
                    "admin_user_id": admin_user_id,
                    "subject": subject,
                    "body_text": body_text,
                    "status": "processing",
                }
            ).execute()
            model = ContactReply.from_record((response.data or [{}])[0])
            if model is None:
                raise ContactRepositoryError("Không tạo được lịch sử phản hồi.")
            return model
        except ContactRepositoryError:
            raise
        except Exception as exc:
            self._raise(exc)

    def finish_reply(
        self, reply_id: str, *, sent: bool, error_message: str | None = None
    ) -> None:
        now = self._now_iso()
        try:
            reply = (
                self._client.table("contact_replies")
                .select("contact_message_id")
                .eq("id", reply_id)
                .limit(1)
                .execute()
            )
            self._client.table("contact_replies").update(
                {
                    "status": "sent" if sent else "failed",
                    "sent_at": now if sent else None,
                    "error_message": None if sent else str(error_message or "Không gửi được email.")[:500],
                    "updated_at": now,
                }
            ).eq("id", reply_id).execute()
            if sent and reply.data:
                self._client.table("contact_messages").update(
                    {
                        "status": "replied",
                        "replied_at": now,
                        "is_unread": False,
                        "updated_at": now,
                    }
                ).eq("id", reply.data[0]["contact_message_id"]).execute()
        except Exception as exc:
            self._raise(exc)
