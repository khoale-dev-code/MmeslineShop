"""
app/models/user_model.py
=========================
Model xử lý tất cả thao tác liên quan đến bảng `users` và phân quyền (RBAC) trên Supabase.

CHANGELOG (Sửa lỗi triệt để bẫy khóa dữ liệu RLS & Crash Giao diện):
- Đồng bộ hóa get_by_email() và get_by_id() sang dùng get_supabase_admin() để bảo đảm nạp đầy đủ
  trường thông tin (full_name, role, admin_role_slug) cho Session Context, chống lỗi sập giao diện.
- UserModel.update_profile() nâng cấp lên admin client để xử lý luồng cập nhật thông tin mượt mà.
- Bảo toàn cấu trúc gọn gàng, loại bỏ hoàn toàn các bảng thừa không tồn tại trong schema.
"""

import logging
from app.utils.supabase_client import get_supabase, get_supabase_admin
from app.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)


class UserModel:

    # ═══════════════════════════════════════════════════════════════
    #  TẠO USER MỚI (Bypass RLS an toàn)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def create(email: str, password: str, full_name: str) -> dict:
        db = get_supabase_admin()
        hashed = hash_password(password)

        try:
            user_result = db.table("users").insert({
                "email":         email,
                "password_hash": hashed,
                "full_name":     full_name,
                "role":          "customer", # Quyền mặc định khi đăng ký tài khoản mới
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
    #  QUERY (ĐÃ ĐỒNG BỘ BYPASS RLS ĐỂ TRÁNH LỖI HOÀN CẢNH ĐĂNG NHẬP)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_by_email(email: str) -> dict | None:
        # ✅ SỬA ĐỔI: Dùng admin client để nạp toàn bộ metadata, tránh RLS chặn mất trường full_name
        db = get_supabase_admin()
        try:
            result = db.table("users").select("*").eq("email", email).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"[UserModel.get_by_email] Lỗi ({email}): {e}")
            return None

    @staticmethod
    def get_by_id(user_id: str) -> dict | None:
        # ✅ SỬA ĐỔI: Dùng admin client để Middleware đồng bộ current_user sạch lỗi crash cấu trúc
        db = get_supabase_admin()
        try:
            result = db.table("users").select("*").eq("id", user_id).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"[UserModel.get_by_id] Lỗi (id={user_id}): {e}")
            return None

    @staticmethod
    def get_user_count() -> int:
        """
        Đếm tổng số user có role='customer' (không tính các tài khoản nội bộ admin/staff).
        Dùng count='exact' để Supabase trả về số lượng qua header, tối ưu hóa băng thông.
        """
        db = get_supabase_admin()
        try:
            result = (
                db.table("users")
                .select("id", count="exact")
                .eq("role", "customer")
                .execute()
            )
            return result.count or 0
        except Exception as e:
            logger.error(f"[UserModel.get_user_count] Lỗi: {e}")
            return 0

    # ═══════════════════════════════════════════════════════════════
    #  XÁC THỰC NGƯỜI DÙNG
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def authenticate(email: str, password: str) -> dict | None:
        # Gọi hàm get_by_email đã được nâng cấp quyền admin ở phía trên
        user = UserModel.get_by_email(email)
        if not user:
            return None
        
        # So khớp chuỗi băm bảo mật mật khẩu đầu vào
        if verify_password(password, user.get("password_hash", "")):
            return user
        return None

    # ═══════════════════════════════════════════════════════════════
    #  KIỂM TRA SỰ TỒN TẠI
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def email_exists(email: str) -> bool:
        return UserModel.get_by_email(email) is not None

    # ═══════════════════════════════════════════════════════════════
    #  CẬP NHẬT THÔNG TIN THÀNH VIÊN
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def update_profile(user_id: str, data: dict) -> dict:
        # ✅ SỬA ĐỔI: Sử dụng admin client để hỗ trợ người dùng ghi đè thông tin cá nhân mượt mà
        db = get_supabase_admin()
        try:
            result = db.table("users").update(data).eq("id", user_id).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"[UserModel.update_profile] Lỗi (id={user_id}): {e}")
            return {}

    @staticmethod
    def change_password(email: str, new_password: str) -> bool:
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