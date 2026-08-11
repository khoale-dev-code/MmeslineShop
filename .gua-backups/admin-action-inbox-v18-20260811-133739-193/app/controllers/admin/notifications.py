"""
app/controllers/admin/notifications.py
Quản lý thông báo hệ thống (Admin CRUD)
"""
import logging
from flask import render_template, redirect, url_for, flash, request
from app.middleware.auth_required import admin_required
from app.models.notification_model import NotificationModel
from ._blueprint import admin_bp
from ._helpers import _form, _db, handle_errors

logger = logging.getLogger(__name__)


@admin_bp.route("/notifications")
@admin_required
@handle_errors("Lỗi tải danh sách thông báo.", "admin.dashboard")
def notifications_index():
    """Danh sách thông báo (admin)."""
    notifications = NotificationModel.get_all_admin()
    return render_template("admin/notifications/index.html", notifications=notifications)


@admin_bp.route("/notifications/add", methods=["GET", "POST"])
@admin_required
@handle_errors("Lỗi xử lý thêm thông báo.", "admin.notifications_index")
def add_notification():
    """Thêm thông báo mới."""
    if request.method == "POST":
        form = _form()
        data = {
            "title": form.get("title", "").strip(),
            "content": form.get("content", "").strip(),
            "is_active": "is_active" in form,
            "is_permanent": "is_permanent" in form,
            "start_at": form.get("start_at") or None,
            "end_at": form.get("end_at") or None,
            "link": form.get("link", "").strip() or None,
            "link_text": form.get("link_text", "").strip() or None,
            "sort_order": int(form.get("sort_order", 0)),
        }
        if not data["title"] or not data["content"]:
            flash("Vui lòng nhập đầy đủ tiêu đề và nội dung.", "danger")
            return render_template("admin/notifications/form.html", notification=None)

        new_notif = NotificationModel.create(data)
        if new_notif:
            flash("Đã thêm thông báo thành công!", "success")
            return redirect(url_for("admin.notifications_index"))
        else:
            flash("Lỗi khi tạo thông báo. Vui lòng thử lại.", "danger")

    return render_template("admin/notifications/form.html", notification=None)


@admin_bp.route("/notifications/edit/<notif_id>", methods=["GET", "POST"])
@admin_required
@handle_errors("Lỗi xử lý cập nhật thông báo.", "admin.notifications_index")
def edit_notification(notif_id):
    """Chỉnh sửa thông báo."""
    notif = NotificationModel.get_by_id(notif_id)
    if not notif:
        flash("Thông báo không tồn tại.", "danger")
        return redirect(url_for("admin.notifications_index"))

    if request.method == "POST":
        form = _form()
        data = {
            "title": form.get("title", "").strip(),
            "content": form.get("content", "").strip(),
            "is_active": "is_active" in form,
            "is_permanent": "is_permanent" in form,
            "start_at": form.get("start_at") or None,
            "end_at": form.get("end_at") or None,
            "link": form.get("link", "").strip() or None,
            "link_text": form.get("link_text", "").strip() or None,
            "sort_order": int(form.get("sort_order", 0)),
        }
        if not data["title"] or not data["content"]:
            flash("Vui lòng nhập đầy đủ tiêu đề và nội dung.", "danger")
            return render_template("admin/notifications/form.html", notification=notif)

        if NotificationModel.update(notif_id, data):
            flash("Đã cập nhật thông báo!", "success")
            return redirect(url_for("admin.notifications_index"))
        else:
            flash("Lỗi khi cập nhật.", "danger")

    return render_template("admin/notifications/form.html", notification=notif)


@admin_bp.route("/notifications/delete/<notif_id>", methods=["POST"])
@admin_required
@handle_errors("Lỗi xóa thông báo.", "admin.notifications_index")
def delete_notification(notif_id):
    """Xóa thông báo (vĩnh viễn)."""
    if NotificationModel.delete(notif_id):
        flash("Đã xóa thông báo.", "success")
    else:
        flash("Xóa thất bại.", "danger")
    return redirect(url_for("admin.notifications_index"))


@admin_bp.route("/notifications/toggle/<notif_id>", methods=["POST"])
@admin_required
@handle_errors("Lỗi thay đổi trạng thái.", "admin.notifications_index")
def toggle_notification(notif_id):
    """Bật/tắt trạng thái hiển thị của thông báo."""
    if NotificationModel.toggle_active(notif_id):
        flash("Đã thay đổi trạng thái.", "success")
    else:
        flash("Thao tác thất bại.", "danger")
    return redirect(url_for("admin.notifications_index"))


@admin_bp.route("/notifications/backfill", methods=["POST"])
@admin_required
@handle_errors("Lỗi backfill thông báo.", "admin.notifications_index")
def backfill_notifications():
    """Fan-out tất cả thông báo active hiện có cho toàn bộ user (dùng 1 lần để fix data cũ)."""
    notifications = NotificationModel.get_all_admin()
    total = 0
    for notif in notifications:
        if notif.get("is_active"):
            total += NotificationModel.fan_out_to_all_users(notif["id"])
    flash(f"Đã backfill {total} bản ghi user_notifications.", "success")
    return redirect(url_for("admin.notifications_index"))
