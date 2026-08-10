"""HTTP adapter for storefront newsletter actions."""

from __future__ import annotations

import logging
from uuid import UUID

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app.repositories.newsletter_repository import NewsletterMigrationRequired
from app.services.newsletter_service import (
    NewsletterRateLimitError,
    NewsletterService,
    NewsletterValidationError,
)

logger = logging.getLogger(__name__)
newsletter_bp = Blueprint("newsletter", __name__, url_prefix="/newsletter")


def _wants_json() -> bool:
    return request.is_json or request.accept_mimetypes.best == "application/json"


def _respond(payload: dict, status_code: int = 200):
    if _wants_json():
        return jsonify(payload), status_code
    flash(payload.get("message") or "Đã xử lý yêu cầu.", "success" if payload.get("ok") else "danger")
    return redirect(url_for("products.index"))


@newsletter_bp.post("/subscribe")
def subscribe():
    payload = request.get_json(silent=True) if request.is_json else request.form
    payload = payload or {}
    consent_value = payload.get("consent")
    consent = consent_value is True or str(consent_value or "").lower() in {"1", "true", "yes", "on"}
    try:
        result = NewsletterService().subscribe(
            email=str(payload.get("email") or ""),
            full_name=str(payload.get("full_name") or ""),
            consent=consent,
            source=str(payload.get("source") or "homepage"),
            locale=request.accept_languages.best_match(["vi", "en"]) or "vi",
            remote_address=request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip(),
            user_agent=request.user_agent.string,
            honeypot=str(payload.get("website") or ""),
        )
        return _respond(
            {"ok": result.code not in {"blocked"}, "code": result.code, "message": result.message},
            201 if result.created else 200,
        )
    except NewsletterValidationError as exc:
        return _respond({"ok": False, "code": "validation_error", "message": str(exc)}, 422)
    except NewsletterRateLimitError as exc:
        return _respond({"ok": False, "code": "rate_limited", "message": str(exc)}, 429)
    except NewsletterMigrationRequired:
        logger.error("Newsletter v11 migration has not been applied.")
        return _respond(
            {"ok": False, "code": "migration_required", "message": "Hệ thống nhận tin đang được cập nhật. Vui lòng thử lại sau."},
            503,
        )
    except Exception:
        logger.exception("Newsletter subscribe failed")
        return _respond(
            {"ok": False, "code": "server_error", "message": "Chưa thể đăng ký lúc này. Vui lòng thử lại sau."},
            500,
        )


@newsletter_bp.route("/unsubscribe/<uuid:token>", methods=["GET", "POST"])
def unsubscribe(token: UUID):
    if request.method == "GET":
        return render_template("newsletter/unsubscribe.html", token=str(token), completed=False)
    try:
        completed = NewsletterService().unsubscribe(str(token))
        return render_template("newsletter/unsubscribe.html", token=str(token), completed=completed)
    except NewsletterValidationError as exc:
        return render_template("newsletter/unsubscribe.html", token=str(token), completed=False, error=str(exc)), 422
    except Exception:
        logger.exception("Newsletter unsubscribe failed")
        return render_template(
            "newsletter/unsubscribe.html",
            token=str(token),
            completed=False,
            error="Chưa thể cập nhật yêu cầu. Vui lòng thử lại sau.",
        ), 500

