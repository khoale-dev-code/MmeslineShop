"""
app/controllers/product_controller.py
=====================================

Storefront Product Controller - GUAMAISON

Mục tiêu:
- Shop / index / product detail hoạt động ổn định.
- Tránh lỗi sản phẩm không hiển thị do select thiếu/sai cột.
- Không fallback sai sang sản phẩm khác khi slug không tồn tại.
- Giảm query vòng làm trang chi tiết load lâu.
- Giữ tương thích với template cũ: products/index.html, products/shop.html, products/detail.html.
"""

from __future__ import annotations

import logging
import re
import time
from html import unescape
from math import ceil
from typing import Any, Optional

import requests
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.models.collection_model import CollectionModel
from app.models.product_model import ProductModel
from app.services.about_page_service import AboutPageService
from app.services.size_chart_service import size_chart_service
from app.utils.supabase_client import get_supabase

logger = logging.getLogger(__name__)

products_bp = Blueprint("products", __name__)


# =============================================================================
# SELECT CONFIG
# =============================================================================
# Dùng "*" cho bảng products để tránh lỗi nếu database của bạn chưa có một vài cột
# như search_keywords, gender, sold_count, low_stock_threshold...
# Tối ưu hiệu năng bằng cách giảm query vòng, không tối ưu bằng cách liệt kê cột
# khi schema chưa ổn định.

PRODUCT_SELECT = (
    "*, "
    "product_categories(categories(id, name, slug)), "
    "collection_products(collections(id, name, slug)), "
    "product_images(*), "
    "product_variants(*)"
)


# =============================================================================
# SMALL TTL CACHE
# =============================================================================

_CACHE: dict[str, tuple[float, Any]] = {}
DEFAULT_CACHE_TTL = 180


def _cache_get(key: str) -> Any | None:
    item = _CACHE.get(key)

    if not item:
        return None

    expires_at, value = item

    if expires_at < time.time():
        _CACHE.pop(key, None)
        return None

    return value


def _cache_set(key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> Any:
    _CACHE[key] = (time.time() + ttl, value)
    return value


# =============================================================================
# BASIC HELPERS
# =============================================================================

def _clean(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _rich_text_to_plain(value: Any) -> str:
    """Đổi mô tả HTML/JSON/list cũ thành text an toàn cho SEO và template."""
    if value is None:
        return ""

    if isinstance(value, str):
        raw = value
    elif isinstance(value, (list, tuple, set)):
        raw = " ".join(_rich_text_to_plain(item) for item in value)
    elif isinstance(value, dict):
        preferred = next(
            (
                value.get(key)
                for key in ("html", "text", "content", "value", "description")
                if value.get(key) not in (None, "")
            ),
            None,
        )
        if preferred is not None:
            raw = _rich_text_to_plain(preferred)
        else:
            raw = " ".join(_rich_text_to_plain(item) for item in value.values())
    else:
        raw = str(value)

    raw = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return " ".join(unescape(raw).split())


def _format_vnd(value: Any) -> str:
    number = _safe_int(value, 0)
    return f"{number:,.0f}".replace(",", ".") + "đ"


def _discount_percent(price: Any, compare_at_price: Any) -> int | None:
    price_num = _safe_float(price, 0)
    compare_num = _safe_float(compare_at_price, 0)

    if compare_num > price_num > 0:
        return int(round((compare_num - price_num) / compare_num * 100))

    return None


def _sanitize_keyword(keyword: Optional[str]) -> Optional[str]:
    if not keyword:
        return None

    text = str(keyword).strip()

    # Tránh lỗi cú pháp filter của Supabase khi user nhập ký tự đặc biệt.
    for char in [",", "%", "*", "(", ")", "[", "]", "{", "}", ";", "'"]:
        text = text.replace(char, " ")

    text = " ".join(text.split())

    return text or None


def _unique_ids(values: list[Any]) -> list[str]:
    seen = set()
    result: list[str] = []

    for value in values or []:
        if not value:
            continue

        text = str(value)

        if text in seen:
            continue

        seen.add(text)
        result.append(text)

    return result


def _intersect_ids(current_ids: Optional[list[str]], next_ids: list[str]) -> list[str]:
    next_ids = _unique_ids(next_ids)

    if current_ids is None:
        return next_ids

    current_set = set(str(item) for item in current_ids)
    return [item for item in next_ids if item in current_set]


def _maybe_format_with_model(product: dict) -> dict:
    """
    Nếu ProductModel._format_product tồn tại và chạy ổn thì dùng.
    Nếu lỗi thì vẫn trả raw product để không làm storefront trắng sản phẩm.
    """
    if not product:
        return product

    try:
        formatter = getattr(ProductModel, "_format_product", None)

        if callable(formatter):
            return formatter(product)

    except Exception as exc:
        logger.debug("[ProductModel._format_product ignored] %s", exc)

    return product


# =============================================================================
# PRODUCT NORMALIZATION
# =============================================================================

def _normalize_images(product: dict) -> dict:
    images = product.get("product_images") or []

    if not isinstance(images, list):
        images = []

    images = [img for img in images if isinstance(img, dict)]

    images.sort(
        key=lambda img: (
            0 if img.get("is_primary") else 1,
            _safe_int(img.get("sort_order"), 0),
            str(img.get("created_at") or ""),
        )
    )

    product["product_images"] = images
    product["images"] = images

    primary = next(
        (img.get("url") for img in images if img.get("is_primary") and img.get("url")),
        None,
    )

    first = next(
        (img.get("url") for img in images if img.get("url")),
        None,
    )

    thumbnail = (
        product.get("thumbnail_url")
        or primary
        or first
        or "https://placehold.co/800x1067/f7f8f4/1b4922?text=GUAMAISON"
    )

    product["thumbnail_url"] = thumbnail
    product["main_image_url"] = primary or thumbnail

    return product


def _normalize_relations(product: dict) -> dict:
    product_categories = product.get("product_categories") or []
    collection_products = product.get("collection_products") or []

    category_list = []
    collection_list = []

    for row in product_categories:
        if not isinstance(row, dict):
            continue

        cat = row.get("categories")

        if isinstance(cat, dict) and cat.get("id"):
            category_list.append(cat)

    for row in collection_products:
        if not isinstance(row, dict):
            continue

        collection = row.get("collections")

        if isinstance(collection, dict) and collection.get("id"):
            collection_list.append(collection)

    product["category_list"] = category_list
    product["collection_list"] = collection_list

    if category_list and not product.get("categories"):
        product["categories"] = category_list[0]

    if collection_list and not product.get("collections"):
        product["collections"] = collection_list[0]

    product["category_name"] = category_list[0].get("name") if category_list else "GUAMAISON"
    product["collection_name"] = collection_list[0].get("name") if collection_list else None

    return product


def _normalize_price(product: dict) -> dict:
    price = _safe_int(product.get("price"), 0)

    compare_at_price = _safe_int(
        product.get("compare_at_price")
        or product.get("old_price")
        or product.get("original_price"),
        0,
    )

    if compare_at_price <= price:
        compare_at_price = 0

    discount = _discount_percent(price, compare_at_price)

    product["price"] = price
    product["price_formatted"] = _format_vnd(price)

    product["compare_at_price"] = compare_at_price or None
    product["old_price"] = compare_at_price or None
    product["compare_at_price_formatted"] = _format_vnd(compare_at_price) if compare_at_price else None
    product["old_price_formatted"] = product["compare_at_price_formatted"]

    product["discount_percent"] = discount
    product["has_discount"] = discount is not None

    return product


def _normalize_variant(
    variant: dict,
    base_price: int,
    base_compare_at_price: int | None,
    allow_backorder: bool,
) -> dict:
    stock = _safe_int(variant.get("stock"), 0)

    price_override = _safe_int(variant.get("price_override"), 0)
    effective_price = price_override or base_price

    variant_compare = _safe_int(variant.get("compare_at_price"), 0)
    product_compare = _safe_int(base_compare_at_price, 0)

    if variant_compare > effective_price:
        effective_compare = variant_compare
    elif product_compare > effective_price:
        effective_compare = product_compare
    else:
        effective_compare = 0

    discount = _discount_percent(effective_price, effective_compare)

    variant["stock"] = stock
    variant["color_name"] = variant.get("color_name") or "Mặc định"
    variant["color_hex"] = variant.get("color_hex") or "#1b4922"

    variant["is_in_stock"] = stock > 0
    variant["is_available"] = stock > 0 or allow_backorder

    variant["effective_price"] = effective_price
    variant["effective_price_formatted"] = _format_vnd(effective_price)

    variant["effective_compare_at_price"] = effective_compare or None
    variant["effective_compare_at_price_formatted"] = (
        _format_vnd(effective_compare) if effective_compare else None
    )

    variant["discount_percent"] = discount
    variant["has_discount"] = discount is not None

    return variant


def _stock_status(stock: int, allow_backorder: bool, low_stock_threshold: int) -> dict:
    if stock > low_stock_threshold:
        return {
            "key": "in_stock",
            "label": "Còn hàng",
            "message": f"Còn {stock} sản phẩm",
            "can_buy": True,
        }

    if stock > 0:
        return {
            "key": "low_stock",
            "label": "Sắp hết hàng",
            "message": f"Chỉ còn {stock} sản phẩm",
            "can_buy": True,
        }

    if allow_backorder:
        return {
            "key": "backorder",
            "label": "Cho phép đặt trước",
            "message": "Sản phẩm tạm hết hàng nhưng vẫn có thể đặt trước",
            "can_buy": True,
        }

    return {
        "key": "out_of_stock",
        "label": "Hết hàng",
        "message": "Sản phẩm hiện đã hết hàng",
        "can_buy": False,
    }


def _normalize_product(product: dict) -> dict:
    if not product:
        return product

    product = _maybe_format_with_model(product)
    product = _normalize_images(product)
    product = _normalize_relations(product)
    product = _normalize_price(product)

    variants = product.get("product_variants") or []

    if not isinstance(variants, list):
        variants = []

    allow_backorder = _safe_bool(product.get("allow_backorder"))
    base_price = _safe_int(product.get("price"), 0)
    base_compare = _safe_int(product.get("compare_at_price"), 0)

    normalized_variants = [
        _normalize_variant(
            variant=variant,
            base_price=base_price,
            base_compare_at_price=base_compare,
            allow_backorder=allow_backorder,
        )
        for variant in variants
        if isinstance(variant, dict)
    ]

    normalized_variants.sort(
        key=lambda item: (
            str(item.get("color_name") or ""),
            _safe_int(item.get("sort_order"), 0),
            str(item.get("size") or ""),
        )
    )

    product["product_variants"] = normalized_variants
    product["variants"] = normalized_variants

    if normalized_variants:
        total_stock = sum(_safe_int(v.get("stock"), 0) for v in normalized_variants)
    else:
        total_stock = _safe_int(product.get("stock"), 0)

    low_stock_threshold = _safe_int(product.get("low_stock_threshold"), 5)

    product["stock"] = total_stock
    product["stock_quantity"] = total_stock
    product["total_stock"] = total_stock

    product["allow_backorder"] = allow_backorder
    product["is_active"] = _safe_bool(product.get("is_active"))
    product["is_featured"] = _safe_bool(product.get("is_featured"))

    product["is_in_stock"] = total_stock > 0
    product["is_available"] = total_stock > 0 or allow_backorder
    product["is_low_stock"] = 0 < total_stock <= low_stock_threshold
    product["stock_status"] = _stock_status(
        stock=total_stock,
        allow_backorder=allow_backorder,
        low_stock_threshold=low_stock_threshold,
    )

    product["seo_title"] = (
        product.get("seo_title")
        or product.get("meta_title")
        or product.get("name")
        or "GUAMAISON"
    )

    product["seo_description"] = (
        product.get("seo_description")
        or product.get("meta_description")
        or product.get("description")
        or ""
    )

    product["description_html"] = (
        product.get("description_html")
        or product.get("description")
        or ""
    )

    return product


def _normalize_products(products: list[dict]) -> list[dict]:
    return [
        _normalize_product(item)
        for item in (products or [])
        if isinstance(item, dict)
    ]


def _build_color_groups(product: dict) -> dict:
    groups: dict[str, dict] = {}

    if not product:
        return groups

    allow_backorder = _safe_bool(product.get("allow_backorder"))

    for variant in product.get("product_variants") or []:
        color_name = variant.get("color_name") or "Mặc định"
        color_hex = variant.get("color_hex") or "#1b4922"
        stock = _safe_int(variant.get("stock"), 0)
        is_available = stock > 0 or allow_backorder

        if color_name not in groups:
            groups[color_name] = {
                "name": color_name,
                "hex": color_hex,
                "total_stock": 0,
                "is_available": False,
                "sizes": [],
            }

        groups[color_name]["total_stock"] += stock
        groups[color_name]["is_available"] = groups[color_name]["is_available"] or is_available

        groups[color_name]["sizes"].append({
            "variant_id": variant.get("id"),
            "size": variant.get("size") or "Freesize",
            "stock": stock,
            "is_in_stock": stock > 0,
            "is_available": is_available,
            "price": variant.get("effective_price"),
            "price_formatted": variant.get("effective_price_formatted"),
            "compare_at_price": variant.get("effective_compare_at_price"),
            "compare_at_price_formatted": variant.get("effective_compare_at_price_formatted"),
            "discount_percent": variant.get("discount_percent"),
            "has_discount": variant.get("has_discount"),
            "sku": variant.get("sku"),
            "barcode": variant.get("barcode"),
        })

    return groups


def _select_default_variant(product: dict) -> dict | None:
    variants = product.get("product_variants") or []

    if not variants:
        return None

    return next((v for v in variants if v.get("is_available")), None) or variants[0]


# =============================================================================
# FILTER HELPERS
# =============================================================================

def _get_product_ids_by_category_slug(db, category_slug: Optional[str]) -> Optional[list[str]]:
    if not category_slug:
        return None

    cache_key = f"category-products:{category_slug}"
    cached = _cache_get(cache_key)

    if cached is not None:
        return cached

    try:
        category_res = (
            db.table("categories")
            .select("id")
            .eq("slug", category_slug)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        if not category_res.data:
            return _cache_set(cache_key, [], ttl=60)

        category_id = category_res.data[0]["id"]

        child_res = (
            db.table("categories")
            .select("id")
            .eq("parent_id", category_id)
            .eq("is_active", True)
            .execute()
        )

        category_ids = [category_id] + [
            row["id"]
            for row in (child_res.data or [])
            if row.get("id")
        ]

        product_category_res = (
            db.table("product_categories")
            .select("product_id")
            .in_("category_id", category_ids)
            .execute()
        )

        product_ids = [
            row["product_id"]
            for row in (product_category_res.data or [])
            if row.get("product_id")
        ]

        return _cache_set(cache_key, _unique_ids(product_ids))

    except Exception as exc:
        logger.error("[category filter] %s", exc, exc_info=True)
        return []


def _get_product_ids_by_collection_slug(db, collection_slug: Optional[str]) -> Optional[list[str]]:
    if not collection_slug:
        return None

    cache_key = f"collection-products:{collection_slug}"
    cached = _cache_get(cache_key)

    if cached is not None:
        return cached

    try:
        collection_res = (
            db.table("collections")
            .select("id")
            .eq("slug", collection_slug)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        if not collection_res.data:
            return _cache_set(cache_key, [], ttl=60)

        collection_id = collection_res.data[0]["id"]

        collection_product_res = (
            db.table("collection_products")
            .select("product_id")
            .eq("collection_id", collection_id)
            .execute()
        )

        product_ids = [
            row["product_id"]
            for row in (collection_product_res.data or [])
            if row.get("product_id")
        ]

        return _cache_set(cache_key, _unique_ids(product_ids))

    except Exception as exc:
        logger.error("[collection filter] %s", exc, exc_info=True)
        return []


def _query_storefront_products(
    *,
    page: int = 1,
    per_page: int = 30,
    category_slug: Optional[str] = None,
    collection_slug: Optional[str] = None,
    gender: Optional[str] = None,
    keyword: Optional[str] = None,
    featured_only: bool = False,
    sort: Optional[str] = None,
) -> dict:
    db = get_supabase()

    page = max(1, _safe_int(page, 1))
    per_page = max(1, min(_safe_int(per_page, 30), 60))

    product_ids: Optional[list[str]] = None

    category_product_ids = _get_product_ids_by_category_slug(db, category_slug)
    if category_product_ids is not None:
        product_ids = _intersect_ids(product_ids, category_product_ids)

    collection_product_ids = _get_product_ids_by_collection_slug(db, collection_slug)
    if collection_product_ids is not None:
        product_ids = _intersect_ids(product_ids, collection_product_ids)

    if product_ids is not None and not product_ids:
        return {"items": [], "total": 0}

    offset = (page - 1) * per_page
    end = offset + per_page - 1

    query = (
        db.table("products")
        .select(PRODUCT_SELECT, count="exact")
        .eq("is_active", True)
        .is_("deleted_at", "null")
    )

    if featured_only:
        query = query.eq("is_featured", True)

    if product_ids is not None:
        query = query.in_("id", product_ids)

    if gender:
        # Nếu DB của bạn chưa có cột gender và lỗi, xóa filter này hoặc thêm cột gender.
        query = query.eq("gender", gender)

    safe_keyword = _sanitize_keyword(keyword)
    if safe_keyword:
        query = query.or_(
            f"name.ilike.%{safe_keyword}%,"
            f"slug.ilike.%{safe_keyword}%,"
            f"description.ilike.%{safe_keyword}%"
        )

    sort_key = sort or "new"

    if sort_key == "price_asc":
        query = query.order("price", desc=False)
    elif sort_key == "price_desc":
        query = query.order("price", desc=True)
    elif sort_key == "featured":
        query = query.order("is_featured", desc=True).order("created_at", desc=True)
    else:
        query = query.order("created_at", desc=True)

    response = query.range(offset, end).execute()

    items = _normalize_products(response.data or [])
    total = int(response.count or len(items))

    return {"items": items, "total": total}


# =============================================================================
# DETAIL HELPERS
# =============================================================================

def _get_product_by_slug(slug: str) -> dict | None:
    db = get_supabase()

    response = (
        db.table("products")
        .select(PRODUCT_SELECT)
        .eq("slug", slug)
        .eq("is_active", True)
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )

    data = response.data or []
    return data[0] if data else None


def _get_related_products(product: dict, limit: int = 4) -> list[dict]:
    """
    Tối ưu cho detail:
    - Không gọi lại _query_storefront_products().
    - Không đi qua category slug.
    - Dùng category id đã có từ product detail.
    """
    if not product:
        return []

    db = get_supabase()
    product_id = product.get("id")

    category_ids: list[str] = []

    for row in product.get("product_categories") or []:
        if not isinstance(row, dict):
            continue

        category = row.get("categories")

        if isinstance(category, dict) and category.get("id"):
            category_ids.append(category["id"])

    category_ids = _unique_ids(category_ids)

    try:
        if category_ids:
            product_category_res = (
                db.table("product_categories")
                .select("product_id")
                .in_("category_id", category_ids[:2])
                .neq("product_id", product_id)
                .limit(limit * 3)
                .execute()
            )

            ids = _unique_ids([
                row.get("product_id")
                for row in (product_category_res.data or [])
                if row.get("product_id")
            ])

            if ids:
                product_res = (
                    db.table("products")
                    .select(PRODUCT_SELECT)
                    .in_("id", ids[: limit * 2])
                    .eq("is_active", True)
                    .is_("deleted_at", "null")
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )

                related = [
                    item for item in _normalize_products(product_res.data or [])
                    if item.get("id") != product_id
                ][:limit]

                if related:
                    return related

        fallback_res = (
            db.table("products")
            .select(PRODUCT_SELECT)
            .eq("is_active", True)
            .is_("deleted_at", "null")
            .eq("is_featured", True)
            .neq("id", product_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return _normalize_products(fallback_res.data or [])[:limit]

    except Exception as exc:
        logger.warning("[related products] %s", exc, exc_info=True)
        return []


# =============================================================================
# ROUTES
# =============================================================================

@products_bp.route("/")
def index():
    try:
        result = _query_storefront_products(
            page=1,
            per_page=8,
            featured_only=True,
            sort="new",
        )
        featured_products = result["items"]

        if not featured_products:
            fallback = _query_storefront_products(
                page=1,
                per_page=8,
                sort="new",
            )
            featured_products = fallback["items"]

    except Exception as exc:
        logger.error("[index] featured products failed: %s", exc, exc_info=True)
        featured_products = []

    try:
        collections = CollectionModel.get_all(admin_mode=False)
    except Exception as exc:
        logger.error("[index] collections failed: %s", exc, exc_info=True)
        collections = []

    return render_template(
        "products/index.html",
        featured_products=featured_products,
        collections=collections,
    )


@products_bp.route("/shop")
def shop():
    page = max(1, _safe_int(request.args.get("page"), 1))
    per_page = 30

    category_slug = _clean(request.args.get("category"))
    collection_slug = _clean(request.args.get("collection"))
    gender = _clean(request.args.get("gender"))
    keyword = _clean(request.args.get("q"))
    sort = _clean(request.args.get("sort"))

    try:
        result = _query_storefront_products(
            page=page,
            per_page=per_page,
            category_slug=category_slug,
            collection_slug=collection_slug,
            gender=gender,
            keyword=keyword,
            sort=sort,
        )

        products = result["items"]
        total = result["total"]

    except Exception as exc:
        logger.error("[shop] products query failed: %s", exc, exc_info=True)
        products = []
        total = 0

    return render_template(
        "products/shop.html",
        products=products,
        total=total,
        total_pages=max(1, ceil(total / per_page)) if total else 1,
        page=page,
        category=category_slug,
        collection=collection_slug,
        current_gender=gender,
        keyword=keyword,
        sort=sort,
    )


@products_bp.route("/product/<slug>")
def detail(slug: str):
    slug = _clean(slug)

    if not slug or slug.lower() in {"none", "null", "undefined"}:
        abort(404)

    try:
        product = _get_product_by_slug(slug)
    except Exception as exc:
        logger.error("[detail] get product failed slug=%s: %s", slug, exc, exc_info=True)
        product = None

    if not product:
        abort(404)

    product = _normalize_product(product)
    product["color_groups"] = _build_color_groups(product)
    product["default_variant"] = _select_default_variant(product)
    try:
        size_chart = size_chart_service.get_for_product(product)
    except Exception as exc:
        logger.warning("[detail] Không tải được bảng size product=%s: %s", product.get("id"), exc)
        size_chart = None

    related_products = _get_related_products(product, limit=4)

    return render_template(
        "products/detail.html",
        product=product,
        related_products=related_products,
        size_chart=size_chart,
    )


@products_bp.route("/collections")
def collections():
    try:
        all_collections = CollectionModel.get_all(active_only=True, admin_mode=False)
    except Exception as exc:
        logger.error("[collections] failed: %s", exc, exc_info=True)
        all_collections = []

    return render_template(
        "products/collections.html",
        collections=all_collections,
    )


@products_bp.route("/collections/<slug>")
def collection_detail(slug: str):
    """Trang nhóm sản phẩm có URL/SEO ổn định như Haravan."""
    slug = _clean(slug)
    collection_info = CollectionModel.get_by_slug(slug, active_only=True)
    if not collection_info:
        abort(404)

    page = max(1, _safe_int(request.args.get("page"), 1))
    keyword = _clean(request.args.get("q"))
    sort = _clean(request.args.get("sort"))
    per_page = 30
    try:
        result = _query_storefront_products(
            page=page,
            per_page=per_page,
            collection_slug=slug,
            keyword=keyword,
            sort=sort,
        )
        products = result["items"]
        total = result["total"]
    except Exception as exc:
        logger.error("[collection detail] query failed slug=%s: %s", slug, exc, exc_info=True)
        products, total = [], 0

    plain_description = _rich_text_to_plain(collection_info.get("description"))[:320]
    return render_template(
        "products/shop.html",
        products=products,
        total=total,
        total_pages=max(1, ceil(total / per_page)) if total else 1,
        page=page,
        category=None,
        collection=slug,
        collection_info=collection_info,
        current_gender=None,
        keyword=keyword,
        sort=sort,
        shop_description=collection_info.get("meta_description") or plain_description,
    )


@products_bp.route("/visual-search", methods=["POST"])
def visual_search():
    file = request.files.get("image")

    if not file or not file.filename:
        flash("Vui lòng tải lên một hình ảnh để tìm kiếm.", "warning")
        return redirect(request.referrer or url_for("products.shop"))

    engine_url = current_app.config.get("AI_ENGINE_URL")

    if not engine_url:
        flash("Hệ thống AI chưa được cấu hình.", "danger")
        return redirect(request.referrer or url_for("products.shop"))

    matched_products = []

    try:
        token = current_app.config.get("HF_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        response = requests.post(
            f"{engine_url}/search",
            files={"image": (file.filename, file.stream, file.mimetype)},
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()

        ids = [
            item["id"]
            for item in response.json().get("results", [])
            if item.get("id")
        ]

        if ids:
            db = get_supabase()

            result = (
                db.table("products")
                .select(PRODUCT_SELECT)
                .in_("id", ids)
                .eq("is_active", True)
                .is_("deleted_at", "null")
                .execute()
            )

            matched_products = _normalize_products(result.data or [])

        flash(
            f"Tìm thấy {len(matched_products)} thiết kế tương tự."
            if matched_products else "Không tìm thấy sản phẩm phù hợp.",
            "success" if matched_products else "info",
        )

    except requests.exceptions.Timeout:
        flash("AI Engine timeout. Vui lòng thử lại sau.", "danger")
        return redirect(request.referrer or url_for("products.shop"))

    except Exception as exc:
        logger.error("[visual_search] failed: %s", exc, exc_info=True)
        flash("Lỗi kết nối máy chủ AI.", "danger")
        return redirect(request.referrer or url_for("products.shop"))

    return render_template(
        "products/shop.html",
        products=matched_products,
        total=len(matched_products),
        total_pages=1,
        page=1,
        category=None,
        collection=None,
        current_gender=None,
        keyword="Kết quả Visual Search",
        sort=None,
    )


@products_bp.route("/about")
def about():
    about_content = AboutPageService.get_published()
    return render_template("partials/about.html", about=about_content)

@products_bp.route("/contact", methods=["GET", "POST"])
def contact():
    from app.controllers.contact_controller import render_contact_page
    return render_contact_page()

@products_bp.route("/size-guide")
def size_guide():
    return render_template("products/size_guide.html")