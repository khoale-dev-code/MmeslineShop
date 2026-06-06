"""
app/controllers/profile_controller.py
Quản lý hồ sơ cá nhân, bảo mật tài khoản, lịch sử giao dịch và sổ địa chỉ khách hàng.
"""
import os
import uuid
import logging

# Tách riêng request ra để VS Code/PyDev không bị lỗi ngầm
from flask import request, current_app
from flask import Blueprint, render_template, redirect, url_for, session, flash, abort, jsonify

from app.models.user_model import UserModel
from app.models.order_model import OrderModel
from app.models.address_model import AddressModel
from app.utils.security import hash_password, verify_password
from app.middleware.auth_required import login_required
from app.models.shipment_model import ShipmentModel

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")
logger = logging.getLogger(__name__)
# ═══════════════════════════════════════════════════════════════
#  DASHBOARD CÁ NHÂN
# ═══════════════════════════════════════════════════════════════

@profile_bp.route("/")
@login_required
def index():
    """Trang tổng quan tài khoản khách hàng."""
    user_id = session.get("user_id")

    if not user_id:
        session.clear()
        return redirect(url_for("auth.login"))

    try:
        user = UserModel.get_by_id(user_id)

        if not user:
            session.clear()
            flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
            return redirect(url_for("auth.login"))

        # Chuẩn hóa tên hiển thị để tránh None/"None"
        full_name = (user.get("full_name") or "").strip()

        if full_name.lower() in ("none", "null", "undefined"):
            full_name = ""

        fallback_name = (
            full_name
            or session.get("user_name")
            or session.get("full_name")
            or (user.get("email", "").split("@")[0] if user.get("email") else "Khách hàng")
        )

        user["full_name"] = fallback_name

        # Đồng bộ session để navbar/profile dùng cùng dữ liệu
        session["user_name"] = fallback_name
        session["full_name"] = fallback_name
        session["email"] = user.get("email") or session.get("email")

        orders = OrderModel.get_user_orders(user_id) or []

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
        logger.exception(f"Critical Error in Profile Index: {e}")
        return abort(500)
# ═══════════════════════════════════════════════════════════════
#  LỊCH SỬ ĐƠN HÀNG & THEO DÕI VẬN CHUYỂN
# ═══════════════════════════════════════════════════════════════


@profile_bp.route("/orders")
@login_required
def my_orders():
    """Trang danh sách Lịch sử giao dịch của Khách hàng"""
    user_id = session.get("user_id")
    page = request.args.get("page", 1, type=int)
    
    # Lấy danh sách đơn hàng có phân trang
    result = OrderModel.get_user_orders_paginated(user_id, page=page, per_page=10)
    
    return render_template(
        "profile/order/orders.html",
        orders=result["items"],
        pagination=result["pagination"]
    )


@profile_bp.route("/orders/<order_id>")
@login_required
def order_detail(order_id):
    """Trang chi tiết và theo dõi hành trình vận chuyển của 1 đơn hàng"""
    user_id = session.get("user_id")
    order = OrderModel.get_by_id(order_id)
    
    # BẢO MẬT: Chỉ cho phép người dùng xem đơn hàng của chính họ
    if not order or order.get("user_id") != user_id:
        flash("Không tìm thấy đơn hàng hoặc bạn không có quyền xem.", "danger")
        return redirect(url_for("profile.my_orders"))
        
    # Kéo thêm dữ liệu vận chuyển (Timeline) để khách hàng theo dõi (Live Tracking)
    shipment = ShipmentModel.get_by_order_id(order_id)
    if shipment:
        order["shipments"] = shipment
        
    return render_template("profile/order/order_detail.html", order=order)

# ═══════════════════════════════════════════════════════════════
#  HỦY ĐƠN HÀNG (CUSTOMER SELF-CANCEL)
# ═══════════════════════════════════════════════════════════════


@profile_bp.route("/orders/<order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    """
    Khách hàng tự hủy đơn trong vòng 3 giờ đầu. 
    Hỗ trợ cả JSON (fetch API) và form submit thông thường.
    """
    user_id = session.get("user_id")
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" \
              or request.accept_mimetypes.accept_json

    try:
        # Guard an toàn đã nằm trong model cancel_order_by_user (check pending & < 3 giờ)
        success, message = OrderModel.cancel_order_by_user(order_id, user_id)

        if is_ajax:
            return jsonify({"success": success, "message": message}), (200 if success else 400)

        # Fallback: form submit thông thường
        flash(message, "success" if success else "danger")
        return redirect(url_for("profile.order_detail", order_id=order_id))

    except Exception as e:
        logger.error(f"Cancel order error [{order_id}]: {e}")
        if is_ajax:
            return jsonify({"success": False, "message": "Lỗi hệ thống, vui lòng thử lại."}), 500
        flash("Lỗi hệ thống, vui lòng thử lại.", "danger")
        return redirect(url_for("profile.order_detail", order_id=order_id))


# ═══════════════════════════════════════════════════════════════
#  YÊU CẦU ĐỔI / TRẢ HÀNG (RETURN REQUEST)
# ═══════════════════════════════════════════════════════════════
@profile_bp.route("/orders/<order_id>/return", methods=["POST"])
@login_required
def request_return(order_id):
    """
    Khách hàng gửi yêu cầu đổi/trả sau khi nhận hàng.
    Nhận: reason (text), image (File upload thực tế)
    """
    user_id = session.get("user_id")

    reason = request.form.get("reason", "").strip()
    image_file = request.files.get("image")

    if not reason:
        flash("Vui lòng mô tả lý do đổi/trả hàng.", "danger")
        return redirect(url_for("profile.order_detail", order_id=order_id))

    if not image_file or image_file.filename == '':
        flash("Vui lòng đính kèm hình ảnh sản phẩm để hoàn tất yêu cầu.", "danger")
        return redirect(url_for("profile.order_detail", order_id=order_id))

    try:
        # 1. XỬ LÝ LƯU ẢNH THỰC TẾ VÀO SERVER
        # Lấy phần mở rộng của file (ví dụ: .jpg, .png)
        ext = os.path.splitext(image_file.filename)[1]
        # Tạo tên file ngẫu nhiên để không bị trùng lặp
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        
        # Khai báo thư mục lưu ảnh (app/static/uploads/returns)
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'returns')
        os.makedirs(upload_folder, exist_ok=True)  # Tự động tạo thư mục nếu chưa có
        
        # Lưu file ảnh thực tế vào thư mục
        file_path = os.path.join(upload_folder, unique_filename)
        image_file.save(file_path)
        
        # Tạo đường dẫn URL thực tế để lưu vào Database
        image_url = f"/static/uploads/returns/{unique_filename}"

        # 2. LƯU VÀO DATABASE THÔNG QUA MODEL
        success, msg_model = OrderModel.request_return(order_id, user_id, reason, image_url)
        
        if success:
            flash("Yêu cầu hoàn trả đã được gửi thành công!", "success")
        else:
            flash(msg_model or "Không thể gửi yêu cầu đổi/trả.", "danger")

    except Exception as e:
        logger.error(f"Return request error [{order_id}]: {e}")
        flash("Lỗi hệ thống, vui lòng thử lại sau.", "danger")

    return redirect(url_for("profile.order_detail", order_id=order_id))

# ═══════════════════════════════════════════════════════════════
#  QUẢN LÝ THÔNG TIN BẢO MẬT & TÀI KHOẢN
# ═══════════════════════════════════════════════════════════════


@profile_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    user_id = session.get("user_id")

    if not user_id:
        session.clear()
        return redirect(url_for("auth.login"))

    user = UserModel.get_by_id(user_id)

    if not user:
        session.clear()
        flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        form_data = request.form
        full_name = (form_data.get("full_name") or "").strip()
        phone = (form_data.get("phone") or "").strip()

        if not full_name or len(full_name) < 2:
            flash("Định dạng tên không hợp lệ. Tên cần tối thiểu 2 ký tự.", "danger")
            return render_template("profile/edit.html", user=user, current_user=user)

        try:
            update_data = {
                "full_name": full_name,
                "phone": phone,
            }

            if UserModel.update_profile(user_id, update_data):
                # Đồng bộ đủ key session
                session["user_name"] = full_name
                session["full_name"] = full_name

                flash("Hồ sơ cá nhân đã được cập nhật.", "success")
                return redirect(url_for("profile.index"))

            flash("Không thể cập nhật hồ sơ. Vui lòng thử lại.", "danger")

        except Exception as e:
            logger.exception(f"Profile Sync Failed: {e}")
            flash("Lỗi kết nối máy chủ dữ liệu.", "danger")

    return render_template("profile/edit.html", user=user, current_user=user)


@profile_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        form_data = request.form
        current = form_data.get("current_password", "")
        new_pwd = form_data.get("new_password", "")
        confirm = form_data.get("confirm_password", "")
        user_id = session.get("user_id")

        try:
            user = UserModel.get_by_id(user_id)
            if not verify_password(current, user.get("password_hash", "")):
                flash("Xác thực mật khẩu hiện tại thất bại.", "danger")
                return render_template("profile/change_password.html")

            if len(new_pwd) < 8 or new_pwd != confirm:
                flash("Mật khẩu mới không khớp hoặc không đủ độ mạnh (Min 8 ký tự).", "danger")
                return render_template("profile/change_password.html")

            if UserModel.update_profile(user_id, {"password_hash": hash_password(new_pwd)}):
                flash("Mật khẩu đã được thay đổi an toàn.", "success")
                return redirect(url_for("profile.index"))
        except Exception as e:
            logger.error(f"Security Update Failed: {e}")
            flash("Hệ thống bảo mật đang bận.", "danger")

    return render_template("profile/change_password.html")

# ═══════════════════════════════════════════════════════════════
#  QUẢN LÝ SỔ ĐỊA CHỈ (ADDRESS BOOK)
# ═══════════════════════════════════════════════════════════════


@profile_bp.route("/addresses", methods=["GET", "POST"])
@login_required
def addresses():
    user_id = session.get("user_id")
    
    if request.method == "POST":
        form_data = request.form
        
        data = {
            "full_name": form_data.get("full_name", "").strip(),
            "phone": form_data.get("phone", "").strip(),
            "province": form_data.get("province_name", "").strip(),
            "district": form_data.get("district_name", "").strip(),
            "ward": form_data.get("ward_name", "").strip(),
            "address_line": form_data.get("address_line", "").strip(),
            "note": form_data.get("note", "").strip()
        }
        
        is_default = form_data.get("is_default") == "on"
        
        required_fields = ["full_name", "phone", "province", "district", "ward", "address_line"]
        if not all(data[field] for field in required_fields):
            flash("Vui lòng điền đầy đủ thông tin bắt buộc.", "danger")
        else:
            new_addr = AddressModel.add_address(user_id, data)
            
            if is_default and new_addr and new_addr.get("id"):
                AddressModel.set_default(user_id, new_addr["id"])
                
            flash("Đã thêm địa chỉ mới thành công.", "success")
            return redirect(url_for("profile.addresses", next=request.args.get('next')))

    user_addresses = AddressModel.get_user_addresses(user_id)
    return render_template("profile/address/addresses.html", addresses=user_addresses)
@profile_bp.route("/addresses/add", methods=["POST"])
@login_required
def add_address():
    user_id = session.get("user_id")

    full_name = (request.form.get("full_name") or "").strip()
    phone = re.sub(r"\s+", "", (request.form.get("phone") or "").strip())
    address_line = (request.form.get("address_line") or "").strip()

    province = (
        request.form.get("province_name")
        or request.form.get("province")
        or ""
    ).strip()

    district = (
        request.form.get("district_name")
        or request.form.get("district")
        or ""
    ).strip()

    ward = (
        request.form.get("ward_name")
        or request.form.get("ward")
        or ""
    ).strip()

    note = (request.form.get("note") or "").strip()
    is_default = request.form.get("is_default") == "1"

    if not all([full_name, phone, address_line, province, district, ward]):
        flash("Vui lòng nhập đầy đủ thông tin địa chỉ.", "danger")
        return redirect(url_for("profile.addresses"))

    data = {
        "user_id": user_id,
        "full_name": full_name,
        "phone": phone,
        "address_line": address_line,
        "province": province,
        "district": district,
        "ward": ward,
        "province_name": province,
        "district_name": district,
        "ward_name": ward,
        "note": note,
        "is_default": is_default,
    }

    AddressModel.create(data)

    flash("Đã thêm địa chỉ mới.", "success")
    return redirect(url_for("profile.addresses"))

@profile_bp.route("/addresses/set-default/<address_id>", methods=["POST"])
@login_required
def set_default_address(address_id):
    user_id = session.get("user_id")
    if AddressModel.set_default(user_id, address_id):
        flash("Đã cập nhật địa chỉ mặc định.", "success")
    else:
        flash("Có lỗi xảy ra khi cập nhật địa chỉ, vui lòng thử lại.", "danger")
    
    form_data = request.form
    next_url = form_data.get("next_url", url_for("profile.addresses"))
    
    return redirect(next_url)


@profile_bp.route("/addresses/delete/<address_id>", methods=["POST"])
@login_required
def delete_address(address_id):
    user_id = session.get("user_id")
    if AddressModel.delete_address(user_id, address_id):
        flash("Đã xóa địa chỉ thành công.", "success")
    else:
        flash("Không thể xóa địa chỉ này.", "danger")
        
    return redirect(url_for("profile.addresses"))


@profile_bp.route("/addresses/edit/<address_id>", methods=["POST"])
@login_required
def edit_address(address_id):
    """Cập nhật một địa chỉ hiện có."""
    user_id = session.get("user_id")
    form_data = request.form
    
    data = {
        "full_name": form_data.get("full_name", "").strip(),
        "phone": form_data.get("phone", "").strip(),
        "province": form_data.get("province_name", "").strip(),
        "district": form_data.get("district_name", "").strip(),
        "ward": form_data.get("ward_name", "").strip(),
        "address_line": form_data.get("address_line", "").strip(),
        "note": form_data.get("note", "").strip()
    }
    
    is_default = form_data.get("is_default") == "on"
    
    required_fields = ["full_name", "phone", "province", "district", "ward", "address_line"]
    if not all(data[field] for field in required_fields):
        flash("Vui lòng điền đầy đủ thông tin bắt buộc.", "danger")
    else:
        if AddressModel.update_address(user_id, address_id, data):
            if is_default:
                AddressModel.set_default(user_id, address_id)
            flash("Đã cập nhật địa chỉ thành công.", "success")
        else:
            flash("Không thể cập nhật địa chỉ này hoặc bạn không có quyền.", "danger")
            
    next_url = request.args.get('next')
    if next_url:
        return redirect(url_for("profile.addresses", next=next_url))
    return redirect(url_for("profile.addresses"))
