"""Contact Center business rules; no Flask or Supabase imports are allowed here."""

from __future__ import annotations

import hashlib
import hmac
import html
import os
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse

try:
    from email_validator import EmailNotValidError, validate_email
except ImportError:  # pragma: no cover
    EmailNotValidError = ValueError
    validate_email = None

from app.models.contact_model import (
    ContactMessage,
    ContactMessagePage,
    ContactPageSettings,
    ContactReply,
)
from app.repositories.contact_repository import ContactMigrationRequired, ContactRepository
from app.services.email_service import send_transactional_email
from app.services.storefront_media_service import (
    StorefrontMediaService,
    StorefrontMediaValidationError,
)


class ContactValidationError(ValueError):
    pass


class ContactRateLimitError(RuntimeError):
    pass


class ContactSendError(RuntimeError):
    pass


@dataclass(frozen=True)
class PublicContactResponse:
    code: str
    message: str
    reference: str = ""
    created: bool = False


@dataclass(frozen=True)
class AdminContactDetail:
    message: ContactMessage
    replies: tuple[ContactReply, ...]


class _IframeSrcParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.src = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.src or tag.lower() != "iframe":
            return
        values = {str(key).lower(): str(value or "") for key, value in attrs}
        self.src = values.get("src", "").strip()


class ContactService:
    ALLOWED_THEMES = {"ink", "rose", "espresso"}
    ALLOWED_STATUSES = {"new", "open", "replied", "closed", "spam"}

    def __init__(self, repository: ContactRepository | None = None) -> None:
        self.repository = repository or ContactRepository()

    @staticmethod
    def is_mail_configured() -> bool:
        return bool(
            os.getenv("MAIL_SENDER_EMAIL", "").strip()
            and os.getenv("MAIL_APP_PASSWORD", "").strip()
        )

    @staticmethod
    def _clean_text(value: str, *, max_length: int, required: bool = False) -> str:
        text = " ".join(str(value or "").replace("\x00", " ").split())
        text = text[:max_length]
        if required and not text:
            raise ContactValidationError("Vui lòng nhập đầy đủ thông tin bắt buộc.")
        return text

    @staticmethod
    def _clean_multiline(value: str, *, max_length: int, required: bool = False) -> str:
        raw = str(value or "").replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
        lines = [" ".join(line.split()) for line in raw.split("\n")]
        text = "\n".join(line for line in lines if line).strip()[:max_length]
        if required and not text:
            raise ContactValidationError("Vui lòng nhập đầy đủ thông tin bắt buộc.")
        return text

    @staticmethod
    def _normalize_email(value: str) -> str:
        value = str(value or "").strip().lower()
        if not value or len(value) > 254:
            raise ContactValidationError("Vui lòng nhập địa chỉ email hợp lệ.")
        if validate_email is not None:
            try:
                return validate_email(value, check_deliverability=False).normalized.lower()
            except EmailNotValidError as exc:
                raise ContactValidationError("Vui lòng nhập địa chỉ email hợp lệ.") from exc
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
            raise ContactValidationError("Vui lòng nhập địa chỉ email hợp lệ.")
        return value

    @staticmethod
    def _clean_phone(value: str) -> str:
        value = " ".join(str(value or "").split())[:30]
        if value and not re.match(r"^[+()0-9 .-]{7,30}$", value):
            raise ContactValidationError("Số điện thoại chưa đúng định dạng.")
        return value

    @staticmethod
    def _fingerprint(remote_address: str, user_agent: str) -> str:
        secret = os.getenv("SECRET_KEY", "").strip()
        if not secret:
            raise RuntimeError("SECRET_KEY chưa được cấu hình cho Contact Center.")
        raw = f"{remote_address or 'unknown'}|{(user_agent or '')[:180]}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()

    @staticmethod
    def _extract_map_url(value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        candidate = raw
        if "<" in raw:
            parser = _IframeSrcParser()
            try:
                parser.feed(raw)
            except Exception as exc:
                raise ContactValidationError("Mã nhúng Google Maps không hợp lệ.") from exc
            candidate = parser.src
        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower().rstrip(".")
        allowed_host = host == "google.com" or host.endswith(".google.com")
        if parsed.scheme != "https" or not allowed_host or not parsed.path.startswith("/maps/embed"):
            raise ContactValidationError(
                "Hãy dán mã iframe hoặc URL nhúng lấy từ Google Maps → Chia sẻ → Nhúng bản đồ."
            )
        return candidate[:2500]

    @staticmethod
    def _clean_directions_url(value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return "https://www.google.com/maps"
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower().rstrip(".")
        allowed = (
            host == "google.com"
            or host.endswith(".google.com")
            or host == "maps.app.goo.gl"
            or (host == "goo.gl" and parsed.path.startswith("/maps"))
        )
        if parsed.scheme != "https" or not allowed:
            raise ContactValidationError("Liên kết chỉ đường phải là liên kết Google Maps HTTPS.")
        return raw[:2500]

    @staticmethod
    def _clean_hero_media_url(value: str) -> str:
        try:
            return StorefrontMediaService.normalize_media_url(
                value, allow_video=False
            )
        except StorefrontMediaValidationError as exc:
            raise ContactValidationError(str(exc)) from exc

    @classmethod
    def _clean_topics(cls, value: str | list[str] | tuple[str, ...]) -> list[str]:
        raw = value if isinstance(value, (list, tuple)) else str(value or "").splitlines()
        topics: list[str] = []
        seen: set[str] = set()
        for item in raw:
            topic = cls._clean_text(str(item), max_length=80)
            key = topic.casefold()
            if not topic or key in seen:
                continue
            seen.add(key)
            topics.append(topic)
            if len(topics) == 12:
                break
        if not topics:
            raise ContactValidationError("Cần có ít nhất một chủ đề liên hệ.")
        return topics

    def get_public_settings(self) -> ContactPageSettings:
        return self.repository.get_settings()

    def count_unread(self) -> int:
        return self.repository.count_unread()

    def save_settings(
        self, *, data: dict[str, str], admin_user_id: str | None
    ) -> ContactPageSettings:
        theme = str(data.get("theme") or "ink").strip().lower()
        if theme not in self.ALLOWED_THEMES:
            theme = "ink"
        payload = {
            "eyebrow": self._clean_text(data.get("eyebrow", ""), max_length=80, required=True),
            "title": self._clean_text(data.get("title", ""), max_length=120, required=True),
            "accent_text": self._clean_text(data.get("accent_text", ""), max_length=80, required=True),
            "description": self._clean_multiline(data.get("description", ""), max_length=700, required=True),
            "form_eyebrow": self._clean_text(data.get("form_eyebrow", ""), max_length=80, required=True),
            "form_title": self._clean_text(data.get("form_title", ""), max_length=140, required=True),
            "form_description": self._clean_multiline(data.get("form_description", ""), max_length=500, required=True),
            "map_title": self._clean_text(data.get("map_title", ""), max_length=120, required=True),
            "address": self._clean_multiline(data.get("address", ""), max_length=500, required=True),
            "contact_email": self._normalize_email(data.get("contact_email", "")),
            "contact_phone": self._clean_phone(data.get("contact_phone", "")),
            "business_hours": self._clean_multiline(data.get("business_hours", ""), max_length=300, required=True),
            "response_note": self._clean_text(data.get("response_note", ""), max_length=220, required=True),
            "hero_media_url": self._clean_hero_media_url(data.get("hero_media_url", "")),
            "map_embed_url": self._extract_map_url(data.get("map_embed", "")),
            "directions_url": self._clean_directions_url(data.get("directions_url", "")),
            "theme": theme,
            "topics": self._clean_topics(data.get("topics", "")),
        }
        return self.repository.save_settings(payload, admin_user_id=admin_user_id)

    def submit(
        self,
        *,
        full_name: str,
        email: str,
        phone: str,
        topic: str,
        message: str,
        remote_address: str,
        user_agent: str,
        honeypot: str = "",
    ) -> PublicContactResponse:
        if honeypot:
            return PublicContactResponse(
                code="accepted", message="GUAMAISON đã nhận được lời nhắn của bạn."
            )
        name = self._clean_text(full_name, max_length=100, required=True)
        if len(name) < 2:
            raise ContactValidationError("Vui lòng nhập họ và tên đầy đủ hơn.")
        normalized_email = self._normalize_email(email)
        clean_phone = self._clean_phone(phone)
        clean_message = self._clean_multiline(message, max_length=4000, required=True)
        if len(clean_message) < 10:
            raise ContactValidationError("Lời nhắn cần ít nhất 10 ký tự.")
        settings = self.repository.get_settings()
        allowed = {item.casefold(): item for item in settings.topics}
        selected = self._clean_text(topic, max_length=80).casefold()
        clean_topic = allowed.get(selected) or (settings.topics[-1] if settings.topics else "Khác")
        result = self.repository.submit_message(
            full_name=name,
            email=normalized_email,
            phone=clean_phone,
            topic=clean_topic,
            message=clean_message,
            fingerprint=self._fingerprint(remote_address, user_agent),
        )
        if result.code == "rate_limited":
            raise ContactRateLimitError(
                "Bạn đã gửi nhiều lời nhắn trong thời gian ngắn. Vui lòng thử lại sau."
            )
        if result.code != "created" or not result.message_id:
            raise ContactValidationError("Không thể ghi nhận lời nhắn này. Vui lòng kiểm tra lại.")
        reference = "GM-" + result.message_id.replace("-", "")[:8].upper()
        return PublicContactResponse(
            code="created",
            message="Cảm ơn bạn. GUAMAISON đã nhận được lời nhắn và sẽ phản hồi sớm.",
            reference=reference,
            created=True,
        )

    def admin_list(
        self,
        *,
        page: int,
        per_page: int,
        query_text: str,
        status: str,
        topic: str,
        unread_only: bool,
    ) -> tuple[ContactMessagePage, dict[str, int], ContactPageSettings]:
        return (
            self.repository.list_messages(
                page=max(1, page),
                per_page=min(50, max(10, per_page)),
                query_text=query_text,
                status=status,
                topic=topic,
                unread_only=unread_only,
            ),
            self.repository.stats(),
            self.repository.get_settings(),
        )

    def admin_detail(self, message_id: str, *, mark_read: bool = True) -> AdminContactDetail | None:
        message = self.repository.get_message(message_id)
        if message is None:
            return None
        if mark_read and message.is_unread:
            self.repository.mark_read(message_id)
            message = self.repository.get_message(message_id) or message
        return AdminContactDetail(
            message=message,
            replies=self.repository.list_replies(message_id),
        )

    def update_message(self, *, message_id: str, status: str, admin_note: str) -> ContactMessage:
        normalized = str(status or "").strip().lower()
        if normalized not in self.ALLOWED_STATUSES:
            raise ContactValidationError("Trạng thái tin nhắn không hợp lệ.")
        note = self._clean_multiline(admin_note, max_length=2000)
        updated = self.repository.update_message(message_id, status=normalized, admin_note=note)
        if updated is None:
            raise ContactValidationError("Không tìm thấy tin nhắn liên hệ.")
        return updated

    @staticmethod
    def _reply_html(message: ContactMessage, body: str) -> str:
        safe_name = html.escape(message.full_name or "bạn")
        safe_body = "<br>".join(html.escape(body).splitlines())
        return f"""<!doctype html><html lang=\"vi\"><body style=\"margin:0;background:#f4f1ec;font-family:Arial,sans-serif;color:#181716\"><table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\"><tr><td style=\"padding:32px 16px\"><table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:640px;margin:auto;background:#fff;border:1px solid #ded9d1;border-radius:20px\"><tr><td style=\"padding:36px\"><p style=\"margin:0 0 24px;font-size:12px;font-weight:800;letter-spacing:.18em\">GUAMAISON · CUSTOMER CARE</p><h1 style=\"margin:0 0 18px;font-size:28px\">Xin chào {safe_name},</h1><div style=\"font-size:15px;line-height:1.8;color:#4d4944\">{safe_body}</div><p style=\"margin:30px 0 0;padding-top:20px;border-top:1px solid #e6e1da;font-size:12px;color:#77716a\">Email này được gửi để phản hồi lời nhắn của bạn trên GUAMAISON.</p></td></tr></table></td></tr></table></body></html>"""

    def send_reply(
        self,
        *,
        message_id: str,
        admin_user_id: str | None,
        subject: str,
        body_text: str,
    ) -> None:
        message = self.repository.get_message(message_id)
        if message is None:
            raise ContactValidationError("Không tìm thấy tin nhắn liên hệ.")
        clean_subject = self._clean_text(subject, max_length=160, required=True)
        clean_body = self._clean_multiline(body_text, max_length=8000, required=True)
        reply = self.repository.create_reply(
            message_id=message_id,
            admin_user_id=admin_user_id,
            subject=clean_subject,
            body_text=clean_body,
        )
        sent = False
        error_message = "SMTP chưa gửi được email."
        try:
            sent = send_transactional_email(
                recipient_email=message.email,
                subject=clean_subject,
                html_body=self._reply_html(message, clean_body),
                text_body=clean_body,
                reply_to=os.getenv("MAIL_SENDER_EMAIL", "").strip() or None,
            )
        except Exception as exc:
            error_message = str(exc)[:500] or error_message
        self.repository.finish_reply(reply.id, sent=sent, error_message=None if sent else error_message)
        if not sent:
            raise ContactSendError(
                "Nội dung đã được lưu nhưng email chưa gửi được. Hãy kiểm tra SMTP rồi gửi lại."
            )
