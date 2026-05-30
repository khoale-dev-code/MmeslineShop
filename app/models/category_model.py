"""
app/models/category_model.py  –  CRUD danh mục (Enterprise Edition - Lazy Initialization)
Hỗ trợ: Media Upload, Auto Cleanup Storage, SEO Metadata, Sort Order & Visibility.
CHANGELOG:
- Di chuyển toàn bộ khởi tạo db vào trong từng hàm để kích hoạt Lazy Initialization, giảm tải Cold Start trên Vercel.
- Đồng bộ hóa các hàm Write/Delete sang get_supabase_admin() để bảo đảm luồng dọn rác Storage bypass RLS.
"""
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from app.utils.supabase_client import get_supabase, get_supabase_admin

# Khởi tạo logger để bắt lỗi hệ thống
logger = logging.getLogger(__name__)


class CategoryModel:
    # 🔴 ĐÃ GỠ BỎ: db = get_supabase() ở cấp Class để chống nghẽn mạng khi nạp file ứng dụng.

    # ═══════════════════════════════════════════════════════════════
    #  UTILITIES (TIỆN ÍCH)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def generate_slug(name: str) -> str:
        """Tạo slug không dấu tự động từ tên danh mục."""
        if not name:
            return ""
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

    # ═══════════════════════════════════════════════════════════════
    #  READ (TRUY VẤN DỮ LIỆU)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_all(active_only: bool=False) -> List[Dict]:
        """Lấy danh sách danh mục. Có hỗ trợ lọc chỉ lấy danh mục đang Active."""
        db = get_supabase()  # ✅ Khởi tạo cục bộ khi hàm chạy thực tế
        try:
            query = db.table("categories").select("*")
            if active_only:
                query = query.eq("is_active", True)
            
            # Ưu tiên sắp xếp theo sort_order, sau đó theo alphabet
            r = query.order("sort_order").order("name").execute()
            return r.data
        except Exception:
            logger.exception("Lỗi truy vấn danh sách danh mục (get_all)")
            return []

    @staticmethod
    def get_by_id(cid: str) -> Optional[Dict]:
        """Lấy thông tin một danh mục theo UUID."""
        db = get_supabase()  # ✅ Khởi tạo cục bộ
        try:
            r = db.table("categories").select("*").eq("id", cid).limit(1).execute()
            return r.data[0] if r.data else None
        except Exception:
            logger.exception(f"Lỗi lấy thông tin danh mục ID: {cid}")
            return None

    @staticmethod
    def get_by_slug(slug: str) -> Optional[Dict]:
        """Lấy thông tin danh mục theo Slug (Dùng cho Storefront)."""
        db = get_supabase()  # ✅ Khởi tạo cục bộ
        try:
            r = db.table("categories").select("*").eq("slug", slug).eq("is_active", True).limit(1).execute()
            return r.data[0] if r.data else None
        except Exception:
            logger.exception(f"Lỗi lấy thông tin danh mục bằng Slug: {slug}")
            return None

    @staticmethod
    def get_homepage_categories(limit: int=9) -> List[Dict]:
        """Lấy danh mục để hiển thị ra trang chủ (được ghim, đang hoạt động, có hình ảnh/video)"""
        db = get_supabase()  # ✅ Khởi tạo cục bộ
        try:
            r = db.table("categories").select("*") \
                .eq("is_active", True) \
                .eq("show_on_home", True) \
                .order("sort_order").order("name").execute()
            
            valid_categories = []
            for cat in r.data:
                has_image = bool(cat.get("image_url") and str(cat.get("image_url")).strip())
                has_video = bool(cat.get("video_url") and str(cat.get("video_url")).strip())
                
                if has_image or has_video:
                    valid_categories.append(cat)
                    
            return valid_categories[:limit]
        except Exception:
            logger.exception("Lỗi lấy danh mục trang chủ")
            return []

    # ═══════════════════════════════════════════════════════════════
    #  WRITE (THÊM / SỬA / XÓA)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict:
        """Tạo mới danh mục nhận vào một dictionary chứa toàn bộ dữ liệu."""
        db = get_supabase_admin()  # ✅ Sử dụng admin client để tránh lỗi chặn ghi dữ liệu do RLS
        try:
            if not data.get("slug") and data.get("name"):
                data["slug"] = CategoryModel.generate_slug(data["name"])

            r = db.table("categories").insert(data).execute()
            return r.data[0] if r.data else {}
        except Exception:
            logger.exception(f"Lỗi tạo danh mục mới: {data.get('name')}")
            return {}

    @staticmethod
    def update(cid: str, data: Dict[str, Any]) -> Dict:
        """Cập nhật danh mục."""
        db = get_supabase_admin()  # ✅ Sử dụng admin client an toàn
        try:
            old_cat = CategoryModel.get_by_id(cid)
            clean_data = {k: v for k, v in data.items() if v is not None}
            
            if not clean_data:
                return {}

            r = db.table("categories").update(clean_data).eq("id", cid).execute()

            # Dọn rác: Xóa file cũ khỏi Storage nếu có thay đổi URL
            if old_cat:
                new_img = clean_data.get("image_url")
                new_vid = clean_data.get("video_url")
                
                if new_img and old_cat.get("image_url") and new_img != old_cat.get("image_url"):
                    CategoryModel.delete_media_from_url(old_cat.get("image_url"))
                
                if new_vid and old_cat.get("video_url") and new_vid != old_cat.get("video_url"):
                    CategoryModel.delete_media_from_url(old_cat.get("video_url"))

            return r.data[0] if r.data else {}
        except Exception:
            logger.exception(f"Lỗi cập nhật danh mục ID: {cid}")
            return {}

    @staticmethod
    def delete(cid: str) -> bool:
        """Xóa danh mục. Tự động xóa file media đi kèm trên Storage."""
        db = get_supabase_admin()  # ✅ Khởi tạo kết nối cục bộ admin quyền cao nhất
        try:
            cat = CategoryModel.get_by_id(cid)
            r = db.table("categories").delete().eq("id", cid).execute()
            
            if r.data and cat:
                if cat.get("image_url"):
                    CategoryModel.delete_media_from_url(cat.get("image_url"))
                if cat.get("video_url"):
                    CategoryModel.delete_media_from_url(cat.get("video_url"))
                    
            return bool(r.data)
        except Exception:
            logger.exception(f"Lỗi xóa danh mục ID: {cid}")
            return False

    # ═══════════════════════════════════════════════════════════════
    #  MEDIA PROCESSING (XỬ LÝ FILE)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def upload_media(file_bytes: bytes, filename: str, content_type: str) -> str:
        """Upload file (ảnh/video) lên bucket 'categories' trong Supabase Storage."""
        db = get_supabase_admin()  # ✅ Khởi tạo cục bộ admin phục vụ ghi file vào Bucket
        try:
            safe_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            path = f"media/{safe_filename}"
            
            db.storage.from_("categories").upload(
                path, file_bytes, {"content-type": content_type}
            )
            return db.storage.from_("categories").get_public_url(path)
        except Exception:
            logger.exception("Lỗi upload media danh mục")
            return ""

    @staticmethod
    def delete_media_from_url(public_url: str) -> bool:
        """Hàm bóc tách tên file từ URL và xóa file trên Supabase Bucket."""
        db = get_supabase_admin()  # ✅ Khởi tạo cục bộ admin để dọn sạch tệp tin
        try:
            if not public_url or "supabase.co" not in public_url:
                return False
                
            parts = public_url.split("/categories/")
            if len(parts) > 1:
                file_path = parts[1]
                db.storage.from_("categories").remove([file_path])
                return True
            return False
        except Exception:
            logger.exception(f"Lỗi xóa file rác từ URL: {public_url}")
            return False