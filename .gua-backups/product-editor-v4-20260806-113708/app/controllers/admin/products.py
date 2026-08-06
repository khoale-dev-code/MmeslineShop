"""
app/controllers/admin/products.py
=================================
Quản lý Admin:
- Products
- Product variants
- Product images
- Categories
- Collections

Đồng bộ với product_form.html mới:
- Giá bán, giá so sánh, giá vốn
- SKU / Barcode
- SEO title / description / keywords
- description_html
- is_active / is_featured / allow_backorder
- Tạo nhanh category / collection trong form sản phẩm
- Variant linh hoạt: size, color, stock, price_override, compare_at_price, cost_price, sku, barcode
- Dùng service_role/admin client cho khu vực admin để tránh RLS
"""

import logging
import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.middleware.auth_required import admin_required
from app.models.category_model import CategoryModel
from app.models.collection_model import CollectionModel
from app.models.navigation_model import NavigationModel
from app.models.product_model import ProductModel
from app.models.product_group_model import ProductGroupModel
from app.utils.supabase_client import get_supabase_admin

from . import admin_bp
from ._helpers import (
    _allowed_file,
    _args,
    _filelist,
    _form,
    _getlist,
    _paginate,
    _total_pages,
    handle_errors,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# BASIC HELPERS
# ═══════════════════════════════════════════════════════════════

def _db_admin():
    return get_supabase_admin()


def _clean_text(value: Any, max_len: int | None = None) -> str:
    text = str(value or "").strip()
    if max_len is not None:
        text = text[:max_len]
    return text


def _parse_vnd(value: Any, default: int = 0) -> int:
    """
    Nhận các dạng:
    - 199000
    - 199.000
    - 199,000
    - 199 000
    - 199.000đ
    """
    if value is None:
        return default

    digits = re.sub(r"[^\d]", "", str(value).strip())
    if not digits:
        return default

    try:
        return int(digits)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0, min_value: int | None = 0) -> int:
    try:
        number = int(float(str(value or "").strip()))
    except Exception:
        number = default

    if min_value is not None:
        number = max(min_value, number)

    return number


def _slugify_vi(value: Any) -> str:
    text = _clean_text(value).lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "item"


def _split_new_names(value: Any) -> list[str]:
    raw = str(value or "")
    parts = re.split(r"[\n,]+", raw)
    return [p.strip() for p in parts if p.strip()]


def _unique_keep_order(values: list[Any]) -> list[Any]:
    seen = set()
    result = []

    for value in values:
        if not value:
            continue

        value = str(value).strip()
        if not value or value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _none_if_empty(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _safe_http_url(value: Any) -> str:
    """Chỉ nhận URL ảnh/video http(s), chặn javascript/data URL từ request sửa tay."""
    value = _clean_text(value, 1000)
    if not value:
        return ""
    parsed = urlparse(value)
    return value if parsed.scheme.lower() in {"http", "https"} and parsed.netloc else ""


def _upper_or_none(value: Any, max_len: int = 80) -> str | None:
    text = _clean_text(value, max_len).upper()
    return text or None


def _get_existing_tags(limit: int = 500) -> list[str]:
    """
    Lấy danh sách tag đã từng dùng từ products.tags để gợi ý ở product_form.
    products.tags có thể là list JSONB hoặc text tùy schema cũ.
    """
    tags: set[str] = set()

    try:
        rows = (
            _db_admin()
            .table("products")
            .select("tags")
            .limit(limit)
            .execute()
            .data
            or []
        )

        for row in rows:
            raw = row.get("tags")

            if isinstance(raw, list):
                for item in raw:
                    text = _clean_text(item, 60)
                    if text:
                        tags.add(text)

            elif isinstance(raw, str):
                for item in re.split(r"[,|;]+", raw):
                    text = _clean_text(item, 60)
                    if text:
                        tags.add(text)

    except Exception as e:
        logger.warning("[products] Không lấy được existing tags: %s", e)

    return sorted(tags, key=lambda x: x.lower())


def _render_product_form(
    *,
    product: dict | None,
    cats: list,
    colles: list,
    tag_options: list[str],
    status_code: int | None = None,
):
    response = render_template(
        "admin/product_form.html",
        product=product,
        cats=cats,
        colles=colles,
        tag_options=tag_options,
    )

    if status_code:
        return response, status_code

    return response


# ═══════════════════════════════════════════════════════════════
# QUICK CREATE CATEGORY / COLLECTION
# ═══════════════════════════════════════════════════════════════

def _get_or_create_category(db, name: str) -> str | None:
    name = _clean_text(name, 120)
    if not name:
        return None

    slug = _slugify_vi(name)

    try:
        existed = (
            db.table("categories")
            .select("id")
            .eq("slug", slug)
            .limit(1)
            .execute()
            .data
            or []
        )
        if existed:
            return existed[0]["id"]

        existed = (
            db.table("categories")
            .select("id")
            .eq("name", name)
            .limit(1)
            .execute()
            .data
            or []
        )
        if existed:
            return existed[0]["id"]

        created = (
            db.table("categories")
            .insert({
                "name": name,
                "slug": slug,
                "description": "",
                "is_active": True,
                "sort_order": 0,
            })
            .execute()
            .data
            or []
        )

        return created[0]["id"] if created else None

    except Exception as e:
        logger.error("[products] Không tạo được category '%s': %s", name, e, exc_info=True)
        return None


def _get_or_create_collection(db, name: str) -> str | None:
    name = _clean_text(name, 120)
    if not name:
        return None

    slug = _slugify_vi(name)
    try:
        existed = (
            db.table("collections").select("id").eq("slug", slug).limit(1).execute().data
            or []
        )
        if existed:
            return existed[0]["id"]
        existed = (
            db.table("collections").select("id").eq("name", name).limit(1).execute().data
            or []
        )
        if existed:
            return existed[0]["id"]
        created = (
            db.table("collections")
            .insert({
                "name": name, "slug": slug, "description": "", "is_active": True,
                "show_on_home": False, "image_url": None, "video_url": None, "sort_order": 0,
            })
            .execute().data
            or []
        )
        return created[0]["id"] if created else None
    except Exception as e:
        logger.error("[products] Không tạo được collection '%s': %s", name, e, exc_info=True)
        return None


def _collection_product_picker(collection_id: str | None = None) -> list[dict]:
    """Danh sách sản phẩm cho màn hình tạo/sửa nhóm sản phẩm."""
    db = _db_admin()
    try:
        products = (
            db.table("products").select("id,name,slug,thumbnail_url,is_active")
            .order("name").limit(2000).execute().data or []
        )
        selected_ids: set[str] = set()
        if collection_id:
            rows = (
                db.table("collection_products").select("product_id")
                .eq("collection_id", collection_id).execute().data or []
            )
            selected_ids = {str(row.get("product_id")) for row in rows if row.get("product_id")}
        for product in products:
            product["selected_in_group"] = str(product.get("id")) in selected_ids
        return products
    except Exception as exc:
        logger.warning("[collections] Không tải được product picker: %s", exc)
        return []


def _collection_group_payload(form: dict) -> dict[str, Any]:
    """Đọc và chuẩn hóa điều kiện nhóm từ form; model sẽ kiểm tra lần cuối."""
    raw_rules: Any = []
    try:
        raw_rules = json.loads(_clean_text(form.get("rules_json"), 12000) or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        raw_rules = []

    return ProductGroupModel.normalize_group({
        "selection_mode": form.get("selection_mode"),
        "match_mode": form.get("match_mode"),
        "rules": raw_rules,
        "template": form.get("template"),
    })


def _collection_form_context(cat: dict | None, product_picker: list[dict], group: dict | None = None) -> dict:
    menu_config = NavigationModel.get_config(force_reload=True)
    collection_id = str((cat or {}).get("id") or "")
    return {
        "cat": cat,
        "collection_products_catalog": product_picker,
        "group_config": group or ProductGroupModel.get_group(collection_id),
        "menu_library": menu_config.get("menus") or [],
        "menu_usage": NavigationModel.find_target_usage(menu_config, "collection", collection_id) if collection_id else [],
    }


def _add_collection_to_menu(collection: dict, form: dict) -> None:
    if "add_to_menu" not in form:
        return
    menu_handle = _clean_text(form.get("menu_handle"), 100)
    if not menu_handle:
        return
    NavigationModel.upsert_target_link(
        menu_handle=menu_handle,
        link_type="collection",
        target_id=str(collection.get("id") or ""),
        label=_clean_text(form.get("menu_label"), 100) or _clean_text(collection.get("name"), 100),
        parent_id=_clean_text(form.get("menu_parent_id"), 100),
    )


def _invalidate_storefront_catalog_cache() -> None:
    """Cho thay đổi nhóm/sản phẩm xuất hiện ngay, không chờ cache storefront hết hạn."""
    try:
        from app.controllers import product_controller
        cache = getattr(product_controller, "_CACHE", None)
        if isinstance(cache, dict):
            cache.clear()
    except Exception as exc:
        logger.debug("[products] Không xóa được product controller cache: %s", exc)
    try:
        from app.context_processors import invalidate_shared_cache
        invalidate_shared_cache()
    except Exception as exc:
        logger.debug("[products] Không xóa được shared context cache: %s", exc)


def _sync_collection_members(collection_id: str) -> int:
    db = _db_admin()
    product_ids = _unique_keep_order(
        request.form.getlist("product_ids[]") or request.form.getlist("product_ids")
    )[:2000]
    if product_ids:
        valid_ids: set[str] = set()
        for start in range(0, len(product_ids), 200):
            valid_rows = (
                db.table("products").select("id")
                .in_("id", product_ids[start:start + 200]).execute().data or []
            )
            valid_ids.update(str(row.get("id")) for row in valid_rows if row.get("id"))
        product_ids = [product_id for product_id in product_ids if product_id in valid_ids]
    db.table("collection_products").delete().eq("collection_id", collection_id).execute()
    for start in range(0, len(product_ids), 200):
        db.table("collection_products").insert([
            {"collection_id": collection_id, "product_id": product_id}
            for product_id in product_ids[start:start + 200]
        ]).execute()
    return len(product_ids)


# ═══════════════════════════════════════════════════════════════
# PRODUCT FORM PARSING
# ═══════════════════════════════════════════════════════════════

def _parse_tags(value: Any) -> list[str]:
    if not value:
        return []

    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[,|;]+", str(value))

    result = []
    seen = set()

    for raw in raw_items:
        tag = _clean_text(raw, 60)
        if not tag:
            continue

        key = tag.lower()
        if key in seen:
            continue

        seen.add(key)
        result.append(tag)

    return result


def _product_data_from_form(form: dict) -> dict:
    name = _clean_text(form.get("name"), 180)

    slug = _clean_text(form.get("slug"), 180)
    if not slug and name:
        try:
            slug = ProductModel.generate_slug(name)
        except Exception:
            slug = _slugify_vi(name)

    price = _parse_vnd(form.get("price"), default=0)
    compare_at_price = _parse_vnd(form.get("compare_at_price"), default=0)
    cost_price = _parse_vnd(form.get("cost_price"), default=0)

    # Giá so sánh chỉ hợp lệ khi lớn hơn giá bán.
    if compare_at_price and price and compare_at_price <= price:
        compare_at_price = 0

    description_html = form.get("description") or form.get("description_html") or ""

    seo_title = _clean_text(form.get("seo_title") or form.get("meta_title"), 70)
    seo_description = _clean_text(form.get("seo_description") or form.get("meta_description"), 170)
    seo_keywords = _clean_text(form.get("seo_keywords"), 255)
    search_keywords = _clean_text(form.get("search_keywords"), 255) or seo_keywords

    payload = {
        "name": name,
        "slug": slug,
        "description": description_html,
        "description_html": description_html,

        "price": price,
        "compare_at_price": compare_at_price or None,
        "cost_price": cost_price or None,

        # SKU / barcode rỗng phải là None để tránh lỗi UNIQUE với chuỗi rỗng.
        "sku": _upper_or_none(form.get("sku")),
        "barcode": _upper_or_none(form.get("barcode")),

        "thumbnail_url": _none_if_empty(form.get("thumbnail_url")),

        # Checkbox không tick sẽ không gửi field lên.
        "is_active": "is_active" in form,
        "is_featured": "is_featured" in form,
        "allow_backorder": "allow_backorder" in form,

        "low_stock_threshold": _safe_int(
            form.get("low_stock_threshold"),
            default=5,
            min_value=0,
        ),

        "gender": _clean_text(form.get("gender"), 30) or "unisex",
        "brand": _clean_text(form.get("brand"), 120) or "GUAMAISON",

        "meta_title": seo_title or None,
        "meta_description": seo_description or None,

        "seo_title": seo_title or None,
        "seo_description": seo_description or None,
        "seo_keywords": seo_keywords or None,
        "search_keywords": search_keywords or None,

        "tags": _parse_tags(form.get("tags")),
    }

    return payload


def _validate_product_payload(payload: dict) -> str | None:
    if not payload.get("name"):
        return "Tên sản phẩm không được để trống."

    if not payload.get("slug"):
        return "Slug URL không được để trống."

    if not payload.get("price") or payload.get("price") <= 0:
        return "Giá bán sản phẩm không hợp lệ."

    if payload.get("compare_at_price") and payload["compare_at_price"] <= payload["price"]:
        return "Giá so sánh phải lớn hơn giá bán."

    return None


# ═══════════════════════════════════════════════════════════════
# IMAGE HELPERS
# ═══════════════════════════════════════════════════════════════

def _extract_image_urls() -> list[str]:
    seen = set()
    result = []

    for raw in _getlist("image_urls"):
        url = _clean_text(raw)
        if url and url not in seen:
            seen.add(url)
            result.append(url)

    return result


def _handle_images_on_save(product_id: str, form_dict: dict) -> None:
    uploaded = []

    for file in _filelist("image_files"):
        if not file or not file.filename:
            continue

        if not _allowed_file(file.filename):
            logger.warning("[products] Bỏ qua file không hợp lệ: %s", file.filename)
            continue

        try:
            url = ProductModel.upload_to_storage(
                file.read(),
                file.filename,
                file.content_type or "image/jpeg",
            )
            if url:
                uploaded.append(url)

        except Exception as e:
            logger.error("[products] Upload ảnh lỗi: %s", e, exc_info=True)

    external_urls = _extract_image_urls()
    all_urls = list(dict.fromkeys(uploaded + external_urls))

    # Nếu không upload/thay đổi ảnh, không sync để tránh xóa ảnh cũ ngoài ý muốn.
    should_sync = bool(all_urls) or bool(form_dict.get("_images_synced"))
    if not should_sync:
        return

    ProductModel.sync_images(product_id, all_urls)

    images = ProductModel.get_images(product_id)
    thumb = next(
        (img for img in images if img.get("is_primary")),
        images[0] if images else None,
    )

    if thumb and thumb.get("url"):
        (
            _db_admin()
            .table("products")
            .update({"thumbnail_url": thumb["url"]})
            .eq("id", product_id)
            .execute()
        )


# ═══════════════════════════════════════════════════════════════
# VARIANT HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_indexed(values: list[Any], index: int, default: Any = "") -> Any:
    return values[index] if index < len(values) else default


def _save_product_variants(db, product_id: str) -> None:
    """
    Field nhận từ form:
    - v_color[]
    - v_color_hex[]
    - v_size[]
    - v_stock[]
    - v_price_override[]
    - v_compare_at_price[]
    - v_cost_price[]
    - v_sku[]
    - v_barcode[]
    """
    db.table("product_variants").delete().eq("product_id", product_id).execute()

    colors = _getlist("v_color[]")
    hexes = _getlist("v_color_hex[]")
    sizes = _getlist("v_size[]")
    stocks = _getlist("v_stock[]")
    price_overrides = _getlist("v_price_override[]")
    compare_prices = _getlist("v_compare_at_price[]")
    cost_prices = _getlist("v_cost_price[]")
    skus = _getlist("v_sku[]")
    barcodes = _getlist("v_barcode[]")

    total_stock = 0
    variants = []

    # Form variant lấy size làm trục chính.
    for i, raw_size in enumerate(sizes):
        size = _clean_text(raw_size, 50)
        if not size:
            continue

        color_name = _clean_text(_get_indexed(colors, i), 80) or "Mặc định"
        color_hex = _clean_text(_get_indexed(hexes, i, "#3b2414"), 20)

        if not color_hex.startswith("#"):
            color_hex = "#3b2414"

        stock = _safe_int(_get_indexed(stocks, i, 0), default=0)
        total_stock += stock

        price_override = _parse_vnd(_get_indexed(price_overrides, i), default=0)
        compare_at_price = _parse_vnd(_get_indexed(compare_prices, i), default=0)
        cost_price = _parse_vnd(_get_indexed(cost_prices, i), default=0)

        variant_sku = _upper_or_none(_get_indexed(skus, i))
        variant_barcode = _upper_or_none(_get_indexed(barcodes, i))

        variants.append({
            "product_id": product_id,
            "size": size,
            "color_name": color_name,
            "color_hex": color_hex,
            "stock": stock,
            "price_override": price_override or None,
            "compare_at_price": compare_at_price or None,
            "cost_price": cost_price or None,
            "sku": variant_sku,
            "barcode": variant_barcode,
            "sort_order": i,
        })

    if variants:
        db.table("product_variants").insert(variants).execute()

    db.table("products").update({"stock": total_stock}).eq("id", product_id).execute()


# ═══════════════════════════════════════════════════════════════
# RELATION HELPERS
# ═══════════════════════════════════════════════════════════════

def _sync_product_categories(db, product_id: str, form: dict) -> None:
    category_ids = _getlist("category_ids[]") or _getlist("category_ids")

    if not category_ids and form.get("category_id"):
        category_ids = [form.get("category_id")]

    for name in _split_new_names(form.get("new_categories")):
        created_id = _get_or_create_category(db, name)
        if created_id:
            category_ids.append(created_id)

    ProductModel.sync_categories(product_id, _unique_keep_order(category_ids))


def _sync_product_collections(db, product_id: str, form: dict) -> None:
    collection_ids = _getlist("collection_ids[]") or _getlist("collection_ids")

    if not collection_ids and form.get("collection_id"):
        collection_ids = [form.get("collection_id")]

    for name in _split_new_names(form.get("new_collections")):
        created_id = _get_or_create_collection(db, name)
        if created_id:
            collection_ids.append(created_id)

    ProductModel.sync_collections(product_id, _unique_keep_order(collection_ids))


def _after_save_product(db, product_id: str, form: dict) -> None:
    _handle_images_on_save(product_id, form)
    _save_product_variants(db, product_id)
    _sync_product_categories(db, product_id, form)
    _sync_product_collections(db, product_id, form)
    ProductGroupModel.sync_automatic_for_product(product_id)
    _invalidate_storefront_catalog_cache()


# ═══════════════════════════════════════════════════════════════
# PRODUCTS ROUTES
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/products")
@admin_required
@handle_errors("Lỗi tải sản phẩm.")
def products():
    args = _args()
    per_page_cfg = current_app.config.get("ADMIN_PRODUCTS_PER_PAGE", 15)
    page, per_page, _ = _paginate(args, per_page_cfg)

    keyword = _clean_text(args.get("q"))
    status = _clean_text(args.get("status"))

    db = _db_admin()

    query = db.table("products").select(
        "*, "
        "product_categories(categories(id, name, slug)), "
        "collection_products(collections(id, name, slug)), "
        "product_images(*), "
        "product_variants(*)",
        count="exact",
    )

    if keyword:
        safe_keyword = keyword.replace(",", " ").replace("(", " ").replace(")", " ").strip()
        query = query.or_(
            f"name.ilike.%{safe_keyword}%,sku.ilike.%{safe_keyword}%,barcode.ilike.%{safe_keyword}%"
        )

    if status == "active":
        query = query.eq("is_active", True).is_("deleted_at", "null")
    elif status == "hidden":
        query = query.eq("is_active", False).is_("deleted_at", "null")
    elif status == "featured":
        query = query.eq("is_featured", True).is_("deleted_at", "null")
    elif status == "deleted":
        query = query.filter("deleted_at", "not.is", "null")
    else:
        query = query.is_("deleted_at", "null")

    start = (page - 1) * per_page
    end = page * per_page - 1

    try:
        result = query.order("created_at", desc=True).range(start, end).execute()
        products_list = result.data or []
        total = result.count or 0

    except Exception as e:
        products_list, total = [], 0
        current_app.logger.error("[Admin Products] Lỗi truy vấn: %s", e, exc_info=True)

    return render_template(
        "admin/products.html",
        products=products_list,
        total=total,
        page=page,
        total_pages=_total_pages(total, per_page),
        keyword=keyword,
        status=status,
        cats=CategoryModel.get_all(),
    )


@admin_bp.route("/products/add", methods=["GET", "POST"])
@admin_required
@handle_errors("Lỗi hệ thống.", "admin.products")
def add_product():
    cats = CategoryModel.get_all()
    colles = ProductGroupModel.enrich_collections(CollectionModel.get_all(admin_mode=True), include_counts=False)
    tag_options = _get_existing_tags()

    if request.method == "POST":
        form = _form()
        db = _db_admin()
        payload = _product_data_from_form(form)

        error = _validate_product_payload(payload)
        if error:
            flash(error, "danger")
            return _render_product_form(
                product=None,
                cats=cats,
                colles=colles,
                tag_options=tag_options,
                status_code=400,
            )

        product = ProductModel.create(payload)

        if not product:
            flash("Không tạo được sản phẩm. Vui lòng kiểm tra dữ liệu hoặc database.", "danger")
            return _render_product_form(
                product=None,
                cats=cats,
                colles=colles,
                tag_options=tag_options,
                status_code=400,
            )

        product_id = product["id"]

        try:
            _after_save_product(db, product_id, form)
        except Exception as e:
            logger.error("[products] Lỗi xử lý dữ liệu sau khi tạo sản phẩm: %s", e, exc_info=True)
            flash("Sản phẩm đã tạo nhưng có lỗi khi lưu ảnh / biến thể / danh mục.", "warning")
            return redirect(url_for("admin.edit_product", pid=product_id))

        flash(f"Đã thêm sản phẩm: {payload['name']}", "success")
        return redirect(url_for("admin.products"))

    return _render_product_form(
        product=None,
        cats=cats,
        colles=colles,
        tag_options=tag_options,
    )


@admin_bp.route("/products/edit/<pid>", methods=["GET", "POST"])
@admin_required
@handle_errors("Lỗi cập nhật.", "admin.products")
def edit_product(pid):
    product = ProductModel.get_by_id(pid)
    cats = CategoryModel.get_all()
    colles = ProductGroupModel.enrich_collections(CollectionModel.get_all(admin_mode=True), include_counts=False)
    tag_options = _get_existing_tags()

    if not product:
        flash("Sản phẩm không tồn tại.", "danger")
        return redirect(url_for("admin.products"))

    if request.method == "POST":
        form = _form()
        db = _db_admin()
        payload = _product_data_from_form(form)

        error = _validate_product_payload(payload)
        if error:
            flash(error, "danger")
            return _render_product_form(
                product=product,
                cats=cats,
                colles=colles,
                tag_options=tag_options,
                status_code=400,
            )

        updated = ProductModel.update(pid, payload)

        if not updated:
            flash("Không lưu được sản phẩm. Vui lòng kiểm tra dữ liệu hoặc database.", "danger")
            return _render_product_form(
                product=product,
                cats=cats,
                colles=colles,
                tag_options=tag_options,
                status_code=400,
            )

        try:
            _after_save_product(db, pid, form)
        except Exception as e:
            logger.error("[products] Lỗi xử lý dữ liệu sau khi cập nhật sản phẩm: %s", e, exc_info=True)
            flash("Sản phẩm đã lưu nhưng có lỗi khi cập nhật ảnh / biến thể / danh mục.", "warning")
            return redirect(url_for("admin.edit_product", pid=pid))

        flash("Lưu sản phẩm thành công.", "success")
        return redirect(url_for("admin.products"))

    return _render_product_form(
        product=product,
        cats=cats,
        colles=colles,
        tag_options=tag_options,
    )


@admin_bp.route("/products/delete/<pid>", methods=["POST"])
@admin_required
@handle_errors("Lỗi khi xóa.", "admin.products")
def delete_product(pid):
    if ProductModel.delete(pid, permanent=False):
        flash("Đã đưa sản phẩm vào thùng rác.", "success")
    else:
        flash("Lỗi khi xóa sản phẩm.", "danger")

    return redirect(url_for("admin.products"))


@admin_bp.route("/products/upload-async", methods=["POST"])
@admin_required
def upload_product_image_async():
    if "file" not in request.files:
        return {"error": "Không tìm thấy file ảnh dữ liệu."}, 400

    file = request.files["file"]

    if file and file.filename and _allowed_file(file.filename):
        try:
            url = ProductModel.upload_to_storage(
                file.read(),
                file.filename,
                file.content_type or "image/jpeg",
            )
            if url:
                return {"url": url}, 200

        except Exception as e:
            logger.error("[products] upload_product_image_async error: %s", e, exc_info=True)
            return {"error": str(e)}, 500

    return {"error": "Định dạng file ảnh không được hệ thống hỗ trợ."}, 400


# ═══════════════════════════════════════════════════════════════
# CATEGORIES ROUTES
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/categories")
@admin_required
def categories():
    return render_template("admin/categories.html", cats=CategoryModel.get_all())


@admin_bp.route("/categories/add", methods=["POST"])
@admin_required
def add_category():
    form = _form()

    name = _clean_text(form.get("name"), 120)
    slug = _clean_text(form.get("slug"), 120) or _slugify_vi(name)
    description = _clean_text(form.get("description"), 500)
    is_active = "is_active" in form

    if not name:
        flash("Tên danh mục trống không hợp lệ.", "danger")
        return redirect(url_for("admin.categories"))

    CategoryModel.create({
        "name": name,
        "slug": slug,
        "description": description,
        "is_active": is_active,
    })

    flash(f"Đã thêm danh mục: {name}", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/edit/<cat_id>", methods=["GET", "POST"])
@admin_required
@handle_errors("Lỗi chỉnh sửa danh mục.", "admin.categories")
def edit_category(cat_id):
    cat = CategoryModel.get_by_id(cat_id)

    if not cat:
        flash("Danh mục không tồn tại.", "danger")
        return redirect(url_for("admin.categories"))

    if request.method == "POST":
        form = _form()

        name = _clean_text(form.get("name"), 120)
        slug = _clean_text(form.get("slug"), 120) or _slugify_vi(name)
        description = _clean_text(form.get("description"), 500)
        is_active = "is_active" in form

        if not name:
            flash("Tên không hợp lệ.", "danger")
            return render_template("admin/category_form.html", cat=cat)

        CategoryModel.update(cat_id, {
            "name": name,
            "slug": slug,
            "description": description,
            "is_active": is_active,
        })

        flash("Cập nhật danh mục thành công.", "success")
        return redirect(url_for("admin.categories"))

    return render_template("admin/category_form.html", cat=cat)


@admin_bp.route("/categories/delete/<cat_id>", methods=["POST"])
@admin_required
@handle_errors("Lỗi xóa danh mục.", "admin.categories")
def delete_category(cat_id):
    CategoryModel.delete(cat_id)

    flash("Đã xóa danh mục khỏi hệ thống.", "success")
    return redirect(url_for("admin.categories"))


# ═══════════════════════════════════════════════════════════════
# COLLECTIONS ROUTES
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/collections")
@admin_required
def collections():
    collection_rows = ProductGroupModel.enrich_collections(
        CollectionModel.get_all(admin_mode=True)
    )
    return render_template(
        "admin/collections.html",
        colles=collection_rows,
    )


@admin_bp.route("/collections/add", methods=["GET", "POST"])
@admin_required
@handle_errors("Lỗi thêm bộ sưu tập.", "admin.collections")
def add_collection():
    product_picker = _collection_product_picker()
    if request.method == "POST":
        form = _form()

        name = _clean_text(form.get("name"), 120)
        slug = _slugify_vi(_clean_text(form.get("slug"), 120) or name)
        description = _clean_text(form.get("description"), 12000)
        meta_title = _clean_text(form.get("meta_title"), 160) or name
        meta_description = _clean_text(form.get("meta_description"), 320)
        is_active = "is_active" in form
        show_on_home = "show_on_home" in form
        group_config = _collection_group_payload(form)

        if not name:
            flash("Tên nhóm sản phẩm không được để trống.", "danger")
            return render_template("admin/collection_form.html", **_collection_form_context(None, product_picker, group_config))

        if group_config["selection_mode"] == "automatic" and not group_config["rules"]:
            flash("Nhóm tự động cần ít nhất một điều kiện hợp lệ.", "danger")
            return render_template("admin/collection_form.html", **_collection_form_context(None, product_picker, group_config))

        image_url, video_url = None, None
        raw_ext_url = _clean_text(form.get("external_url"), 1000)
        ext_url = _safe_http_url(raw_ext_url)
        file = request.files.get("collection_media")

        if raw_ext_url and not ext_url:
            flash("URL ảnh/video phải bắt đầu bằng http:// hoặc https://.", "danger")
            return render_template("admin/collection_form.html", **_collection_form_context(None, product_picker, group_config))

        if ext_url:
            lowered = ext_url.lower()
            if lowered.endswith((".mp4", ".webm", ".mov")) or "video" in lowered:
                video_url = ext_url
            else:
                image_url = ext_url

        elif file and file.filename:
            uploaded_url = CollectionModel.upload_media(
                file_bytes=file.read(),
                filename=file.filename,
                content_type=file.content_type,
            )

            if not uploaded_url:
                flash(
                    "Không tải được media lên Storage. Kiểm tra bucket `store-assets`, service_role key, định dạng file hoặc dung lượng file.",
                    "danger",
                )
                return render_template("admin/collection_form.html", **_collection_form_context(None, product_picker, group_config))

            if (file.content_type or "").startswith("video/"):
                video_url = uploaded_url
            else:
                image_url = uploaded_url

        created = CollectionModel.create({
            "name": name,
            "slug": slug,
            "description": description,
            "is_active": is_active,
            "show_on_home": show_on_home,
            "image_url": image_url,
            "video_url": video_url,
            "sort_order": 0,
            "meta_title": meta_title,
            "meta_description": meta_description,
        })

        if not created:
            flash("Không tạo được nhóm sản phẩm. Vui lòng kiểm tra đường dẫn có bị trùng.", "danger")
            return render_template("admin/collection_form.html", **_collection_form_context(None, product_picker, group_config))

        collection_id = str(created.get("id") or "")
        settings_saved, group_config = ProductGroupModel.save_group(collection_id, group_config)
        member_count = 0
        if group_config["selection_mode"] == "automatic" and settings_saved:
            member_count = ProductGroupModel.sync_collection(collection_id)
        else:
            member_count = _sync_collection_members(collection_id)

        try:
            _add_collection_to_menu(created, form)
        except Exception as exc:
            logger.warning("[collections] Nhóm đã tạo nhưng chưa thêm được vào menu: %s", exc)
            flash("Nhóm đã tạo nhưng chưa thêm được vào menu. Bạn có thể thêm lại tại Menu & liên kết.", "warning")

        if not settings_saved:
            flash("Nhóm đã tạo nhưng chưa lưu được cấu hình điều kiện; hệ thống đang dùng chế độ thủ công.", "warning")
        _invalidate_storefront_catalog_cache()
        flash(f"Đã tạo nhóm sản phẩm “{name}” với {member_count} sản phẩm.", "success")
        return redirect(url_for("admin.collections"))

    return render_template("admin/collection_form.html", **_collection_form_context(None, product_picker))


@admin_bp.route("/collections/edit/<cid>", methods=["GET", "POST"])
@admin_required
@handle_errors("Lỗi cập nhật lookbook.", "admin.collections")
def edit_collection(cid):
    cat = CollectionModel.get_by_id(cid)
    product_picker = _collection_product_picker(cid)
    group_config = ProductGroupModel.get_group(cid)

    if not cat:
        flash("Bộ sưu tập không tồn tại.", "danger")
        return redirect(url_for("admin.collections"))

    if request.method == "POST":
        form = _form()

        name = _clean_text(form.get("name"), 120)
        slug = _slugify_vi(_clean_text(form.get("slug"), 120) or name)
        description = _clean_text(form.get("description"), 12000)
        meta_title = _clean_text(form.get("meta_title"), 160) or name
        meta_description = _clean_text(form.get("meta_description"), 320)
        is_active = "is_active" in form
        show_on_home = "show_on_home" in form
        group_config = _collection_group_payload(form)

        if not name:
            flash("Tên nhóm sản phẩm không được để trống.", "danger")
            return render_template("admin/collection_form.html", **_collection_form_context(cat, product_picker, group_config))

        if group_config["selection_mode"] == "automatic" and not group_config["rules"]:
            flash("Nhóm tự động cần ít nhất một điều kiện hợp lệ.", "danger")
            return render_template("admin/collection_form.html", **_collection_form_context(cat, product_picker, group_config))

        image_url = cat.get("image_url")
        video_url = cat.get("video_url")

        raw_ext_url = _clean_text(form.get("external_url"), 1000)
        ext_url = _safe_http_url(raw_ext_url)
        file = request.files.get("collection_media")

        if raw_ext_url and not ext_url:
            flash("URL ảnh/video phải bắt đầu bằng http:// hoặc https://.", "danger")
            return render_template("admin/collection_form.html", **_collection_form_context(cat, product_picker, group_config))

        if "remove_media" in form:
            CollectionModel.delete_media_from_url(image_url)
            CollectionModel.delete_media_from_url(video_url)
            image_url, video_url = None, None

        if ext_url:
            lowered = ext_url.lower()
            if lowered.endswith((".mp4", ".webm", ".mov")) or "video" in lowered:
                video_url = ext_url
                image_url = None
            else:
                image_url = ext_url
                video_url = None

        elif file and file.filename:
            uploaded_url = CollectionModel.upload_media(
                file_bytes=file.read(),
                filename=file.filename,
                content_type=file.content_type,
            )

            if not uploaded_url:
                flash(
                    "Không tải được media lên Storage. Kiểm tra bucket `store-assets`, service_role key, định dạng file hoặc dung lượng file.",
                    "danger",
                )
                return render_template("admin/collection_form.html", **_collection_form_context(cat, product_picker, group_config))

            CollectionModel.delete_media_from_url(cat.get("image_url"))
            CollectionModel.delete_media_from_url(cat.get("video_url"))

            if (file.content_type or "").startswith("video/"):
                video_url = uploaded_url
                image_url = None
            else:
                image_url = uploaded_url
                video_url = None

        updated = CollectionModel.update(cid, {
            "name": name,
            "slug": slug,
            "description": description,
            "is_active": is_active,
            "show_on_home": show_on_home,
            "image_url": image_url,
            "video_url": video_url,
            "meta_title": meta_title,
            "meta_description": meta_description,
        })

        if not updated:
            flash("Không cập nhật được bộ sưu tập. Vui lòng kiểm tra database hoặc slug bị trùng.", "danger")
            return render_template("admin/collection_form.html", **_collection_form_context(cat, product_picker, group_config))

        settings_saved, group_config = ProductGroupModel.save_group(cid, group_config)
        if group_config["selection_mode"] == "automatic" and settings_saved:
            member_count = ProductGroupModel.sync_collection(cid)
        else:
            member_count = _sync_collection_members(cid)

        try:
            _add_collection_to_menu(updated or cat, form)
        except Exception as exc:
            logger.warning("[collections] Nhóm đã lưu nhưng chưa thêm được vào menu: %s", exc)
            flash("Nhóm đã lưu nhưng chưa thêm được vào menu. Bạn có thể thêm lại tại Menu & liên kết.", "warning")

        if not settings_saved:
            flash("Thông tin nhóm đã lưu nhưng cấu hình điều kiện chưa được cập nhật.", "warning")
        _invalidate_storefront_catalog_cache()
        flash(f"Cập nhật nhóm sản phẩm thành công ({member_count} sản phẩm).", "success")
        return redirect(url_for("admin.collections"))

    return render_template("admin/collection_form.html", **_collection_form_context(cat, product_picker, group_config))


@admin_bp.route("/collections/delete/<cid>", methods=["POST"])
@admin_required
def delete_collection(cid):
    if CollectionModel.delete(cid):
        ProductGroupModel.delete_group(cid)
        NavigationModel.remove_target_links("collection", cid)
        _invalidate_storefront_catalog_cache()
        flash("Đã xóa nhóm sản phẩm và dọn các liên kết menu liên quan.", "success")
    else:
        flash("Không thể xóa nhóm sản phẩm.", "danger")
    return redirect(url_for("admin.collections"))


@admin_bp.route("/collections/update-homepage", methods=["POST"])
@admin_required
def update_homepage_layout():
    home_ids = request.form.getlist("home_cats[]")
    db = _db_admin()

    try:
        db.table("collections").update({
            "show_on_home": False,
            "sort_order": 0,
        }).eq("show_on_home", True).execute()

        for index, collection_id in enumerate(home_ids):
            db.table("collections").update({
                "show_on_home": True,
                "sort_order": index + 1,
            }).eq("id", collection_id).execute()

        flash("Đã lưu cấu hình kéo thả Lookbook trang chủ.", "success")

    except Exception as e:
        current_app.logger.error("[collections] Lỗi kéo thả homepage: %s", e, exc_info=True)
        flash("Lỗi kết nối khi lưu bố cục trang chủ.", "danger")

    return redirect(url_for("admin.collections"))