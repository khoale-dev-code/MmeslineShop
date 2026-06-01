"""
app/models/category_model.py
=========================
CRUD Danh mục hàng hóa thuần túy (Chủng loại cứng). 
Đã loại bỏ toàn bộ tính năng xử lý Media để tối ưu dung lượng và tốc độ phản hồi hệ thống.
"""
import logging
import re
from typing import List, Dict, Optional, Any
from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)

class CategoryModel:

    @staticmethod
    def generate_slug(name: str) -> str:
        if not name: return ""
        slug = name.lower()
        slug = re.sub(r'[áàảãạăắằẳẵặâấầẩẫậ]', 'a', slug)
        slug = re.sub(r'[éèẻẽẹêếềểễệ]', 'e', slug)
        slug = re.sub(r'[íìỉĩị]', 'i', slug)
        slug = re.sub(r'[óòỏõọôốồổỗộơớờởỡợ]', 'o', slug)
        slug = re.sub(r'[úùủũụưứừửữự]', 'u', slug)
        slug = re.sub(r'[ýỳỷỹỵ]', 'y', slug)
        slug = re.sub(r'[đ]', 'd', slug)
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '-', slug).strip('-')
        return slug

    @staticmethod
    def get_all(active_only: bool = False) -> List[Dict]:
        db = get_supabase()
        try:
            query = db.table("categories").select("*")
            if active_only:
                query = query.eq("is_active", True)
            r = query.order("name").execute()
            return r.data or []
        except Exception:
            logger.exception("Lỗi lấy danh sách danh mục cứng")
            return []

    @staticmethod
    def get_by_id(cid: str) -> Optional[Dict]:
        db = get_supabase()
        try:
            r = db.table("categories").select("*").eq("id", cid).limit(1).execute()
            return r.data[0] if r.data else None
        except Exception:
            logger.exception(f"Lỗi lấy danh mục ID: {cid}")
            return None

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict:
        db = get_supabase_admin()
        try:
            if not data.get("slug") and data.get("name"):
                data["slug"] = CategoryModel.generate_slug(data["name"])
            r = db.table("categories").insert(data).execute()
            return r.data[0] if r.data else {}
        except Exception:
            logger.exception("Lỗi tạo danh mục mới")
            return {}

    @staticmethod
    def update(cid: str, data: Dict[str, Any]) -> Dict:
        db = get_supabase_admin()
        try:
            clean_data = {k: v for k, v in data.items() if v is not None}
            r = db.table("categories").update(clean_data).eq("id", cid).execute()
            return r.data[0] if r.data else {}
        except Exception:
            logger.exception(f"Lỗi cập nhật danh mục ID: {cid}")
            return {}

    @staticmethod
    def delete(cid: str) -> bool:
        db = get_supabase_admin()
        try:
            r = db.table("categories").delete().eq("id", cid).execute()
            return bool(r.data)
        except Exception:
            logger.exception(f"Lỗi xóa danh mục ID: {cid}")
            return False