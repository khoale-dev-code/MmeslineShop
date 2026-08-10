"""Newsletter business rules; this module has no Flask or Supabase imports."""

from __future__ import annotations

import hashlib
import hmac
import html
import os
import re
from dataclasses import dataclass
from urllib.parse import urljoin

try:
    from email_validator import EmailNotValidError, validate_email
except ImportError:  # pragma: no cover - project requirements already include it
    EmailNotValidError = ValueError
    validate_email = None

from app.models.newsletter_model import NewsletterMessage, NewsletterPage, NewsletterSubscriber
from app.repositories.newsletter_repository import NewsletterRepository
from app.services.email_service import send_transactional_email


class NewsletterValidationError(ValueError):
    pass


class NewsletterRateLimitError(RuntimeError):
    pass


class NewsletterSendError(RuntimeError):
    pass


@dataclass(frozen=True)
class PublicSubscriptionResponse:
    code: str
    message: str
    created: bool = False


@dataclass(frozen=True)
class AdminNewsletterDetail:
    subscriber: NewsletterSubscriber
    messages: tuple[NewsletterMessage, ...]


class NewsletterService:
    CONSENT_VERSION = "newsletter-v11-2026-08"

    def __init__(self, repository: NewsletterRepository | None = None) -> None:
        self.repository = repository or NewsletterRepository()

    @staticmethod
    def is_mail_configured() -> bool:
        return bool(
            os.getenv("MAIL_SENDER_EMAIL", "").strip()
            and os.getenv("MAIL_APP_PASSWORD", "").strip()
        )

    @staticmethod
    def _normalize_email(value: str) -> str:
        value = str(value or "").strip().lower()
        if not value or len(value) > 254:
            raise NewsletterValidationError("Vui lòng nhập địa chỉ email hợp lệ.")
        if validate_email is not None:
            try:
                return validate_email(value, check_deliverability=False).normalized.lower()
            except EmailNotValidError as exc:
                raise NewsletterValidationError("Vui lòng nhập địa chỉ email hợp lệ.") from exc
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
            raise NewsletterValidationError("Vui lòng nhập địa chỉ email hợp lệ.")
        return value

    @staticmethod
    def _clean_name(value: str) -> str:
        value = " ".join(str(value or "").split())
        return value[:100]

    @staticmethod
    def _clean_label(value: str, default: str, max_length: int) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_./-]+", "-", str(value or "").strip())
        return (cleaned.strip("-") or default)[:max_length]

    @staticmethod
    def _fingerprint(remote_address: str, user_agent: str) -> str:
        secret = os.getenv("SECRET_KEY", "guamaison-newsletter-v11")
        raw = f"{remote_address or 'unknown'}|{(user_agent or '')[:180]}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()

    def subscribe(
        self,
        *,
        email: str,
        full_name: str,
        consent: bool,
        source: str,
        locale: str,
        remote_address: str,
        user_agent: str,
        honeypot: str = "",
    ) -> PublicSubscriptionResponse:
        if honeypot:
            return PublicSubscriptionResponse(
                code="accepted", message="Cảm ơn bạn đã đăng ký nhận tin."
            )
        if not consent:
            raise NewsletterValidationError("Bạn cần đồng ý nhận email từ GUAMAISON.")
        normalized_email = self._normalize_email(email)
        result = self.repository.subscribe(
            email=normalized_email,
            full_name=self._clean_name(full_name),
            source=self._clean_label(source, "storefront", 80),
            locale=self._clean_label(locale, "vi", 12),
            consent_version=self.CONSENT_VERSION,
            fingerprint=self._fingerprint(remote_address, user_agent),
        )
        if result.code == "rate_limited":
            raise NewsletterRateLimitError("Bạn thao tác quá nhanh. Vui lòng thử lại sau ít phút.")
        if result.code == "blocked":
            return PublicSubscriptionResponse(
                code="blocked",
                message="Không thể đăng ký email này. Vui lòng liên hệ GUAMAISON để được hỗ trợ.",
            )
        if result.code == "already_active":
            return PublicSubscriptionResponse(
                code="already_active",
                message="Email này đã nằm trong danh sách nhận tin của GUAMAISON.",
            )
        if result.code == "reactivated":
            return PublicSubscriptionResponse(
                code="reactivated",
                message="Chào mừng bạn quay lại danh sách nhận tin GUAMAISON.",
                created=True,
            )
        if result.code != "created":
            raise RuntimeError("Không thể hoàn tất đăng ký nhận tin.")
        return PublicSubscriptionResponse(
            code="created",
            message="Đăng ký thành công. Tin mới từ GUAMAISON sẽ sớm đến hộp thư của bạn.",
            created=True,
        )

    def unsubscribe(self, token: str) -> bool:
        token = str(token or "").strip()
        if not re.match(r"^[0-9a-fA-F-]{36}$", token):
            raise NewsletterValidationError("Liên kết hủy đăng ký không hợp lệ.")
        return self.repository.unsubscribe(token)

    def admin_list(
        self,
        *,
        page: int,
        per_page: int,
        query_text: str,
        status: str,
        unread_only: bool,
    ) -> tuple[NewsletterPage, dict[str, int]]:
        page = max(1, int(page or 1))
        per_page = min(50, max(10, int(per_page or 20)))
        return (
            self.repository.list_subscribers(
                page=page,
                per_page=per_page,
                query_text=query_text,
                status=status,
                unread_only=unread_only,
            ),
            self.repository.stats(),
        )

    def admin_detail(self, subscriber_id: str, *, mark_read: bool = True) -> AdminNewsletterDetail | None:
        subscriber = self.repository.get_subscriber(str(subscriber_id))
        if subscriber is None:
            return None
        if mark_read and subscriber.is_unread:
            self.repository.mark_read(subscriber.id)
            subscriber = self.repository.get_subscriber(subscriber.id) or subscriber
        return AdminNewsletterDetail(
            subscriber=subscriber,
            messages=self.repository.list_messages(subscriber.id),
        )

    @staticmethod
    def _reply_html(subscriber: NewsletterSubscriber, message: str, unsubscribe_url: str) -> str:
        safe_name = html.escape(subscriber.full_name or "Quý khách")
        safe_message = "<br>".join(html.escape(message).splitlines())
        safe_unsubscribe = html.escape(unsubscribe_url, quote=True)
        return f"""<!doctype html>
<html lang=\"vi\"><body style=\"margin:0;background:#f6f3ec;color:#171a17;font-family:Arial,Helvetica,sans-serif\">
<table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"background:#f6f3ec;padding:28px 12px\"><tr><td align=\"center\">
<table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:620px;background:#fff;border:1px solid #ded8cc;border-radius:22px;overflow:hidden\">
<tr><td style=\"padding:26px 30px;background:#171a17;color:#fff\"><strong style=\"font-size:18px;letter-spacing:.14em\">GUAMAISON</strong><div style=\"margin-top:7px;color:#c9a96b;font-size:11px;letter-spacing:.16em;text-transform:uppercase\">Private notes</div></td></tr>
<tr><td style=\"padding:34px 30px\"><p style=\"margin:0 0 18px;font-size:15px;font-weight:700\">Xin chào {safe_name},</p><div style=\"font-size:15px;line-height:1.8;color:#505650\">{safe_message}</div><div style=\"height:1px;background:#ece7dd;margin:30px 0 20px\"></div><p style=\"margin:0;color:#787e78;font-size:12px;line-height:1.7\">Email được gửi từ hộp thư chăm sóc khách hàng GUAMAISON. <a href=\"{safe_unsubscribe}\" style=\"color:#171a17\">Hủy nhận bản tin</a>.</p></td></tr>
</table></td></tr></table></body></html>"""

    def send_admin_reply(
        self,
        *,
        subscriber_id: str,
        admin_user_id: str | None,
        subject: str,
        message: str,
        base_url: str,
    ) -> NewsletterMessage:
        subject = " ".join(str(subject or "").split())[:160]
        message = str(message or "").strip()[:10000]
        if len(subject) < 3:
            raise NewsletterValidationError("Tiêu đề email cần ít nhất 3 ký tự.")
        if len(message) < 10:
            raise NewsletterValidationError("Nội dung email cần ít nhất 10 ký tự.")
        subscriber = self.repository.get_subscriber(str(subscriber_id))
        if subscriber is None:
            raise NewsletterValidationError("Không tìm thấy người đăng ký.")
        if subscriber.status != "active":
            raise NewsletterValidationError(
                "Khách hàng đã hủy nhận tin hoặc email đang bị chặn; hệ thống không gửi để tôn trọng lựa chọn của khách."
            )
        if not subscriber.unsubscribe_token:
            raise NewsletterValidationError("Người đăng ký chưa có mã hủy nhận tin hợp lệ.")
        history = self.repository.create_message(
            subscriber_id=subscriber.id,
            admin_user_id=admin_user_id,
            subject=subject,
            body_text=message,
        )
        unsubscribe_url = urljoin(
            base_url.rstrip("/") + "/",
            f"newsletter/unsubscribe/{subscriber.unsubscribe_token}",
        )
        sent = send_transactional_email(
            recipient_email=subscriber.email,
            subject=subject,
            html_body=self._reply_html(subscriber, message, unsubscribe_url),
            text_body=(
                f"Xin chào {subscriber.full_name or 'Quý khách'},\n\n{message}\n\n"
                f"Hủy nhận bản tin: {unsubscribe_url}\n\nGUAMAISON"
            ),
        )
        self.repository.finish_message(
            history.id,
            sent=sent,
            error_message=None if sent else "SMTP chưa gửi được email. Kiểm tra cấu hình và thử lại.",
        )
        if not sent:
            raise NewsletterSendError(
                "Không gửi được email. Nội dung đã được lưu để Admin kiểm tra và gửi lại."
            )
        return history
