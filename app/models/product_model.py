"""
app/models/product_model.py
=========================
Quản lý dữ liệu Sản phẩm, Biến thể (Variants) và SEO chuẩn E-commerce cho GUA Maison.
Hỗ trợ Soft Delete, Slug generation, Barcode generation, và đồng bộ hình ảnh.

CHANGELOG (Tối ưu hóa Lazy Initialization & Khắc phục bẫy RLS Admin):
- Chuẩn hóa cơ chế Lazy Initialization qua hàm helper _db() công khai và _db_admin() bảo mật.
- Ép các hàm ghi dữ liệu (create, update, delete, sync_images) chạy qua admin client để bypass RLS.
- Loại bỏ các dòng print debug thừa, tối ưu hóa tốc độ xử lý phản hồi trên Vercel Serverless.
"""

import logging
import re
import uuid
from datetime import datetime
from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)


class ProductModel:

    # ═══════════════════════════════════════════════════════════════
    #  LAZY INITIALIZATION HELPERS (KHỞI TẠO LƯỜI KHI CÓ REQUEST)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _db():
        """Khởi tạo lười kết nối Client công khai (Dành cho đọc dữ liệu Storefront)"""
        return get_supabase()

    @staticmethod
    def _db_admin():
        """Khởi tạo lười kết nối Client quyền Admin (Dành cho ghi/sửa dữ liệu Admin Dashboard)"""
        return get_supabase_admin()

    # ═══════════════════════════════════════════════════════════════
    #  UTILITIES & FORMATTERS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def generate_slug(name: str) -> str:
        """Tạo slug không dấu chuẩn SEO: 'Áo Thun GUA' -> 'ao-thun-gua'"""
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

    @staticmethod
    def generate_barcode(product_id: str = None) -> str:
        """
        Sinh mã vạch duy nhất theo format: GUA-YYMM-XXXXXX
        - GUA     : Thương hiệu GUA Maison
        - YYMM    : Năm + Tháng tạo (VD: 2605 = tháng 5/2026)
        - XXXXXX  : 6 ký tự hex đầu của UUID (lấy từ product_id nếu có)
        """
        now = datetime.now()
        prefix = f"GUA-{now.strftime('%y%m')}"

        if product_id:
            hex_part = str(product_id).replace("-", "")[:6].upper()
        else:
            hex_part = uuid.uuid4().hex[:6].upper()

        return f"{prefix}-{hex_part}"

    # Bảng từ điển màu chuẩn phục vụ ngành Fashion
    COLOR_DICT = {
        'đen': '#000000', 'black': '#000000',
        'trắng': '#ffffff', 'white': '#ffffff',
        'đỏ': '#dc2626', 'red': '#dc2626',
        'xanh dương': '#2563eb', 'blue': '#2563eb',
        'xanh navy': '#1e3a8a', 'navy': '#1e3a8a',
        'xanh lá': '#16a34a', 'green': '#16a34a',
        'vàng': '#eab308', 'yellow': '#eab308',
        'cam': '#ea580c', 'orange': '#ea580c',
        'hồng': '#ec4899', 'pink': '#ec4899',
        'tím': '#9333ea', 'purple': '#9333ea',
        'xám': '#6b7280', 'gray': '#6b7280', 'grey': '#6b7280',
        'nâu': '#78350f', 'brown': '#78350f',
        'be': '#f5f5dc', 'beige': '#f5f5dc',
        'kem': '#fef3c7', 'cream': '#fef3c7'
    }

    @staticmethod
    def _format_product(product: dict) -> dict:
        """Format dữ liệu 1 sản phẩm: sắp xếp ảnh, tính giảm giá, map màu."""
        if not product:
            return product

        imgs = sorted(product.get("product_images") or [], key=lambda x: x.get("sort_order", 0))
        product["product_images"] = imgs
        product["images"] = imgs

        if not product.get("thumbnail_url"):
            primary = next((img["url"] for img in imgs if img.get("is_primary")), None)
            product["thumbnail_url"] = primary or (imgs[0]["url"] if imgs else "https://placehold.co/600x800/f8f8f8/cccccc?text=GUA")

        price = product.get("price")
        old_price = product.get("old_price")
        if price and old_price and old_price > price:
            product["discount_percent"] = int(100 - (price / old_price * 100))
        else:
            product["discount_percent"] = None

        variants = product.get("product_variants") or []
        for v in variants:
            c_hex = v.get("color_hex")
            if not c_hex or c_hex == "#1a1a1a":
                c_name = (v.get("color_name") or "").lower().strip()
                v["color_hex"] = ProductModel.COLOR_DICT.get(c_name, "#e5e5e5")
        product["product_variants"] = variants

        return product

    @staticmethod
    def fix_missing_slugs() -> int:
        """Backfill slug cho các sản phẩm bị thiếu trong DB (Dùng Admin Client)."""
        db = ProductModel._db_admin()
        fixed = 0
        try:
            res = db.table("products").select("id, name, slug").execute()
            for p in (res.data or []):
                if p.get("slug") and p["slug"] not in ("None", "null", ""):
                    continue
                new_slug = ProductModel.generate_slug(p.get("name", ""))
                if not new_slug:
                    continue
                db.table("products").update({"slug": new_slug}).eq("id", p["id"]).execute()
                fixed += 1
            return fixed
        except Exception as e:
            logger.error(f"[ProductModel.fix_missing_slugs] Gặp sự cố hệ thống: {e}")
            return 0

    @staticmethod
    def fix_missing_barcodes() -> int:
        """Backfill barcode cho các sản phẩm cũ chưa có (Dùng Admin Client)."""
        db = ProductModel._db_admin()
        fixed = 0
        try:
            res = db.table("products").select("id, created_at, barcode").execute()
            for p in (res.data or []):
                if p.get("barcode"):
                    continue
                created = p.get("created_at", "")
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    prefix = f"GUA-{dt.strftime('%y%m')}"
                except Exception:
                    prefix = f"GUA-{datetime.now().strftime('%y%m')}"

                hex_part = p["id"].replace("-", "")[:6].upper()
                barcode = f"{prefix}-{hex_part}"
                db.table("products").update({"barcode": barcode}).eq("id", p["id"]).execute()
                fixed += 1
            return fixed
        except Exception as e:
            logger.error(f"[ProductModel.fix_missing_barcodes] Gặp sự cố hệ thống: {e}")
            return 0

    # ═══════════════════════════════════════════════════════════════
    #  READ (DÙNG PUBLIC CLIENT CHO STOREFRONT CÔNG KHAI)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_categories(limit: int = 3) -> list:
        db = ProductModel._db()
        try:
            res = db.table("categories").select("*").limit(limit).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Lỗi get_categories: {e}")
            return []

    @staticmethod
    def get_featured(limit: int = 8) -> list:
        db = ProductModel._db()
        try:
            res = (
                db.table("products")
                .select("*, categories(name, slug), product_images(*), product_variants(*)")
                .is_("deleted_at", "null")
                .eq("is_active", True)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return [ProductModel._format_product(item) for item in (res.data or [])]
        except Exception as e:
            logger.error(f"Lỗi get_featured: {e}")
            return []

    @staticmethod
    def get_all(
        page: int = 1,
        per_page: int = 12,
        category_slug: str = None,
        gender: str = None,
        keyword: str = None,
        admin_mode: bool = False,
    ) -> dict:
        # Nếu ở admin_mode, dùng thẳng admin client để kéo toàn bộ sản phẩm bất kể RLS
        db = ProductModel._db_admin() if admin_mode else ProductModel._db()
        offset = (page - 1) * per_page
        try:
            query = db.table("products").select(
                "*, categories(name, slug), product_variants(*), product_images(*)", count="exact"
            )
            if not admin_mode:
                query = query.is_("deleted_at", "null").eq("is_active", True)

            if category_slug:
                try:
                    cat_res = db.table("categories").select("id").eq("slug", category_slug).limit(1).execute()
                    if cat_res.data:
                        query = query.eq("category_id", cat_res.data[0]["id"])
                    else:
                        return {"items": [], "total": 0, "page": page, "per_page": per_page}
                except Exception as cat_err:
                    logger.error(f"Lỗi resolve category_slug '{category_slug}': {cat_err}")

            if gender:
                query = query.eq("gender", gender)
            if keyword:
                query = query.ilike("name", f"%{keyword}%")

            res = query.order("created_at", desc=True).range(offset, offset + per_page - 1).execute()
            return {
                "items": [ProductModel._format_product(item) for item in (res.data or [])],
                "total": res.count or 0,
                "page": page,
                "per_page": per_page,
            }
        except Exception as e:
            logger.error(f"Lỗi get_all products: {e}")
            return {"items": [], "total": 0, "page": page, "per_page": per_page}

    @staticmethod
    def get_by_id(pid: str):
        if not pid:
            return None
        db = ProductModel._db()
        try:
            res = (
                db.table("products")
                .select("*, categories(name, slug), product_images(*), product_variants(*)")
                .eq("id", str(pid).strip())
                .limit(1)
                .execute()
            )
            return ProductModel._format_product(res.data[0]) if res.data else None
        except Exception as e:
            logger.error(f"Lỗi get_by_id product '{pid}': {e}")
            return None

    @staticmethod
    def get_by_slug(slug: str):
        if not slug or slug in ("None", "null", "undefined", ""):
            return None
        db = ProductModel._db()
        try:
            res = (
                db.table("products")
                .select("*, categories(name, slug), product_images(*), product_variants(*)")
                .eq("slug", slug)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            return ProductModel._format_product(res.data[0]) if res.data else None
        except Exception as e:
            logger.error(f"Lỗi get_by_slug '{slug}': {e}")
            return None

    @staticmethod
    def get_by_barcode(barcode: str):
        """Tìm sản phẩm theo mã vạch — phục vụ hệ thống POS scan tại quầy."""
        if not barcode:
            return None
        db = ProductModel._db_admin() # Dùng admin client đề phòng nhân viên quét tại quầy POS bị dính RLS công khai
        try:
            res = (
                db.table("products")
                .select("*, product_variants(*)")
                .eq("barcode", barcode.strip().upper())
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            return ProductModel._format_product(res.data[0]) if res.data else None
        except Exception as e:
            logger.error(f"Lỗi get_by_barcode '{barcode}': {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    #  WRITE (DÙNG ADMIN CLIENT ĐỂ BYPASS RLS CHO DASHBOARD WORKSPACE)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def create(data: dict) -> dict:
        db = ProductModel._db_admin()
        if not data.get("slug") and data.get("name"):
            data["slug"] = ProductModel.generate_slug(data["name"])
        try:
            res = db.table("products").insert(data).execute()
            if not res.data:
                logger.error("[ProductModel.create] Thất bại! Không có dữ liệu trả về từ Supabase.")
                return None

            product = res.data[0]
            pid = product["id"]

            barcode = ProductModel.generate_barcode(pid)
            bc_res = db.table("products").update({"barcode": barcode}).eq("id", pid).execute()
            
            if bc_res.data:
                product["barcode"] = barcode
            else:
                logger.warning(f"[ProductModel.create] Không thể ghi đè Barcode tự động cho ID '{pid}'.")

            return product
        except Exception as e:
            logger.error(f"Lỗi tạo sản phẩm: {e}")
            return None

    @staticmethod
    def update(pid: str, data: dict) -> bool:
        """Cập nhật thông tin sản phẩm (Bypass RLS an toàn)."""
        if not pid:
            return False
            
        # Làm sạch dữ liệu payload rác đầu vào
        if "slug" in data and not data["slug"]:
            data.pop("slug")
        if "thumbnail_url" in data and not data["thumbnail_url"]:
            data.pop("thumbnail_url")
            
        data.pop("barcode", None) # Không cho phép tự ý viết đè mã Barcode gốc hệ thống
        clean_pid = str(pid).strip()
        db = ProductModel._db_admin()

        try:
            res = db.table("products").update(data).eq("id", clean_pid).execute()
            if not res.data:
                logger.warning(f"[ProductModel.update] Không tìm thấy dòng hoặc bị RLS chặn tại ID '{clean_pid}'")
                return False
            return True
        except Exception as e:
            logger.error(f"Lỗi cập nhật sản phẩm '{pid}': {e}")
            return False

    @staticmethod
    def delete(pid: str, permanent: bool = False) -> bool:
        """Xóa sản phẩm hệ thống (Mặc định là Soft Delete để bảo toàn liên kết khóa ngoại đơn hàng)."""
        db = ProductModel._db_admin()
        clean_pid = str(pid).strip()
        try:
            if permanent:
                res = db.table("products").delete().eq("id", clean_pid).execute()
            else:
                res = db.table("products").update({
                    "deleted_at": datetime.now().isoformat(),
                    "is_active": False,
                }).eq("id", clean_pid).execute()
                
            if not res.data:
                logger.warning(f"[ProductModel.delete] Không thể xóa hoặc cập nhật dòng cho ID '{clean_pid}'.")
                return False
            return True
        except Exception as e:
            logger.error(f"Lỗi xóa sản phẩm '{pid}': {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    #  IMAGES MANAGEMENT (QUẢN LÝ THƯ VIỆN ẢNH)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_images(pid: str) -> list:
        try:
            res = (
                ProductModel._db()
                .table("product_images")
                .select("*")
                .eq("product_id", str(pid).strip())
                .order("sort_order")
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"Lỗi get_images '{pid}': {e}")
            return []

    @staticmethod
    def sync_images(pid: str, urls: list) -> bool:
        """Đồng bộ danh sách hình ảnh sản phẩm (Xóa cũ, ghi đè mới bằng quyền Admin)."""
        db = ProductModel._db_admin()
        clean_pid = str(pid).strip()
        try:
            db.table("product_images").delete().eq("product_id", clean_pid).execute()
            if urls:
                db.table("product_images").insert([
                    {"product_id": clean_pid, "url": url, "sort_order": i, "is_primary": (i == 0)}
                    for i, url in enumerate(urls)
                ]).execute()
            return True
        except Exception as e:
            logger.error(f"Lỗi sync_images '{pid}': {e}")
            return False

    @staticmethod
    def upload_to_storage(file_bytes: bytes, filename: str, content_type: str) -> str:
        """Đẩy tệp tin hình ảnh lên Bucket Storage của Supabase."""
        db = ProductModel._db_admin()
        try:
            path = f"products/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            db.storage.from_("products").upload(path, file_bytes, {"content-type": content_type})
            return db.storage.from_("products").get_public_url(path)
        except Exception as e:
            logger.error(f"Lỗi upload storage: {e}")
            return ""