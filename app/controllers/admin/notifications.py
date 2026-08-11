"""HTTP controller for the Admin action inbox and customer broadcasts."""

from __future__ import annotations

import logging

from flask import flash, g, jsonify, redirect, render_template, request, url_for

from app.middleware.auth_required import admin_required, permission_required
from app.services.admin_event_service import (
    AdminEventMigrationRequired,
    AdminEventService,
    AdminEventValidationError,
)
from app.services.broadcast_notification_service import (
    BroadcastNotificationService,
    BroadcastValidationError,
)
from ._blueprint import admin_bp, clear_admin_context_cache
from ._helpers import handle_errors

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


def _broadcast_form() -> dict:
    return {
        "title": request.form.get("title", ""),
        "content": request.form.get("content", ""),
        "is_active": "is_active" in request.form,
        "is_permanent": "is_permanent" in request.form,
        "start_at": request.form.get("start_at"),
        "end_at": request.form.get("end_at"),
        "link": request.form.get("link", ""),
        "link_text": request.form.get("link_text", ""),
        "sort_order": request.form.get("sort_order", 0),
    }


def _return_to_inbox():
    target = str(request.form.get("next") or "")
    if target.startswith("/admin/notifications") and not target.startswith("//"):
        return redirect(target)
    return redirect(url_for("admin.notifications_index"))


@admin_bp.get("/notifications")
@admin_required
@permission_required("notifications.manage")
@handle_errors("Lỗi tải trung tâm thông báo.", "admin.dashboard")
def notifications_index():
    tab = request.args.get("tab", "inbox")
    tab = tab if tab in {"inbox", "broadcasts"} else "inbox"
    try:
        broadcasts = BroadcastNotificationService().list_all()
    except Exception:
        logger.exception("Cannot load customer broadcasts")
        broadcasts = []
    inbox_page = None
    inbox_stats = {"unread": 0, "high_priority": 0, "open_work": 0, "resolved_today": 0, "total": 0}
    migration_missing = False
    try:
        inbox_page, inbox_stats = AdminEventService().inbox(
            page=_page_number(),
            per_page=20,
            status=request.args.get("status", ""),
            category=request.args.get("category", ""),
            priority=request.args.get("priority", ""),
            query_text=request.args.get("q", ""),
        )
    except AdminEventMigrationRequired:
        migration_missing = True

    return render_template(
        "admin/notifications/index.html",
        tab=tab,
        inbox_page=inbox_page,
        inbox_stats=inbox_stats,
        broadcasts=broadcasts,
        migration_missing=migration_missing,
        filters={
            "status": request.args.get("status", ""),
            "category": request.args.get("category", ""),
            "priority": request.args.get("priority", ""),
            "q": request.args.get("q", ""),
        },
    )


@admin_bp.get("/notifications/events/unread-count")
@admin_required
@permission_required("notifications.manage")
def admin_events_unread_count():
    try:
        return jsonify({"ok": True, "count": AdminEventService().unread_count()})
    except AdminEventMigrationRequired:
        return jsonify({"ok": True, "count": 0, "migration_missing": True})


@admin_bp.post("/notifications/events/<uuid:event_id>/read")
@admin_required
@permission_required("notifications.manage")
def admin_event_read(event_id):
    try:
        AdminEventService().mark_read(str(event_id), admin_user_id=_admin_user_id())
        clear_admin_context_cache()
    except AdminEventValidationError as exc:
        flash(str(exc), "warning")
    return _return_to_inbox()


@admin_bp.post("/notifications/events/<uuid:event_id>/resolve")
@admin_required
@permission_required("notifications.manage")
def admin_event_resolve(event_id):
    try:
        AdminEventService().resolve(str(event_id), admin_user_id=_admin_user_id())
        clear_admin_context_cache()
        flash("Đã đánh dấu công việc là hoàn tất.", "success")
    except AdminEventValidationError as exc:
        flash(str(exc), "warning")
    return _return_to_inbox()


@admin_bp.post("/notifications/events/<uuid:event_id>/reopen")
@admin_required
@permission_required("notifications.manage")
def admin_event_reopen(event_id):
    try:
        AdminEventService().reopen(str(event_id), admin_user_id=_admin_user_id())
        clear_admin_context_cache()
        flash("Đã đưa công việc trở lại danh sách cần xử lý.", "success")
    except AdminEventValidationError as exc:
        flash(str(exc), "warning")
    return _return_to_inbox()


@admin_bp.post("/notifications/events/<uuid:event_id>/open")
@admin_required
@permission_required("notifications.manage")
def admin_event_open(event_id):
    try:
        action_url = AdminEventService().open_action(str(event_id), admin_user_id=_admin_user_id())
        clear_admin_context_cache()
        return redirect(action_url)
    except AdminEventValidationError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("admin.notifications_index"))


@admin_bp.post("/notifications/events/read-all")
@admin_required
@permission_required("notifications.manage")
def admin_events_read_all():
    count = AdminEventService().mark_all_read(admin_user_id=_admin_user_id())
    clear_admin_context_cache()
    flash(f"Đã đánh dấu {count} thông báo là đã đọc.", "success" if count else "info")
    return redirect(url_for("admin.notifications_index"))


@admin_bp.route("/notifications/add", methods=["GET", "POST"])
@admin_required
@permission_required("notifications.manage")
@handle_errors("Lỗi xử lý thêm thông báo.", "admin.notifications_index")
def add_notification():
    if request.method == "POST":
        try:
            item = BroadcastNotificationService().create(_broadcast_form())
            if item:
                clear_admin_context_cache()
                flash("Đã tạo broadcast và đồng bộ đến khách hàng.", "success")
                return redirect(url_for("admin.notifications_index", tab="broadcasts"))
            flash("Không thể tạo broadcast lúc này.", "danger")
        except BroadcastValidationError as exc:
            flash(str(exc), "danger")
    return render_template("admin/notifications/form.html", notification=None)


@admin_bp.route("/notifications/edit/<notif_id>", methods=["GET", "POST"])
@admin_required
@permission_required("notifications.manage")
@handle_errors("Lỗi xử lý cập nhật thông báo.", "admin.notifications_index")
def edit_notification(notif_id):
    service = BroadcastNotificationService()
    item = service.get(notif_id)
    if not item:
        flash("Broadcast không tồn tại.", "danger")
        return redirect(url_for("admin.notifications_index", tab="broadcasts"))
    if request.method == "POST":
        try:
            if service.update(notif_id, _broadcast_form()):
                clear_admin_context_cache()
                flash("Đã cập nhật broadcast.", "success")
                return redirect(url_for("admin.notifications_index", tab="broadcasts"))
            flash("Không thể cập nhật broadcast.", "danger")
        except BroadcastValidationError as exc:
            flash(str(exc), "danger")
    return render_template("admin/notifications/form.html", notification=item)


@admin_bp.post("/notifications/delete/<notif_id>")
@admin_required
@permission_required("notifications.manage")
def delete_notification(notif_id):
    ok = BroadcastNotificationService().delete(notif_id)
    clear_admin_context_cache()
    flash("Đã xóa broadcast." if ok else "Xóa broadcast thất bại.", "success" if ok else "danger")
    return redirect(url_for("admin.notifications_index", tab="broadcasts"))


@admin_bp.post("/notifications/toggle/<notif_id>")
@admin_required
@permission_required("notifications.manage")
def toggle_notification(notif_id):
    ok = BroadcastNotificationService().toggle(notif_id)
    clear_admin_context_cache()
    flash("Đã thay đổi trạng thái broadcast." if ok else "Thao tác thất bại.", "success" if ok else "danger")
    return redirect(url_for("admin.notifications_index", tab="broadcasts"))


@admin_bp.post("/notifications/backfill")
@admin_required
@permission_required("notifications.manage")
def backfill_notifications():
    service = BroadcastNotificationService()
    total = sum(service.fan_out(item["id"]) for item in service.list_all() if item.get("is_active"))
    flash(f"Đã bổ sung {total} bản ghi thông báo khách hàng còn thiếu.", "success")
    return redirect(url_for("admin.notifications_index", tab="broadcasts"))
