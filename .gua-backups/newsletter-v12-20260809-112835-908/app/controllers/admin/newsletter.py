"""HTTP-only Admin newsletter controller."""

from __future__ import annotations

import logging
from uuid import UUID

from flask import current_app, flash, g, redirect, render_template, request, url_for

from app.middleware.auth_required import admin_required, permission_required
from app.repositories.newsletter_repository import NewsletterMigrationRequired
from app.services.newsletter_service import (
    NewsletterSendError,
    NewsletterService,
    NewsletterValidationError,
)
from ._blueprint import admin_bp, clear_admin_context_cache

logger = logging.getLogger(__name__)


def _page_number() -> int:
    try:
        return max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        return 1


@admin_bp.get("/newsletter")
@admin_required
@permission_required("notifications.manage")
def newsletter_index():
    try:
        page_data, stats = NewsletterService().admin_list(
            page=_page_number(),
            per_page=20,
            query_text=request.args.get("q", ""),
            status=request.args.get("status", ""),
            unread_only=request.args.get("unread") == "1",
        )
        return render_template(
            "admin/newsletter/index.html",
            page_data=page_data,
            stats=stats,
            query_text=request.args.get("q", ""),
            selected_status=request.args.get("status", ""),
            unread_only=request.args.get("unread") == "1",
            migration_missing=False,
        )
    except NewsletterMigrationRequired:
        return render_template(
            "admin/newsletter/index.html",
            page_data=None,
            stats={"active": 0, "unread": 0, "unsubscribed": 0, "sent": 0},
            query_text="",
            selected_status="",
            unread_only=False,
            migration_missing=True,
        ), 503


@admin_bp.get("/newsletter/<uuid:subscriber_id>")
@admin_required
@permission_required("notifications.manage")
def newsletter_detail(subscriber_id: UUID):
    detail = NewsletterService().admin_detail(str(subscriber_id), mark_read=True)
    if detail is None:
        flash("Không tìm thấy người đăng ký nhận tin.", "danger")
        return redirect(url_for("admin.newsletter_index"))
    clear_admin_context_cache()
    return render_template(
        "admin/newsletter/detail.html",
        detail=detail,
        mail_ready=NewsletterService.is_mail_configured(),
    )


@admin_bp.post("/newsletter/<uuid:subscriber_id>/reply")
@admin_required
@permission_required("notifications.manage")
def newsletter_reply(subscriber_id: UUID):
    admin = getattr(g, "current_admin", {}) or {}
    base_url = current_app.config.get("BASE_URL") or request.url_root
    try:
        NewsletterService().send_admin_reply(
            subscriber_id=str(subscriber_id),
            admin_user_id=str(admin.get("id")) if admin.get("id") else None,
            subject=request.form.get("subject", ""),
            message=request.form.get("message", ""),
            base_url=base_url,
        )
        flash("Đã gửi email đến khách hàng và lưu lịch sử.", "success")
    except NewsletterValidationError as exc:
        flash(str(exc), "danger")
    except NewsletterSendError as exc:
        flash(str(exc), "warning")
    except Exception:
        logger.exception("Admin newsletter reply failed")
        flash("Không thể gửi email lúc này. Vui lòng kiểm tra cấu hình SMTP.", "danger")
    return redirect(url_for("admin.newsletter_detail", subscriber_id=subscriber_id))
