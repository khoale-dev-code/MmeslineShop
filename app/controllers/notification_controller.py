"""
app/controllers/notification_controller.py
==========================================
Trang thông báo cho khách hàng.

Hỗ trợ:
- Danh sách thông báo giống Shopee
- Phân trang
- Lọc: all / unread / read
- Đánh dấu đã đọc một thông báo
- Đánh dấu tất cả đã đọc
- Xóa mềm thông báo
- API unread-count cho navbar badge

Nguyên tắc quan trọng:
- Controller KHÔNG query trực tiếp bảng user_notifications bằng get_supabase().
- Mọi thao tác user_notifications đi qua NotificationModel.
- NotificationModel dùng service_role ở server-side và luôn filter theo user_id.
"""

import logging
from typing import Any

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    abort,
    redirect,
    url_for,
    flash,
)

from app.middleware.auth_required import login_required
from app.models.notification_model import NotificationModel

logger = logging.getLogger(__name__)

notification_bp = Blueprint(
    "notification",
    __name__,
    url_prefix="/notifications",
)


# ═══════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════

def _current_user_id() -> str | None:
    """Lấy user_id hiện tại từ Flask session."""
    return session.get("user_id")


def _wants_json() -> bool:
    """
    Kiểm tra request có muốn nhận JSON không.

    Dùng cho action POST có thể được gọi bằng fetch/ajax hoặc form truyền thống.
    """
    return (
        request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in (request.headers.get("Accept") or "")
    )


def _json_error(message: str, status: int = 400, **extra: Any):
    payload = {
        "success": False,
        "error": message,
    }
    payload.update(extra)
    return jsonify(payload), status


def _json_success(**extra: Any):
    payload = {
        "success": True,
    }
    payload.update(extra)
    return jsonify(payload)


def _safe_int(value: Any, default: int = 1, min_value: int = 1, max_value: int | None = None) -> int:
    try:
        number = int(value)
    except Exception:
        number = default

    number = max(min_value, number)

    if max_value is not None:
        number = min(number, max_value)

    return number


def _normalize_filter(value: str | None) -> str:
    if value not in {"all", "unread", "read"}:
        return "all"
    return value


# ═══════════════════════════════════════════════════════════════
# PAGES
# ═══════════════════════════════════════════════════════════════

@notification_bp.route("/")
@login_required
def index():
    """
    Trang danh sách thông báo của người dùng.

    Query params:
      - page: int, mặc định 1
      - filter: all | unread | read, mặc định all
    """
    user_id = _current_user_id()
    if not user_id:
        return abort(403)

    page = _safe_int(request.args.get("page"), default=1, min_value=1)
    filter_type = _normalize_filter(request.args.get("filter", "all"))

    try:
        data = NotificationModel.get_user_notifications(
            user_id=user_id,
            page=page,
            per_page=15,
            filter_type=filter_type,
        )

    except Exception as e:
        logger.error(
            "[notification_controller] index error user_id=%s: %s",
            user_id,
            e,
            exc_info=True,
        )

        data = {
            "items": [],
            "total": 0,
            "page": 1,
            "per_page": 15,
            "total_pages": 1,
        }

        flash("Không tải được danh sách thông báo. Vui lòng thử lại sau.", "warning")

    return render_template(
        "notifications/index.html",
        notifications=data.get("items", []),
        total=data.get("total", 0),
        page=data.get("page", page),
        per_page=data.get("per_page", 15),
        total_pages=data.get("total_pages", 1),
        current_filter=filter_type,
    )


# ═══════════════════════════════════════════════════════════════
# ACTIONS
# ═══════════════════════════════════════════════════════════════

@notification_bp.route("/mark-read/<notification_id>", methods=["POST"])
@login_required
def mark_read(notification_id: str):
    """
    Đánh dấu một thông báo là đã đọc.

    Không tự query user_notifications ở controller.
    NotificationModel.mark_as_read(user_id, notification_id) đã filter theo user_id.
    """
    user_id = _current_user_id()
    if not user_id:
        return _json_error("Unauthorized", 401)

    if not notification_id:
        return _json_error("Missing notification_id", 400)

    try:
        success = NotificationModel.mark_as_read(user_id, notification_id)

        if not success:
            return _json_error("Notification not found or already unavailable", 404)

        if _wants_json():
            return _json_success(notification_id=notification_id)

        flash("Đã đánh dấu thông báo là đã đọc.", "success")
        return redirect(url_for("notification.index"))

    except Exception as e:
        logger.error(
            "[notification_controller] mark_read error user_id=%s notification_id=%s: %s",
            user_id,
            notification_id,
            e,
            exc_info=True,
        )

        if _wants_json():
            return _json_error("Không thể đánh dấu thông báo đã đọc.", 500)

        flash("Không thể đánh dấu thông báo đã đọc.", "danger")
        return redirect(url_for("notification.index"))


@notification_bp.route("/mark-all-read", methods=["POST"])
@login_required
def mark_all_read():
    """Đánh dấu tất cả thông báo chưa đọc của user thành đã đọc."""
    user_id = _current_user_id()
    if not user_id:
        return _json_error("Unauthorized", 401)

    try:
        success = NotificationModel.mark_all_as_read(user_id)

        if _wants_json():
            return _json_success(success=bool(success))

        if success:
            flash("Đã đánh dấu tất cả thông báo là đã đọc.", "success")
        else:
            flash("Không có thông báo nào cần cập nhật.", "info")

        return redirect(url_for("notification.index"))

    except Exception as e:
        logger.error(
            "[notification_controller] mark_all_read error user_id=%s: %s",
            user_id,
            e,
            exc_info=True,
        )

        if _wants_json():
            return _json_error("Không thể đánh dấu tất cả thông báo đã đọc.", 500)

        flash("Không thể đánh dấu tất cả thông báo đã đọc.", "danger")
        return redirect(url_for("notification.index"))


@notification_bp.route("/delete/<notification_id>", methods=["POST"])
@login_required
def delete(notification_id: str):
    """
    Xóa mềm thông báo của user.

    Không kiểm tra bằng anon client ở controller.
    NotificationModel.delete_notification(user_id, notification_id) đã filter user_id.
    """
    user_id = _current_user_id()
    if not user_id:
        return _json_error("Unauthorized", 401)

    if not notification_id:
        return _json_error("Missing notification_id", 400)

    try:
        success = NotificationModel.delete_notification(user_id, notification_id)

        if not success:
            return _json_error("Notification not found or already unavailable", 404)

        if _wants_json():
            return _json_success(notification_id=notification_id)

        flash("Đã xóa thông báo.", "success")
        return redirect(url_for("notification.index"))

    except Exception as e:
        logger.error(
            "[notification_controller] delete error user_id=%s notification_id=%s: %s",
            user_id,
            notification_id,
            e,
            exc_info=True,
        )

        if _wants_json():
            return _json_error("Không thể xóa thông báo.", 500)

        flash("Không thể xóa thông báo.", "danger")
        return redirect(url_for("notification.index"))


# ═══════════════════════════════════════════════════════════════
# API
# ═══════════════════════════════════════════════════════════════

@notification_bp.route("/unread-count", methods=["GET"])
@login_required
def unread_count():
    """
    API trả về số lượng thông báo chưa đọc của user.

    Dùng cho navbar badge.
    Không query trực tiếp user_notifications ở controller.
    """
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"count": 0})

    try:
        count = NotificationModel.get_unread_count(user_id)
        return jsonify({
            "count": int(count or 0)
        })

    except Exception as e:
        logger.error(
            "[notification_controller] unread_count error user_id=%s: %s",
            user_id,
            e,
            exc_info=True,
        )

        return jsonify({"count": 0})    