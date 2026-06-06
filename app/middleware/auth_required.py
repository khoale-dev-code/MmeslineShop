"""
app/middleware/auth_required.py
================================
Middleware xác thực & phân quyền dựa trên schema hiện tại:

  - users.role             : 'admin' | 'staff' | 'customer'
  - users.admin_role_slug  : FK -> admin_roles.slug, chỉ áp dụng cho staff
  - admin_roles.permissions: JSONB, danh sách permission codes

QUAN TRỌNG:
  - Không dùng anon client để đọc bảng users/admin_roles trong middleware admin.
  - Middleware chạy server-side, nên dùng get_supabase_admin() với service_role.
  - Không mở SELECT public.users cho anon/authenticated vì bảng users có dữ liệu nhạy cảm.
"""

import logging
from functools import wraps
from typing import Callable, Any

from flask import session, redirect, url_for, flash, request, abort, g

from app.utils.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
#  INTERNAL HELPERS
# ──────────────────────────────────────────────────────────────────

def _get_user_record(user_id: str) -> dict | None:
    """
    Lấy thông tin user từ DB bằng service_role.

    Lý do dùng service_role:
      - Bảng public.users không nên grant SELECT cho anon/authenticated.
      - Middleware admin là server-side code.
      - service_role bypass RLS, phù hợp để kiểm tra role nội bộ.

    Có cache per-request trong flask.g để tránh query lặp.
    """
    if not user_id:
        return None

    cache = getattr(g, "_auth_user_cache", {})
    if user_id in cache:
        return cache[user_id]

    try:
        db = get_supabase_admin()

        res = (
            db.table("users")
            .select("id, email, role, is_suspended, admin_role_slug")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        user = res.data[0] if res.data else None

        if not hasattr(g, "_auth_user_cache"):
            g._auth_user_cache = {}

        g._auth_user_cache[user_id] = user
        return user

    except Exception as e:
        logger.error(f"[auth_required] Lỗi lấy user_id={user_id}: {e}")
        return None


def _get_admin_role_permissions(slug: str) -> list[str]:
    """
    Lấy danh sách quyền của một admin_role từ bảng admin_roles.

    permissions có thể là:
      - list: ["orders.view", "orders.manage"]
      - dict: {"orders.view": true, "orders.manage": false}

    Dùng service_role vì admin_roles là bảng nội bộ, không nên expose ra client.
    """
    if not slug:
        return []

    cache = getattr(g, "_admin_role_perms", {})
    if slug in cache:
        return cache[slug]

    try:
        db = get_supabase_admin()

        res = (
            db.table("admin_roles")
            .select("permissions")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )

        if not res.data:
            perms: list[str] = []
        else:
            raw = res.data[0].get("permissions") or []

            if isinstance(raw, list):
                perms = [str(p) for p in raw]
            elif isinstance(raw, dict):
                perms = [str(k) for k, v in raw.items() if v]
            else:
                perms = []

    except Exception as e:
        logger.error(f"[auth_required] Lỗi lấy quyền admin_role slug={slug}: {e}")
        perms = []

    if not hasattr(g, "_admin_role_perms"):
        g._admin_role_perms = {}

    g._admin_role_perms[slug] = perms
    return perms


def _is_super_admin(user: dict | None) -> bool:
    """Super admin: users.role == 'admin'."""
    return bool(user and user.get("role") == "admin")


def _is_staff(user: dict | None) -> bool:
    """Staff: users.role == 'staff'."""
    return bool(user and user.get("role") == "staff")


def _can_access_admin(user: dict | None) -> bool:
    """Có thể vào khu vực /admin không?"""
    return _is_super_admin(user) or _is_staff(user)


def _has_permission(user: dict | None, permission_code: str) -> bool:
    """
    Kiểm tra quyền cụ thể:
      - admin: toàn quyền
      - staff: kiểm tra permission_code trong admin_roles.permissions
      - customer/khác: không có quyền
    """
    if not user:
        return False

    if _is_super_admin(user):
        return True

    if _is_staff(user):
        slug = user.get("admin_role_slug")
        if not slug:
            return False

        perms = _get_admin_role_permissions(slug)
        return permission_code in perms

    return False


def _sync_session_user_role(user: dict) -> None:
    """
    Đồng bộ session với role mới nhất trong DB.

    Code cũ có nơi dùng session["role"], có nơi dùng session["user_role"].
    Để tránh lỗi lệch session, cập nhật cả hai.
    """
    db_role = user.get("role")
    admin_role_slug = user.get("admin_role_slug")

    if db_role and session.get("user_role") != db_role:
        session["user_role"] = db_role

    if db_role and session.get("role") != db_role:
        session["role"] = db_role

    if session.get("admin_role_slug") != admin_role_slug:
        session["admin_role_slug"] = admin_role_slug

    session.modified = True


def _redirect_to_login(message: str = "Vui lòng đăng nhập để tiếp tục."):
    flash(message, "warning")
    return redirect(url_for("auth.login", next=request.url))


def _redirect_home(message: str, category: str = "danger"):
    flash(message, category)
    try:
        return redirect(url_for("products.index"))
    except Exception:
        return redirect("/")


# ──────────────────────────────────────────────────────────────────
#  PUBLIC DECORATORS
# ──────────────────────────────────────────────────────────────────

def login_required(f: Callable) -> Callable:
    """
    Yêu cầu đăng nhập.
    Redirect về trang login nếu chưa đăng nhập.
    """

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        if "user_id" not in session:
            return _redirect_to_login("Vui lòng đăng nhập để tiếp tục.")

        return f(*args, **kwargs)

    return decorated


def admin_required(f: Callable) -> Callable:
    """
    Yêu cầu tài khoản có role 'admin' hoặc 'staff'.

    Luồng:
      1. Chưa đăng nhập -> redirect login
      2. Không tìm thấy user trong DB -> clear session, redirect login
      3. User bị khóa -> clear session, redirect home
      4. Không phải admin/staff -> 403 hoặc redirect home
      5. Đồng bộ session role
      6. Gán g.current_admin
    """

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        user_id = session.get("user_id")

        # 1. Chưa đăng nhập
        if not user_id:
            return _redirect_to_login("Vui lòng đăng nhập tài khoản quản trị.")

        # 2. Lấy user bằng service_role
        user = _get_user_record(user_id)
        if not user:
            logger.warning(f"[admin_required] Không tìm thấy user_id={user_id}. Clear session.")
            session.clear()
            flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "danger")
            return redirect(url_for("auth.login"))

        # 3. Tài khoản bị khóa
        if user.get("is_suspended"):
            logger.warning(f"[admin_required] User bị khóa user_id={user_id}. Clear session.")
            session.clear()
            return _redirect_home("Tài khoản của bạn đã bị tạm khóa.", "danger")

        # 4. Không đủ quyền vào admin
        if not _can_access_admin(user):
            logger.warning(
                f"[admin_required] User không có quyền admin: "
                f"user_id={user_id}, role={user.get('role')}"
            )

            if request.is_json:
                abort(403)

            return _redirect_home("Bạn không có quyền truy cập khu vực quản trị.", "danger")

        # 5. Đồng bộ session
        _sync_session_user_role(user)

        # 6. Cho view dùng lại
        g.current_admin = user
        g.current_user = user

        return f(*args, **kwargs)

    return decorated


def permission_required(permission_code: str):
    """
    Kiểm tra quyền cụ thể.

    Dùng cho staff role:
      @admin_required
      @permission_required("orders.manage")

    Super admin role='admin' luôn pass.
    """

    def decorator(f: Callable) -> Callable:

        @wraps(f)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            user_id = session.get("user_id")

            if not user_id:
                if request.is_json:
                    abort(401)
                return _redirect_to_login("Vui lòng đăng nhập.")

            user = _get_user_record(user_id)
            if not user:
                session.clear()
                if request.is_json:
                    abort(401)
                flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "danger")
                return redirect(url_for("auth.login"))

            if user.get("is_suspended"):
                session.clear()
                if request.is_json:
                    abort(403)
                return _redirect_home("Tài khoản của bạn đã bị tạm khóa.", "danger")

            if _has_permission(user, permission_code):
                _sync_session_user_role(user)
                g.current_admin = user
                g.current_user = user
                return f(*args, **kwargs)

            logger.warning(
                f"[permission_required] user_id={user_id} "
                f"role={user.get('role')} "
                f"slug={user.get('admin_role_slug')} "
                f"thiếu quyền '{permission_code}'"
            )

            if request.is_json or request.method != "GET":
                abort(403)

            flash(f"Bạn không có quyền thực hiện thao tác này ({permission_code}).", "danger")

            try:
                return redirect(url_for("admin.dashboard"))
            except Exception:
                return redirect("/admin/")

        return decorated

    return decorator


def super_admin_required(f: Callable) -> Callable:
    """
    Chỉ cho phép Super Admin: users.role == 'admin'.

    Dùng cho:
      - quản lý phân quyền
      - settings hệ thống
      - audit logs
      - tác vụ nhạy cảm
    """

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        user_id = session.get("user_id")

        if not user_id:
            return _redirect_to_login("Vui lòng đăng nhập.")

        user = _get_user_record(user_id)
        if not user:
            session.clear()
            flash("Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", "danger")
            return redirect(url_for("auth.login"))

        if user.get("is_suspended"):
            session.clear()
            return _redirect_home("Tài khoản của bạn đã bị tạm khóa.", "danger")

        if not _is_super_admin(user):
            logger.warning(
                f"[super_admin_required] User không phải super admin: "
                f"user_id={user_id}, role={user.get('role')}"
            )

            if request.is_json:
                abort(403)

            flash("Chức năng này chỉ dành cho Super Admin.", "danger")

            try:
                return redirect(url_for("admin.dashboard"))
            except Exception:
                return redirect("/admin/")

        _sync_session_user_role(user)
        g.current_admin = user
        g.current_user = user

        return f(*args, **kwargs)

    return decorated