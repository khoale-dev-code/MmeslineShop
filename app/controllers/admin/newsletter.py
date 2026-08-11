"""HTTP-only Admin newsletter controller."""

from __future__ import annotations

import logging
from uuid import UUID

from flask import current_app, flash, g, jsonify, redirect, render_template, request, url_for

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


def _admin_user_id() -> str | None:
    admin = getattr(g, "current_admin", {}) or {}
    if isinstance(admin, dict):
        value = admin.get("id")
    else:
        value = getattr(admin, "id", None)
    return str(value) if value else None


@admin_bp.get("/newsletter/campaigns")
@admin_required
@permission_required("notifications.manage")
def newsletter_campaigns():
    try:
        return render_template(
            "admin/newsletter/campaigns.html",
            page_data=NewsletterService().list_campaigns(page=_page_number()),
            migration_missing=False,
        )
    except NewsletterMigrationRequired:
        return render_template(
            "admin/newsletter/campaigns.html",
            page_data=None,
            migration_missing=True,
        ), 503


@admin_bp.route("/newsletter/campaigns/new", methods=["GET", "POST"])
@admin_required
@permission_required("notifications.manage")
def newsletter_campaign_new():
    selected_ids = (
        request.form.getlist("subscriber_id")
        if request.method == "POST"
        else request.args.getlist("subscriber_id")
    )
    if request.method == "GET":
        try:
            _, stats = NewsletterService().admin_list(
                page=1,
                per_page=10,
                query_text="",
                status="active",
                unread_only=False,
            )
            return render_template(
                "admin/newsletter/campaign_new.html",
                selected_ids=selected_ids,
                active_count=stats.get("active", 0),
                form_data={},
            )
        except NewsletterMigrationRequired:
            flash("Hãy chạy migration Newsletter v12 trước khi tạo chiến dịch.", "warning")
            return redirect(url_for("admin.newsletter_campaigns"))

    form_data = request.form.to_dict()
    try:
        campaign = NewsletterService().create_campaign(
            admin_user_id=_admin_user_id(),
            name=request.form.get("name", ""),
            subject=request.form.get("subject", ""),
            body_text=request.form.get("body_text", ""),
            action_label=request.form.get("action_label", ""),
            action_url=request.form.get("action_url", ""),
            target_mode=request.form.get("target_mode", "all_active"),
            subscriber_ids=selected_ids,
        )
        flash(
            f"Đã tạo chiến dịch với {campaign.target_count} người nhận. Hãy gửi thử trước khi gửi thật.",
            "success",
        )
        return redirect(url_for("admin.newsletter_campaign_detail", campaign_id=campaign.id))
    except NewsletterValidationError as exc:
        flash(str(exc), "danger")
    except NewsletterMigrationRequired:
        flash("Chưa chạy migration Newsletter v12 trên Supabase.", "danger")
        return redirect(url_for("admin.newsletter_campaigns"))
    except Exception:
        logger.exception("Create newsletter campaign failed")
        flash("Không thể tạo chiến dịch email lúc này.", "danger")

    try:
        _, stats = NewsletterService().admin_list(
            page=1,
            per_page=10,
            query_text="",
            status="active",
            unread_only=False,
        )
        active_count = stats.get("active", 0)
    except Exception:
        active_count = 0
    return render_template(
        "admin/newsletter/campaign_new.html",
        selected_ids=selected_ids,
        active_count=active_count,
        form_data=form_data,
    ), 400


@admin_bp.get("/newsletter/campaigns/<uuid:campaign_id>")
@admin_required
@permission_required("notifications.manage")
def newsletter_campaign_detail(campaign_id: UUID):
    detail = NewsletterService().campaign_detail(str(campaign_id))
    if detail is None:
        flash("Không tìm thấy chiến dịch email.", "danger")
        return redirect(url_for("admin.newsletter_campaigns"))
    return render_template(
        "admin/newsletter/campaign_detail.html",
        detail=detail,
        mail_ready=NewsletterService.is_mail_configured(),
        default_test_email=NewsletterService.mail_sender_email()
        or current_app.config.get("ADMIN_EMAIL")
        or "",
    )


@admin_bp.post("/newsletter/campaigns/<uuid:campaign_id>/test")
@admin_required
@permission_required("notifications.manage")
def newsletter_campaign_test(campaign_id: UUID):
    base_url = current_app.config.get("BASE_URL") or request.url_root
    try:
        sent = NewsletterService().send_campaign_test(
            campaign_id=str(campaign_id),
            recipient_email=request.form.get("test_email", ""),
            base_url=base_url,
        )
        flash(
            "Đã gửi bản thử. Hãy kiểm tra cả Hộp thư đến và Spam."
            if sent
            else "SMTP chưa gửi được bản thử. Hãy kiểm tra cấu hình email.",
            "success" if sent else "warning",
        )
    except NewsletterValidationError as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Newsletter campaign test failed")
        flash("Không thể gửi email thử lúc này.", "danger")
    return redirect(url_for("admin.newsletter_campaign_detail", campaign_id=campaign_id))


@admin_bp.post("/newsletter/campaigns/<uuid:campaign_id>/send-batch")
@admin_required
@permission_required("notifications.manage")
def newsletter_campaign_send_batch(campaign_id: UUID):
    base_url = current_app.config.get("BASE_URL") or request.url_root
    try:
        result = NewsletterService().send_campaign_batch(
            campaign_id=str(campaign_id), base_url=base_url
        )
        campaign = result.campaign
        return jsonify(
            {
                "ok": True,
                "campaign": {
                    "status": campaign.status,
                    "target_count": campaign.target_count,
                    "pending_count": campaign.pending_count,
                    "processing_count": campaign.processing_count,
                    "sent_count": campaign.sent_count,
                    "failed_count": campaign.failed_count,
                    "skipped_count": campaign.skipped_count,
                    "progress_percent": campaign.progress_percent,
                },
                "batch": {
                    "claimed": result.claimed,
                    "sent": result.sent,
                    "failed": result.failed,
                    "skipped": result.skipped,
                },
                "quota": {
                    "daily_sent": result.daily_sent,
                    "daily_limit": result.daily_limit,
                },
                "stop_reason": result.stop_reason,
            }
        )
    except (NewsletterValidationError, NewsletterSendError) as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400
    except Exception:
        logger.exception("Newsletter campaign batch failed")
        return jsonify(
            {"ok": False, "message": "Không thể gửi lô email lúc này. Bạn có thể tiếp tục sau."}
        ), 500


@admin_bp.post("/newsletter/campaigns/<uuid:campaign_id>/retry-failed")
@admin_required
@permission_required("notifications.manage")
def newsletter_campaign_retry_failed(campaign_id: UUID):
    try:
        campaign = NewsletterService().retry_failed_campaign(str(campaign_id))
        flash(f"Đã đưa {campaign.pending_count} email về hàng chờ để gửi lại.", "success")
    except NewsletterValidationError as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Retry newsletter campaign failed")
        flash("Không thể chuẩn bị gửi lại email lỗi.", "danger")
    return redirect(url_for("admin.newsletter_campaign_detail", campaign_id=campaign_id))


@admin_bp.post("/newsletter/campaigns/<uuid:campaign_id>/cancel")
@admin_required
@permission_required("notifications.manage")
def newsletter_campaign_cancel(campaign_id: UUID):
    try:
        NewsletterService().cancel_campaign(str(campaign_id))
        flash("Đã hủy phần email chưa gửi của chiến dịch.", "success")
    except NewsletterValidationError as exc:
        flash(str(exc), "danger")
    except Exception:
        logger.exception("Cancel newsletter campaign failed")
        flash("Không thể hủy chiến dịch lúc này.", "danger")
    return redirect(url_for("admin.newsletter_campaign_detail", campaign_id=campaign_id))
