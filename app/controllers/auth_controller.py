"""
app/controllers/auth_controller.py
==================================
Controller xác thực cho GUAMAISON / Fashion Store.

Đã xử lý:
- Sửa lỗi POST /auth/login bị 403 do CSRF tokens do not match.
- Không session.clear() trần khi login/logout.
- Không xóa csrf_token khi logout.
- Chống cache trang /auth/* để tránh browser dùng form login cũ.
- Đồng bộ session user_name/full_name để profile/navbar không hiện None.
- Chuẩn hóa tên người dùng khi register/login.
- Có đủ route:
  /auth/login
  /auth/logout
  /auth/register
  /auth/forgot-password
  /auth/reset-password/<token>
"""

import logging
import re
from urllib.parse import urljoin, urlparse

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_wtf.csrf import CSRFError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.models.user_model import UserModel

try:
    from app.services.email_service import send_password_reset_email
except Exception:
    send_password_reset_email = None


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^\@\s]+@[^\@\s]+\.[^\@\s]+$")


# ═══════════════════════════════════════════════════════════════
# CSRF ERROR HANDLER
# ═══════════════════════════════════════════════════════════════

@auth_bp.errorhandler(CSRFError)
def handle_auth_csrf_error(e):
    """
    Khi token CSRF cũ bị submit ở /auth/login, không trả 403 trắng.
    Redirect về login mới để server render lại csrf_token mới.
    """
    logger.warning("[AUTH CSRF] CSRF token mismatch ở %s: %s", request.path, e.description)

    preserved_csrf = session.get("csrf_token")

    for key in [
        "user_id",
        "email",
        "user_name",
        "full_name",
        "role",
        "user_role",
        "admin_role_slug",
        "is_authenticated",
        "cart_items",
        "cart_count",
        "cart_total",
    ]:
        session.pop(key, None)

    if preserved_csrf:
        session["csrf_token"] = preserved_csrf

    session.modified = True

    flash("Phiên đăng nhập đã được làm mới. Vui lòng đăng nhập lại.", "warning")
    return redirect(url_for("auth.login"))


# ═══════════════════════════════════════════════════════════════
# RESPONSE HEADERS
# ═══════════════════════════════════════════════════════════════

@auth_bp.after_request
def add_auth_no_cache_headers(response):
    """
    Không cache trang auth.

    Lý do:
    - CSRF token phụ thuộc session.
    - Nếu browser dùng lại trang login cũ sau logout, form sẽ gửi token cũ.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Auth-Page"] = "no-cache"
    return response


# ═══════════════════════════════════════════════════════════════
# SESSION HELPERS
# ═══════════════════════════════════════════════════════════════

def _clean_name(value: str | None) -> str:
    """
    Chuẩn hóa tên để tránh UI hiện None/null/undefined.
    """
    value = (value or "").strip()

    if value.lower() in ("none", "null", "undefined", "nan"):
        return ""

    return value


def _clear_auth_session_preserve_csrf() -> None:
    """
    Xóa trạng thái đăng nhập nhưng giữ csrf_token.

    Đây là phần quan trọng để tránh lỗi:
    flask_wtf.csrf:The CSRF tokens do not match.
    """
    preserved_csrf = session.get("csrf_token")

    keys_to_remove = [
        "user_id",
        "email",
        "user_name",
        "full_name",
        "role",
        "user_role",
        "admin_role_slug",
        "is_authenticated",
        "cart_items",
        "cart_count",
        "cart_total",
    ]

    for key in keys_to_remove:
        session.pop(key, None)

    if preserved_csrf:
        session["csrf_token"] = preserved_csrf

    session.modified = True


def _set_login_session(user: dict, remember: bool = False) -> None:
    """
    Set session đăng nhập nhưng vẫn giữ csrf_token hiện tại.
    Không dùng session.clear() trần.
    Đồng bộ user_name/full_name để profile/navbar không hiện None.
    """
    preserved_csrf = session.get("csrf_token")

    _clear_auth_session_preserve_csrf()

    if preserved_csrf:
        session["csrf_token"] = preserved_csrf

    role = _fetch_role(user)
    email = _normalize_email(user.get("email"))

    full_name = (
        _clean_name(user.get("full_name"))
        or _clean_name(user.get("name"))
        or (email.split("@")[0] if email else "")
        or "Khách hàng"
    )

    session.permanent = bool(remember)

    session["user_id"] = user.get("id")
    session["email"] = email
    session["user_name"] = full_name
    session["full_name"] = full_name

    # Giữ cả 2 key để tương thích code cũ.
    session["role"] = role
    session["user_role"] = role

    session["admin_role_slug"] = user.get("admin_role_slug")
    session["is_authenticated"] = True

    session.modified = True


# ═══════════════════════════════════════════════════════════════
# BASIC HELPERS
# ═══════════════════════════════════════════════════════════════

def _normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def _is_safe_url(target: str | None) -> bool:
    if not target:
        return False

    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))

    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def _safe_next_url() -> str | None:
    target = request.args.get("next") or request.form.get("next")

    if _is_safe_url(target):
        return target

    return None


def _get_serializer() -> URLSafeTimedSerializer:
    secret = current_app.config.get("SECRET_KEY") or "GUAMAISON-dev-secret"
    return URLSafeTimedSerializer(secret)


def _fetch_role(user: dict) -> str:
    role = (user.get("role") or "customer").strip().lower()

    if role in ("super_admin", "admin", "staff"):
        return role

    return "customer"


def _get_user_by_email(email: str) -> dict | None:
    try:
        return UserModel.get_by_email(email)
    except Exception as e:
        logger.error("[AUTH] Lỗi UserModel.get_by_email(%s): %s", email, e, exc_info=True)
        return None


def _verify_user_password(user: dict, password: str) -> bool:
    if not user or not password:
        return False

    try:
        if hasattr(UserModel, "verify_password"):
            return bool(UserModel.verify_password(user, password))

        if hasattr(UserModel, "check_password"):
            return bool(UserModel.check_password(user, password))

        if hasattr(UserModel, "authenticate"):
            email = user.get("email")
            authenticated = UserModel.authenticate(email, password)
            return bool(authenticated)

    except Exception as e:
        logger.error(
            "[AUTH] Lỗi verify password cho email=%s: %s",
            user.get("email"),
            e,
            exc_info=True,
        )
        return False

    logger.error("[AUTH] UserModel thiếu method verify_password/check_password/authenticate.")
    return False


def _create_user(email: str, password: str, full_name: str, phone: str | None = None) -> dict | None:
    try:
        try:
            return UserModel.create(
                email=email,
                password=password,
                full_name=full_name,
                phone=phone,
            )
        except TypeError:
            return UserModel.create(
                email=email,
                password=password,
                full_name=full_name,
            )

    except Exception as e:
        logger.error("[AUTH] Lỗi tạo user email=%s: %s", email, e, exc_info=True)
        return None


def _change_password(email: str, new_password: str) -> bool:
    try:
        if hasattr(UserModel, "change_password"):
            return bool(UserModel.change_password(email, new_password))

        if hasattr(UserModel, "update_password"):
            return bool(UserModel.update_password(email, new_password))

        user = _get_user_by_email(email)
        if not user:
            return False

        if hasattr(UserModel, "set_password"):
            return bool(UserModel.set_password(user.get("id"), new_password))

    except Exception as e:
        logger.error("[AUTH] Lỗi đổi mật khẩu email=%s: %s", email, e, exc_info=True)
        return False

    logger.error("[AUTH] UserModel thiếu method change_password/update_password/set_password.")
    return False


def _redirect_for_user(user: dict):
    next_url = _safe_next_url()
    if next_url:
        return redirect(next_url)

    role = _fetch_role(user)

    if role in ("super_admin", "admin", "staff"):
        try:
            return redirect(url_for("admin.dashboard"))
        except Exception:
            return redirect("/admin/")

    try:
        return redirect(url_for("products.index"))
    except Exception:
        try:
            return redirect(url_for("main.index"))
        except Exception:
            return redirect("/")


def _redirect_if_logged_in():
    if not session.get("user_id"):
        return None

    role = session.get("role") or session.get("user_role") or "customer"

    if role in ("super_admin", "admin", "staff"):
        try:
            return redirect(url_for("admin.dashboard"))
        except Exception:
            return redirect("/admin/")

    try:
        return redirect(url_for("products.index"))
    except Exception:
        try:
            return redirect(url_for("main.index"))
        except Exception:
            return redirect("/")


# ═══════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    already = _redirect_if_logged_in()
    if already:
        return already

    error = None

    if request.method == "POST":
        email = _normalize_email(request.form.get("email"))
        password = request.form.get("password") or ""
        remember = bool(request.form.get("remember"))

        logger.info("[LOGIN ATTEMPT] Đang xác thực tài khoản: email='%s'", email)

        if not email or not EMAIL_RE.match(email):
            error = "Vui lòng nhập địa chỉ email hợp lệ."
            flash(error, "danger")
            return render_template("auth/login.html", error=error)

        if not password:
            error = "Vui lòng nhập mật khẩu."
            flash(error, "danger")
            return render_template("auth/login.html", error=error)

        user_record = _get_user_by_email(email)

        if not user_record:
            logger.warning("[LOGIN FAILED] Tài khoản không tồn tại: %s", email)
            error = "Địa chỉ email hoặc mật khẩu không chính xác."
            flash(error, "danger")
            return render_template("auth/login.html", error=error)

        if user_record.get("is_suspended"):
            logger.warning("[LOGIN BLOCKED] Tài khoản bị khóa: %s", email)
            error = "Tài khoản của bạn đã bị tạm khóa. Vui lòng liên hệ quản trị viên."
            flash(error, "danger")
            return render_template("auth/login.html", error=error)

        if not _verify_user_password(user_record, password):
            logger.warning("[LOGIN FAILED] Sai mật khẩu: %s", email)
            error = "Địa chỉ email hoặc mật khẩu không chính xác."
            flash(error, "danger")
            return render_template("auth/login.html", error=error)

        _set_login_session(user_record, remember=remember)

        logger.info(
            "[SESSION SET SUCCESS] Đăng nhập thành công: email=%s | user_role=%s | admin_role_slug=%s | user_name=%s",
            email,
            session.get("user_role"),
            session.get("admin_role_slug"),
            session.get("user_name"),
        )

        flash("Đăng nhập thành công.", "success")
        return _redirect_for_user(user_record)

    return render_template("auth/login.html", error=error)


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """
    Đăng xuất an toàn.

    Cho phép GET để tránh template cũ bị lỗi.
    Navbar nên dùng POST.
    """
    email = session.get("email", "unknown")

    _clear_auth_session_preserve_csrf()

    logger.info("[LOGOUT SUCCESS] Người dùng đã đăng xuất an toàn: %s", email)

    flash("Bạn đã đăng xuất tài khoản làm việc an toàn.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    already = _redirect_if_logged_in()
    if already:
        return already

    errors = {}

    if request.method == "POST":
        full_name = _clean_name(request.form.get("full_name") or request.form.get("name"))
        email = _normalize_email(request.form.get("email"))
        phone = (request.form.get("phone") or "").strip() or None
        password = request.form.get("password") or ""
        confirm_password = (
            request.form.get("confirm_password")
            or request.form.get("password_confirm")
            or ""
        )

        if not full_name:
            errors["full_name"] = "Vui lòng nhập họ và tên."

        if not email or not EMAIL_RE.match(email):
            errors["email"] = "Vui lòng nhập địa chỉ email hợp lệ."

        if not password or len(password) < 6:
            errors["password"] = "Mật khẩu cần có ít nhất 6 ký tự."

        if confirm_password and password != confirm_password:
            errors["confirm_password"] = "Mật khẩu xác nhận nhập lại không trùng khớp."

        if not errors:
            existing = _get_user_by_email(email)
            if existing:
                logger.info("[REGISTER VALIDATION FAILED] Email đã tồn tại: %s", email)
                errors["email"] = "Địa chỉ email này đã được sử dụng trên hệ thống."

        if not errors:
            user = _create_user(
                email=email,
                password=password,
                full_name=full_name,
                phone=phone,
            )

            if user:
                # Quan trọng:
                # Một số UserModel.create() chỉ trả về id/email hoặc object thiếu full_name.
                # Ép lại dữ liệu form vào user trước khi set session để không hiện None.
                user["full_name"] = full_name
                user["name"] = full_name
                user["email"] = email

                if phone:
                    user["phone"] = phone

                logger.info(
                    "[REGISTER SUCCESS] Tạo tài khoản mới thành công: id=%s | email=%s | full_name=%s",
                    user.get("id"),
                    email,
                    full_name,
                )

                _set_login_session(user, remember=False)

                flash(
                    f"Đăng ký tài khoản thành công! Chào mừng {session.get('user_name', 'Khách hàng')} đến với GUAMAISON.",
                    "success",
                )
                return _redirect_for_user(user)

            flash("Hệ thống đăng ký gặp sự cố kỹ thuật. Vui lòng thử lại sau.", "danger")

    return render_template("auth/register.html", errors=errors)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    already = _redirect_if_logged_in()
    if already:
        return already

    if request.method == "POST":
        email = _normalize_email(request.form.get("email"))

        if not email or not EMAIL_RE.match(email):
            flash("Vui lòng nhập địa chỉ email hợp lệ.", "danger")
            return render_template("auth/forgot_password.html")

        user = _get_user_by_email(email)

        if user:
            try:
                serializer = _get_serializer()
                token = serializer.dumps(email, salt="password-reset-salt")
                reset_url = url_for("auth.reset_password", token=token, _external=True)

                if send_password_reset_email:
                    send_password_reset_email(email, reset_url)
                    logger.info("[FORGOT PASSWORD SUCCESS] Đã gửi mail reset tới: %s", email)
                else:
                    logger.warning(
                        "[FORGOT PASSWORD WARNING] Chưa có send_password_reset_email. Reset URL: %s",
                        reset_url,
                    )

            except Exception as e:
                logger.error(
                    "[FORGOT PASSWORD CRASH] Lỗi gửi reset email tới %s: %s",
                    email,
                    e,
                    exc_info=True,
                )

        flash(
            "Nếu tài khoản email tồn tại, hệ thống đã gửi đường liên kết đặt lại mật khẩu. Vui lòng kiểm tra hộp thư.",
            "info",
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    already = _redirect_if_logged_in()
    if already:
        return already

    serializer = _get_serializer()

    try:
        email = serializer.loads(
            token,
            salt="password-reset-salt",
            max_age=3600,
        )
    except SignatureExpired:
        flash("Liên kết đặt lại mật khẩu đã hết hạn. Vui lòng yêu cầu lại.", "danger")
        return redirect(url_for("auth.forgot_password"))
    except BadSignature:
        flash("Liên kết đặt lại mật khẩu không hợp lệ.", "danger")
        return redirect(url_for("auth.forgot_password"))

    email = _normalize_email(email)

    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm_password = (
            request.form.get("confirm_password")
            or request.form.get("password_confirm")
            or ""
        )

        if len(password) < 6:
            flash("Mật khẩu mới cần có ít nhất 6 ký tự.", "danger")
            return render_template("auth/reset_password.html", token=token, email=email)

        if confirm_password and password != confirm_password:
            flash("Mật khẩu xác nhận không khớp.", "danger")
            return render_template("auth/reset_password.html", token=token, email=email)

        if _change_password(email, password):
            logger.info("[RESET PASSWORD SUCCESS] Đổi mật khẩu thành công cho email=%s", email)
            flash("Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại.", "success")
            return redirect(url_for("auth.login"))

        flash("Không thể đặt lại mật khẩu. Vui lòng thử lại hoặc liên hệ quản trị viên.", "danger")

    return render_template("auth/reset_password.html", token=token, email=email)