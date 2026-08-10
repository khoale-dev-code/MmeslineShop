"""HTTP-only Admin controller for contact messages and page settings."""

from __future__ import annotations

import logging
from uuid import UUID

from flask import flash, g, redirect, render_template, request, url_for

from app.middleware.auth_required import admin_required, permission_required
from app.models.contact_model import ContactPageSettings
from app.services.contact_service import (
    ContactMigrationRequired,
    ContactSendError,
    ContactService,
    ContactValidationError,
)
from ._blueprint import admin_bp, clear_admin_context_cache

logger = logging.getLogger(__name__)


def _page_number() -> int:
    try:
        return max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        return 1


def _admin_user_id() -> str | None:
    admin = getattr(g, "current_admin", {}) or {}
    value = admin.get("id") if isinstance(admin, dict) else getattr(admin, "id", None)
    return str(value) if value else None


@admin_bp.get("/newsletter/messages")
@admin_required
@permission_required("notifications.manage")
def contact_messages_index():
    try:
        page_data, stats, settings = ContactService().admin_list(
            page=_page_number(),
            per_page=24,
            query_text=request.args.get("q", ""),
            status=request.args.get("status", ""),
            topic=request.args.get("topic", ""),
            unread_only=request.args.get("unread") == "1",
        )
        return render_template(
            "admin/contact/index.html",
            page_data=page_data,
            stats=stats,
            settings=settings,
            query_text=request.args.get("q", ""),
            selected_status=request.args.get("status", ""),
            selected_topic=request.args.get("topic", ""),
            unread_only=request.args.get("unread") == "1",
            migration_missing=False,
        )
    except ContactMigrationRequired:
        return render_template(
            "admin/contact/index.html",
            page_data=None,
            stats={"total": 0, "unread": 0, "new": 0, "open": 0, "replied": 0, "closed": 0},
            settings=ContactPageSettings.defaults(),
            query_text="",
            selected_status="",
            selected_topic="",
            unread_only=False,
            migration_missing=True,
        ), 503


@admin_bp.get("/newsletter/messages/<uuid:message_id>")
@admin_required
@permission_required("notifications.manage")
def contact_message_detail(message_id: UUID):
    detail = ContactService().admin_detail(str(message_id), mark_read=True)
    if detail is None:
        flash("Không tìm thấy lời nhắn liên hệ.", "danger")
        return redirect(url_for("admin.contact_messages_index"))
    clear_admin_context_cache()
    return render_template(
        "admin/contact/detail.html",
        detail=detail,
        mail_ready=ContactService.is_mail_configured(),
    )


@admin_bp.post("/newsletter/messages/<uuid:message_id>/reply")
@admin_required
@permission_required("notifications.manage")
def contact_message_reply(message_id: UUID):
    try:
        ContactService().send_reply(
            message_id=str(message_id),
            admin_user_id=_admin_user_id(),
            subject=request.form.get("subject", ""),
            body_text=request.form.get("message", ""),
        )
        clear_admin_context_cache()
        flash("Đã gửi phản hồi đến khách hàng và lưu lịch sử.", "success")
    except ContactValidationError as exc:
        flash(str(exc), "danger")
    except ContactSendError as exc:
        flash(str(exc), "warning")
    except ContactMigrationRequired:
        flash("Chưa chạy migration Contact Center v13 trên Supabase.", "danger")
    except Exception:
        logger.exception("Admin contact reply failed")
        flash("Không thể gửi email lúc này. Vui lòng kiểm tra cấu hình SMTP.", "danger")
    return redirect(url_for("admin.contact_message_detail", message_id=message_id))


@admin_bp.post("/newsletter/messages/<uuid:message_id>/update")
@admin_required
@permission_required("notifications.manage")
def contact_message_update(message_id: UUID):
    try:
        ContactService().update_message(
            message_id=str(message_id),
            status=request.form.get("status", "open"),
            admin_note=request.form.get("admin_note", ""),
        )
        clear_admin_context_cache()
        flash("Đã cập nhật trạng thái lời nhắn.", "success")
    except ContactValidationError as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Update contact message failed")
        flash("Không thể cập nhật lời nhắn lúc này.", "danger")
    return redirect(url_for("admin.contact_message_detail", message_id=message_id))


@admin_bp.route("/newsletter/contact-page", methods=["GET", "POST"])
@admin_required
@permission_required("notifications.manage")
def contact_page_settings():
    service = ContactService()
    if request.method == "POST":
        try:
            service.save_settings(
                data=request.form.to_dict(),
                admin_user_id=_admin_user_id(),
            )
            flash("Đã cập nhật trang Liên hệ và bản đồ Google Maps.", "success")
            return redirect(url_for("admin.contact_page_settings"))
        except ContactValidationError as exc:
            flash(str(exc), "danger")
        except ContactMigrationRequired:
            flash("Chưa chạy migration Contact Center v13 trên Supabase.", "danger")
        except Exception:
            logger.exception("Save contact page settings failed")
            flash("Không thể lưu cài đặt trang Liên hệ lúc này.", "danger")
        return render_template(
            "admin/contact/settings.html",
            settings=ContactPageSettings.from_record(request.form.to_dict()),
            map_embed_input=request.form.get("map_embed", ""),
            migration_missing=False,
        ), 400

    try:
        settings = service.get_public_settings()
        migration_missing = False
    except ContactMigrationRequired:
        settings = ContactPageSettings.defaults()
        migration_missing = True
    return render_template(
        "admin/contact/settings.html",
        settings=settings,
        map_embed_input=settings.map_embed_url,
        migration_missing=migration_missing,
    ), 503 if migration_missing else 200
