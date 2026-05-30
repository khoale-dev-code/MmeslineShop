"""
app/models/favorite_model.py
=============================
Quản lý danh sách sản phẩm yêu thích (Wishlist) của người dùng GUA Maison.
Hỗ trợ Multi-channel Tracking (Web, POS, TikTok, Shopee, Facebook, Instagram).

CHANGELOG (Lazy Initialization & Multi-channel Tracking Optimization):
- Chuẩn hóa cơ chế Lazy Initialization qua hàm helper _db() công khai và _db_admin() bảo mật.
- Ép các hàm thay đổi dữ liệu (insert, delete) qua admin client để bypass RLS an toàn.
- Bổ sung tham số động 'channel' và 'source' để đồng bộ dữ liệu tracking marketing chuẩn schema.
"""

import logging
from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)


class FavoriteModel:

    # ═══════════════════════════════════════════════════════════════
    #  LAZY INITIALIZATION HELPERS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _db():
        """Khởi tạo lười kết nối Client công khai (Dành cho đọc danh sách)"""
        return get_supabase()

    @staticmethod
    def _db_admin():
        """Khởi tạo lười kết nối Client quyền Admin (Dành cho ghi/xóa dữ liệu Wishlist)"""
        return get_supabase_admin()

    # ═══════════════════════════════════════════════════════════════
    #  CORE OPERATIONS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def toggle_favorite(user_id: str, product_id: str, channel: str = "web", source: str = "organic") -> dict:
        """
        Bật/Tắt trạng thái yêu thích sản phẩm (Bypass RLS an toàn).
        Tích hợp lưu trữ kênh tương tác (channel) và nguồn chiến dịch (source) chuẩn tiếp thị.
        """
        if not user_id or not product_id:
            return {"status": "error", "message": "Thiếu thông tin người dùng hoặc sản phẩm."}
            
        db = FavoriteModel._db_admin()
        clean_uid = str(user_id).strip()
        clean_pid = str(product_id).strip()

        try:
            # Bước 1: Kiểm tra xem sản phẩm này đã được người dùng yêu thích chưa
            existing = db.table('favorites')\
                         .select('*')\
                         .eq('user_id', clean_uid)\
                         .eq('product_id', clean_pid)\
                         .execute()
            
            if existing.data:
                # Nếu đã tồn tại bản ghi -> Tiến hành Xóa (Bỏ yêu thích)
                db.table('favorites')\
                  .delete()\
                  .eq('user_id', clean_uid)\
                  .eq('product_id', clean_pid)\
                  .execute()
                  
                logger.info(f"[WISHLIST] User '{clean_uid}' xóa bỏ yêu thích sản phẩm '{clean_pid}'")
                return {"status": "removed"}
            else:
                # Nếu chưa tồn tại -> Thêm mới bản ghi kèm metadata theo dõi nguồn marketing
                db.table('favorites').insert({
                    "user_id":    clean_uid,
                    "product_id": clean_pid,
                    "channel":    channel.strip().lower(),
                    "source":     source.strip().lower()
                }).execute()
                
                logger.info(f"[WISHLIST] User '{clean_uid}' thêm yêu thích sản phẩm '{clean_pid}' qua kênh '{channel}' [{source}]")
                return {"status": "added"}

        except Exception as e:
            logger.error(f"[FavoriteModel.toggle_favorite] Gặp sự cố khi tương tác Wishlist: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_user_favorites(user_id: str) -> list:
        """
        Lấy toàn bộ danh sách sản phẩm yêu thích của người dùng kèm thông tin chi tiết Product.
        Sử dụng cơ chế Lazy Loading nạp dữ liệu nhanh khi có yêu cầu.
        """
        if not user_id:
            return []
            
        db = FavoriteModel._db()
        try:
            # Lấy danh sách yêu thích kèm theo quan hệ kết hợp bảng products thông qua khóa ngoại fkey
            response = db.table('favorites')\
                         .select('*, products(*)')\
                         .eq('user_id', str(user_id).strip())\
                         .execute()
                         
            return response.data or []
        except Exception as e:
            logger.error(f"[FavoriteModel.get_user_favorites] Lỗi truy vấn Wishlist cho user '{user_id}': {e}")
            return []