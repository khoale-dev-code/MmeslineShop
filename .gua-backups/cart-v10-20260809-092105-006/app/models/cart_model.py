"""
app/models/cart_model.py
=========================
Quản lý dữ liệu Giỏ hàng của người dùng trên hệ thống GUA Maison.
Phiên bản Premium: Tích hợp kiểm tra tồn kho (Stock Check), 
chống Over-sell và lọc dữ liệu mồ côi (Orphan Data).

CHANGELOG (Tối ưu hóa Lazy Initialization & Phân tuyến kết nối an toàn):
- Tích hợp cơ chế Lazy Initialization thông qua hai helper _db() (Public) và _db_admin() (Service Role).
- Chuyển đổi các hàm can thiệp dữ liệu giỏ hàng hoặc can thiệp tồn kho sang admin client để tránh lỗi chặn quyền RLS.
- Giữ vững logic core chống mua quá mức tồn kho (Over-sell) và tự dọn dữ liệu rác mồ côi.
"""

import logging
from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)


class CartModel:

    # ═══════════════════════════════════════════════════════════════
    #  LAZY INITIALIZATION HELPERS (KHỞI TẠO LƯỜI DỮ LIỆU)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _db():
        """Helper lấy kết nối Supabase công khai (Dành cho đọc thông tin cơ bản)"""
        return get_supabase()

    @staticmethod
    def _db_admin():
        """Helper lấy kết nối Supabase quyền Admin (Dành cho xử lý dữ liệu và kiểm kho bypass RLS)"""
        return get_supabase_admin()

    # ═══════════════════════════════════════════════════════════════
    #  GIAO DIỆN ĐỌC (READ METHODS)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_user_cart(user_id: str) -> list:
        """
        Lấy toàn bộ sản phẩm trong giỏ hàng.
        Tự động Join với products và product_variants. Có bộ lọc an toàn.
        """
        # Dùng admin client để bảo đảm đọc mượt mà dữ liệu giỏ hàng, tránh lỗi RLS chặn dữ liệu quan hệ (Join)
        db = CartModel._db_admin()
        try:
            res = db.table("cart_items") \
                .select("*, products(id, name, price, thumbnail_url, stock, slug, is_active, deleted_at), product_variants(*)") \
                .eq("user_id", user_id) \
                .order("created_at", desc=False) \
                .execute()
            
            # Lọc bỏ dữ liệu rác (Sản phẩm hoặc Biến thể đã bị Admin xóa hẳn khỏi Database)
            valid_items = []
            if res.data:
                for item in res.data:
                    # Chỉ lấy item nếu products và product_variants vẫn còn tồn tại dữ liệu thực
                    if item.get("products") and item.get("product_variants"):
                        valid_items.append(item)
                        
            return valid_items
        except Exception as e:
            logger.error(f"[CartModel.get_user_cart] Lỗi hệ thống khi nạp giỏ hàng user {user_id}: {e}")
            return []

    @staticmethod
    def get_count(user_id: str) -> int:
        """Đếm tổng số lượng sản phẩm đang có trong giỏ hàng của người dùng"""
        try:
            items = CartModel.get_user_cart(user_id)
            return sum(item.get("quantity", 0) for item in items)
        except Exception as e:
            logger.error(f"[CartModel.get_count] Lỗi tính số lượng: {e}")
            return 0

    # ═══════════════════════════════════════════════════════════════
    #  GIAO DIỆN GHI / SỬA (WRITE METHODS)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def add_item(user_id: str, product_id: str, variant_id: str, quantity: int = 1) -> dict:
        """
        Thêm sản phẩm vào giỏ với Logic An Toàn Tuyệt Đối:
        1. Kiểm tra biến thể kích thước/màu sắc có tồn tại thực tế không.
        2. Ép số lượng mua KHÔNG VƯỢT QUÁ giới hạn tồn kho trong database.
        """
        db = CartModel._db_admin() # Dùng admin client để đọc tồn kho chính xác và bypass RLS bảo vệ
        try:
            # Bước 1: Kiểm tra Tồn kho thực tế của Biến thể (Product Variant)
            variant_check = db.table("product_variants").select("stock").eq("id", variant_id).execute()
            if not variant_check.data:
                logger.warning(f"[CartModel.add_item] Thất bại: Biến thể {variant_id} không tồn tại trên hệ thống.")
                return {}
            
            max_stock = variant_check.data[0].get("stock", 0)
            if max_stock <= 0:
                logger.warning(f"[CartModel.add_item] Thất bại: Mã biến thể {variant_id} đã cháy hàng.")
                return {}  # Đã hết hàng, từ chối luồng xử lý tiếp theo

            # Bước 2: Kiểm tra item này đã nằm sẵn trong giỏ của user chưa
            existing = db.table("cart_items") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("variant_id", variant_id) \
                .execute()
            
            if existing.data:
                # Nếu đã có -> Cộng dồn số lượng mua mới và ép giới hạn trần theo tồn kho thực
                item_id = existing.data[0]["id"]
                new_qty = existing.data[0]["quantity"] + quantity
                
                if new_qty > max_stock:
                    new_qty = max_stock  # Ngăn chặn hành vi over-sell mua lố kho
                    
                res = db.table("cart_items") \
                    .update({"quantity": new_qty}) \
                    .eq("id", item_id) \
                    .execute()
                return res.data[0] if res.data else {}
            else:
                # Nếu chưa có món này -> Thêm bản ghi mới vào giỏ hàng
                if quantity > max_stock:
                    quantity = max_stock
                    
                res = db.table("cart_items").insert({
                    "user_id": user_id,
                    "product_id": product_id,
                    "variant_id": variant_id,
                    "quantity": quantity
                }).execute()
                return res.data[0] if res.data else {}
                
        except Exception as e:
            logger.error(f"[CartModel.add_item] Lỗi thêm sản phẩm vào giỏ hàng: {e}")
            return {}

    @staticmethod
    def update_quantity(user_id: str, item_id: str, quantity: int) -> dict:
        """Cập nhật số lượng của 1 món hàng trong giỏ. Kiểm tra tồn kho thời gian thực trực tiếp."""
        if quantity <= 0:
            CartModel.remove_item(user_id, item_id)
            return {}

        db = CartModel._db_admin()
        try:
            # Bước 1: Lấy thông tin item để xác minh mối liên kết Variant
            item = db.table("cart_items").select("variant_id").eq("id", item_id).eq("user_id", user_id).execute()
            if not item.data:
                return {}
            
            variant_id = item.data[0]["variant_id"]
            
            # Bước 2: Truy quét kiểm kho trực tiếp của mã Variant đó
            variant_check = db.table("product_variants").select("stock").eq("id", variant_id).execute()
            if variant_check.data:
                max_stock = variant_check.data[0].get("stock", 0)
                if quantity > max_stock:
                    quantity = max_stock  # Triệt tiêu thủ thuật sửa mã HTML/F12 để cố tình tăng quantity lố kho
                    
            # Bước 3: Thực thi cập nhật số lượng an toàn
            res = db.table("cart_items") \
                .update({"quantity": quantity}) \
                .eq("id", item_id) \
                .eq("user_id", user_id) \
                .execute()
            return res.data[0] if res.data else {}
            
        except Exception as e:
            logger.error(f"[CartModel.update_quantity] Lỗi cập nhật số lượng cho item {item_id}: {e}")
            return {}

    @staticmethod
    def remove_item(user_id: str, item_id: str) -> bool:
        """Xóa một sản phẩm khỏi giỏ hàng. Kiểm tra bảo mật chéo qua user_id."""
        db = CartModel._db_admin()
        try:
            res = db.table("cart_items") \
                .delete() \
                .eq("id", item_id) \
                .eq("user_id", user_id) \
                .execute()
            return len(res.data) > 0 if res.data else False
        except Exception as e:
            logger.error(f"[CartModel.remove_item] Lỗi xóa món hàng {item_id}: {e}")
            return False

    @staticmethod
    def clear_cart(user_id: str) -> bool:
        """Xóa sạch giỏ hàng hoàn toàn (Gọi tự động sau khi đơn hàng thanh toán thành công)."""
        db = CartModel._db_admin()
        try:
            db.table("cart_items") \
                .delete() \
                .eq("user_id", user_id) \
                .execute()
            return True
        except Exception as e:
            logger.error(f"[CartModel.clear_cart] Lỗi làm trống giỏ hàng của user {user_id}: {e}")
            return False