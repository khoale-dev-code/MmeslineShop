"""
app/models/collection_model.py
===========================
Quản lý các chiến dịch bộ sưu tập thời trang xu hướng (Lookbook/Campaigns).
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)

class CollectionModel:

    @staticmethod
    def _db(): 
        return get_supabase()

    @staticmethod
    def _db_admin(): 
        return get_supabase_admin()

    @staticmethod
    def get_all(active_only: bool = False, admin_mode: bool = False) -> List[Dict]:
        """
        Lấy danh sách bộ sưu tập.
        - Nếu admin_mode=True: Bypass RLS, lấy cả những bộ sưu tập đang ẩn.
        - Nếu active_only=True: Chỉ lấy những bộ sưu tập có is_active=True.
        """
        db = CollectionModel._db_admin() if admin_mode else CollectionModel._db()
        try:
            query = db.table("collections").select("*")
            
            if active_only:
                query = query.eq("is_active", True)
            
            # Ưu tiên sort_order, nếu trùng thì lấy cái mới tạo gần nhất
            r = query.order("sort_order").order("created_at", desc=True).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"Lỗi truy vấn danh sách bộ sưu tập: {e}")
            return []

    @staticmethod
    def get_by_id(cid: str) -> Optional[Dict]:
        db = CollectionModel._db_admin()
        try:
            r = db.table("collections").select("*").eq("id", cid).limit(1).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"Lỗi lấy bộ sưu tập ID: {cid} — {e}")
            return None

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict:
        db = CollectionModel._db_admin()
        try:
            r = db.table("collections").insert(data).execute()
            return r.data[0] if r.data else {}
        except Exception as e:
            logger.error(f"Lỗi tạo bộ sưu tập mới: {e}")
            return {}

    @staticmethod
    def update(cid: str, data: Dict[str, Any]) -> Dict:
        db = CollectionModel._db_admin()
        try:
            # Loại bỏ None để tránh ghi đè dữ liệu rác vào Supabase
            clean_data = {k: v for k, v in data.items() if v is not None}
            if not clean_data: return {}
            
            r = db.table("collections").update(clean_data).eq("id", cid).execute()
            return r.data[0] if r.data else {}
        except Exception as e:
            logger.error(f"Lỗi cập nhật bộ sưu tập ID: {cid} — {e}")
            return {}

    @staticmethod
    def delete(cid: str) -> bool:
        db = CollectionModel._db_admin()
        try:
            # Lấy info để xóa file media trên storage trước khi xóa record
            coll = CollectionModel.get_by_id(cid)
            if not coll: return False
            
            r = db.table("collections").delete().eq("id", cid).execute()
            if r.data:
                if coll.get("image_url"): CollectionModel.delete_media_from_url(coll["image_url"])
                if coll.get("video_url"): CollectionModel.delete_media_from_url(coll["video_url"])
            return bool(r.data)
        except Exception as e:
            logger.error(f"Lỗi xóa bộ sưu tập ID: {cid} — {e}")
            return False

    @staticmethod
    def upload_media(file_bytes: bytes, filename: str, content_type: str) -> str:
        db = CollectionModel._db_admin()
        try:
            # Đảm bảo đường dẫn file an toàn
            safe_filename = filename.replace(" ", "_")
            path = f"media/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_filename}"
            db.storage.from_("store-assets").upload(path, file_bytes, {"content-type": content_type})
            return db.storage.from_("store-assets").get_public_url(path)
        except Exception as e:
            logger.error(f"Lỗi đẩy file bộ sưu tập lên Storage: {e}")
            return ""

    @staticmethod
    def delete_media_from_url(public_url: str) -> bool:
        db = CollectionModel._db_admin()
        try:
            if not public_url or "store-assets" not in public_url: return False
            # Trích xuất đường dẫn file sau tên bucket
            parts = public_url.split("/store-assets/")
            if len(parts) > 1:
                db.storage.from_("store-assets").remove([parts[1]])
                return True
            return False
        except Exception as e:
            logger.error(f"Lỗi xóa file rác từ URL: {e}")
            return False