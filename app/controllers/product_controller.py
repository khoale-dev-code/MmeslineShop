"""
app/controllers/product_controller.py
=====================================
Storefront controller cho MMESTLINE.

Đồng bộ với product form/backend mới:
- Hiểu compare_at_price thay cho old_price.
- Hiểu giá riêng theo biến thể: product_variants.price_override.
- Hiểu compare_at_price riêng của biến thể.
- Tính trạng thái tồn kho theo variant và allow_backorder.
- Format tiền Việt Nam dạng 199.000đ.
- Tạo color_groups cho trang chi tiết sản phẩm dùng JS/template dễ hơn.
"""

import logging
from math import ceil
from typing import Any, Optional

import requests
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.models.collection_model import CollectionModel
from app.models.product_model import ProductModel
from app.utils.supabase_client import get_supabase

products_bp = Blueprint("products", __name__)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _clean(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except Exception:
        return default


def _format_vnd(value: Any) -> str:
    number = _safe_int(value, 0)
    return f"{number:,.0f}".replace(",", ".") + "đ"


def _discount_percent(price: Any, compare_at_price: Any) -> int | None:
    price_num = _safe_float(price)
    compare_num = _safe_float(compare_at_price)

    if compare_num > price_num > 0:
        return int(round((compare_num - price_num) / compare_num * 100))

    return None


def _normalize_price_fields(product: dict) -> dict:
    """
    Chuẩn hóa giá ở cấp sản phẩm.

    Ưu tiên:
    - compare_at_price mới.
    - fallback old_price nếu model/template cũ vẫn còn dùng.
    """
    if not product:
        return product

    price = _safe_int(product.get("price"), 0)
    compare_at_price = _safe_int(
        product.get("compare_at_price") or product.get("old_price"),
        0,
    )
    cost_price = _safe_int(product.get("cost_price"), 0)

    if compare_at_price <= price:
        compare_at_price = 0

    discount = _discount_percent(price, compare_at_price)

    product["price"] = price
    product["compare_at_price"] = compare_at_price or None
    product["old_price"] = compare_at_price or None
    product["cost_price"] = cost_price or None

    product["price_formatted"] = _format_vnd(price)
    product["compare_at_price_formatted"] = (
        _format_vnd(compare_at_price) if compare_at_price else None
    )
    product["old_price_formatted"] = product["compare_at_price_formatted"]
    product["cost_price_formatted"] = _format_vnd(cost_price) if cost_price else None

    product["discount_percent"] = discount
    product["has_discount"] = discount is not None

    return product


def _normalize_variant(
    variant: dict,
    base_price: int,
    base_compare_at_price: int | None = None,
    allow_backorder: bool = False,
) -> dict:
    """
    Chuẩn hóa một biến thể.

    Logic giá:
    - effective_price = price_override nếu có, ngược lại dùng product.price.
    - effective_compare_at_price:
        1. dùng variant.compare_at_price nếu có và > effective_price
        2. nếu không có, dùng product.compare_at_price nếu > effective_price
        3. không thì None
    """
    if not variant:
        return variant

    stock = _safe_int(variant.get("stock"), 0)

    price_override = _safe_int(variant.get("price_override"), 0)
    effective_price = price_override or base_price

    variant_compare_at_price = _safe_int(variant.get("compare_at_price"), 0)
    product_compare_at_price = _safe_int(base_compare_at_price, 0)

    if variant_compare_at_price > effective_price:
        effective_compare_at_price = variant_compare_at_price
    elif product_compare_at_price > effective_price:
        effective_compare_at_price = product_compare_at_price
    else:
        effective_compare_at_price = 0

    discount = _discount_percent(effective_price, effective_compare_at_price)

    color_name = variant.get("color_name") or "Mặc định"
    color_hex = variant.get("color_hex") or "#3b2414"

    variant["color_name"] = color_name
    variant["color_hex"] = color_hex

    variant["stock"] = stock
    variant["is_in_stock"] = stock > 0
    variant["is_available"] = stock > 0 or bool(allow_backorder)

    variant["price_override"] = price_override or None
    variant["effective_price"] = effective_price
    variant["effective_price_formatted"] = _format_vnd(effective_price)

    variant["compare_at_price"] = effective_compare_at_price or None
    variant["effective_compare_at_price"] = effective_compare_at_price or None
    variant["effective_compare_at_price_formatted"] = (
        _format_vnd(effective_compare_at_price) if effective_compare_at_price else None
    )

    variant["discount_percent"] = discount
    variant["has_discount"] = discount is not None

    variant["sku"] = variant.get("sku") or None
    variant["barcode"] = variant.get("barcode") or None

    return variant


def _normalize_product_for_storefront(product: dict) -> dict:
    """
    Chuẩn hóa product trước khi đưa vào template storefront.
    """
    if not product:
        return product

    product = _normalize_price_fields(product)

    allow_backorder = bool(product.get("allow_backorder"))
    base_price = _safe_int(product.get("price"), 0)
    base_compare_at_price = _safe_int(product.get("compare_at_price"), 0)

    variants = product.get("product_variants") or []

    normalized_variants = [
        _normalize_variant(
            variant=v,
            base_price=base_price,
            base_compare_at_price=base_compare_at_price,
            allow_backorder=allow_backorder,
        )
        for v in variants
    ]

    product["product_variants"] = normalized_variants
    product["variants"] = normalized_variants

    if normalized_variants:
        total_stock = sum(_safe_int(v.get("stock"), 0) for v in normalized_variants)
    else:
        total_stock = _safe_int(product.get("stock"), 0)

    low_stock_threshold = _safe_int(product.get("low_stock_threshold"), 5)

    product["stock"] = total_stock
    product["total_stock"] = total_stock
    product["allow_backorder"] = allow_backorder
    product["is_in_stock"] = total_stock > 0
    product["is_available"] = total_stock > 0 or allow_backorder
    product["is_low_stock"] = 0 < total_stock <= low_stock_threshold
    product["stock_status"] = _get_stock_status(total_stock, allow_backorder, low_stock_threshold)

    # SEO fallback cho product detail.
    product["seo_title"] = (
        product.get("seo_title")
        or product.get("meta_title")
        or product.get("name")
    )

    product["seo_description"] = (
        product.get("seo_description")
        or product.get("meta_description")
        or _clean(product.get("description"))
        or ""
    )

    product["description_html"] = (
        product.get("description_html")
        or product.get("description")
        or ""
    )

    return product


def _get_stock_status(stock: int, allow_backorder: bool, low_stock_threshold: int = 5) -> dict:
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


def _build_color_groups(product: dict) -> dict:
    """
    Build dữ liệu cho trang detail.

    Output ví dụ:
    {
      "Nâu Espresso": {
        "hex": "#3b2414",
        "total_stock": 12,
        "is_available": true,
        "sizes": [
          {
            "variant_id": "...",
            "size": "M",
            "stock": 3,
            "price": 199000,
            "price_formatted": "199.000đ",
            "compare_at_price": 249000,
            "compare_at_price_formatted": "249.000đ",
            "discount_percent": 20,
            "is_available": true
          }
        ]
      }
    }
    """
    groups: dict = {}

    if not product:
        return groups

    allow_backorder = bool(product.get("allow_backorder"))
    variants = product.get("product_variants") or []

    for variant in variants:
        color_name = variant.get("color_name") or "Mặc định"
        color_hex = variant.get("color_hex") or "#3b2414"
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


def _normalize_product_list(products: list[dict]) -> list[dict]:
    return [_normalize_product_for_storefront(p) for p in (products or [])]


# ═══════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════

@products_bp.route("/")
def index():
    try:
        featured_result = ProductModel.get_all(page=1, per_page=8)
        featured = _normalize_product_list(featured_result.get("items", []))
    except Exception as e:
        logger.error("[index] featured: %s", e, exc_info=True)
        featured = []

    try:
        collections = CollectionModel.get_all(admin_mode=False)
    except Exception as e:
        logger.error("[index] collections: %s", e, exc_info=True)
        collections = []

    return render_template(
        "products/index.html",
        featured_products=featured,
        collections=collections,
    )


@products_bp.route("/shop")
def shop():
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    per_page = 30

    category_slug = _clean(request.args.get("category"))
    collection_slug = _clean(request.args.get("collection"))
    gender = _clean(request.args.get("gender"))
    keyword = _clean(request.args.get("q"))

    try:
        result = ProductModel.get_all(
            page=page,
            per_page=per_page,
            category_slug=category_slug,
            collection_slug=collection_slug,
            gender=gender,
            keyword=keyword,
        )

        products_list = _normalize_product_list(result.get("items", []))
        total_items = _safe_int(result.get("total"), 0)

    except Exception as e:
        logger.error("[shop] get_all: %s", e, exc_info=True)
        products_list, total_items = [], 0

    return render_template(
        "products/shop.html",
        products=products_list,
        total=total_items,
        total_pages=max(1, ceil(total_items / per_page)),
        page=page,
        category=category_slug,
        collection=collection_slug,
        current_gender=gender,
        keyword=keyword,
    )


@products_bp.route("/product/<slug>")
def detail(slug: str):
    if not slug or slug in ("None", "null", "undefined", ""):
        flash("Đường dẫn sản phẩm không hợp lệ.", "warning")
        return redirect(url_for("products.shop"))

    try:
        product = ProductModel.get_by_slug(slug)
    except Exception as e:
        logger.error("[detail] get_by_slug '%s': %s", slug, e, exc_info=True)
        product = None

    if not product:
        flash("Sản phẩm không tồn tại hoặc đã ngừng kinh doanh.", "warning")
        return redirect(url_for("products.shop"))

    product = _normalize_product_for_storefront(product)
    product["color_groups"] = _build_color_groups(product)

    # Default variant để template/JS có giá đầu tiên đúng.
    default_variant = None
    for variant in product.get("product_variants") or []:
        if variant.get("is_available"):
            default_variant = variant
            break

    if not default_variant and product.get("product_variants"):
        default_variant = product["product_variants"][0]

    product["default_variant"] = default_variant

    related = []

    try:
        product_categories = product.get("product_categories") or []
        category_slug = None

        if product_categories:
            first_category = product_categories[0].get("categories") or {}
            category_slug = first_category.get("slug")

        if category_slug:
            related_result = ProductModel.get_all(
                page=1,
                per_page=8,
                category_slug=category_slug,
            )

            related = [
                item
                for item in _normalize_product_list(related_result.get("items", []))
                if item.get("id") != product.get("id")
            ][:4]

    except Exception as e:
        logger.warning("[detail] related: %s", e, exc_info=True)

    return render_template(
        "products/detail.html",
        product=product,
        related_products=related,
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

    matched = []

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
                .select(
                    "*, "
                    "product_categories(categories(name, slug)), "
                    "collection_products(collections(name, slug)), "
                    "product_images(*), "
                    "product_variants(*)"
                )
                .in_("id", ids)
                .eq("is_active", True)
                .is_("deleted_at", "null")
                .execute()
            )

            matched = [
                _normalize_product_for_storefront(ProductModel._format_product(product))
                for product in (result.data or [])
            ]

        flash(
            f"Tìm thấy {len(matched)} thiết kế tương tự." if matched else "Không tìm thấy sản phẩm phù hợp.",
            "success" if matched else "info",
        )

    except requests.exceptions.Timeout:
        flash("AI Engine timeout. Vui lòng thử lại sau.", "danger")
        return redirect(request.referrer or url_for("products.shop"))

    except Exception as e:
        logger.error("[visual_search]: %s", e, exc_info=True)
        flash("Lỗi kết nối máy chủ AI.", "danger")
        return redirect(request.referrer or url_for("products.shop"))

    return render_template(
        "products/shop.html",
        products=matched,
        total=len(matched),
        keyword="Kết quả Visual Search",
        category=None,
        collection=None,
        current_gender=None,
        page=1,
        total_pages=1,
    )


@products_bp.route("/collections")
def collections():
    try:
        all_collections = CollectionModel.get_all(admin_mode=False)
    except Exception as e:
        logger.error("[collections]: %s", e, exc_info=True)
        all_collections = []

    return render_template(
        "products/collections.html",
        collections=all_collections,
    )


@products_bp.route("/about")
def about():
    return render_template("partials/about.html")


@products_bp.route("/contact")
def contact():
    return render_template("partials/contact.html")


@products_bp.route("/size-guide")
def size_guide():
    return render_template("products/size_guide.html")