"""
app/controllers/auth_controller.py
====================================
CHANGELOG (fix đăng nhập / đăng ký):
- Thêm debug logging chi tiết ở login() và register() để dễ trace lỗi.
- reset_password() dùng UserModel.change_password() thay vì gọi thẳng DB
  (tránh RLS chặn khi dùng anon key).
- _set_session() bảo vệ KeyError nếu user dict thiếu field.
- Tách rõ các bước validate → query → authenticate để log từng bước.
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
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def _is_safe_url(target: str) -> bool:
    """Kiểm tra URL redirect có cùng host không (chống open redirect)."""
    ref_url  = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def _fetch_role(user: dict) -> str:
    """
    Đọc role từ dict user.
    Chỉ chấp nhận: 'admin' | 'staff' | 'customer'.
    Mọi giá trị khác fallback về 'customer'.
    """
    role = (user.get("role") or "customer").strip().lower()
    if role not in ("admin", "staff", "customer"):
        logger.warning(
            f"[auth._fetch_role] User id={user.get('id')} "
            f"có role không hợp lệ: '{role}' → fallback 'customer'"
        )
        return "customer"
    return role


def _set_session(user: dict, remember: bool = False) -> None:
    """
    Thiết lập Flask session sau khi xác thực thành công.
    Dùng .get() có default để tránh KeyError nếu DB trả thiếu field.
    """
    session.clear()
    session.permanent = remember
    session["user_id"]        = str(user.get("id", ""))
    session["email"]          = user.get("email", "")
    session["full_name"]      = user.get("full_name", "")
    session["role"]           = _fetch_role(user)
    session["admin_role_slug"] = user.get("admin_role_slug")   # None nếu không có

    logger.info(
        f"[SESSION SET] email={session['email']} | "
        f"role={session['role']} | "
        f"admin_role_slug={session.get('admin_role_slug')}"
    )


# ═══════════════════════════════════════════════════════════════
#  REGISTER
# ═══════════════════════════════════════════════════════════════

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    # Đã đăng nhập → chuyển hướng ngay
    if "user_id" in session:
        return redirect(
            url_for("admin.dashboard") if session.get("role") in ("admin", "staff")
            else url_for("products.index")
        )

    errors = {}

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email     = request.form.get("email", "").strip().lower()
        password  = request.form.get("password", "")
        confirm   = request.form.get("confirm_password", "")

        logger.info(f"[REGISTER] Attempt: email='{email}' full_name='{full_name}'")

        # ── Validate ──────────────────────────────────────────
        if not full_name:
            errors["full_name"] = "Vui lòng nhập họ tên."
        if not email or not EMAIL_RE.match(email):
            errors["email"] = "Email không hợp lệ."
        if len(password) < 6:
            errors["password"] = "Mật khẩu tối thiểu 6 ký tự."
        if password != confirm:
            errors["confirm_password"] = "Mật khẩu xác nhận không khớp."

        # ── Kiểm tra email trùng ──────────────────────────────
        if not errors:
            existing = UserModel.get_by_email(email)
            if existing:
                logger.info(f"[REGISTER] Email đã tồn tại: {email}")
                errors["email"] = "Email này đã được sử dụng."

        # ── Tạo user ─────────────────────────────────────────
        if not errors:
            user = UserModel.create(email=email, password=password, full_name=full_name)

            if user:
                logger.info(f"[REGISTER] Thành công: id={user.get('id')} email={email}")
                _set_session(user)
                flash("Đăng ký thành công! Chào mừng bạn.", "success")
                return redirect(url_for("products.index"))
            else:
                # UserModel.create() đã log chi tiết lỗi DB
                logger.error(f"[REGISTER] UserModel.create() trả về rỗng cho email={email}")
                flash("Đăng ký thất bại. Vui lòng thử lại sau.", "danger")

    return render_template("auth/register.html", errors=errors)


# ═══════════════════════════════════════════════════════════════
#  LOGIN
# ═══════════════════════════════════════════════════════════════

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Đã đăng nhập → chuyển hướng ngay
    if "user_id" in session:
        return redirect(
            url_for("admin.dashboard") if session.get("role") in ("admin", "staff")
            else url_for("products.index")
        )

    error = None

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        logger.info(f"[LOGIN] Attempt: email='{email}'")

        # ── Bước 1: Kiểm tra user tồn tại ────────────────────
        user_record = UserModel.get_by_email(email)
        if not user_record:
            logger.warning(f"[LOGIN] Email không tồn tại trong DB: '{email}'")
            error = "Email hoặc mật khẩu không chính xác."
            return render_template("auth/login.html", error=error)

        # ── Bước 2: Xác thực password ─────────────────────────
        user = UserModel.authenticate(email, password)
        if not user:
            logger.warning(f"[LOGIN] Sai mật khẩu cho email='{email}'")
            error = "Email hoặc mật khẩu không chính xác."
            return render_template("auth/login.html", error=error)

        # ── Bước 3: Kiểm tra tài khoản bị khoá ───────────────
        if user.get("is_suspended"):
            logger.warning(f"[LOGIN] Tài khoản bị khoá: email='{email}'")
            error = "Tài khoản của bạn đã bị tạm khoá. Vui lòng liên hệ hỗ trợ."
            return render_template("auth/login.html", error=error)

        # ── Bước 4: Thiết lập session & redirect ──────────────
        _set_session(user, remember=remember)
        flash(f"Chào mừng trở lại, {user.get('full_name', '')}!", "success")

        next_url = request.args.get("next")
        if next_url and _is_safe_url(next_url):
            return redirect(next_url)

        if session.get("role") in ("admin", "staff"):
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("products.index"))

    return render_template("auth/login.html", error=error)


# ═══════════════════════════════════════════════════════════════
#  LOGOUT
# ═══════════════════════════════════════════════════════════════

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    email = session.get("email", "unknown")
    session.clear()
    logger.info(f"[LOGOUT] {email}")
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for("auth.login"))


# ═══════════════════════════════════════════════════════════════
#  FORGOT PASSWORD
# ═══════════════════════════════════════════════════════════════

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email or not EMAIL_RE.match(email):
            flash("Email không hợp lệ.", "danger")
            return render_template("auth/forgot_password.html")

        user = UserModel.get_by_email(email)

        # Luôn hiện thông báo thành công để tránh leak thông tin email tồn tại
        if user:
            try:
                s         = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
                token     = s.dumps(email, salt="password-reset-salt")
                reset_url = url_for("auth.reset_password", token=token, _external=True)
                send_password_reset_email(email, reset_url)
                logger.info(f"[FORGOT PASSWORD] Gửi email reset tới: {email}")
            except Exception as e:
                logger.error(f"[FORGOT PASSWORD] Lỗi gửi email tới {email}: {e}")
        else:
            logger.info(f"[FORGOT PASSWORD] Email không tồn tại (không gửi): {email}")

        flash("Nếu email tồn tại, chúng tôi đã gửi link đặt lại mật khẩu.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


# ═══════════════════════════════════════════════════════════════
#  RESET PASSWORD
# ═══════════════════════════════════════════════════════════════

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    # ── Xác thực token ────────────────────────────────────────
    try:
        s     = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        email = s.loads(token, salt="password-reset-salt", max_age=3600)  # hết hạn sau 1 giờ
    except Exception as e:
        logger.warning(f"[RESET PASSWORD] Token không hợp lệ hoặc hết hạn: {e}")
        flash("Link đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        # ── Validate ──────────────────────────────────────────
        if len(password) < 6:
            flash("Mật khẩu tối thiểu 6 ký tự.", "danger")
            return render_template("auth/reset_password.html", token=token)

        if password != confirm:
            flash("Mật khẩu xác nhận không khớp.", "danger")
            return render_template("auth/reset_password.html", token=token)

        # ── Đổi mật khẩu qua UserModel (dùng service role, bypass RLS) ──
        ok = UserModel.change_password(email, password)
        if ok:
            logger.info(f"[RESET PASSWORD] Đổi mật khẩu thành công cho: {email}")
            flash("Đặt lại mật khẩu thành công! Vui lòng đăng nhập.", "success")
            return redirect(url_for("auth.login"))
        else:
            logger.error(f"[RESET PASSWORD] Đổi mật khẩu thất bại cho: {email}")
            flash("Có lỗi xảy ra khi đặt lại mật khẩu. Vui lòng thử lại.", "danger")

    return render_template("auth/reset_password.html", token=token)