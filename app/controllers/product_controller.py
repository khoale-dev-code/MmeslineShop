"""
app/controllers/product_controller.py
======================================
Quản lý luồng hiển thị sản phẩm Storefront.
Tích hợp AI Visual Search và xử lý Biến thể (Variants) chuẩn E-commerce.
"""

import logging
from nicegui import app
import requests
from flask import (
    Blueprint, render_template, request,
    current_app, flash, redirect, url_for,
)

from typing import Optional
from app.models.product_model import ProductModel
from app.utils.supabase_client import get_supabase
from app.models.category_model import CategoryModel
products_bp = Blueprint("products", __name__)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════


def _get_ai_headers() -> dict:
    """Trả về Authorization header nếu HF Space đang ở chế độ Private."""
    token = current_app.config.get("HF_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _build_color_groups(variants: list, base_price: float) -> dict:
    """
    Gom nhóm product_variants theo màu sắc.
    Trả về dict: { color_name: { hex, sizes: [...] } }
    """
    color_groups: dict = {}
    for v in variants:
        c_name = v.get("color_name")
        if not c_name:
            continue
        if c_name not in color_groups:
            color_groups[c_name] = {
                "hex": v.get("color_hex") or "#1a1a1a",
                "sizes": [],
            }
        color_groups[c_name]["sizes"].append({
            "variant_id": v["id"],
            "size": v.get("size"),
            "stock": int(v.get("stock") or 0),
            "price": float(v.get("price_override") or base_price or 0),
        })
    return color_groups


def _clean_str(val) -> Optional[str]:
    """Trả về None nếu chuỗi rỗng — tránh query DB với param trống."""
    v = (val or "").strip()
    return v if v else None

# ═══════════════════════════════════════════════════════════════
#  STOREFRONT ROUTES
# ═══════════════════════════════════════════════════════════════


@products_bp.route("/")
def index():
    """Trang chủ — Hiển thị sản phẩm nổi bật."""
    try:
        # Lấy sản phẩm nổi bật
        res = ProductModel.get_all(page=1, per_page=8, admin_mode=False)
        featured = res.get("items", [])
    except Exception as e:
        logger.error(f"[index] Lỗi kéo sản phẩm nổi bật: {e}")
        featured = []

    try:
        # Lấy 9 danh mục đã được ghim lên trang chủ
        homepage_categories = CategoryModel.get_homepage_categories(limit=9)
    except Exception as e:
        logger.error(f"[index] Lỗi kéo danh mục trang chủ: {e}")
        homepage_categories = []

    # TRUYỀN CẢ 2 BIẾN RA NGOÀI HTML
    return render_template(
        "products/index.html",
        featured_products=featured,
        categories=homepage_categories  # <-- Biến này sẽ giúp sửa triệt để lỗi UndefinedError
    )


@products_bp.route("/shop")
def shop():
    """
    Trang danh sách sản phẩm.
    Query params: ?page= | ?category= | ?gender= | ?q=
    """
    # ── Parse & sanitize params ──
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    category_slug = _clean_str(request.args.get("category"))
    gender = _clean_str(request.args.get("gender"))
    keyword = _clean_str(request.args.get("q"))

    # ── Kéo danh sách sản phẩm ──
    try:
        result = ProductModel.get_all(
            page=page,
            per_page=30,  # 🔴 CẬP NHẬT: Tăng từ 12 lên 30 để phục vụ hiệu ứng Load More
            category_slug=category_slug,
            gender=gender,
            keyword=keyword,
            admin_mode=False,
        )
    except Exception as e:
        logger.error(f"[shop] Lỗi ProductModel.get_all: {e}")
        result = {"items": [], "total": 0}

    # 🔴 CẬP NHẬT: Thay đổi thuật toán tính tổng số trang khớp với limit 30
    total_pages = max(1, (result["total"] + 29) // 30)

    return render_template(
        "products/shop.html",
        products=result["items"],
        total=result["total"],
        total_pages=total_pages,
        page=page,
        # Tên biến phải khớp CHÍNH XÁC với shop.html
        category=category_slug,  # tab active check + build URL phân trang
        current_gender=gender,
        keyword=keyword,
    )


@products_bp.route("/product/<slug>")
def detail(slug: str):
    """
    Trang chi tiết sản phẩm theo slug.
    - Slug không hợp lệ  → redirect shop (không flash)
    - Sản phẩm không tồn tại → redirect shop + flash warning
    """
    # ── Guard: slug không hợp lệ ──
    if not slug or slug in ("None", "null", "undefined", ""):
        flash("Đường dẫn sản phẩm không hợp lệ.", "warning")
        return redirect(url_for("products.shop"))

    # ── Kéo dữ liệu sản phẩm ──
    try:
        product = ProductModel.get_by_slug(slug)
    except Exception as e:
        logger.error(f"[detail] Lỗi get_by_slug('{slug}'): {e}")
        product = None

    if not product:
        flash("Sản phẩm không tồn tại hoặc đã ngừng kinh doanh.", "warning")
        return redirect(url_for("products.shop"))

    # ── Gom nhóm biến thể theo màu ──
    product["color_groups"] = _build_color_groups(
        variants=product.get("product_variants") or [],
        base_price=float(product.get("price") or 0),
    )

    # ── Sản phẩm liên quan (cùng danh mục, loại trừ SP hiện tại) ──
    related_products: list = []
    try:
        cat_slug = (product.get("categories") or {}).get("slug")
        if cat_slug:
            related_res = ProductModel.get_all(page=1, per_page=5, category_slug=cat_slug)
            related_products = [
                p for p in related_res.get("items", [])
                if p["id"] != product["id"]
            ][:4]
    except Exception as e:
        logger.warning(f"[detail] Không lấy được related products: {e}")

    return render_template(
        "products/detail.html",
        product=product,
        related_products=related_products,
    )

# ═══════════════════════════════════════════════════════════════
#  AI VISUAL SEARCH
# ═══════════════════════════════════════════════════════════════


@products_bp.route("/visual-search", methods=["POST"])
def visual_search():
    """
    Tìm kiếm sản phẩm bằng hình ảnh qua Hugging Face AI Engine.
    Kết quả AI được map lại với DB để đảm bảo dữ liệu real-time.
    """
    # ── Validate file upload (dùng "in" để bypass lỗi PyDev với ImmutableMultiDict) ──
    file = request.files["image"] if "image" in request.files else None
    if not file or not file.filename:
        flash("Vui lòng tải lên một hình ảnh để tìm kiếm.", "warning")
        return redirect(request.referrer or url_for("products.shop"))

    # ── Validate config ──
    engine_url = current_app.config.get("AI_ENGINE_URL")
    if not engine_url:
        logger.error("[visual_search] AI_ENGINE_URL chưa được cấu hình.")
        flash("Hệ thống AI chưa được cấu hình. Vui lòng liên hệ quản trị viên.", "danger")
        return redirect(request.referrer or url_for("products.shop"))

    matched_products: list = []

    try:
        # ── Gọi AI Engine ──
        response = requests.post(
            f"{engine_url}/search",
            files={"image": (file.filename, file.stream, file.mimetype)},
            headers=_get_ai_headers(),
            timeout=20,
        )
        response.raise_for_status()

        ai_results = response.json().get("results", [])
        matched_product_ids = [item["id"] for item in ai_results if "id" in item]

        # ── Map kết quả AI với DB (real-time, bỏ qua SP bị ẩn/xoá) ──
        if matched_product_ids:
            try:
                db = get_supabase()
                db_res = (
                    db.table("products")
                    .select("*, categories(name, slug), product_images(*), product_variants(*)")
                    .in_("id", matched_product_ids)
                    .eq("is_active", True)
                    .is_("deleted_at", "null")
                    .execute()
                )
                matched_products = db_res.data or []
            except Exception as db_err:
                logger.error(f"[visual_search] Lỗi map DB: {db_err}")

        flash(
            f"Tìm thấy {len(matched_products)} thiết kế tương tự." if matched_products
            else "Không tìm thấy sản phẩm phù hợp với hình ảnh này.",
            "success" if matched_products else "info",
        )

    except requests.exceptions.Timeout:
        logger.error("[visual_search] AI Engine timeout.")
        flash("Hệ thống AI đang xử lý quá tải. Vui lòng thử lại sau.", "danger")
        return redirect(request.referrer or url_for("products.shop"))

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"[visual_search] AI Engine HTTP error: {http_err}")
        flash("Hệ thống AI trả về lỗi. Vui lòng thử lại.", "danger")
        return redirect(request.referrer or url_for("products.shop"))

    except Exception as e:
        logger.error(f"[visual_search] Lỗi không xác định: {e}", exc_info=True)
        flash("Lỗi kết nối đến máy chủ AI.", "danger")
        return redirect(request.referrer or url_for("products.shop"))

    return render_template(
        "products/shop.html",
        products=matched_products,
        total=len(matched_products),
        keyword="Kết quả Visual Search",
        category=None,
        current_gender=None,
        page=1,
        total_pages=1,
    )


@products_bp.route("/collections")
def collections():
    """
    Trang hiển thị tất cả Bộ sưu tập (Danh mục).
    Khác với trang chủ (chỉ hiện danh mục ghim), trang này hiện TẤT CẢ danh mục đang Active.
    """
    try:
        # Lấy tất cả danh mục có trạng thái is_active = True
        all_cats = CategoryModel.get_all(active_only=True)
    except Exception as e:
        logger.error(f"[collections] Lỗi kéo danh mục: {e}")
        all_cats = []

    return render_template("products/collections.html", categories=all_cats)
     
# ═══════════════════════════════════════════════════════════════
#  STATIC PAGES (GIỚI THIỆU & LIÊN HỆ)
# ═══════════════════════════════════════════════════════════════


@products_bp.route("/about")
def about():
    """Trang giới thiệu thương hiệu GUA Maison."""
    # Trỏ đúng vào thư mục partials theo ý bạn
    return render_template("partials/about.html")


@products_bp.route("/contact")
def contact():
    """Trang liên hệ chăm sóc khách hàng."""
    # Trỏ đúng vào thư mục partials theo ý bạn
    return render_template("partials/contact.html")


# Khai báo đường dẫn /size-guide
@products_bp.route('/size-guide')  # (Hoặc @shop_bp.route tùy vào cách bạn thiết lập Blueprint)
def size_guide():
    # Render file size_guide.html nằm trong thư mục templates/products
    return render_template('products/size_guide.html')

