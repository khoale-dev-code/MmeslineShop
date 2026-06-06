"""app/models/product_model.py"""
import logging
import re
import uuid
from datetime import datetime
from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)

# Chọn join string dùng ở nhiều hàm — định nghĩa 1 lần
_SELECT_STOREFRONT = (
    "*, "
    "product_categories(categories(name, slug)), "
    "collection_products(collections(name, slug)), "
    "product_images(*), product_variants(*)"
)

_VIET_SLUGMAP = [
    (r'[áàảãạăắằẳẵặâấầẩẫậ]', 'a'), (r'[éèẻẽẹêếềểễệ]', 'e'),
    (r'[íìỉĩị]', 'i'),              (r'[óòỏõọôốồổỗộơớờởỡợ]', 'o'),
    (r'[úùủũụưứừửữự]', 'u'),       (r'[ýỳỷỹỵ]', 'y'),
    (r'[đ]', 'd'),
]

COLOR_MAP = {
    'đen': '#000000', 'black': '#000000', 'trắng': '#ffffff', 'white': '#ffffff',
    'đỏ': '#dc2626',  'red': '#dc2626',   'xanh dương': '#2563eb', 'blue': '#2563eb',
    'xanh navy': '#1e3a8a', 'navy': '#1e3a8a', 'xanh lá': '#16a34a', 'green': '#16a34a',
    'vàng': '#eab308', 'yellow': '#eab308', 'cam': '#ea580c', 'orange': '#ea580c',
    'hồng': '#ec4899', 'pink': '#ec4899',   'tím': '#9333ea', 'purple': '#9333ea',
    'xám': '#6b7280',  'gray': '#6b7280',   'grey': '#6b7280',
    'nâu': '#78350f',  'brown': '#78350f',  'be': '#f5f5dc', 'beige': '#f5f5dc',
    'kem': '#fef3c7',  'cream': '#fef3c7',
}


class ProductModel:

    @staticmethod
    def _db():        return get_supabase()
    @staticmethod
    def _db_admin():  return get_supabase_admin()

    # ── Utilities ────────────────────────────────────────────────────────────

    @staticmethod
    def generate_slug(name: str) -> str:
        if not name:
            return ""
        s = name.lower()
        for pat, rep in _VIET_SLUGMAP:
            s = re.sub(pat, rep, s)
        s = re.sub(r'[^a-z0-9\s-]', '', s)
        return re.sub(r'[\s-]+', '-', s).strip('-')

    @staticmethod
    def generate_barcode(product_id: str = None) -> str:
        prefix   = f"GUA-{datetime.now().strftime('%y%m')}"
        hex_part = (str(product_id).replace("-", "")[:6].upper()
                    if product_id else uuid.uuid4().hex[:6].upper())
        return f"{prefix}-{hex_part}"

    @staticmethod
    def _format_product(p: dict) -> dict:
        if not p:
            return p

        imgs = sorted(p.get("product_images") or [], key=lambda x: x.get("sort_order", 0))
        p["product_images"] = p["images"] = imgs

        if not p.get("thumbnail_url"):
            primary = next((i["url"] for i in imgs if i.get("is_primary")), None)
            p["thumbnail_url"] = primary or (imgs[0]["url"] if imgs
                                 else "https://placehold.co/600x800/f8f8f8/ccc?text=GUA")

        price, old = p.get("price"), p.get("old_price")
        p["discount_percent"] = int(100 - price / old * 100) if price and old and old > price else None

        for v in (p.get("product_variants") or []):
            if not v.get("color_hex") or v["color_hex"] == "#1a1a1a":
                v["color_hex"] = COLOR_MAP.get((v.get("color_name") or "").lower().strip(), "#e5e5e5")

        return p

    # ── Read ─────────────────────────────────────────────────────────────────

    @staticmethod
    def get_all(
        page: int = 1,
        per_page: int = 12,
        category_slug: str = None,
        collection_slug: str = None,
        gender: str = None,
        keyword: str = None,
        admin_mode: bool = False,
    ) -> dict:
        """
        Lấy danh sách sản phẩm có phân trang + lọc.
        Hỗ trợ lọc đồng thời category_slug VÀ collection_slug.
        """
        db     = ProductModel._db_admin() if admin_mode else ProductModel._db()
        offset = (page - 1) * per_page
        empty  = {"items": [], "total": 0, "page": page, "per_page": per_page}

        try:
            query = db.table("products").select(_SELECT_STOREFRONT, count="exact")
            if not admin_mode:
                query = query.is_("deleted_at", "null").eq("is_active", True)

            # Lọc theo danh mục (N-N, bao gồm danh mục con)
            if category_slug:
                cat = db.table("categories").select("id").eq("slug", category_slug).limit(1).execute()
                if not cat.data:
                    return empty
                cat_id = cat.data[0]["id"]

                children = db.table("categories").select("id").eq("parent_id", cat_id).execute()
                all_ids  = [cat_id] + [c["id"] for c in (children.data or [])]

                pc = db.table("product_categories").select("product_id").in_("category_id", all_ids).execute()
                pids = list({r["product_id"] for r in (pc.data or [])})
                if not pids:
                    return empty
                query = query.in_("id", pids)

            # Lọc theo bộ sưu tập (N-N)
            if collection_slug:
                coll = (db.table("collections").select("id")
                          .eq("slug", collection_slug).eq("is_active", True)
                          .limit(1).execute())
                if not coll.data:
                    return empty
                coll_id = coll.data[0]["id"]

                cp = db.table("collection_products").select("product_id").eq("collection_id", coll_id).execute()
                pids = list({r["product_id"] for r in (cp.data or [])})
                if not pids:
                    return empty
                query = query.in_("id", pids)

            if gender:   query = query.eq("gender", gender)
            if keyword:  query = query.ilike("name", f"%{keyword}%")

            res = query.order("created_at", desc=True).range(offset, offset + per_page - 1).execute()
            return {
                "items":    [ProductModel._format_product(p) for p in (res.data or [])],
                "total":    res.count or 0,
                "page":     page,
                "per_page": per_page,
            }
        except Exception as e:
            logger.error(f"ProductModel.get_all: {e}")
            return empty

    @staticmethod
    def get_featured(limit: int = 8) -> list:
        try:
            res = (ProductModel._db().table("products")
                   .select(_SELECT_STOREFRONT)
                   .is_("deleted_at", "null").eq("is_active", True)
                   .order("created_at", desc=True).limit(limit).execute())
            return [ProductModel._format_product(p) for p in (res.data or [])]
        except Exception as e:
            logger.error(f"get_featured: {e}")
            return []

    @staticmethod
    def get_by_slug(slug: str):
        if not slug or slug in ("None", "null", "undefined", ""):
            return None
        try:
            res = (ProductModel._db().table("products")
                   .select(_SELECT_STOREFRONT)
                   .eq("slug", slug).is_("deleted_at", "null")
                   .limit(1).execute())
            return ProductModel._format_product(res.data[0]) if res.data else None
        except Exception as e:
            logger.error(f"get_by_slug '{slug}': {e}")
            return None

    @staticmethod
    def get_by_id(pid: str):
        if not pid:
            return None
        db = ProductModel._db_admin()
        try:
            res = (db.table("products")
                   .select("*, product_images(*), product_variants(*)")
                   .eq("id", str(pid).strip()).limit(1).execute())
            if not res.data:
                return None
            p = res.data[0]

            cats  = db.table("product_categories").select("category_id").eq("product_id", p["id"]).execute()
            colls = db.table("collection_products").select("collection_id").eq("product_id", p["id"]).execute()
            p["category_ids"]   = [c["category_id"]   for c in (cats.data  or [])]
            p["collection_ids"] = [c["collection_id"] for c in (colls.data or [])]
            return ProductModel._format_product(p)
        except Exception as e:
            logger.error(f"get_by_id '{pid}': {e}")
            return None

    @staticmethod
    def get_by_barcode(barcode: str):
        if not barcode:
            return None
        try:
            res = (ProductModel._db_admin().table("products")
                   .select("*, product_variants(*)")
                   .eq("barcode", barcode.strip().upper())
                   .is_("deleted_at", "null").limit(1).execute())
            return ProductModel._format_product(res.data[0]) if res.data else None
        except Exception as e:
            logger.error(f"get_by_barcode '{barcode}': {e}")
            return None

    @staticmethod
    def get_categories(limit: int = 3) -> list:
        try:
            res = ProductModel._db().table("categories").select("*").limit(limit).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"get_categories: {e}")
            return []

    # ── Write ────────────────────────────────────────────────────────────────

    @staticmethod
    def create(data: dict) -> dict:
        db = ProductModel._db_admin()
        if not data.get("slug") and data.get("name"):
            data["slug"] = ProductModel.generate_slug(data["name"])
        try:
            res = db.table("products").insert(data).execute()
            if not res.data:
                logger.error("create: Supabase không trả về dữ liệu.")
                return None
            p   = res.data[0]
            pid = p["id"]
            bc_res = db.table("products").update({"barcode": ProductModel.generate_barcode(pid)}).eq("id", pid).execute()
            if bc_res.data:
                p["barcode"] = bc_res.data[0]["barcode"]
            return p
        except Exception as e:
            logger.error(f"create: {e}")
            return None

    @staticmethod
    def update(pid: str, data: dict) -> bool:
        if not pid:
            return False
        data = {k: v for k, v in data.items() if k not in ("barcode",) and v is not None}
        data.pop("slug", None) if not data.get("slug") else None
        data.pop("thumbnail_url", None) if not data.get("thumbnail_url") else None
        try:
            ProductModel._db_admin().table("products").update(data).eq("id", str(pid).strip()).execute()
            return True
        except Exception as e:
            logger.error(f"update '{pid}': {e}")
            return False

    @staticmethod
    def delete(pid: str, permanent: bool = False) -> bool:
        db  = ProductModel._db_admin()
        cpid = str(pid).strip()
        try:
            if permanent:
                res = db.table("products").delete().eq("id", cpid).execute()
            else:
                res = db.table("products").update({
                    "deleted_at": datetime.now().isoformat(),
                    "is_active": False,
                }).eq("id", cpid).execute()
            return bool(res.data)
        except Exception as e:
            logger.error(f"delete '{pid}': {e}")
            return False

    @staticmethod
    def sync_categories(pid: str, category_ids: list) -> bool:
        db = ProductModel._db_admin()
        try:
            db.table("product_categories").delete().eq("product_id", pid).execute()
            if category_ids:
                db.table("product_categories").insert(
                    [{"product_id": pid, "category_id": cid} for cid in category_ids if cid]
                ).execute()
            return True
        except Exception as e:
            logger.error(f"sync_categories '{pid}': {e}")
            return False

    @staticmethod
    def sync_collections(pid: str, collection_ids: list) -> bool:
        db = ProductModel._db_admin()
        try:
            db.table("collection_products").delete().eq("product_id", pid).execute()
            if collection_ids:
                db.table("collection_products").insert(
                    [{"product_id": pid, "collection_id": cid} for cid in collection_ids if cid]
                ).execute()
            return True
        except Exception as e:
            logger.error(f"sync_collections '{pid}': {e}")
            return False

    # ── Images ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_images(pid: str) -> list:
        try:
            res = (ProductModel._db().table("product_images").select("*")
                   .eq("product_id", str(pid).strip()).order("sort_order").execute())
            return res.data or []
        except Exception as e:
            logger.error(f"get_images '{pid}': {e}")
            return []

    @staticmethod
    def sync_images(pid: str, urls: list) -> bool:
        db   = ProductModel._db_admin()
        cpid = str(pid).strip()
        try:
            db.table("product_images").delete().eq("product_id", cpid).execute()
            if urls:
                db.table("product_images").insert([
                    {"product_id": cpid, "url": url, "sort_order": i, "is_primary": i == 0}
                    for i, url in enumerate(urls)
                ]).execute()
            return True
        except Exception as e:
            logger.error(f"sync_images '{pid}': {e}")
            return False

    @staticmethod
    def upload_to_storage(file_bytes: bytes, filename: str, content_type: str) -> str:
        db = ProductModel._db_admin()
        try:
            path = f"products/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            db.storage.from_("store-assets").upload(path, file_bytes, {"content-type": content_type})
            return db.storage.from_("store-assets").get_public_url(path)
        except Exception as e:
            logger.error(f"upload_to_storage: {e}")
            return ""

    # ── Backfills (admin utils) ───────────────────────────────────────────────

    @staticmethod
    def fix_missing_slugs() -> int:
        db, fixed = ProductModel._db_admin(), 0
        try:
            for p in (db.table("products").select("id, name, slug").execute().data or []):
                if p.get("slug") and p["slug"] not in ("None", "null", ""):
                    continue
                slug = ProductModel.generate_slug(p.get("name", ""))
                if slug:
                    db.table("products").update({"slug": slug}).eq("id", p["id"]).execute()
                    fixed += 1
        except Exception as e:
            logger.error(f"fix_missing_slugs: {e}")
        return fixed

    @staticmethod
    def fix_missing_barcodes() -> int:
        db, fixed = ProductModel._db_admin(), 0
        try:
            for p in (db.table("products").select("id, created_at, barcode").execute().data or []):
                if p.get("barcode"):
                    continue
                try:
                    dt = datetime.fromisoformat(p.get("created_at", "").replace("Z", "+00:00"))
                    prefix = f"GUA-{dt.strftime('%y%m')}"
                except Exception:
                    prefix = f"GUA-{datetime.now().strftime('%y%m')}"
                barcode = f"{prefix}-{p['id'].replace('-', '')[:6].upper()}"
                db.table("products").update({"barcode": barcode}).eq("id", p["id"]).execute()
                fixed += 1
        except Exception as e:
            logger.error(f"fix_missing_barcodes: {e}")
        return fixed