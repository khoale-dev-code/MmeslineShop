"""
app/controllers/auth_controller.py
====================================
CHANGELOG (Đồng bộ phân quyền & Khắc phục bẫy lỗi Session Admin):
- ĐỒNG BỘ: Sửa đổi các hàm kiểm tra hasattr() điều hướng, loại bỏ bẫy gọi sai Blueprint gây kẹt vòng lặp 302.
- Đồng bộ hóa cấu trúc khóa session["user_role"] và session["user_name"] chuẩn hệ thống GUA Admin.
- Thêm debug logging chi tiết từng bước ở login() và register() để dễ trace lỗi Terminal.
- reset_password() áp dụng UserModel.change_password() để dùng service role bypass RLS.
- Helper _set_session() bảo vệ nghiêm ngặt bằng .get(), chống sập lỗi KeyError nếu DB thiếu trường.
"""

import re
import logging
from urllib.parse import urlparse, urljoin

from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash, current_app)
from itsdangerous import URLSafeTimedSerializer

from app.models.user_model import UserModel
from app.services.email_service import send_password_reset_email

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
EMAIL_RE = re.compile(r"^[^\@\s]+@[^\@\s]+\.[^\@\s]+$")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  HELPERS (XỬ LÝ AN TOÀN HỆ THỐNG)
# ═══════════════════════════════════════════════════════════════

def _is_safe_url(target: str) -> bool:
    """Kiểm tra URL redirect có cùng host không (chống tấn công Open Redirect)."""
    if not target:
        return False
    ref_url  = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def _fetch_role(user: dict) -> str:
    """
    Đọc phân quyền từ bản ghi người dùng.
    Hỗ trợ kiểm tra cả admin_role_slug để gán quyền chuẩn xác nhất.
    """
    # Ưu tiên lấy admin_role_slug, nếu không có lấy trường role, mặc định là customer
    role = (user.get("admin_role_slug") or user.get("role") or "customer").strip().lower()
    
    # Chuẩn hóa nhóm quyền Admin/Staff hệ thống
    if role in ("super_admin", "admin", "staff"):
        return role
    return "customer"


def _set_session(user: dict, remember: bool = False) -> None:
    """
    Thiết lập Flask session sau khi xác thực thành công.
    ✅ ĐÃ ĐỒNG BỘ: Sử dụng các khóa session["user_id"], session["user_role"], 
    session["user_name"] chuẩn hóa để không bị đẩy ngược ra trang Login Admin.
    """
    session.clear()
    session.permanent = remember
    
    # Bọc dữ liệu an toàn phòng hờ DB trả thiếu trường (Tránh KeyError gây lỗi sập 500 HTML)
    session["user_id"]         = str(user.get("id", ""))
    session["email"]           = user.get("email", "")
    session["user_name"]       = user.get("full_name", "Khách hàng")
    session["user_role"]       = _fetch_role(user)
    session["admin_role_slug"] = user.get("admin_role_slug")   # Lưu trữ phục vụ RLS và Audit logs

    logger.info(
        f"[SESSION SET SUCCESS] Đăng nhập thành công: email={session['email']} | "
        f"user_role={session['user_role']} | admin_role_slug={session.get('admin_role_slug')}"
    )


# ═══════════════════════════════════════════════════════════════
#  REGISTER (ĐĂNG KÝ TÀI KHOẢN KHÁCH HÀNG)
# ═══════════════════════════════════════════════════════════════

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    # Khách hàng đã đăng nhập từ trước -> Chuyển hướng an toàn ngay dựa trên quyền hạn
    if "user_id" in session:
        if session.get("user_role") in ("super_admin", "admin", "staff"):
            try:
                return redirect(url_for("admin.dashboard"))
            except Exception:
                return redirect("/admin/")
        try:
            return redirect(url_for("main.index"))
        except Exception:
            return redirect("/")

    errors = {}

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email     = request.form.get("email", "").strip().lower()
        password  = request.form.get("password", "")
        confirm   = request.form.get("confirm_password", "")

        logger.info(f"[REGISTER ATTEMPT] Bắt đầu xử lý đăng ký: email='{email}' | name='{full_name}'")

        # ── Bước 1: Validate dữ liệu đầu vào ──────────────────
        if not full_name:
            errors["full_name"] = "Vui lòng nhập họ và tên của bạn."
        if not email or not EMAIL_RE.match(email):
            errors["email"] = "Định dạng địa chỉ email không hợp lệ."
        if len(password) < 6:
            errors["password"] = "Mật khẩu bảo mật phải tối thiểu từ 6 ký tự trở lên."
        if password != confirm:
            errors["confirm_password"] = "Mật khẩu xác nhận nhập lại không trùng khớp."

        # ── Bước 2: Kiểm tra trùng lặp email hệ thống ─────────
        if not errors:
            existing = UserModel.get_by_email(email)
            if existing:
                logger.info(f"[REGISTER VALIDATION FAILED] Email đã được đăng ký từ trước: {email}")
                errors["email"] = "Địa chỉ email này đã được sử dụng trên hệ thống."

        # ── Bước 3: Đẩy bản ghi mới vào Supabase ──────────────
        if not errors:
            user = UserModel.create(email=email, password=password, full_name=full_name)

            if user:
                logger.info(f"[REGISTER SUCCESS] Tạo tài khoản mới thành công: id={user.get('id')} | email={email}")
                _set_session(user)
                flash(f"Đăng ký tài khoản thành công! Chào mừng {session['user_name']} đến với GUA.", "success")
                try:
                    return redirect(url_for("main.index"))
                except Exception:
                    return redirect("/")
            else:
                logger.error(f"[REGISTER CRASH] UserModel.create() trả về rỗng không rõ nguyên nhân cho email={email}")
                flash("Hệ thống đăng ký gặp sự cố kỹ thuật. Vui lòng thử lại sau!", "danger")

    return render_template("auth/register.html", errors=errors)


# ═══════════════════════════════════════════════════════════════
#  LOGIN (XÁC THỰC VÀ ĐĂNG NHẬP)
# ═══════════════════════════════════════════════════════════════

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Tài khoản đang giữ phiên làm việc active -> Ép chuyển hướng trực tiếp chống kẹt trang login
    if "user_id" in session:
        if session.get("user_role") in ("super_admin", "admin", "staff"):
            try:
                return redirect(url_for("admin.dashboard"))
            except Exception:
                return redirect("/admin/")
        try:
            return redirect(url_for("main.index"))
        except Exception:
            return redirect("/")

    error = None

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        logger.info(f"[LOGIN ATTEMPT] Đang tiến hành xác thực tài khoản: email='{email}'")

        # ── Bước 1: Kiểm tra tài khoản tồn tại trong DB ──────
        user_record = UserModel.get_by_email(email)
        if not user_record:
            logger.warning(f"[LOGIN FAILED] Tài khoản không tồn tại trên hệ thống: '{email}'")
            error = "Địa chỉ email hoặc mật khẩu không chính xác."
            return render_template("auth/login.html", error=error)

        # ── Bước 2: So khớp mật khẩu mã hóa mật định ─────────
        user = UserModel.authenticate(email, password)
        if not user:
            logger.warning(f"[LOGIN FAILED] Sai thông tin mật khẩu truy cập cho tài khoản email='{email}'")
            error = "Địa chỉ email hoặc mật khẩu không chính xác."
            return render_template("auth/login.html", error=error)

        # ── Bước 3: Chặn đứng nếu tài khoản bị khóa RLS/Admin ──
        if user.get("is_suspended") is True:
            logger.warning(f"[LOGIN BLOCKED] Truy cập bị chặn, tài khoản đang bị tạm khóa: email='{email}'")
            error = "Tài khoản của bạn hiện đang bị tạm khóa. Vui lòng liên hệ với bộ phận CSKH để được hỗ trợ."
            return render_template("auth/login.html", error=error)

        # ── Bước 4: Khởi chạy Session & Điều hướng phân vùng ──
        _set_session(user, remember=remember)
        flash(f"Đăng nhập thành công. Chào mừng trở lại, {session['user_name']}!", "success")

        # Kiểm tra tham số next đề phòng bẫy Open Redirect bảo mật
        next_url = request.args.get("next")
        if next_url and _is_safe_url(next_url):
            return redirect(next_url)

        # Điều phối luồng giao diện Admin hoặc trang bán hàng công khai
        if session.get("user_role") in ("super_admin", "admin", "staff"):
            try:
                return redirect(url_for("admin.dashboard"))
            except Exception:
                return redirect("/admin/")
        try:
            return redirect(url_for("main.index"))
        except Exception:
            return redirect("/")

    return render_template("auth/login.html", error=error)


# ═══════════════════════════════════════════════════════════════
#  LOGOUT (ĐĂNG XUẤT HỆ THỐNG)
# ═══════════════════════════════════════════════════════════════

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    email = session.get("email", "unknown")
    session.clear()
    logger.info(f"[LOGOUT SUCCESS] Người dùng đã đăng xuất an toàn: {email}")
    flash("Bạn đã đăng xuất tài khoản làm việc an toàn.", "info")
    return redirect(url_for("auth.login"))


# ═══════════════════════════════════════════════════════════════
#  FORGOT PASSWORD (YÊU CẦU ĐẶT LẠI MẬT KHẨU)
# ═══════════════════════════════════════════════════════════════

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email or not EMAIL_RE.match(email):
            flash("Vui lòng điền địa chỉ định dạng email hợp lệ.", "danger")
            return render_template("auth/forgot_password.html")

        user = UserModel.get_by_email(email)

        # Cơ chế Blind Privacy: Luôn báo thành công ra ngoài để tránh lỗ hổng rò rỉ dữ liệu email tồn tại
        if user:
            try:
                secret_key = current_app.config.get("SECRET_KEY", "fallback_gua_secret")
                s = URLSafeTimedSerializer(secret_key)
                token = s.dumps(email, salt="password-reset-salt")
                reset_url = url_for("auth.reset_password", token=token, _external=True)
                
                send_password_reset_email(email, reset_url)
                logger.info(f"[FORGOT PASSWORD SUCCESS] Đã phát hành mã thông báo và gửi mail reset tới: {email}")
            except Exception as e:
                logger.error(f"[FORGOT PASSWORD CRASH] Lỗi xử lý gửi mail mã hóa tới {email}: {e}")
        else:
            logger.info(f"[FORGOT PASSWORD PRIVACY] Email không tồn tại trên hệ thống (Hủy bỏ gửi): {email}")

        flash("Nếu tài khoản email tồn tại, hệ thống đã gửi đường liên kết đặt lại mật khẩu thành công. Vui lòng kiểm tra Hòm thư!", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


# ═══════════════════════════════════════════════════════════════
#  RESET PASSWORD (XÁC THỰC MÃ TOKEN & ĐỔI MẬT KHẨU)
# ═══════════════════════════════════════════════════════════════

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    # ── Bước 1: Giải mã và kiểm tra hạn mức Token ─────────────
    try:
        secret_key = current_app.config.get("SECRET_KEY", "fallback_gua_secret")
        s = URLSafeTimedSerializer(secret_key)
        email = s.loads(token, salt="password-reset-salt", max_age=3600)  # Hết hiệu lực chính xác sau 1 giờ
    except Exception as e:
        logger.warning(f"[RESET PASSWORD FAILED] Mã thông báo token không hợp lệ hoặc đã hết hạn sử dụng: {e}")
        flash("Đường liên kết đặt lại mật khẩu của bạn không hợp lệ hoặc đã quá hạn sử dụng.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        # ── Bước 2: Validate độ phức tạp mật khẩu mới ──────────
        if len(password) < 6:
            flash("Mật khẩu bảo mật an toàn yêu cầu tối thiểu từ 6 ký tự.", "danger")
            return render_template("auth/reset_password.html", token=token)

        if password != confirm:
            flash("Mật khẩu xác nhận nhập lại không trùng khớp.", "danger")
            return render_template("auth/reset_password.html", token=token)

        # ── Bước 3: Đổi mật khẩu thông qua UserModel Service Role (Bypass RLS) ──
        ok = UserModel.change_password(email, password)
        if ok:
            logger.info(f"[RESET PASSWORD SUCCESS] Đặt lại mật khẩu thành công bằng Service Role cho: {email}")
            flash("Đặt lại mật khẩu thành công! Vui lòng sử dụng mật khẩu mới để đăng nhập hệ thống.", "success")
            return redirect(url_for("auth.login"))
        else:
            logger.error(f"[RESET PASSWORD CRASH] Đổi mật khẩu thất bại tại tầng Database cho: {email}")
            flash("Có lỗi hệ thống xảy ra khi cố gắng thiết lập mật khẩu mới. Vui lòng thử lại sau.", "danger")

    return render_template("auth/reset_password.html", token=token)