"""
app/services/email_service.py
=============================
GUAMAISON Email Service

Gửi email qua Gmail SMTP hoặc SMTP server tùy cấu hình.

Yêu cầu .env:
    MAIL_SENDER_EMAIL=your_email@gmail.com
    MAIL_SENDER_NAME=GUAMAISON
    MAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
    MAIL_SMTP_HOST=smtp.gmail.com
    MAIL_SMTP_PORT=587
    MAIL_USE_TLS=true
    MAIL_USE_SSL=false

Ghi chú Gmail:
- MAIL_APP_PASSWORD phải là Google App Password, không phải mật khẩu Gmail thường.
- Tài khoản Google cần bật 2-Step Verification để tạo App Password.
"""

from __future__ import annotations

import html
import logging
import os
import re
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

BRAND_NAME = "GUAMAISON"
BRAND_GREEN = "#1b4922"
BRAND_GREEN_DARK = "#123418"
BRAND_GOLD = "#c99e14"
BRAND_CREAM = "#fbfaf4"
BRAND_SOFT = "#f7f9f2"
BRAND_MUTED = "#687466"

DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_TIMEOUT = 20

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class MailConfig:
    smtp_host: str
    smtp_port: int
    sender_email: str
    sender_name: str
    app_password: str
    use_tls: bool
    use_ssl: bool
    timeout: int


# ═══════════════════════════════════════════════════════════════
# BASIC HELPERS
# ═══════════════════════════════════════════════════════════════

def _env_bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _safe_text(value: Optional[str], default: str = "", max_len: int = 500) -> str:
    text = str(value or default).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_len]


def _safe_html(value: Optional[str], default: str = "", max_len: int = 500) -> str:
    return html.escape(_safe_text(value, default=default, max_len=max_len))


def _is_valid_email(email: Optional[str]) -> bool:
    return bool(email and EMAIL_RE.match(email.strip()))


def _first_name(full_name: Optional[str]) -> str:
    name = _safe_text(full_name, default="Quý khách", max_len=80)
    if not name:
        return "Quý khách"
    return name.split()[0]


def _mask_email(email: str) -> str:
    email = str(email or "")
    if "@" not in email:
        return "***"

    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[:1] + "***"
    else:
        masked_local = local[:2] + "***"

    return f"{masked_local}@{domain}"


def _get_mail_config() -> Optional[MailConfig]:
    sender_email = os.environ.get("MAIL_SENDER_EMAIL", "").strip()
    app_password = os.environ.get("MAIL_APP_PASSWORD", "").strip()

    if not sender_email or not app_password:
        logger.error("[EMAIL] Thiếu MAIL_SENDER_EMAIL hoặc MAIL_APP_PASSWORD trong .env.")
        return None

    if not _is_valid_email(sender_email):
        logger.error("[EMAIL] MAIL_SENDER_EMAIL không hợp lệ: %s", _mask_email(sender_email))
        return None

    try:
        smtp_port = int(os.environ.get("MAIL_SMTP_PORT", DEFAULT_SMTP_PORT))
    except Exception:
        smtp_port = DEFAULT_SMTP_PORT

    return MailConfig(
        smtp_host=os.environ.get("MAIL_SMTP_HOST", DEFAULT_SMTP_HOST).strip() or DEFAULT_SMTP_HOST,
        smtp_port=smtp_port,
        sender_email=sender_email,
        sender_name=os.environ.get("MAIL_SENDER_NAME", BRAND_NAME).strip() or BRAND_NAME,
        app_password=app_password,
        use_tls=_env_bool("MAIL_USE_TLS", "true"),
        use_ssl=_env_bool("MAIL_USE_SSL", "false"),
        timeout=int(os.environ.get("MAIL_TIMEOUT", DEFAULT_TIMEOUT)),
    )


# ═══════════════════════════════════════════════════════════════
# EMAIL TEMPLATES
# ═══════════════════════════════════════════════════════════════

def _build_email_shell(
    *,
    title: str,
    preheader: str,
    body_html: str,
    footer_note: str = "Email tự động — vui lòng không trả lời email này.",
) -> str:
    safe_title = _safe_html(title, max_len=140)
    safe_preheader = _safe_html(preheader, max_len=220)
    safe_footer_note = _safe_html(footer_note, max_len=220)

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <meta name="x-apple-disable-message-reformatting">
  <title>{safe_title}</title>
</head>

<body style="margin:0;padding:0;background:{BRAND_SOFT};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
    {safe_preheader}
  </div>

  <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:{BRAND_SOFT};padding:42px 14px;">
    <tr>
      <td align="center">

        <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
               style="max-width:560px;background:#ffffff;border:1px solid rgba(27,73,34,.16);border-radius:18px;overflow:hidden;box-shadow:0 24px 70px -54px rgba(27,73,34,.58);">

          <tr>
            <td style="background:{BRAND_GREEN};padding:28px 34px;">
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td>
                    <p style="margin:0 0 5px;font-family:Arial,Helvetica,sans-serif;font-size:9px;font-weight:900;letter-spacing:.28em;text-transform:uppercase;color:{BRAND_GOLD};">
                      Official Online Store
                    </p>

                    <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:24px;font-weight:900;letter-spacing:-.03em;color:#ffffff;">
                      MMEST<span style="color:{BRAND_GOLD};">LINE</span>
                    </p>
                  </td>

                  <td align="right" valign="middle">
                    <div style="width:38px;height:38px;border-radius:12px;background:rgba(255,255,255,.08);border:1px solid rgba(201,158,20,.38);text-align:center;line-height:38px;">
                      <span style="font-family:Arial,Helvetica,sans-serif;font-size:14px;font-weight:900;color:{BRAND_GOLD};">M</span>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          {body_html}

          <tr>
            <td style="padding:0 34px;">
              <div style="height:1px;background:rgba(27,73,34,.12);"></div>
            </td>
          </tr>

          <tr>
            <td style="padding:22px 34px 30px;background:{BRAND_CREAM};">
              <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                <tr>
                  <td>
                    <p style="margin:0 0 5px;font-family:Arial,Helvetica,sans-serif;font-size:10px;font-weight:900;letter-spacing:.22em;text-transform:uppercase;color:{BRAND_GREEN};">
                      GUAMAISON
                    </p>

                    <p style="margin:0 0 4px;font-family:Arial,Helvetica,sans-serif;font-size:11px;font-weight:600;color:{BRAND_MUTED};line-height:1.6;">
                      {safe_footer_note}
                    </p>

                    <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:10px;font-weight:700;color:rgba(27,73,34,.42);">
                      &copy; 2026 GUAMAISON. All rights reserved.
                    </p>
                  </td>

                  <td align="right" valign="bottom">
                    <div style="width:30px;height:2px;background:{BRAND_GOLD};margin-left:auto;"></div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_reset_email_html(first_name: str, reset_link: str) -> str:
    safe_first_name = _safe_html(first_name, default="Quý khách", max_len=80)
    safe_reset_link = html.escape(str(reset_link or "").strip(), quote=True)

    body_html = f"""
      <tr>
        <td style="padding:38px 34px 28px;background:#ffffff;">
          <p style="margin:0 0 8px;font-family:Arial,Helvetica,sans-serif;font-size:10px;font-weight:900;letter-spacing:.24em;text-transform:uppercase;color:{BRAND_GOLD};">
            Khôi phục tài khoản
          </p>

          <h1 style="margin:0 0 18px;font-family:Arial,Helvetica,sans-serif;font-size:30px;font-weight:900;line-height:1.08;letter-spacing:-.045em;color:{BRAND_GREEN};">
            Đặt lại mật khẩu<br>của bạn
          </h1>

          <div style="width:44px;height:2px;background:{BRAND_GOLD};margin:0 0 26px;"></div>

          <p style="margin:0 0 10px;font-family:Arial,Helvetica,sans-serif;font-size:14px;font-weight:600;color:{BRAND_GREEN_DARK};line-height:1.8;">
            Xin chào <strong>{safe_first_name}</strong>,
          </p>

          <p style="margin:0 0 30px;font-family:Arial,Helvetica,sans-serif;font-size:13px;font-weight:500;color:{BRAND_MUTED};line-height:1.85;">
            GUAMAISON nhận được yêu cầu đặt lại mật khẩu cho tài khoản gắn với địa chỉ email này.
            Nhấn vào nút bên dưới để thiết lập mật khẩu mới.
          </p>

          <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
            <tr>
              <td align="center" style="padding-bottom:30px;">
                <a href="{safe_reset_link}"
                   style="display:inline-block;background:{BRAND_GREEN};color:#ffffff;text-decoration:none;font-family:Arial,Helvetica,sans-serif;font-size:10px;font-weight:900;letter-spacing:.18em;text-transform:uppercase;padding:17px 34px;border-radius:10px;border:1px solid {BRAND_GREEN};">
                  Đặt lại mật khẩu →
                </a>
              </td>
            </tr>
          </table>

          <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin-bottom:28px;">
            <tr>
              <td style="background:#fffaf0;border:1px solid rgba(201,158,20,.35);border-left:4px solid {BRAND_GOLD};border-radius:10px;padding:14px 16px;">
                <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:11px;font-weight:600;color:#7a5a00;line-height:1.75;">
                  <strong>Lưu ý:</strong> Đường dẫn này sẽ hết hạn sau <strong>1 giờ</strong>.
                  Nếu bạn không thực hiện yêu cầu này, hãy bỏ qua email — tài khoản của bạn vẫn an toàn.
                </p>
              </td>
            </tr>
          </table>

          <p style="margin:0 0 6px;font-family:Arial,Helvetica,sans-serif;font-size:10px;font-weight:700;color:rgba(27,73,34,.52);line-height:1.6;">
            Nếu nút không hoạt động, sao chép liên kết sau vào trình duyệt:
          </p>

          <p style="margin:0;font-family:'Courier New',Courier,monospace;font-size:10px;color:{BRAND_GREEN};word-break:break-all;line-height:1.7;">
            {safe_reset_link}
          </p>
        </td>
      </tr>
    """

    return _build_email_shell(
        title="Khôi phục mật khẩu – GUAMAISON",
        preheader="Đặt lại mật khẩu GUAMAISON của bạn. Liên kết hết hạn sau 1 giờ.",
        body_html=body_html,
    )


def _build_reset_email_text(first_name: str, reset_link: str) -> str:
    return f"""GUAMAISON - Khôi phục mật khẩu

Xin chào {first_name},

GUAMAISON nhận được yêu cầu đặt lại mật khẩu cho tài khoản gắn với email này.

Bạn có thể đặt lại mật khẩu tại liên kết sau:
{reset_link}

Lưu ý: Liên kết này sẽ hết hạn sau 1 giờ.
Nếu bạn không thực hiện yêu cầu này, hãy bỏ qua email này.

GUAMAISON
Email tự động — vui lòng không trả lời email này.
"""


# ═══════════════════════════════════════════════════════════════
# SMTP SENDING
# ═══════════════════════════════════════════════════════════════

def _send_email(
    *,
    recipient_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    reply_to: Optional[str] = None,
) -> bool:
    config = _get_mail_config()

    if not config:
        return False

    recipient_email = str(recipient_email or "").strip()

    if not _is_valid_email(recipient_email):
        logger.error("[EMAIL] Email người nhận không hợp lệ: %s", _mask_email(recipient_email))
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((config.sender_name, config.sender_email))
    msg["To"] = recipient_email
    msg["Message-ID"] = make_msgid(domain=config.sender_email.split("@")[-1])

    if reply_to and _is_valid_email(reply_to):
        msg["Reply-To"] = reply_to

    msg.set_content(text_body, subtype="plain", charset="utf-8")
    msg.add_alternative(html_body, subtype="html", charset="utf-8")

    try:
        if config.use_ssl:
            context = ssl.create_default_context()

            with smtplib.SMTP_SSL(
                config.smtp_host,
                config.smtp_port,
                timeout=config.timeout,
                context=context,
            ) as server:
                server.login(config.sender_email, config.app_password)
                server.send_message(msg)

        else:
            with smtplib.SMTP(
                config.smtp_host,
                config.smtp_port,
                timeout=config.timeout,
            ) as server:
                server.ehlo()

                if config.use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()

                server.login(config.sender_email, config.app_password)
                server.send_message(msg)

        logger.info("[EMAIL] Sent email subject='%s' to=%s", subject, _mask_email(recipient_email))
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("[EMAIL] Xác thực SMTP thất bại. Kiểm tra MAIL_SENDER_EMAIL và MAIL_APP_PASSWORD.")
        return False

    except smtplib.SMTPRecipientsRefused:
        logger.error("[EMAIL] SMTP từ chối người nhận: %s", _mask_email(recipient_email))
        return False

    except smtplib.SMTPConnectError:
        logger.error("[EMAIL] Không kết nối được SMTP server %s:%s", config.smtp_host, config.smtp_port)
        return False

    except smtplib.SMTPException as e:
        logger.error("[EMAIL] SMTP error khi gửi đến %s: %s", _mask_email(recipient_email), e)
        return False

    except Exception as e:
        logger.error("[EMAIL] Lỗi không xác định khi gửi đến %s: %s", _mask_email(recipient_email), e, exc_info=True)
        return False


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def send_password_reset_email(
    recipient_email: str,
    recipient_name: str,
    reset_link: str,
) -> bool:
    """
    Gửi email khôi phục mật khẩu qua SMTP.

    Args:
        recipient_email: Email người nhận.
        recipient_name: Tên người nhận.
        reset_link: Link reset password.

    Returns:
        True nếu gửi thành công, False nếu thất bại.
    """
    if not reset_link:
        logger.error("[EMAIL] reset_link trống, không thể gửi email reset password.")
        return False

    first_name = _first_name(recipient_name)

    subject = "[GUAMAISON] Khôi phục mật khẩu của bạn"
    html_body = _build_reset_email_html(first_name, reset_link)
    text_body = _build_reset_email_text(first_name, reset_link)

    return _send_email(
        recipient_email=recipient_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


def send_test_email(recipient_email: str) -> bool:
    """
    Gửi email test để kiểm tra cấu hình SMTP.
    Có thể dùng trong debug/admin.
    """
    body_html = _build_email_shell(
        title="Kiểm tra email – GUAMAISON",
        preheader="Email kiểm tra cấu hình SMTP GUAMAISON.",
        body_html=f"""
          <tr>
            <td style="padding:38px 34px;background:#ffffff;">
              <p style="margin:0 0 8px;font-family:Arial,Helvetica,sans-serif;font-size:10px;font-weight:900;letter-spacing:.24em;text-transform:uppercase;color:{BRAND_GOLD};">
                SMTP Test
              </p>

              <h1 style="margin:0 0 18px;font-family:Arial,Helvetica,sans-serif;font-size:28px;font-weight:900;line-height:1.1;letter-spacing:-.04em;color:{BRAND_GREEN};">
                Email service hoạt động
              </h1>

              <p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:13px;font-weight:600;color:{BRAND_MUTED};line-height:1.8;">
                Nếu bạn nhận được email này, cấu hình SMTP của GUAMAISON đang hoạt động bình thường.
              </p>
            </td>
          </tr>
        """,
    )

    body_text = """GUAMAISON SMTP Test

Email service hoạt động.
Nếu bạn nhận được email này, cấu hình SMTP của GUAMAISON đang hoạt động bình thường.
"""

    return _send_email(
        recipient_email=recipient_email,
        subject="[GUAMAISON] Kiểm tra cấu hình email",
        html_body=body_html,
        text_body=body_text,
    )