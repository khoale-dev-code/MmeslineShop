"""
app/models/collection_model.py
===========================
Quản lý các chiến dịch bộ sưu tập thời trang xu hướng (Lookbook/Campaigns).
Hỗ trợ lưu trữ Media và sắp xếp thứ tự hiển thị bằng phương thức kéo thả linh hoạt.
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
        Nếu admin_mode=True, sử dụng admin client để bypass hoàn toàn RLS trên Supabase.
        """
        # 🟢 ĐÃ FIX BẪY RLS: Admin mode sẽ dùng thẳng kết nối Admin quyền tối cao
        db = CollectionModel._db_admin() if admin_mode else CollectionModel._db()
        try:
            query = db.table("collections").select("*")
            if active_only:
                query = query.eq("is_active", True)
            r = query.order("sort_order").order("created_at", desc=True).execute()
            return r.data or []
        except Exception:
            logger.exception("Lỗi truy vấn danh sách bộ sưu tập")
            return []

    @staticmethod
    def get_by_id(cid: str) -> Optional[Dict]:
        db = CollectionModel._db_admin() # Dùng admin để đảm bảo tìm thấy trong không gian quản trị
        try:
            r = db.table("collections").select("*").eq("id", cid).limit(1).execute()
            return r.data[0] if r.data else None
        except Exception:
            logger.exception(f"Lỗi lấy bộ sưu tập ID: {cid}")
            return None

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict:
        db = CollectionModel._db_admin()
        try:
            r = db.table("collections").insert(data).execute()
            return r.data[0] if r.data else {}
        except Exception:
            logger.exception("Lỗi tạo bộ sưu tập mới")
            return {}

    @staticmethod
    def update(cid: str, data: Dict[str, Any]) -> Dict:
        db = CollectionModel._db_admin()
        try:
            clean_data = {k: v for k, v in data.items() if v is not None}
            r = db.table("collections").update(clean_data).eq("id", cid).execute()
            return r.data[0] if r.data else {}
        except Exception:
            logger.exception(f"Lỗi cập nhật bộ sưu tập ID: {cid}")
            return {}

    @staticmethod
    def delete(cid: str) -> bool:
        db = CollectionModel._db_admin()
        try:
            coll = CollectionModel.get_by_id(cid)
            r = db.table("collections").delete().eq("id", cid).execute()
            if r.data and coll:
                if coll.get("image_url"): CollectionModel.delete_media_from_url(coll["image_url"])
                if coll.get("video_url"): CollectionModel.delete_media_from_url(coll["video_url"])
            return bool(r.data)
        except Exception:
            logger.exception(f"Lỗi xóa bộ sưu tập ID: {cid}")
            return False

    @staticmethod
    def upload_media(file_bytes: bytes, filename: str, content_type: str) -> str:
        db = CollectionModel._db_admin()
        try:
            path = f"media/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            db.storage.from_("store-assets").upload(path, file_bytes, {"content-type": content_type})
            return db.storage.from_("store-assets").get_public_url(path)
        except Exception:
            logger.exception("Lỗi đẩy file bộ sưu tập lên Storage")
            return ""

    @staticmethod
    def delete_media_from_url(public_url: str) -> bool:
        db = CollectionModel._db_admin()
        try:
            if not public_url or "store-assets" not in public_url: return False
            parts = public_url.split("/store-assets/")
            if len(parts) > 1:
                db.storage.from_("store-assets").remove([parts[1]])
                return True
            return False
        except Exception:
            logger.exception("Lỗi xóa file rác từ URL")
            return False