"""HTTP adapter for the public GUAMAISON contact page."""

from __future__ import annotations

import logging

from flask import flash, jsonify, redirect, render_template, request, url_for

from app.models.contact_model import ContactPageSettings
from app.services.contact_service import (
    ContactMigrationRequired,
    ContactRateLimitError,
    ContactService,
    ContactValidationError,
)

logger = logging.getLogger(__name__)


def _wants_json() -> bool:
    return bool(
        request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.accept_mimetypes.best == "application/json"
    )


def _client_address() -> str:
    route = list(request.access_route or [])
    return str(route[0] if route else request.remote_addr or "unknown")[:120]


def _payload() -> dict[str, str]:
    source = request.get_json(silent=True) if request.is_json else request.form
    source = source or {}
    return {
        "full_name": str(source.get("full_name") or source.get("name") or ""),
        "email": str(source.get("email") or ""),
        "phone": str(source.get("phone") or ""),
        "topic": str(source.get("topic") or ""),
        "message": str(source.get("message") or ""),
        "honeypot": str(source.get("website") or ""),
    }


def _respond_error(message: str, status: int):
    if _wants_json():
        return jsonify({"ok": False, "message": message}), status
    flash(message, "danger")
    return redirect(url_for("products.contact") + "#contact-form")


def render_contact_page():
    """Called by the existing products.contact route after installer delegation."""
    service = ContactService()
    if request.method == "POST":
        data = _payload()
        try:
            result = service.submit(
                full_name=data["full_name"],
                email=data["email"],
                phone=data["phone"],
                topic=data["topic"],
                message=data["message"],
                honeypot=data["honeypot"],
                remote_address=_client_address(),
                user_agent=request.headers.get("User-Agent", "")[:300],
            )
            if _wants_json():
                return jsonify(
                    {
                        "ok": True,
                        "message": result.message,
                        "reference": result.reference,
                    }
                ), 201 if result.created else 202
            flash(result.message, "success")
            return redirect(url_for("products.contact") + "#contact-form")
        except ContactValidationError as exc:
            return _respond_error(str(exc), 422)
        except ContactRateLimitError as exc:
            return _respond_error(str(exc), 429)
        except ContactMigrationRequired:
            return _respond_error(
                "Hộp thư liên hệ đang được cấu hình. Vui lòng liên hệ GUAMAISON qua email hoặc hotline.",
                503,
            )
        except Exception:
            logger.exception("Public contact submission failed")
            return _respond_error(
                "Chưa thể gửi lời nhắn lúc này. Vui lòng thử lại sau.", 500
            )

    try:
        settings = service.get_public_settings()
        migration_missing = False
    except ContactMigrationRequired:
        settings = ContactPageSettings.defaults()
        migration_missing = True
    except Exception:
        logger.exception("Contact settings unavailable")
        settings = ContactPageSettings.defaults()
        migration_missing = False
    return render_template(
        "partials/contact.html",
        contact=settings,
        contact_migration_missing=migration_missing,
    )
