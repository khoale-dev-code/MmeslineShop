"""
app/controllers/profile_controller.py
Quản lý hồ sơ cá nhân, bảo mật tài khoản, lịch sử giao dịch và sổ địa chỉ khách hàng.
"""

import os
import re
import uuid
import logging

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    abort,
    jsonify,
    request,
    current_app,
)

from app.models.user_model import UserModel
from app.models.order_model import OrderModel
from app.models.address_model import AddressModel
from app.models.shipment_model import ShipmentModel
from app.utils.security import hash_password, verify_password
from app.middleware.auth_required import login_required

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _clean_text(value: str | None) -> str:
    value = (value or "").strip()
    if value.lower() in ("none", "null", "undefined", "nan"):
        return ""
    return value


def _clean_phone(value: str | None) -> str:
    """
    Chuẩn hóa số điện thoại:
    - Bỏ khoảng trắng, dấu chấm, dấu gạch.
    - Giữ lại dấu + nếu có.
    """
    value = (value or "").strip()
    value = re.sub(r"[\s\-.()]+", "", value)
    return value


def _is_checked(value: str | None) -> bool:
    return str(value or "").lower() in ("1", "true", "on", "yes")


def _get_current_user_or_redirect():
    user_id = session.get("user_id")

    if not user_id:
        session.clear()
        return None, redirect(url_for("auth.login"))

    user = UserModel.get_by_id(user_id)

    if not user:
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return None, redirect(url_for("auth.login"))

    email = _clean_text(user.get("email") or session.get("email"))
    full_name = (
        _clean_text(user.get("full_name"))
        or _clean_text(user.get("name"))
        or _clean_text(session.get("user_name"))
        or _clean_text(session.get("full_name"))
        or (email.split("@")[0] if email else "Khách hàng")
    )

    user["full_name"] = full_name
    user["email"] = email

    session["user_name"] = full_name
    session["full_name"] = full_name
    if email:
        session["email"] = email

    session.modified = True
    return user, None


def _address_payload_from_form(user_id: str) -> dict:
    """
    Đồng bộ tên field giữa form mới/cũ:
    - province_name/district_name/ward_name
    - province/district/ward
    - alias hidden fields
    """
    province = _clean_text(
        request.form.get("province_name")
        or request.form.get("province")
        or request.form.get("hid-prov")
    )

    district = _clean_text(
        request.form.get("district_name")
        or request.form.get("district")
        or request.form.get("hid-dist")
    )

    ward = _clean_text(
        request.form.get("ward_name")
        or request.form.get("ward")
        or request.form.get("hid-ward")
    )

    return {
        "user_id": user_id,
        "full_name": _clean_text(request.form.get("full_name")),
        "phone": _clean_phone(request.form.get("phone")),
        "province": province,
        "district": district,
        "ward": ward,
        "province_name": province,
        "district_name": district,
        "ward_name": ward,
        "province_code": _clean_text(request.form.get("province_code")),
        "district_code": _clean_text(request.form.get("district_code")),
        "ward_code": _clean_text(request.form.get("ward_code")),
        "address_line": _clean_text(request.form.get("address_line")),
        "note": _clean_text(request.form.get("note")),
        "is_default": _is_checked(request.form.get("is_default")),
    }


def _validate_address_payload(data: dict) -> tuple[bool, str]:
    required_fields = {
        "full_name": "họ và tên",
        "phone": "số điện thoại",
        "province": "tỉnh/thành phố",
        "district": "quận/huyện",
        "ward": "phường/xã",
        "address_line": "địa chỉ chi tiết",
    }

    missing = [label for key, label in required_fields.items() if not data.get(key)]

    if missing:
        return False, "Vui lòng nhập đầy đủ: " + ", ".join(missing) + "."

    if len(data["full_name"]) < 2:
        return False, "Họ và tên cần tối thiểu 2 ký tự."

    if not re.match(r"^(\+?84|0)[0-9]{8,11}$", data["phone"]):
        return False, "Số điện thoại không hợp lệ."

    return True, ""


def _create_address(user_id: str, data: dict):
    """
    Tương thích nhiều phiên bản AddressModel:
    - create(data)
    - add_address(user_id, data)
    """
    if hasattr(AddressModel, "create"):
        return AddressModel.create(data)

    payload = dict(data)
    payload.pop("user_id", None)

    if hasattr(AddressModel, "add_address"):
        return AddressModel.add_address(user_id, payload)

    raise AttributeError("AddressModel thiếu hàm create hoặc add_address.")


def _update_address(user_id: str, address_id: str, data: dict) -> bool:
    payload = dict(data)
    payload.pop("user_id", None)
    payload.pop("is_default", None)

    if hasattr(AddressModel, "update_address"):
        return bool(AddressModel.update_address(user_id, address_id, payload))

    if hasattr(AddressModel, "update"):
        return bool(AddressModel.update(address_id, payload, user_id=user_id))

    raise AttributeError("AddressModel thiếu hàm update_address hoặc update.")


def _safe_next_url(default_endpoint: str = "profile.addresses"):
    next_url = request.args.get("next") or request.form.get("next_url")
    if next_url and next_url.startswith("/"):
        return next_url
    return url_for(default_endpoint)


# ═══════════════════════════════════════════════════════════════
# DASHBOARD CÁ NHÂN
# ═══════════════════════════════════════════════════════════════

@profile_bp.route("/")
@login_required
def index():
    user, redirect_response = _get_current_user_or_redirect()
    if redirect_response:
        return redirect_response

    user_id = session.get("user_id")

    try:
        try:
            orders = OrderModel.get_user_orders(user_id) or []
        except Exception as order_error:
            logger.warning("[Profile.index] Không lấy được orders: %s", order_error)
            orders = []

        stats = {
            "total": len(orders),
            "pending": sum(1 for o in orders if o.get("status") == "pending"),
            "delivered": sum(
                1 for o in orders
                if o.get("status") in ("delivered", "completed")
            ),
            "spent": sum(
                float(o.get("total_amount") or 0)
                for o in orders
                if o.get("status") != "cancelled"
            ),
        }

        return render_template(
            "profile/index.html",
            user=user,
            current_user=user,
            orders=orders[:5],
            stats=stats,
        )

    except Exception as e:
        logger.exception("[Profile.index] Critical error: %s", e)
        return abort(500)


# ═══════════════════════════════════════════════════════════════
# LỊCH SỬ ĐƠN HÀNG
# ═══════════════════════════════════════════════════════════════

@profile_bp.route("/orders")
@login_required
def my_orders():
    user_id = session.get("user_id")
    page = request.args.get("page", 1, type=int)

    try:
        result = OrderModel.get_user_orders_paginated(user_id, page=page, per_page=10)
    except Exception as e:
        logger.exception("[Profile.my_orders] Lỗi lấy đơn hàng: %s", e)
        result = {
            "items": [],
            "pagination": {
                "page": page,
                "per_page": 10,
                "total": 0,
                "pages": 1,
                "has_prev": False,
                "has_next": False,
            },
        }
        flash("Không thể tải lịch sử đơn hàng. Vui lòng thử lại sau.", "warning")

    return render_template(
        "profile/order/orders.html",
        orders=result.get("items", []),
        pagination=result.get("pagination", {}),
    )


@profile_bp.route("/orders/<order_id>")
@login_required
def order_detail(order_id):
    user_id = session.get("user_id")

    try:
        order = OrderModel.get_by_id(order_id)
    except Exception as e:
        logger.exception("[Profile.order_detail] Lỗi lấy đơn hàng %s: %s", order_id, e)
        order = None

    if not order or order.get("user_id") != user_id:
        flash("Không tìm thấy đơn hàng hoặc bạn không có quyền xem.", "danger")
        return redirect(url_for("profile.my_orders"))

    try:
        shipment = ShipmentModel.get_by_order_id(order_id)
        if shipment:
            order["shipments"] = shipment
    except Exception as e:
        logger.warning("[Profile.order_detail] Không lấy được shipment: %s", e)

    return render_template("profile/order/order_detail.html", order=order)


@profile_bp.route("/orders/<order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    user_id = session.get("user_id")
    is_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.accept_mimetypes.accept_json
    )

    try:
        success, message = OrderModel.cancel_order_by_user(order_id, user_id)

        if is_ajax:
            return jsonify({"success": success, "message": message}), (200 if success else 400)

        flash(message, "success" if success else "danger")
        return redirect(url_for("profile.order_detail", order_id=order_id))

    except Exception as e:
        logger.exception("[Profile.cancel_order] Lỗi hủy đơn %s: %s", order_id, e)

        if is_ajax:
            return jsonify({
                "success": False,
                "message": "Lỗi hệ thống, vui lòng thử lại."
            }), 500

        flash("Lỗi hệ thống, vui lòng thử lại.", "danger")
        return redirect(url_for("profile.order_detail", order_id=order_id))


@profile_bp.route("/orders/<order_id>/return", methods=["POST"])
@login_required
def request_return(order_id):
    user_id = session.get("user_id")
    reason = _clean_text(request.form.get("reason"))
    image_file = request.files.get("image")

    if not reason:
        flash("Vui lòng mô tả lý do đổi/trả hàng.", "danger")
        return redirect(url_for("profile.order_detail", order_id=order_id))

    if not image_file or image_file.filename == "":
        flash("Vui lòng đính kèm hình ảnh sản phẩm để hoàn tất yêu cầu.", "danger")
        return redirect(url_for("profile.order_detail", order_id=order_id))

    try:
        ext = os.path.splitext(image_file.filename)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            flash("Định dạng ảnh không hợp lệ. Vui lòng dùng JPG, PNG hoặc WEBP.", "danger")
            return redirect(url_for("profile.order_detail", order_id=order_id))

        unique_filename = f"{uuid.uuid4().hex}{ext}"
        upload_folder = os.path.join(current_app.root_path, "static", "uploads", "returns")
        os.makedirs(upload_folder, exist_ok=True)

        file_path = os.path.join(upload_folder, unique_filename)
        image_file.save(file_path)

        image_url = f"/static/uploads/returns/{unique_filename}"

        success, msg_model = OrderModel.request_return(order_id, user_id, reason, image_url)

        if success:
            flash("Yêu cầu hoàn trả đã được gửi thành công!", "success")
        else:
            flash(msg_model or "Không thể gửi yêu cầu đổi/trả.", "danger")

    except Exception as e:
        logger.exception("[Profile.request_return] Lỗi đổi/trả đơn %s: %s", order_id, e)
        flash("Lỗi hệ thống, vui lòng thử lại sau.", "danger")

    return redirect(url_for("profile.order_detail", order_id=order_id))


# ═══════════════════════════════════════════════════════════════
# HỒ SƠ & BẢO MẬT
# ═══════════════════════════════════════════════════════════════

@profile_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    user, redirect_response = _get_current_user_or_redirect()
    if redirect_response:
        return redirect_response

    user_id = session.get("user_id")

    if request.method == "POST":
        full_name = _clean_text(request.form.get("full_name"))
        phone = _clean_phone(request.form.get("phone"))

        if not full_name or len(full_name) < 2:
            flash("Định dạng tên không hợp lệ. Tên cần tối thiểu 2 ký tự.", "danger")
            return render_template("profile/edit.html", user=user, current_user=user)

        try:
            update_data = {
                "full_name": full_name,
                "phone": phone,
            }

            if UserModel.update_profile(user_id, update_data):
                session["user_name"] = full_name
                session["full_name"] = full_name
                session.modified = True

                flash("Hồ sơ cá nhân đã được cập nhật.", "success")
                return redirect(url_for("profile.index"))

            flash("Không thể cập nhật hồ sơ. Vui lòng thử lại.", "danger")

        except Exception as e:
            logger.exception("[Profile.edit] Cập nhật hồ sơ thất bại: %s", e)
            flash("Lỗi kết nối máy chủ dữ liệu.", "danger")

    return render_template("profile/edit.html", user=user, current_user=user)


@profile_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    user_id = session.get("user_id")

    if request.method == "POST":
        current = request.form.get("current_password", "")
        new_pwd = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        try:
            user = UserModel.get_by_id(user_id)

            if not user:
                session.clear()
                flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
                return redirect(url_for("auth.login"))

            if not verify_password(current, user.get("password_hash", "")):
                flash("Xác thực mật khẩu hiện tại thất bại.", "danger")
                return render_template("profile/change_password.html")

            if len(new_pwd) < 8:
                flash("Mật khẩu mới cần tối thiểu 8 ký tự.", "danger")
                return render_template("profile/change_password.html")

            if new_pwd != confirm:
                flash("Mật khẩu xác nhận không khớp.", "danger")
                return render_template("profile/change_password.html")

            if UserModel.update_profile(user_id, {"password_hash": hash_password(new_pwd)}):
                flash("Mật khẩu đã được thay đổi an toàn.", "success")
                return redirect(url_for("profile.index"))

            flash("Không thể cập nhật mật khẩu. Vui lòng thử lại.", "danger")

        except Exception as e:
            logger.exception("[Profile.change_password] Lỗi đổi mật khẩu: %s", e)
            flash("Hệ thống bảo mật đang bận.", "danger")

    return render_template("profile/change_password.html")


# ═══════════════════════════════════════════════════════════════
# SỔ ĐỊA CHỈ
# ═══════════════════════════════════════════════════════════════

@profile_bp.route("/addresses", methods=["GET"])
@login_required
def addresses():
    user_id = session.get("user_id")

    try:
        user_addresses = AddressModel.get_user_addresses(user_id) or []
    except Exception as e:
        logger.exception("[Profile.addresses] Lỗi lấy địa chỉ: %s", e)
        user_addresses = []
        flash("Không thể tải danh sách địa chỉ. Vui lòng thử lại sau.", "warning")

    return render_template("profile/address/addresses.html", addresses=user_addresses)

@profile_bp.route("/addresses/add", methods=["POST"])
@login_required
def add_address():
    user_id = session.get("user_id")
    data = _address_payload_from_form(user_id)

    valid, message = _validate_address_payload(data)
    if not valid:
        flash(message, "danger")
        return redirect(_safe_next_url())

    try:
        new_addr = _create_address(user_id, data)

        if not new_addr or not new_addr.get("id"):
            flash("Không thể lưu địa chỉ. Vui lòng kiểm tra lại dữ liệu.", "danger")
            return redirect(_safe_next_url())

        if data.get("is_default") and hasattr(AddressModel, "set_default"):
            AddressModel.set_default(user_id, new_addr["id"])

        flash("Đã thêm địa chỉ mới thành công.", "success")

    except Exception as e:
        logger.exception("[Profile.add_address] Lỗi thêm địa chỉ: %s", e)
        flash("Không thể lưu địa chỉ. Vui lòng thử lại.", "danger")

    return redirect(_safe_next_url())


@profile_bp.route("/addresses/set-default/<address_id>", methods=["POST"])
@login_required
def set_default_address(address_id):
    user_id = session.get("user_id")

    try:
        success = AddressModel.set_default(user_id, address_id)
        if success:
            flash("Đã cập nhật địa chỉ mặc định.", "success")
        else:
            flash("Có lỗi xảy ra khi cập nhật địa chỉ, vui lòng thử lại.", "danger")

    except Exception as e:
        logger.exception("[Profile.set_default_address] Lỗi set default %s: %s", address_id, e)
        flash("Không thể cập nhật địa chỉ mặc định.", "danger")

    return redirect(_safe_next_url())


@profile_bp.route("/addresses/delete/<address_id>", methods=["POST"])
@login_required
def delete_address(address_id):
    user_id = session.get("user_id")

    try:
        success = AddressModel.delete_address(user_id, address_id)
        if success:
            flash("Đã xóa địa chỉ thành công.", "success")
        else:
            flash("Không thể xóa địa chỉ này.", "danger")

    except Exception as e:
        logger.exception("[Profile.delete_address] Lỗi xóa địa chỉ %s: %s", address_id, e)
        flash("Không thể xóa địa chỉ này.", "danger")

    return redirect(_safe_next_url())


@profile_bp.route("/addresses/edit/<address_id>", methods=["POST"])
@login_required
def edit_address(address_id):
    user_id = session.get("user_id")
    data = _address_payload_from_form(user_id)

    valid, message = _validate_address_payload(data)
    if not valid:
        flash(message, "danger")
        return redirect(_safe_next_url())

    try:
        success = _update_address(user_id, address_id, data)

        if success:
            if data.get("is_default") and hasattr(AddressModel, "set_default"):
                AddressModel.set_default(user_id, address_id)

            flash("Đã cập nhật địa chỉ thành công.", "success")
        else:
            flash("Không thể cập nhật địa chỉ này hoặc bạn không có quyền.", "danger")

    except Exception as e:
        logger.exception("[Profile.edit_address] Lỗi cập nhật địa chỉ %s: %s", address_id, e)
        flash("Không thể cập nhật địa chỉ. Vui lòng thử lại.", "danger")

    return redirect(_safe_next_url())