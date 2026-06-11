"""app/models/product_model.py"""
import logging
import re
import uuid
from datetime import datetime
from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)


# Select dùng chung cho storefront.
# Lưu ý:
# - product_categories(categories(...)) dùng cho quan hệ nhiều-nhiều danh mục.
# - collection_products(collections(...)) dùng cho quan hệ nhiều-nhiều bộ sưu tập.
_SELECT_STOREFRONT = (
    "*, "
    "product_categories(categories(id, name, slug)), "
    "collection_products(collections(id, name, slug)), "
    "product_images(*), "
    "product_variants(*)"
)

_VIET_SLUGMAP = [
    (r"[áàảãạăắằẳẵặâấầẩẫậ]", "a"),
    (r"[éèẻẽẹêếềểễệ]", "e"),
    (r"[íìỉĩị]", "i"),
    (r"[óòỏõọôốồổỗộơớờởỡợ]", "o"),
    (r"[úùủũụưứừửữự]", "u"),
    (r"[ýỳỷỹỵ]", "y"),
    (r"[đ]", "d"),
]

COLOR_MAP = {
    "đen": "#000000",
    "black": "#000000",
    "trắng": "#ffffff",
    "white": "#ffffff",
    "đỏ": "#dc2626",
    "red": "#dc2626",
    "xanh dương": "#2563eb",
    "blue": "#2563eb",
    "xanh navy": "#1e3a8a",
    "navy": "#1e3a8a",
    "xanh lá": "#16a34a",
    "green": "#16a34a",
    "vàng": "#eab308",
    "yellow": "#eab308",
    "cam": "#ea580c",
    "orange": "#ea580c",
    "hồng": "#ec4899",
    "pink": "#ec4899",
    "tím": "#9333ea",
    "purple": "#9333ea",
    "xám": "#6b7280",
    "gray": "#6b7280",
    "grey": "#6b7280",
    "nâu": "#78350f",
    "brown": "#78350f",
    "be": "#f5f5dc",
    "beige": "#f5f5dc",
    "kem": "#fef3c7",
    "cream": "#fef3c7",
}


class ProductModel:
    @staticmethod
    def _db():
        return get_supabase()

    @staticmethod
    def _db_admin():
        return get_supabase_admin()

    # ───────────────────────────────────────────────────────
    # Utilities
    # ───────────────────────────────────────────────────────

    @staticmethod
    def generate_slug(name: str) -> str:
        if not name:
            return ""

        s = name.lower().strip()

        for pattern, replacement in _VIET_SLUGMAP:
            s = re.sub(pattern, replacement, s)

        s = re.sub(r"[^a-z0-9\s-]", "", s)
        s = re.sub(r"[\s-]+", "-", s).strip("-")

        return s

    @staticmethod
    def generate_barcode(product_id: str = None) -> str:
        prefix = f"GUA-{datetime.now().strftime('%y%m')}"
        hex_part = (
            str(product_id).replace("-", "")[:6].upper()
            if product_id
            else uuid.uuid4().hex[:6].upper()
        )

        return f"{prefix}-{hex_part}"

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value or default)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        try:
            return int(value or default)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _format_product(p: dict) -> dict:
        """
        Chuẩn hóa dữ liệu product để template dùng ổn định hơn.

        Bổ sung:
        - product_images / images
        - thumbnail_url fallback
        - categories từ product_categories
        - collections từ collection_products
        - discount_percent
        - total_stock
        - is_featured boolean
        """
        if not p:
            return p

        # ── Images ─────────────────────────────────────────
        images = sorted(
            p.get("product_images") or [],
            key=lambda x: x.get("sort_order", 0) if isinstance(x, dict) else 0,
        )

        p["product_images"] = images
        p["images"] = images

        if not p.get("thumbnail_url"):
            primary_url = next(
                (
                    img.get("url")
                    for img in images
                    if isinstance(img, dict) and img.get("is_primary") and img.get("url")
                ),
                None,
            )

            first_url = next(
                (
                    img.get("url")
                    for img in images
                    if isinstance(img, dict) and img.get("url")
                ),
                None,
            )

            p["thumbnail_url"] = (
                primary_url
                or first_url
                or "https://placehold.co/600x800/f8f8f8/ccc?text=GUAMAISON"
            )

        # ── Categories từ bảng N-N product_categories ───────
        product_categories = p.get("product_categories") or []
        category_list = []

        for row in product_categories:
            if not isinstance(row, dict):
                continue

            cat = row.get("categories")
            if isinstance(cat, dict):
                category_list.append(cat)

        p["category_list"] = category_list

        # Cho template dùng product.categories.name nếu cần.
        if category_list and not p.get("categories"):
            p["categories"] = category_list[0]

        # ── Collections từ bảng N-N collection_products ─────
        collection_products = p.get("collection_products") or []
        collection_list = []

        for row in collection_products:
            if not isinstance(row, dict):
                continue

            collection = row.get("collections")
            if isinstance(collection, dict):
                collection_list.append(collection)

        p["collection_list"] = collection_list

        if collection_list and not p.get("collections"):
            p["collections"] = collection_list[0]

        # ── Price / discount ───────────────────────────────
        price = ProductModel._safe_float(p.get("price"))
        old_price = ProductModel._safe_float(
            p.get("old_price")
            or p.get("compare_at_price")
            or p.get("original_price")
        )

        if old_price > price > 0:
            p["discount_percent"] = int(100 - price / old_price * 100)
        else:
            p["discount_percent"] = None

        # ── Variants color + stock ─────────────────────────
        variants = p.get("product_variants") or []
        total_variant_stock = 0
        has_variant_stock = False

        for variant in variants:
            if not isinstance(variant, dict):
                continue

            color_name = (variant.get("color_name") or "").lower().strip()

            if not variant.get("color_hex") or variant.get("color_hex") == "#1a1a1a":
                variant["color_hex"] = COLOR_MAP.get(color_name, "#e5e5e5")

            if "stock" in variant:
                total_variant_stock += ProductModel._safe_int(variant.get("stock"))
                has_variant_stock = True

        if has_variant_stock:
            p["total_stock"] = total_variant_stock
        else:
            p["total_stock"] = ProductModel._safe_int(
                p.get("stock") or p.get("stock_quantity")
            )

        # ── Boolean normalize ──────────────────────────────
        p["is_active"] = bool(p.get("is_active"))
        p["is_featured"] = bool(p.get("is_featured"))

        return p

    # ───────────────────────────────────────────────────────
    # Read
    # ───────────────────────────────────────────────────────

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

        Hỗ trợ:
        - category_slug
        - collection_slug
        - gender
        - keyword
        - admin_mode
        """
        db = ProductModel._db_admin() if admin_mode else ProductModel._db()

        page = max(ProductModel._safe_int(page, 1), 1)
        per_page = max(ProductModel._safe_int(per_page, 12), 1)
        offset = (page - 1) * per_page

        empty = {
            "items": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
        }

        try:
            query = db.table("products").select(_SELECT_STOREFRONT, count="exact")

            if not admin_mode:
                query = query.is_("deleted_at", "null").eq("is_active", True)

            # Lọc theo danh mục, bao gồm danh mục con.
            if category_slug:
                cat = (
                    db.table("categories")
                    .select("id")
                    .eq("slug", category_slug)
                    .limit(1)
                    .execute()
                )

                if not cat.data:
                    return empty

                cat_id = cat.data[0]["id"]

                children = (
                    db.table("categories")
                    .select("id")
                    .eq("parent_id", cat_id)
                    .execute()
                )

                category_ids = [cat_id] + [c["id"] for c in (children.data or [])]

                product_category_rows = (
                    db.table("product_categories")
                    .select("product_id")
                    .in_("category_id", category_ids)
                    .execute()
                )

                product_ids = list(
                    {row["product_id"] for row in (product_category_rows.data or [])}
                )

                if not product_ids:
                    return empty

                query = query.in_("id", product_ids)

            # Lọc theo bộ sưu tập.
            if collection_slug:
                collection = (
                    db.table("collections")
                    .select("id")
                    .eq("slug", collection_slug)
                    .eq("is_active", True)
                    .limit(1)
                    .execute()
                )

                if not collection.data:
                    return empty

                collection_id = collection.data[0]["id"]

                collection_product_rows = (
                    db.table("collection_products")
                    .select("product_id")
                    .eq("collection_id", collection_id)
                    .execute()
                )

                product_ids = list(
                    {row["product_id"] for row in (collection_product_rows.data or [])}
                )

                if not product_ids:
                    return empty

                query = query.in_("id", product_ids)

            if gender:
                query = query.eq("gender", gender)

            if keyword:
                query = query.ilike("name", f"%{keyword.strip()}%")

            res = (
                query.order("created_at", desc=True)
                .range(offset, offset + per_page - 1)
                .execute()
            )

            return {
                "items": [ProductModel._format_product(p) for p in (res.data or [])],
                "total": res.count or 0,
                "page": page,
                "per_page": per_page,
            }

        except Exception as e:
            logger.error(f"ProductModel.get_all: {e}")
            return empty

    @staticmethod
    def get_featured(limit: int = 8) -> list:
        """
        Lấy sản phẩm nổi bật cho storefront / _featured.html.

        Điều kiện:
        - deleted_at IS NULL
        - is_active = true
        - is_featured = true
        """
        limit = max(ProductModel._safe_int(limit, 8), 1)

        try:
            res = (
                ProductModel._db()
                .table("products")
                .select(_SELECT_STOREFRONT)
                .is_("deleted_at", "null")
                .eq("is_active", True)
                .eq("is_featured", True)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            return [ProductModel._format_product(p) for p in (res.data or [])]

        except Exception as e:
            logger.error(f"ProductModel.get_featured: {e}")
            return []

    @staticmethod
    def get_featured_products(limit: int = 10) -> list:
        """
        Alias rõ nghĩa cho trang chủ.

        Controller trang chủ nên truyền:
            featured_products = ProductModel.get_featured_products(limit=10)
        """
        return ProductModel.get_featured(limit=limit)

    @staticmethod
    def get_by_slug(slug: str):
        if not slug or slug in ("None", "null", "undefined", ""):
            return None

        try:
            res = (
                ProductModel._db()
                .table("products")
                .select(_SELECT_STOREFRONT)
                .eq("slug", slug)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )

            return ProductModel._format_product(res.data[0]) if res.data else None

        except Exception as e:
            logger.error(f"ProductModel.get_by_slug '{slug}': {e}")
            return None

    @staticmethod
    def get_by_id(pid: str):
        if not pid:
            return None

        db = ProductModel._db_admin()
        product_id = str(pid).strip()

        try:
            res = (
                db.table("products")
                .select("*, product_images(*), product_variants(*)")
                .eq("id", product_id)
                .limit(1)
                .execute()
            )

            if not res.data:
                return None

            product = res.data[0]

            cats = (
                db.table("product_categories")
                .select("category_id")
                .eq("product_id", product["id"])
                .execute()
            )

            colls = (
                db.table("collection_products")
                .select("collection_id")
                .eq("product_id", product["id"])
                .execute()
            )

            product["category_ids"] = [
                c["category_id"] for c in (cats.data or []) if c.get("category_id")
            ]

            product["collection_ids"] = [
                c["collection_id"] for c in (colls.data or []) if c.get("collection_id")
            ]

            return ProductModel._format_product(product)

        except Exception as e:
            logger.error(f"ProductModel.get_by_id '{pid}': {e}")
            return None

    @staticmethod
    def get_by_barcode(barcode: str):
        if not barcode:
            return None

        try:
            res = (
                ProductModel._db_admin()
                .table("products")
                .select("*, product_variants(*)")
                .eq("barcode", barcode.strip().upper())
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )

            return ProductModel._format_product(res.data[0]) if res.data else None

        except Exception as e:
            logger.error(f"ProductModel.get_by_barcode '{barcode}': {e}")
            return None

    @staticmethod
    def get_categories(limit: int = 3) -> list:
        try:
            res = (
                ProductModel._db()
                .table("categories")
                .select("*")
                .limit(limit)
                .execute()
            )

            return res.data or []

        except Exception as e:
            logger.error(f"ProductModel.get_categories: {e}")
            return []

    # ───────────────────────────────────────────────────────
    # Write
    # ───────────────────────────────────────────────────────

    @staticmethod
    def create(data: dict) -> dict:
        db = ProductModel._db_admin()

        if not data:
            return None

        if not data.get("slug") and data.get("name"):
            data["slug"] = ProductModel.generate_slug(data["name"])

        try:
            res = db.table("products").insert(data).execute()

            if not res.data:
                logger.error("ProductModel.create: Supabase không trả về dữ liệu.")
                return None

            product = res.data[0]
            product_id = product["id"]

            barcode = ProductModel.generate_barcode(product_id)

            barcode_res = (
                db.table("products")
                .update({"barcode": barcode})
                .eq("id", product_id)
                .execute()
            )

            if barcode_res.data:
                product["barcode"] = barcode_res.data[0].get("barcode", barcode)
            else:
                product["barcode"] = barcode

            return product

        except Exception as e:
            logger.error(f"ProductModel.create: {e}")
            return None

    @staticmethod
    def update(pid: str, data: dict) -> bool:
        if not pid or not data:
            return False

        product_id = str(pid).strip()

        clean_data = {
            key: value
            for key, value in data.items()
            if key not in ("barcode",) and value is not None
        }

        if not clean_data.get("slug"):
            clean_data.pop("slug", None)

        if not clean_data.get("thumbnail_url"):
            clean_data.pop("thumbnail_url", None)

        try:
            (
                ProductModel._db_admin()
                .table("products")
                .update(clean_data)
                .eq("id", product_id)
                .execute()
            )

            return True

        except Exception as e:
            logger.error(f"ProductModel.update '{pid}': {e}")
            return False

    @staticmethod
    def delete(pid: str, permanent: bool = False) -> bool:
        if not pid:
            return False

        db = ProductModel._db_admin()
        product_id = str(pid).strip()

        try:
            if permanent:
                res = db.table("products").delete().eq("id", product_id).execute()
            else:
                res = (
                    db.table("products")
                    .update(
                        {
                            "deleted_at": datetime.now().isoformat(),
                            "is_active": False,
                        }
                    )
                    .eq("id", product_id)
                    .execute()
                )

            return bool(res.data)

        except Exception as e:
            logger.error(f"ProductModel.delete '{pid}': {e}")
            return False

    @staticmethod
    def sync_categories(pid: str, category_ids: list) -> bool:
        if not pid:
            return False

        db = ProductModel._db_admin()
        product_id = str(pid).strip()

        try:
            db.table("product_categories").delete().eq("product_id", product_id).execute()

            if category_ids:
                rows = [
                    {"product_id": product_id, "category_id": cid}
                    for cid in category_ids
                    if cid
                ]

                if rows:
                    db.table("product_categories").insert(rows).execute()

            return True

        except Exception as e:
            logger.error(f"ProductModel.sync_categories '{pid}': {e}")
            return False

    @staticmethod
    def sync_collections(pid: str, collection_ids: list) -> bool:
        if not pid:
            return False

        db = ProductModel._db_admin()
        product_id = str(pid).strip()

        try:
            db.table("collection_products").delete().eq("product_id", product_id).execute()

            if collection_ids:
                rows = [
                    {"product_id": product_id, "collection_id": cid}
                    for cid in collection_ids
                    if cid
                ]

                if rows:
                    db.table("collection_products").insert(rows).execute()

            return True

        except Exception as e:
            logger.error(f"ProductModel.sync_collections '{pid}': {e}")
            return False

    # ───────────────────────────────────────────────────────
    # Images
    # ───────────────────────────────────────────────────────

    @staticmethod
    def get_images(pid: str) -> list:
        if not pid:
            return []

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
            logger.error(f"ProductModel.get_images '{pid}': {e}")
            return []

    @staticmethod
    def sync_images(pid: str, urls: list) -> bool:
        if not pid:
            return False

        db = ProductModel._db_admin()
        product_id = str(pid).strip()

        try:
            db.table("product_images").delete().eq("product_id", product_id).execute()

            if urls:
                rows = [
                    {
                        "product_id": product_id,
                        "url": url,
                        "sort_order": index,
                        "is_primary": index == 0,
                    }
                    for index, url in enumerate(urls)
                    if url
                ]

                if rows:
                    db.table("product_images").insert(rows).execute()

            return True

        except Exception as e:
            logger.error(f"ProductModel.sync_images '{pid}': {e}")
            return False

    @staticmethod
    def upload_to_storage(file_bytes: bytes, filename: str, content_type: str) -> str:
        db = ProductModel._db_admin()

        try:
            safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename or "product")
            path = f"products/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_filename}"

            db.storage.from_("store-assets").upload(
                path,
                file_bytes,
                {"content-type": content_type},
            )

            return db.storage.from_("store-assets").get_public_url(path)

        except Exception as e:
            logger.error(f"ProductModel.upload_to_storage: {e}")
            return ""

    # ───────────────────────────────────────────────────────
    # Backfills / admin utils
    # ───────────────────────────────────────────────────────

    @staticmethod
    def fix_missing_slugs() -> int:
        db = ProductModel._db_admin()
        fixed = 0

        try:
            res = db.table("products").select("id, name, slug").execute()

            for product in res.data or []:
                slug = product.get("slug")

                if slug and slug not in ("None", "null", ""):
                    continue

                new_slug = ProductModel.generate_slug(product.get("name", ""))

                if new_slug:
                    db.table("products").update({"slug": new_slug}).eq(
                        "id", product["id"]
                    ).execute()
                    fixed += 1

        except Exception as e:
            logger.error(f"ProductModel.fix_missing_slugs: {e}")

        return fixed

    @staticmethod
    def fix_missing_barcodes() -> int:
        db = ProductModel._db_admin()
        fixed = 0

        try:
            res = db.table("products").select("id, created_at, barcode").execute()

            for product in res.data or []:
                if product.get("barcode"):
                    continue

                try:
                    created_at = product.get("created_at", "")
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    prefix = f"GUA-{dt.strftime('%y%m')}"
                except Exception:
                    prefix = f"GUA-{datetime.now().strftime('%y%m')}"

                barcode = f"{prefix}-{product['id'].replace('-', '')[:6].upper()}"

                db.table("products").update({"barcode": barcode}).eq(
                    "id", product["id"]
                ).execute()

                fixed += 1

        except Exception as e:
            logger.error(f"ProductModel.fix_missing_barcodes: {e}")

        return fixed