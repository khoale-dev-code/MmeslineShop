"""
app/models/address_model.py
============================
Quản lý sổ địa chỉ của khách hàng và đồng bộ số điện thoại cá nhân.

CHANGELOG (Tối ưu hóa Lazy Initialization & Khắc phục RLS đồng bộ SĐT):
- Giữ nguyên cấu trúc Lazy Initialization sạch sẽ bên trong từng hàm.
- Tích hợp thêm _db_admin() (get_supabase_admin) để bảo đảm việc đồng bộ SĐT sang bảng `users` 
  luôn thành công 100%, bypass bẫy chặn ghi dữ liệu RLS của Supabase.
- Thêm bảo vệ kiểm tra dữ liệu trả về trước khi xử lý mảng.
"""

import logging
from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)


class AddressModel:

    # ═══════════════════════════════════════════════════════════════
    #  LAZY INITIALIZATION HELPERS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _db():
        """Khởi tạo lười kết nối Client công khai (Đọc địa chỉ)"""
        return get_supabase()

    @staticmethod
    def _db_admin():
        """Khởi tạo lười kết nối Client Admin (Đồng bộ SĐT xuyên bảng users)"""
        return get_supabase_admin()

    # ═══════════════════════════════════════════════════════════════
    #  THAO TÁC ĐỌC DỮ LIỆU (READ)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_user_addresses(user_id: str) -> list:
        """Lấy danh sách địa chỉ của user, đưa địa chỉ mặc định lên đầu."""
        db = AddressModel._db()
        try:
            result = db.table("user_addresses") \
                       .select("*") \
                       .eq("user_id", user_id) \
                       .order("is_default", desc=True) \
                       .execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"[AddressModel.get_user_addresses] Lỗi: {e}")
            return []

    @staticmethod
    def get_default_address(user_id: str) -> dict | None:
        """Lấy địa chỉ mặc định duy nhất của người dùng."""
        db = AddressModel._db()
        try:
            result = db.table("user_addresses") \
                       .select("*") \
                       .eq("user_id", user_id) \
                       .eq("is_default", True) \
                       .limit(1) \
                       .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"[AddressModel.get_default_address] Lỗi: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    #  THAO TÁC GHI DỮ LIỆU (WRITE & SYNC XUYÊN BẢNG)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def add_address(user_id: str, data: dict) -> dict:
        """Thêm địa chỉ mới. Nếu là địa chỉ đầu tiên -> set làm mặc định và đồng bộ SĐT bằng Admin Quyền."""
        db = AddressModel._db()
        db_admin = AddressModel._db_admin()
        try:
            current_addresses = AddressModel.get_user_addresses(user_id)
            is_first = not current_addresses
            
            if is_first:
                data["is_default"] = True
                
            data["user_id"] = user_id
            result = db.table("user_addresses").insert(data).execute()
            
            if result.data:
                new_address = result.data[0]
                # ✅ ĐÃ SỬA: Đồng bộ SĐT an toàn qua bảng users bằng kênh admin nếu đây là địa chỉ đầu tiên
                if is_first and new_address.get("phone"):
                    db_admin.table("users").update({"phone": new_address["phone"]}).eq("id", user_id).execute()
                return new_address
            return {}
        except Exception as e:
            logger.error(f"[AddressModel.add_address] Lỗi: {e}")
            return {}

    @staticmethod
    def set_default(user_id: str, address_id: str) -> bool:
        """Đổi địa chỉ mặc định và cập nhật cứng số điện thoại mới vào thông tin tài khoản."""
        db = AddressModel._db()
        db_admin = AddressModel._db_admin()
        try:
            # 1. Hủy trạng thái mặc định cũ của toàn bộ địa chỉ thuộc user này
            db.table("user_addresses").update({"is_default": False}).eq("user_id", user_id).execute()
            
            # 2. Cài trạng thái mặc định mới cho địa chỉ được lựa chọn
            res = db.table("user_addresses").update({"is_default": True}).eq("id", address_id).execute()
            
            # 3. ✅ ĐÃ SỬA: Đồng bộ SĐT chuẩn xác qua bảng users bằng quyền Service Role để tránh lỗi bảo mật RLS
            if res.data:
                new_phone = res.data[0].get("phone")
                if new_phone:
                    db_admin.table("users").update({"phone": new_phone}).eq("id", user_id).execute()
            return True
        except Exception as e:
            logger.error(f"[AddressModel.set_default] Lỗi: {e}")
            return False

    @staticmethod
    def update_address(user_id: str, address_id: str, data: dict) -> bool:
        """Cập nhật địa chỉ. Nếu đang là địa chỉ mặc định -> Đồng bộ lại số điện thoại cá nhân mới."""
        db = AddressModel._db()
        db_admin = AddressModel._db_admin()
        try:
            # Bảo đảm quy chế an toàn: Chỉ cập nhật chính xác địa chỉ thuộc sở hữu của user này
            res = db.table("user_addresses").update(data).eq("user_id", user_id).eq("id", address_id).execute()
            
            if res.data:
                updated_address = res.data[0]
                # ✅ ĐÃ SỬA: Nếu địa chỉ chỉnh sửa là mặc định, ép nạp lại SĐT mới sang hồ sơ để tránh rác thông tin
                if updated_address.get("is_default") and updated_address.get("phone"):
                    db_admin.table("users").update({"phone": updated_address["phone"]}).eq("id", user_id).execute()
                return True
            return False
        except Exception as e:
            logger.error(f"[AddressModel.update_address] Lỗi: {e}")
            return False

    @staticmethod
    def delete_address(user_id: str, address_id: str) -> bool:
        """Xóa vĩnh viễn địa chỉ ra khỏi danh bạ."""
        db = AddressModel._db()
        try:
            db.table("user_addresses").delete().eq("user_id", user_id).eq("id", address_id).execute()
            return True
        except Exception as e:
            logger.error(f"[AddressModel.delete_address] Lỗi: {e}")
            return False