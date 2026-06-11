"""
app/services/rbac_service.py
=============================
RBAC Service — phân quyền Admin/Staff theo schema Supabase hiện tại.

Schema đang dùng:
  - public.users.role             : 'admin' | 'staff' | 'customer'
  - public.users.admin_role_slug  : FK -> public.admin_roles.slug
  - public.admin_roles.slug       : PK text
  - public.admin_roles.name       : tên hiển thị
  - public.admin_roles.permissions: jsonb, thường là list[str]

Lưu ý bảo mật:
  - Đây là service chạy server-side.
  - Không dùng anon client để đọc/ghi users/admin_roles vì đây là bảng nội bộ.
  - Dùng get_supabase_admin() để bypass RLS bằng SUPABASE_SERVICE_ROLE_KEY.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from app.utils.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
#  CONSTANTS
# ──────────────────────────────────────────────────────────────────

USER_ROLE_ADMIN = "admin"
USER_ROLE_STAFF = "staff"
USER_ROLE_CUSTOMER = "customer"

# Các slug không nên bị sửa/xóa từ UI, nếu bạn có tạo role này trong admin_roles.
PROTECTED_ROLE_SLUGS = {"admin", "super_admin", "super-admin", "owner"}

# Cache quyền trong RAM. Khi chạy nhiều worker/process, cache này chỉ có hiệu lực trong từng process.
# Nếu production lớn hơn, nên thay bằng Redis.
_CACHE_TTL_SECONDS = 120
_perm_cache: dict[str, dict[str, Any]] = {}


# ──────────────────────────────────────────────────────────────────
#  PERMISSION CATALOG — dùng cho UI render chọn quyền
# ──────────────────────────────────────────────────────────────────

AVAILABLE_PERMISSIONS = {
    "Đơn hàng": [
        {"code": "orders.view", "label": "Xem đơn hàng"},
        {"code": "orders.manage", "label": "Xử lý đơn hàng (duyệt, huỷ)"},
        {"code": "orders.export", "label": "Xuất dữ liệu đơn hàng"},
    ],
    "Sản phẩm": [
        {"code": "products.view", "label": "Xem sản phẩm"},
        {"code": "products.create", "label": "Thêm sản phẩm mới"},
        {"code": "products.edit", "label": "Chỉnh sửa sản phẩm"},
        {"code": "products.delete", "label": "Xoá sản phẩm"},
    ],
    "Khách hàng": [
        {"code": "customers.view", "label": "Xem khách hàng"},
        {"code": "customers.manage", "label": "Quản lý khách hàng (khoá, sửa)"},
    ],
    "Mã giảm giá": [
        {"code": "coupons.view", "label": "Xem mã giảm giá"},
        {"code": "coupons.manage", "label": "Tạo & quản lý mã giảm giá"},
    ],
    "Vận chuyển & Hoàn trả": [
        {"code": "shipping.view", "label": "Xem vận chuyển"},
        {"code": "shipping.manage", "label": "Quản lý vận chuyển"},
        {"code": "returns.view", "label": "Xem yêu cầu hoàn trả"},
        {"code": "returns.manage", "label": "Xử lý hoàn trả"},
    ],
    "Báo cáo": [
        {"code": "reports.view", "label": "Xem báo cáo & thống kê"},
    ],
    "Thông báo": [
        {"code": "notifications.manage", "label": "Quản lý thông báo"},
    ],
    "POS": [
        {"code": "pos.access", "label": "Truy cập POS bán hàng tại quầy"},
    ],
    "Cài đặt": [
        {"code": "settings.view", "label": "Xem cài đặt hệ thống"},
        {"code": "settings.manage", "label": "Thay đổi cài đặt hệ thống"},
    ],
}


class RBACService:
    """Service quản lý nhóm quyền và kiểm tra quyền admin/staff."""

    # ─────────────────────────────────────────────────────────────
    #  INTERNAL HELPERS
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _db():
        """Service role Supabase client. Chỉ dùng server-side."""
        return get_supabase_admin()

    @staticmethod
    def _clean_text(value: Any, max_length: int = 255) -> str:
        value = str(value or "").strip()
        value = re.sub(r"\s+", " ", value)
        return value[:max_length]

    @staticmethod
    def normalize_slug(value: Any) -> str:
        """
        Chuẩn hóa slug role:
          'Sale Manager' -> 'sale-manager'
          'Kho_Hàng'     -> 'kho_hang'
        Giữ chữ, số, gạch ngang, gạch dưới.
        """
        slug = str(value or "").strip().lower()
        slug = re.sub(r"\s+", "-", slug)
        slug = re.sub(r"[^a-z0-9_-]", "", slug)
        slug = re.sub(r"-+", "-", slug).strip("-_")
        return slug[:80]

    @staticmethod
    def _known_permission_codes() -> set[str]:
        codes: set[str] = set()
        for group in AVAILABLE_PERMISSIONS.values():
            for item in group:
                code = str(item.get("code") or "").strip()
                if code:
                    codes.add(code)
        return codes

    @staticmethod
    def normalize_permissions(raw_permissions: Any, *, keep_unknown: bool = False) -> list[str]:
        """
        Chuẩn hóa admin_roles.permissions từ JSONB về list[str].

        Hỗ trợ:
          - list: ["orders.view", "products.edit"]
          - dict: {"orders.view": true, "products.edit": false}
          - string: "orders.view,products.edit" hoặc "orders.view\nproducts.edit"

        Mặc định chỉ giữ permission code có trong AVAILABLE_PERMISSIONS.
        """
        if raw_permissions is None:
            items: list[Any] = []
        elif isinstance(raw_permissions, list):
            items = raw_permissions
        elif isinstance(raw_permissions, tuple) or isinstance(raw_permissions, set):
            items = list(raw_permissions)
        elif isinstance(raw_permissions, dict):
            items = [key for key, enabled in raw_permissions.items() if enabled]
        elif isinstance(raw_permissions, str):
            items = re.split(r"[,;\n|]+", raw_permissions)
        else:
            items = []

        known_codes = RBACService._known_permission_codes()
        result: list[str] = []
        seen: set[str] = set()

        for item in items:
            code = str(item or "").strip()
            if not code or code in seen:
                continue

            if keep_unknown or code == "*" or code in known_codes:
                result.append(code)
                seen.add(code)

        return result

    @staticmethod
    def _normalize_role_row(row: dict | None) -> dict | None:
        if not row:
            return None

        normalized = dict(row)
        normalized["slug"] = str(normalized.get("slug") or "").strip()
        normalized["name"] = str(normalized.get("name") or "").strip()
        normalized["permissions"] = RBACService.normalize_permissions(
            normalized.get("permissions"),
            keep_unknown=True,
        )
        normalized["permission_count"] = len(normalized["permissions"])
        normalized["is_protected"] = normalized["slug"] in PROTECTED_ROLE_SLUGS
        return normalized

    @staticmethod
    def _cache_get(cache_key: str) -> list[str] | None:
        item = _perm_cache.get(cache_key)
        if not item:
            return None

        expires_at = item.get("expires_at", 0)
        if expires_at < time.time():
            _perm_cache.pop(cache_key, None)
            return None

        perms = item.get("permissions")
        return perms if isinstance(perms, list) else None

    @staticmethod
    def _cache_set(cache_key: str, permissions: list[str]) -> None:
        _perm_cache[cache_key] = {
            "permissions": list(permissions),
            "expires_at": time.time() + _CACHE_TTL_SECONDS,
        }

    # ─────────────────────────────────────────────────────────────
    #  ADMIN ROLES CRUD
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def get_all_roles() -> list[dict]:
        """Lấy tất cả role trong bảng admin_roles."""
        try:
            res = (
                RBACService._db()
                .table("admin_roles")
                .select("slug, name, permissions, created_at")
                .order("name", desc=False)
                .execute()
            )
            return [RBACService._normalize_role_row(row) for row in (res.data or [])]
        except Exception as e:
            logger.error("[RBAC] get_all_roles lỗi: %s", e, exc_info=True)
            return []

    @staticmethod
    def get_role(slug: str) -> dict | None:
        """Lấy một role theo slug. Không tìm thấy thì trả None."""
        slug = RBACService.normalize_slug(slug)
        if not slug:
            return None

        try:
            res = (
                RBACService._db()
                .table("admin_roles")
                .select("slug, name, permissions, created_at")
                .eq("slug", slug)
                .limit(1)
                .execute()
            )
            return RBACService._normalize_role_row(res.data[0]) if res.data else None
        except Exception as e:
            logger.error("[RBAC] get_role slug=%s lỗi: %s", slug, e, exc_info=True)
            return None

    @staticmethod
    def role_exists(slug: str) -> bool:
        """Kiểm tra role slug có tồn tại không."""
        return RBACService.get_role(slug) is not None

    @staticmethod
    def create_role(slug: str, name: str, permissions: list[str] | dict | str | None) -> dict:
        """Tạo admin role mới."""
        slug = RBACService.normalize_slug(slug)
        name = RBACService._clean_text(name, 120)
        normalized_permissions = RBACService.normalize_permissions(permissions)

        if not slug:
            raise ValueError("Slug nhóm quyền không hợp lệ.")
        if not name:
            raise ValueError("Tên nhóm quyền không được để trống.")

        try:
            res = (
                RBACService._db()
                .table("admin_roles")
                .insert({
                    "slug": slug,
                    "name": name,
                    "permissions": normalized_permissions,
                })
                .execute()
            )
            RBACService._invalidate_cache_for_role(slug)
            return RBACService._normalize_role_row(res.data[0]) if res.data else {}
        except Exception as e:
            logger.error("[RBAC] create_role slug=%s lỗi: %s", slug, e, exc_info=True)
            raise

    @staticmethod
    def update_role(
        slug: str,
        name: str | None = None,
        permissions: list[str] | dict | str | None = None,
    ) -> dict:
        """Cập nhật tên và/hoặc danh sách quyền của role."""
        slug = RBACService.normalize_slug(slug)
        if not slug:
            raise ValueError("Slug nhóm quyền không hợp lệ.")

        update_data: dict[str, Any] = {}

        if name is not None:
            clean_name = RBACService._clean_text(name, 120)
            if not clean_name:
                raise ValueError("Tên nhóm quyền không được để trống.")
            update_data["name"] = clean_name

        if permissions is not None:
            update_data["permissions"] = RBACService.normalize_permissions(permissions)

        if not update_data:
            role = RBACService.get_role(slug)
            return role or {}

        try:
            res = (
                RBACService._db()
                .table("admin_roles")
                .update(update_data)
                .eq("slug", slug)
                .execute()
            )
            RBACService._invalidate_cache_for_role(slug)
            return RBACService._normalize_role_row(res.data[0]) if res.data else {}
        except Exception as e:
            logger.error("[RBAC] update_role slug=%s lỗi: %s", slug, e, exc_info=True)
            raise

    @staticmethod
    def delete_role(slug: str) -> bool:
        """
        Xóa một admin role.

        Do users.admin_role_slug có FK -> admin_roles.slug, cần gỡ role khỏi users trước.
        Các user đang dùng role bị xóa sẽ bị hạ về customer.
        """
        slug = RBACService.normalize_slug(slug)
        if not slug:
            return False

        if slug in PROTECTED_ROLE_SLUGS:
            logger.warning("[RBAC] Từ chối xóa protected role slug=%s", slug)
            return False

        try:
            db = RBACService._db()

            affected_users = (
                db.table("users")
                .select("id")
                .eq("admin_role_slug", slug)
                .execute()
                .data
                or []
            )

            db.table("users").update({
                "role": USER_ROLE_CUSTOMER,
                "admin_role_slug": None,
            }).eq("admin_role_slug", slug).execute()

            db.table("admin_roles").delete().eq("slug", slug).execute()

            RBACService._invalidate_cache_for_role(slug)
            for user in affected_users:
                if user.get("id"):
                    RBACService.invalidate_user_cache(str(user["id"]))

            return True
        except Exception as e:
            logger.error("[RBAC] delete_role slug=%s lỗi: %s", slug, e, exc_info=True)
            return False

    # ─────────────────────────────────────────────────────────────
    #  USER ↔ ROLE ASSIGNMENT
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def get_user(user_id: str) -> dict | None:
        """Lấy thông tin role cơ bản của user."""
        if not user_id:
            return None

        try:
            res = (
                RBACService._db()
                .table("users")
                .select("id, email, full_name, role, admin_role_slug, is_suspended, created_at")
                .eq("id", str(user_id))
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error("[RBAC] get_user user_id=%s lỗi: %s", user_id, e, exc_info=True)
            return None

    @staticmethod
    def get_user_by_email(email: str) -> dict | None:
        """Tìm user theo email."""
        email = str(email or "").strip().lower()
        if not email:
            return None

        try:
            res = (
                RBACService._db()
                .table("users")
                .select("id, email, full_name, role, admin_role_slug, is_suspended, created_at")
                .eq("email", email)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error("[RBAC] get_user_by_email email=%s lỗi: %s", email, e, exc_info=True)
            return None

    @staticmethod
    def assign_role_to_user(user_id: str, admin_role_slug: str | None) -> bool:
        """
        Gán admin role cho user.

        - admin_role_slug=<slug> → users.role='staff', users.admin_role_slug=<slug>
        - admin_role_slug=None   → users.role='customer', users.admin_role_slug=NULL

        Không tự ý hạ tài khoản role='admin' xuống customer để tránh khóa nhầm Super Admin.
        """
        user_id = str(user_id or "").strip()
        if not user_id:
            return False

        admin_role_slug = RBACService.normalize_slug(admin_role_slug) if admin_role_slug else None

        try:
            db = RBACService._db()

            user = RBACService.get_user(user_id)
            if not user:
                logger.warning("[RBAC] assign_role: Không tìm thấy user_id=%s", user_id)
                return False

            if user.get("role") == USER_ROLE_ADMIN and admin_role_slug is None:
                logger.warning("[RBAC] Từ chối thu hồi quyền Super Admin user_id=%s", user_id)
                return False

            if admin_role_slug:
                role = RBACService.get_role(admin_role_slug)
                if not role:
                    logger.warning("[RBAC] Role slug '%s' không tồn tại.", admin_role_slug)
                    return False

                update_data = {
                    "role": USER_ROLE_STAFF,
                    "admin_role_slug": admin_role_slug,
                }
            else:
                update_data = {
                    "role": USER_ROLE_CUSTOMER,
                    "admin_role_slug": None,
                }

            db.table("users").update(update_data).eq("id", user_id).execute()
            RBACService.invalidate_user_cache(user_id)
            return True

        except Exception as e:
            logger.error("[RBAC] assign_role user_id=%s lỗi: %s", user_id, e, exc_info=True)
            return False

    @staticmethod
    def assign_role_by_email(email: str, admin_role_slug: str) -> bool:
        """Gán role cho user bằng email."""
        user = RBACService.get_user_by_email(email)
        if not user:
            return False
        return RBACService.assign_role_to_user(user["id"], admin_role_slug)

    @staticmethod
    def revoke_staff_access(user_id: str) -> bool:
        """Thu hồi quyền staff của user, hạ về customer."""
        return RBACService.assign_role_to_user(user_id, None)

    # ─────────────────────────────────────────────────────────────
    #  PERMISSION CHECKS
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def get_user_permissions(user_id: str) -> list[str]:
        """
        Lấy danh sách permission code của user.

        - role='admin'    → ['*'] toàn quyền
        - role='staff'    → quyền từ admin_roles.permissions
        - role='customer' → []
        """
        user_id = str(user_id or "").strip()
        if not user_id:
            return []

        cache_key = f"perms:{user_id}"
        cached = RBACService._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            db = RBACService._db()

            user_res = (
                db.table("users")
                .select("role, admin_role_slug, is_suspended")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )

            if not user_res.data:
                return []

            user = user_res.data[0]

            if user.get("is_suspended"):
                perms: list[str] = []
            elif user.get("role") == USER_ROLE_ADMIN:
                perms = ["*"]
            elif user.get("role") == USER_ROLE_STAFF:
                slug = user.get("admin_role_slug")
                if not slug:
                    perms = []
                else:
                    role_res = (
                        db.table("admin_roles")
                        .select("permissions")
                        .eq("slug", slug)
                        .limit(1)
                        .execute()
                    )
                    raw_permissions = role_res.data[0].get("permissions") if role_res.data else []
                    perms = RBACService.normalize_permissions(raw_permissions, keep_unknown=True)
            else:
                perms = []

            RBACService._cache_set(cache_key, perms)
            return perms

        except Exception as e:
            logger.error("[RBAC] get_user_permissions user_id=%s lỗi: %s", user_id, e, exc_info=True)
            return []

    @staticmethod
    def has_permission(user_id: str, permission_code: str) -> bool:
        """Kiểm tra một quyền cụ thể."""
        permission_code = str(permission_code or "").strip()
        if not permission_code:
            return False

        perms = RBACService.get_user_permissions(user_id)
        return "*" in perms or permission_code in perms

    @staticmethod
    def has_any_permission(user_id: str, permission_codes: list[str] | tuple[str, ...] | set[str]) -> bool:
        """True nếu user có ít nhất một quyền trong danh sách."""
        perms = set(RBACService.get_user_permissions(user_id))
        if "*" in perms:
            return True
        return any(str(code).strip() in perms for code in permission_codes or [])

    @staticmethod
    def has_all_permissions(user_id: str, permission_codes: list[str] | tuple[str, ...] | set[str]) -> bool:
        """True nếu user có tất cả quyền trong danh sách."""
        perms = set(RBACService.get_user_permissions(user_id))
        if "*" in perms:
            return True
        return all(str(code).strip() in perms for code in permission_codes or [])

    @staticmethod
    def is_super_admin(user_id: str) -> bool:
        """Kiểm tra user có phải Super Admin không."""
        user = RBACService.get_user(user_id)
        return bool(user and user.get("role") == USER_ROLE_ADMIN and not user.get("is_suspended"))

    @staticmethod
    def is_admin_or_staff(user_id: str) -> bool:
        """Kiểm tra user có được vào khu vực admin không."""
        user = RBACService.get_user(user_id)
        return bool(
            user
            and not user.get("is_suspended")
            and user.get("role") in {USER_ROLE_ADMIN, USER_ROLE_STAFF}
        )

    # ─────────────────────────────────────────────────────────────
    #  STAFF USER MANAGEMENT
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def get_all_staff(include_super_admin: bool = False) -> list[dict]:
        """
        Lấy danh sách staff.

        include_super_admin=False: chỉ role='staff'
        include_super_admin=True : lấy cả role='staff' và role='admin'
        """
        try:
            db = RBACService._db()

            query = db.table("users").select(
                "id, email, full_name, role, admin_role_slug, is_suspended, created_at"
            )

            if include_super_admin:
                query = query.in_("role", [USER_ROLE_STAFF, USER_ROLE_ADMIN])
            else:
                query = query.eq("role", USER_ROLE_STAFF)

            res = query.order("full_name", desc=False).execute()
            users = res.data or []

            role_names = {
                role["slug"]: role["name"]
                for role in RBACService.get_all_roles()
                if role.get("slug")
            }

            for user in users:
                role = user.get("role")
                slug = user.get("admin_role_slug")
                user["role_label"] = "Super Admin" if role == USER_ROLE_ADMIN else role_names.get(slug, slug or "Staff")
                user["initials"] = RBACService._make_initials(user.get("full_name") or user.get("email"))

            return users

        except Exception as e:
            logger.error("[RBAC] get_all_staff lỗi: %s", e, exc_info=True)
            return []

    @staticmethod
    def _make_initials(name: str | None) -> str:
        text = str(name or "").strip()
        if not text:
            return "?"

        parts = [p for p in re.split(r"\s+", text) if p]
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return parts[0][0].upper()

    # ─────────────────────────────────────────────────────────────
    #  CACHE MANAGEMENT
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def invalidate_user_cache(user_id: str) -> None:
        """Xóa cache quyền của một user."""
        if user_id:
            _perm_cache.pop(f"perms:{user_id}", None)

    @staticmethod
    def _invalidate_cache_for_role(slug: str) -> None:
        """
        Xóa cache khi role thay đổi.
        Không cần biết user nào dùng role, xóa toàn bộ cache perms cho chắc chắn.
        """
        keys_to_delete = [key for key in _perm_cache if key.startswith("perms:")]
        for key in keys_to_delete:
            _perm_cache.pop(key, None)

    @staticmethod
    def clear_cache() -> None:
        """Xóa toàn bộ cache RBAC."""
        _perm_cache.clear()


__all__ = [
    "RBACService",
    "AVAILABLE_PERMISSIONS",
    "PROTECTED_ROLE_SLUGS",
    "USER_ROLE_ADMIN",
    "USER_ROLE_STAFF",
    "USER_ROLE_CUSTOMER",
]
