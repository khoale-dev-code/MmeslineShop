"""
app/controllers/admin/permissions_controller.py
================================================
Quản lý vai trò (Roles) và phân quyền (Permissions) cho khu vực Admin.

Schema đang dùng:
- users.role            : 'admin' | 'staff' | 'customer'
- users.admin_role_slug : FK -> admin_roles.slug
- admin_roles.slug      : PK text
- admin_roles.name      : text
- admin_roles.permissions : jsonb, lưu dạng list[str]

Lưu ý quan trọng:
- Đây là controller cho trang Super Admin.
- Các bảng users/admin_roles/audit_logs là dữ liệu nhạy cảm.
- Vì vậy controller dùng get_supabase_admin() thay vì get_supabase()
  để tránh lỗi Supabase/PostgREST: permission denied for table users/admin_roles.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from flask import jsonify, render_template, request

from app.middleware.auth_required import super_admin_required
from app.services.audit_service import AuditService
from app.utils.supabase_client import get_supabase_admin

from ._blueprint import admin_bp

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  DANH SÁCH QUYỀN CHUẨN ĐỂ RENDER UI
# ═══════════════════════════════════════════════════════════════

AVAILABLE_PERMISSIONS: dict[str, list[dict[str, str]]] = {
    "Đơn hàng & Vận chuyển": [
        {"code": "orders.view", "name": "Xem đơn hàng", "icon": "fa-eye"},
        {"code": "orders.manage", "name": "Quản lý đơn hàng", "icon": "fa-pen"},
        {"code": "orders.export", "name": "Xuất file đơn hàng", "icon": "fa-file-export"},
        {"code": "shipping.view", "name": "Xem vận chuyển", "icon": "fa-eye"},
        {"code": "shipping.manage", "name": "Quản lý vận chuyển", "icon": "fa-truck"},
        {"code": "returns.view", "name": "Xem đổi trả", "icon": "fa-eye"},
        {"code": "returns.manage", "name": "Quản lý đổi trả", "icon": "fa-rotate-left"},
    ],
    "Sản phẩm & Khách hàng": [
        {"code": "products.view", "name": "Xem sản phẩm", "icon": "fa-eye"},
        {"code": "products.create", "name": "Tạo sản phẩm", "icon": "fa-plus"},
        {"code": "products.edit", "name": "Sửa sản phẩm", "icon": "fa-pen"},
        {"code": "products.delete", "name": "Xóa sản phẩm", "icon": "fa-trash"},
        {"code": "customers.view", "name": "Xem khách hàng", "icon": "fa-eye"},
        {"code": "customers.manage", "name": "Quản lý khách hàng", "icon": "fa-users-cog"},
    ],
    "Khuyến mãi, POS & Hệ thống": [
        {"code": "coupons.view", "name": "Xem khuyến mãi", "icon": "fa-eye"},
        {"code": "coupons.manage", "name": "Quản lý khuyến mãi", "icon": "fa-tags"},
        {"code": "reports.view", "name": "Xem báo cáo", "icon": "fa-chart-line"},
        {"code": "notifications.manage", "name": "Quản lý thông báo", "icon": "fa-bell"},
        {"code": "menus.manage", "name": "Quản lý menu giao diện", "icon": "fa-bars-staggered"},
        {"code": "pos.access", "name": "Truy cập POS (Bán tại quầy)", "icon": "fa-cash-register"},
        {"code": "settings.view", "name": "Xem cài đặt hệ thống", "icon": "fa-cogs"},
        {"code": "settings.manage", "name": "Thay đổi cài đặt hệ thống", "icon": "fa-wrench"},
    ],
}

# Slug hệ thống không cho sửa/xóa/gán qua UI nhân viên.
# Super Admin thật sự được xác định bằng users.role == 'admin'.
PROTECTED_ROLES = ["admin", "super_admin"]


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════


def _db():
    """Supabase service-role client cho các bảng nhạy cảm của Admin."""
    return get_supabase_admin()


def _payload() -> dict[str, Any]:
    """Đọc JSON body an toàn, không để None làm crash controller."""
    return request.get_json(silent=True) or {}


def _json_error(message: str, status: int = 200):
    return jsonify({"success": False, "message": message}), status


def _json_ok(message: str, **extra: Any):
    data = {"success": True, "message": message}
    data.update(extra)
    return jsonify(data)


def _normalize_slug(value: Any) -> str:
    """
    Chuẩn hóa slug role:
    - chữ thường
    - khoảng trắng/dấu gạch ngang -> _
    - chỉ giữ a-z, 0-9, _
    """
    slug = str(value or "").strip().lower()
    slug = re.sub(r"[\s\-]+", "_", slug)
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug


def _all_permission_codes() -> set[str]:
    codes: set[str] = set()
    for group in AVAILABLE_PERMISSIONS.values():
        for item in group:
            code = item.get("code")
            if code:
                codes.add(code)
    return codes


def _normalize_permissions(value: Any) -> list[str]:
    """
    Chuẩn hóa permissions trước khi lưu JSONB.
    Chỉ cho phép các permission code có trong AVAILABLE_PERMISSIONS.
    """
    if not isinstance(value, list):
        return []

    allowed = _all_permission_codes()
    output: list[str] = []

    for item in value:
        code = str(item or "").strip()
        if code in allowed and code not in output:
            output.append(code)

    return output


def _safe_audit(
    action: str,
    table_name: str,
    record_id: str | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> None:
    """
    Ghi audit log nhưng không để audit làm hỏng thao tác chính.
    AuditService hiện tại có thể vẫn dùng anon client; nếu chưa sửa service đó,
    lỗi sẽ được catch ở đây và ở AuditService.
    """
    try:
        AuditService.log_action(
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values,
        )
    except Exception as exc:  # pragma: no cover - fail-safe
        logger.warning("[Permissions] Không ghi được audit log: %s", exc)


def _get_role(slug: str) -> dict | None:
    try:
        res = (
            _db()
            .table("admin_roles")
            .select("slug, name, permissions, created_at")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as exc:
        logger.error("[Permissions] _get_role slug=%s lỗi: %s", slug, exc)
        return None


def _role_exists(slug: str) -> bool:
    return _get_role(slug) is not None


def _get_user(user_id: str) -> dict | None:
    try:
        res = (
            _db()
            .table("users")
            .select("id, email, full_name, role, admin_role_slug, is_suspended")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as exc:
        logger.error("[Permissions] _get_user user_id=%s lỗi: %s", user_id, exc)
        return None


def _get_user_by_email(email: str) -> dict | None:
    try:
        res = (
            _db()
            .table("users")
            .select("id, email, full_name, role, admin_role_slug, is_suspended")
            .eq("email", email.strip().lower())
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as exc:
        logger.error("[Permissions] _get_user_by_email email=%s lỗi: %s", email, exc)
        return None


def _fetch_roles() -> list[dict]:
    """Lấy toàn bộ admin_roles bằng service role."""
    res = (
        _db()
        .table("admin_roles")
        .select("slug, name, permissions, created_at")
        .order("name")
        .execute()
    )

    roles = res.data or []
    for role in roles:
        permissions = role.get("permissions")
        if not isinstance(permissions, list):
            role["permissions"] = []
    return roles


def _fetch_admin_users(role_name_by_slug: dict[str, str]) -> list[dict]:
    """Lấy danh sách Super Admin + Staff để render bảng nhân sự."""
    res = (
        _db()
        .table("users")
        .select("id, email, full_name, role, admin_role_slug, is_suspended, created_at")
        .in_("role", ["staff", "admin"])
        .order("role")
        .order("full_name")
        .execute()
    )

    staff = res.data or []

    for user in staff:
        full_name = (user.get("full_name") or "").strip()
        raw_role = user.get("role") or "customer"
        role_slug = user.get("admin_role_slug") or ""

        user["initials"] = full_name[:1].upper() if full_name else "?"
        user["avatar_bg"] = "bg-stone-200"
        user["avatar_fg"] = "text-stone-700"
        user["role_raw"] = raw_role
        user["role_slug"] = role_slug
        user["role_name"] = role_name_by_slug.get(role_slug, role_slug)

        # Giữ tương thích với template hiện tại: template đang so sánh u.role == 'Super Admin'.
        if raw_role == "admin":
            user["role"] = "Super Admin"
            user["role_display"] = "Super Admin"
        elif raw_role == "staff":
            user["role"] = role_slug or "staff"
            user["role_display"] = role_name_by_slug.get(role_slug, role_slug or "Staff")
        else:
            user["role"] = raw_role
            user["role_display"] = raw_role

    return staff


# ═══════════════════════════════════════════════════════════════
#  PAGE: QUẢN LÝ PHÂN QUYỀN
# ═══════════════════════════════════════════════════════════════


@admin_bp.route("/permissions")
@super_admin_required
def permissions_index():
    try:
        roles = _fetch_roles()
        role_name_by_slug = {r.get("slug"): r.get("name", r.get("slug", "")) for r in roles}
        staff = _fetch_admin_users(role_name_by_slug)

        stats = {
            "total_roles": len(roles),
            "protected_count": len([r for r in roles if r.get("slug") in PROTECTED_ROLES]),
            "total_staff": len(staff),
            "total_permissions": sum(len(perms) for perms in AVAILABLE_PERMISSIONS.values()),
        }

        return render_template(
            "admin/roles/index.html",
            roles=roles,
            available_permissions=AVAILABLE_PERMISSIONS,
            protected_roles=PROTECTED_ROLES,
            staff=staff,
            stats=stats,
        )

    except Exception as exc:
        logger.error("[Permissions] permissions_index lỗi: %s", exc, exc_info=True)
        return render_template(
            "admin/roles/index.html",
            roles=[],
            available_permissions=AVAILABLE_PERMISSIONS,
            protected_roles=PROTECTED_ROLES,
            staff=[],
            stats={
                "total_roles": 0,
                "protected_count": 0,
                "total_staff": 0,
                "total_permissions": sum(len(perms) for perms in AVAILABLE_PERMISSIONS.values()),
            },
        ), 500


# ═══════════════════════════════════════════════════════════════
#  ROLE CRUD
# ═══════════════════════════════════════════════════════════════


@admin_bp.route("/roles/create", methods=["POST"])
@super_admin_required
def create_role():
    data = _payload()
    slug = _normalize_slug(data.get("slug"))
    name = str(data.get("name") or "").strip()
    permissions = _normalize_permissions(data.get("permissions", []))

    if not slug or not name:
        return _json_error("Vui lòng nhập đầy đủ slug và tên vai trò.")

    if len(slug) < 2:
        return _json_error("Slug vai trò quá ngắn.")

    if slug in PROTECTED_ROLES:
        return _json_error("Không thể tạo/sử dụng slug thuộc nhóm quyền hệ thống.")

    if _role_exists(slug):
        return _json_error("Slug vai trò đã tồn tại. Vui lòng chọn slug khác.")

    try:
        insert_data = {
            "slug": slug,
            "name": name,
            "permissions": permissions,
        }
        res = _db().table("admin_roles").insert(insert_data).execute()
        created = res.data[0] if res.data else insert_data

        _safe_audit("CREATE_ROLE", "admin_roles", slug, new_values=created)
        return _json_ok("Tạo nhóm quyền thành công.", role=created)

    except Exception as exc:
        logger.error("[Permissions] create_role slug=%s lỗi: %s", slug, exc, exc_info=True)
        return _json_error("Lỗi tạo nhóm quyền. Vui lòng kiểm tra Supabase service role key hoặc slug đã tồn tại.", 500)


@admin_bp.route("/roles/<slug>/update", methods=["POST"])
@super_admin_required
def update_role(slug: str):
    slug = _normalize_slug(slug)

    if slug in PROTECTED_ROLES:
        return _json_error("Không thể sửa nhóm quyền mặc định/hệ thống.")

    data = _payload()
    name = str(data.get("name") or "").strip()
    permissions = _normalize_permissions(data.get("permissions", []))

    if not slug:
        return _json_error("Thiếu slug vai trò.")

    if not name:
        return _json_error("Vui lòng nhập tên vai trò.")

    old_role = _get_role(slug)
    if not old_role:
        return _json_error("Không tìm thấy nhóm quyền cần cập nhật.", 404)

    try:
        update_data = {
            "name": name,
            "permissions": permissions,
        }
        res = _db().table("admin_roles").update(update_data).eq("slug", slug).execute()
        updated = res.data[0] if res.data else {**old_role, **update_data}

        _safe_audit(
            "UPDATE_ROLE",
            "admin_roles",
            slug,
            old_values=old_role,
            new_values=updated,
        )
        return _json_ok("Cập nhật nhóm quyền thành công.", role=updated)

    except Exception as exc:
        logger.error("[Permissions] update_role slug=%s lỗi: %s", slug, exc, exc_info=True)
        return _json_error("Lỗi cập nhật nhóm quyền.", 500)


@admin_bp.route("/roles/<slug>/delete", methods=["POST"])
@super_admin_required
def delete_role(slug: str):
    slug = _normalize_slug(slug)

    if not slug:
        return _json_error("Thiếu slug vai trò.")

    if slug in PROTECTED_ROLES:
        return _json_error("Không thể xóa nhóm quyền mặc định/hệ thống.")

    old_role = _get_role(slug)
    if not old_role:
        return _json_error("Không tìm thấy nhóm quyền cần xóa.", 404)

    try:
        db = _db()

        # Vì users.admin_role_slug là FK tới admin_roles.slug,
        # phải gỡ role khỏi users trước khi xóa role.
        db.table("users").update({
            "role": "customer",
            "admin_role_slug": None,
        }).eq("admin_role_slug", slug).execute()

        db.table("admin_roles").delete().eq("slug", slug).execute()

        _safe_audit("DELETE_ROLE", "admin_roles", slug, old_values=old_role)
        return _json_ok("Đã xóa nhóm quyền. Nhân viên đang dùng nhóm này đã được hạ về khách hàng.")

    except Exception as exc:
        logger.error("[Permissions] delete_role slug=%s lỗi: %s", slug, exc, exc_info=True)
        return _json_error("Lỗi xóa nhóm quyền.", 500)


# ═══════════════════════════════════════════════════════════════
#  ASSIGN / REVOKE ROLE CHO USER
# ═══════════════════════════════════════════════════════════════


@admin_bp.route("/roles/assign", methods=["POST"])
@super_admin_required
def assign_role():
    data = _payload()
    user_id = str(data.get("user_id") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    role_slug = _normalize_slug(data.get("role_slug"))

    if not role_slug:
        return _json_error("Vui lòng chọn vai trò.")

    if role_slug in PROTECTED_ROLES:
        return _json_error("Không thể gán nhóm quyền hệ thống qua màn hình nhân viên.")

    role = _get_role(role_slug)
    if not role:
        return _json_error("Nhóm quyền không tồn tại hoặc đã bị xóa.", 404)

    # Trường hợp thêm nhân viên mới bằng email: chưa có user_id từ bảng staff.
    user = None
    if user_id:
        user = _get_user(user_id)
    elif email:
        user = _get_user_by_email(email)
        user_id = str(user.get("id")) if user else ""

    if not user:
        return _json_error(f"Không tìm thấy tài khoản người dùng{f' có Email: {email}' if email else ''}.", 404)

    if user.get("is_suspended"):
        return _json_error("Không thể gán quyền cho tài khoản đang bị tạm khóa.")

    if user.get("role") == "admin":
        return _json_error("Không thể thay đổi quyền của Super Admin tại màn hình gán nhân viên.")

    old_values = {
        "role": user.get("role"),
        "admin_role_slug": user.get("admin_role_slug"),
    }
    new_values = {
        "role": "staff",
        "admin_role_slug": role_slug,
    }

    try:
        res = (
            _db()
            .table("users")
            .update(new_values)
            .eq("id", user_id)
            .execute()
        )

        if res.data is not None and len(res.data) == 0:
            return _json_error("Không cập nhật được người dùng. Vui lòng thử lại.", 500)

        _safe_audit(
            "ASSIGN_ROLE",
            "users",
            user_id,
            old_values=old_values,
            new_values=new_values,
        )
        return _json_ok("Cấp phát quyền thành công!", user_id=user_id, role_slug=role_slug)

    except Exception as exc:
        logger.error("[Permissions] assign_role user_id=%s role_slug=%s lỗi: %s", user_id, role_slug, exc, exc_info=True)
        return _json_error("Lỗi hệ thống khi gán quyền.", 500)


@admin_bp.route("/roles/revoke", methods=["POST"])
@super_admin_required
def revoke_role():
    data = _payload()
    user_id = str(data.get("user_id") or "").strip()

    if not user_id:
        return _json_error("Thiếu user_id để thu hồi.")

    user = _get_user(user_id)
    if not user:
        return _json_error("Không tìm thấy người dùng cần thu hồi quyền.", 404)

    if user.get("role") == "admin":
        return _json_error("Không thể thu hồi quyền Super Admin tại màn hình nhân viên.")

    old_values = {
        "role": user.get("role"),
        "admin_role_slug": user.get("admin_role_slug"),
    }
    new_values = {
        "role": "customer",
        "admin_role_slug": None,
    }

    try:
        res = (
            _db()
            .table("users")
            .update(new_values)
            .eq("id", user_id)
            .execute()
        )

        if res.data is not None and len(res.data) == 0:
            return _json_error("Không cập nhật được người dùng. Vui lòng thử lại.", 500)

        _safe_audit(
            "REVOKE_ROLE",
            "users",
            user_id,
            old_values=old_values,
            new_values=new_values,
        )
        return _json_ok("Đã thu hồi quyền truy cập.", user_id=user_id)

    except Exception as exc:
        logger.error("[Permissions] revoke_role user_id=%s lỗi: %s", user_id, exc, exc_info=True)
        return _json_error("Lỗi khi thu hồi quyền.", 500)
