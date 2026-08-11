"""Newsletter business rules; this module has no Flask or Supabase imports."""

from __future__ import annotations

import hashlib
import hmac
import html
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
from urllib.parse import urlparse

try:
    from email_validator import EmailNotValidError, validate_email
except ImportError:  # pragma: no cover - project requirements already include it
    EmailNotValidError = ValueError
    validate_email = None

from app.models.newsletter_model import (
    CampaignBatchResult,
    NewsletterCampaign,
    NewsletterCampaignPage,
    NewsletterCampaignRecipient,
    NewsletterMessage,
    NewsletterPage,
    NewsletterSubscriber,
)
from app.repositories.newsletter_repository import NewsletterRepository
from app.services.email_service import (
    send_transactional_email,
    send_transactional_email_batch,
)


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


@dataclass(frozen=True)
class AdminCampaignDetail:
    campaign: NewsletterCampaign
    recipients: tuple[NewsletterCampaignRecipient, ...]
    daily_sent: int
    daily_limit: int
    batch_size: int


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
    def mail_sender_email() -> str:
        return os.getenv("MAIL_SENDER_EMAIL", "").strip()

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

    @staticmethod
    def _daily_limit() -> int:
        try:
            value = int(os.getenv("NEWSLETTER_DAILY_SEND_LIMIT", "400"))
        except (TypeError, ValueError):
            value = 400
        return min(500, max(1, value))

    @staticmethod
    def _batch_size() -> int:
        try:
            value = int(os.getenv("NEWSLETTER_BATCH_SIZE", "10"))
        except (TypeError, ValueError):
            value = 10
        return min(25, max(1, value))

    @staticmethod
    def _clean_campaign_name(value: str) -> str:
        value = " ".join(str(value or "").split())[:120]
        if len(value) < 3:
            raise NewsletterValidationError("Tên nội bộ của chiến dịch cần ít nhất 3 ký tự.")
        return value

    @staticmethod
    def _clean_subject(value: str) -> str:
        value = " ".join(str(value or "").split())[:160]
        if len(value) < 3:
            raise NewsletterValidationError("Tiêu đề email cần ít nhất 3 ký tự.")
        return value

    @staticmethod
    def _clean_campaign_body(value: str) -> str:
        value = str(value or "").strip()[:10000]
        if len(value) < 10:
            raise NewsletterValidationError("Nội dung email cần ít nhất 10 ký tự.")
        return value

    @staticmethod
    def _clean_action(label: str, url: str) -> tuple[str, str]:
        label = " ".join(str(label or "").split())[:60]
        url = str(url or "").strip()[:1000]
        if bool(label) != bool(url):
            raise NewsletterValidationError(
                "Nút kêu gọi hành động cần có đủ nhãn và đường dẫn."
            )
        if url:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise NewsletterValidationError("Đường dẫn của nút phải bắt đầu bằng http:// hoặc https://.")
        return label, url

    @staticmethod
    def _normalize_subscriber_ids(values: list[str] | tuple[str, ...]) -> list[str]:
        clean: list[str] = []
        for value in values:
            candidate = str(value or "").strip()
            if re.fullmatch(r"[0-9a-fA-F-]{36}", candidate) and candidate not in clean:
                clean.append(candidate)
        return clean[:500]

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
        target_mode = str(target_mode or "all_active").strip()
        if target_mode not in {"all_active", "selected"}:
            raise NewsletterValidationError("Phạm vi người nhận không hợp lệ.")
        selected_ids = self._normalize_subscriber_ids(subscriber_ids)
        if target_mode == "selected" and not selected_ids:
            raise NewsletterValidationError("Hãy chọn ít nhất một người đang nhận tin.")
        action_label, action_url = self._clean_action(action_label, action_url)
        campaign = self.repository.create_campaign(
            admin_user_id=admin_user_id,
            name=self._clean_campaign_name(name),
            subject=self._clean_subject(subject),
            body_text=self._clean_campaign_body(body_text),
            action_label=action_label,
            action_url=action_url,
            target_mode=target_mode,
            subscriber_ids=selected_ids,
        )
        if campaign.target_count <= 0:
            raise NewsletterValidationError(
                "Không có người đăng ký đang hoạt động trong phạm vi đã chọn."
            )
        return campaign

    def list_campaigns(self, *, page: int, per_page: int = 20) -> NewsletterCampaignPage:
        return self.repository.list_campaigns(
            page=max(1, int(page or 1)),
            per_page=min(50, max(10, int(per_page or 20))),
        )

    def campaign_detail(self, campaign_id: str) -> AdminCampaignDetail | None:
        campaign = self.repository.get_campaign(str(campaign_id))
        if campaign is None:
            return None
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        return AdminCampaignDetail(
            campaign=campaign,
            recipients=self.repository.list_campaign_recipients(campaign.id, limit=100),
            daily_sent=self.repository.count_campaign_sent_since(since),
            daily_limit=self._daily_limit(),
            batch_size=self._batch_size(),
        )

    @staticmethod
    def _campaign_email_html(
        campaign: NewsletterCampaign,
        recipient: NewsletterCampaignRecipient,
        unsubscribe_url: str,
    ) -> str:
        safe_name = html.escape(recipient.full_name or "Quý khách")
        safe_subject = html.escape(campaign.subject)
        paragraphs = [
            f'<p style="margin:0 0 16px">{html.escape(part).replace(chr(10), "<br>")}</p>'
            for part in re.split(r"\n\s*\n", campaign.body_text)
            if part.strip()
        ]
        action_html = ""
        if campaign.action_label and campaign.action_url:
            action_html = (
                '<table role="presentation" cellspacing="0" cellpadding="0" style="margin:28px 0">'
                '<tr><td style="border-radius:12px;background:#171a17">'
                f'<a href="{html.escape(campaign.action_url, quote=True)}" '
                'style="display:inline-block;padding:15px 24px;color:#fff;text-decoration:none;'
                'font-size:13px;font-weight:800;letter-spacing:.04em">'
                f'{html.escape(campaign.action_label)}</a></td></tr></table>'
            )
        return f"""<!doctype html>
<html lang="vi"><body style="margin:0;background:#f3f0e9;color:#171a17;font-family:Arial,Helvetica,sans-serif">
<div style="display:none;max-height:0;overflow:hidden">{safe_subject}</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f0e9;padding:28px 12px"><tr><td align="center">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#fff;border:1px solid #ded8cc;border-radius:22px;overflow:hidden">
<tr><td style="padding:28px 32px;background:#171a17;color:#fff"><strong style="font-size:19px;letter-spacing:.16em">GUA MAISON</strong><div style="margin-top:8px;color:#c9a96b;font-size:10px;letter-spacing:.18em;text-transform:uppercase">Fashion notes · 2026</div></td></tr>
<tr><td style="padding:36px 32px"><p style="margin:0 0 18px;font-size:15px;font-weight:800">Xin chào {safe_name},</p><div style="font-size:15px;line-height:1.8;color:#505650">{''.join(paragraphs)}</div>{action_html}<div style="height:1px;background:#ece7dd;margin:30px 0 20px"></div><p style="margin:0;color:#787e78;font-size:12px;line-height:1.7">Bạn nhận email này vì đã đăng ký nhận tin từ GUAMAISON. <a href="{html.escape(unsubscribe_url, quote=True)}" style="color:#171a17">Hủy nhận bản tin</a>.</p></td></tr>
</table></td></tr></table></body></html>"""

    @staticmethod
    def _campaign_email_text(
        campaign: NewsletterCampaign,
        recipient: NewsletterCampaignRecipient,
        unsubscribe_url: str,
    ) -> str:
        action = f"\n\n{campaign.action_label}: {campaign.action_url}" if campaign.action_url else ""
        return (
            f"Xin chào {recipient.full_name or 'Quý khách'},\n\n"
            f"{campaign.body_text}{action}\n\n"
            f"Hủy nhận bản tin: {unsubscribe_url}\n\nGUAMAISON"
        )

    def send_campaign_test(
        self, *, campaign_id: str, recipient_email: str, base_url: str
    ) -> bool:
        campaign = self.repository.get_campaign(str(campaign_id))
        if campaign is None:
            raise NewsletterValidationError("Không tìm thấy chiến dịch email.")
        email_address = self._normalize_email(recipient_email)
        preview = NewsletterCampaignRecipient(
            id="preview",
            campaign_id=campaign.id,
            subscriber_id="preview",
            email=email_address,
            full_name="Khách hàng mẫu",
            unsubscribe_token=None,
            status="preview",
            attempt_count=0,
            error_message=None,
            sent_at=None,
            created_at=None,
        )
        unsubscribe_url = urljoin(base_url.rstrip("/") + "/", "newsletter/unsubscribe/demo")
        return send_transactional_email(
            recipient_email=email_address,
            subject=f"[BẢN THỬ] {campaign.subject}",
            html_body=self._campaign_email_html(campaign, preview, unsubscribe_url),
            text_body=self._campaign_email_text(campaign, preview, unsubscribe_url),
        )

    def send_campaign_batch(
        self, *, campaign_id: str, base_url: str
    ) -> CampaignBatchResult:
        campaign = self.repository.get_campaign(str(campaign_id))
        if campaign is None:
            raise NewsletterValidationError("Không tìm thấy chiến dịch email.")
        if campaign.status in {"completed", "cancelled"}:
            raise NewsletterValidationError("Chiến dịch này đã kết thúc.")
        if not self.is_mail_configured():
            raise NewsletterSendError("SMTP chưa sẵn sàng. Kiểm tra cấu hình email trong .env.")

        daily_limit = self._daily_limit()
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        daily_sent = self.repository.count_campaign_sent_since(since)
        allowance = daily_limit - daily_sent
        if allowance <= 0:
            self.repository.set_campaign_status(campaign.id, "paused")
            campaign = self.repository.refresh_campaign(campaign.id)
            return CampaignBatchResult(
                campaign=campaign,
                claimed=0,
                sent=0,
                failed=0,
                skipped=0,
                daily_sent=daily_sent,
                daily_limit=daily_limit,
                stop_reason="daily_limit",
            )

        self.repository.set_campaign_status(campaign.id, "sending")
        claimed = self.repository.claim_campaign_batch(
            campaign.id, limit=min(self._batch_size(), allowance)
        )
        if not claimed:
            campaign = self.repository.refresh_campaign(campaign.id)
            return CampaignBatchResult(
                campaign=campaign,
                claimed=0,
                sent=0,
                failed=0,
                skipped=0,
                daily_sent=daily_sent,
                daily_limit=daily_limit,
                stop_reason="completed" if campaign.status == "completed" else "no_pending",
            )

        mail_items: list[dict[str, str]] = []
        sendable: list[NewsletterCampaignRecipient] = []
        skipped = 0
        invalid_failed = 0
        for recipient in claimed:
            if not recipient.unsubscribe_token:
                self.repository.finish_campaign_recipient(
                    recipient.id,
                    sent=False,
                    error_message="Người nhận thiếu mã hủy đăng ký hợp lệ.",
                )
                invalid_failed += 1
                continue
            unsubscribe_url = urljoin(
                base_url.rstrip("/") + "/",
                f"newsletter/unsubscribe/{recipient.unsubscribe_token}",
            )
            sendable.append(recipient)
            mail_items.append(
                {
                    "recipient_email": recipient.email,
                    "subject": campaign.subject,
                    "html_body": self._campaign_email_html(campaign, recipient, unsubscribe_url),
                    "text_body": self._campaign_email_text(campaign, recipient, unsubscribe_url),
                }
            )

        results = send_transactional_email_batch(mail_items) if mail_items else []
        sent_count = 0
        failed_count = invalid_failed
        for recipient, sent in zip(sendable, results):
            self.repository.finish_campaign_recipient(
                recipient.id,
                sent=bool(sent),
                error_message=None if sent else "SMTP từ chối hoặc không gửi được email.",
            )
            if sent:
                sent_count += 1
            else:
                failed_count += 1

        campaign = self.repository.refresh_campaign(campaign.id)
        daily_sent += sent_count
        return CampaignBatchResult(
            campaign=campaign,
            claimed=len(claimed),
            sent=sent_count,
            failed=failed_count,
            skipped=skipped,
            daily_sent=daily_sent,
            daily_limit=daily_limit,
            stop_reason="completed" if campaign.status == "completed" else None,
        )

    def retry_failed_campaign(self, campaign_id: str) -> NewsletterCampaign:
        campaign = self.repository.get_campaign(str(campaign_id))
        if campaign is None:
            raise NewsletterValidationError("Không tìm thấy chiến dịch email.")
        if campaign.status == "cancelled":
            raise NewsletterValidationError("Không thể gửi lại chiến dịch đã hủy.")
        return self.repository.retry_failed_campaign(campaign.id)

    def cancel_campaign(self, campaign_id: str) -> NewsletterCampaign:
        campaign = self.repository.get_campaign(str(campaign_id))
        if campaign is None:
            raise NewsletterValidationError("Không tìm thấy chiến dịch email.")
        if campaign.status == "completed":
            raise NewsletterValidationError("Chiến dịch đã hoàn tất nên không thể hủy.")
        return self.repository.cancel_campaign(campaign.id)
