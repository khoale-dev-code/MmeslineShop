"""
app/models/user_model.py
=========================
Model xử lý tất cả thao tác liên quan đến bảng `users` và phân quyền (RBAC) trên Supabase.

CHANGELOG (fix đăng ký / đăng nhập):
- Xoá block gọi bảng `roles` và `user_roles` (không tồn tại trong schema).
- Thêm "role": "customer" vào payload INSERT để session luôn đọc được.
- UserModel.create() dùng get_supabase_admin() để bypass RLS khi tạo user.
- Thêm UserModel.change_password() để dùng ở reset-password / đổi mật khẩu.
"""

import logging
from app.utils.supabase_client import get_supabase, get_supabase_admin
from app.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)


class UserModel:

    # ═══════════════════════════════════════════════════════════════
    #  TẠO USER MỚI
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def create(email: str, password: str, full_name: str) -> dict:
        """
        Tạo user mới – hash password trước khi lưu DB.

        Dùng service-role client để bypass RLS (anon key không có quyền INSERT
        vào bảng users nếu chưa cấu hình policy tương ứng).

        Trả về:
            dict  – user vừa tạo (có đầy đủ field từ DB)
            {}    – nếu có lỗi (đã log chi tiết)
        """
        # Dùng admin client để bypass RLS khi đăng ký
        db = get_supabase_admin()
        hashed = hash_password(password)

        try:
            user_result = db.table("users").insert({
                "email":         email,
                "password_hash": hashed,
                "full_name":     full_name,
                "role":          "customer",   # ← rõ ràng, không phụ thuộc DEFAULT của DB
            }).execute()

            user = user_result.data[0] if user_result.data else {}

            if not user:
                logger.error(
                    f"[UserModel.create] INSERT không trả về data dù không có exception "
                    f"(email={email}). Kiểm tra RLS hoặc constraint bảng users."
                )

            return user

        except Exception as e:
            logger.error(f"[UserModel.create] Lỗi khi tạo user ({email}): {e}")
            return {}

    # ═══════════════════════════════════════════════════════════════
    #  QUERY
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_by_email(email: str) -> dict | None:
        """Tìm user theo email. Trả về None nếu không tồn tại."""
        db = get_supabase()
        try:
            result = db.table("users").select("*").eq("email", email).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"[UserModel.get_by_email] Lỗi ({email}): {e}")
            return None

    @staticmethod
    def get_by_id(user_id: str) -> dict | None:
        """Tìm user theo UUID. Trả về None nếu không tồn tại."""
        db = get_supabase()
        try:
            result = db.table("users").select("*").eq("id", user_id).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"[UserModel.get_by_id] Lỗi (id={user_id}): {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    #  XÁC THỰC
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def authenticate(email: str, password: str) -> dict | None:
        """
        Xác thực email + password.

        Trả về:
            dict  – user nếu thông tin đúng
            None  – nếu email không tồn tại hoặc sai mật khẩu
        """
        user = UserModel.get_by_email(email)
        if not user:
            return None
        if verify_password(password, user.get("password_hash", "")):
            return user
        return None

    # ═══════════════════════════════════════════════════════════════
    #  KIỂM TRA
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def email_exists(email: str) -> bool:
        """Kiểm tra email đã được đăng ký chưa."""
        return UserModel.get_by_email(email) is not None

    # ═══════════════════════════════════════════════════════════════
    #  CẬP NHẬT
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def update_profile(user_id: str, data: dict) -> dict:
        """
        Cập nhật thông tin profile của user (full_name, phone, v.v.).

        Lưu ý: Không truyền password_hash vào đây – dùng change_password() thay thế.
        """
        db = get_supabase()
        try:
            result = db.table("users").update(data).eq("id", user_id).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"[UserModel.update_profile] Lỗi (id={user_id}): {e}")
            return {}

    @staticmethod
    def change_password(email: str, new_password: str) -> bool:
        """
        Đổi mật khẩu theo email (dùng cho forgot-password / reset-password).

        Dùng service-role client để đảm bảo UPDATE luôn thực hiện được
        dù RLS có hạn chế.

        Trả về:
            True  – thành công
            False – thất bại
        """
        db = get_supabase_admin()
        try:
            db.table("users") \
              .update({"password_hash": hash_password(new_password)}) \
              .eq("email", email) \
              .execute()
            return True
        except Exception as e:
            logger.error(f"[UserModel.change_password] Lỗi ({email}): {e}")
            return False