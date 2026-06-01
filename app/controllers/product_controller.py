"""
app/controllers/product_controller.py
======================================
Quản lý luồng hiển thị sản phẩm Storefront dành cho Khách hàng.
Tích hợp hệ thống tìm kiếm bằng hình ảnh (AI Visual Search) và xử lý phân tách 
hoàn toàn giữa Danh mục (Category) và Bộ sưu tập (Collection) chuẩn E-commerce.
"""

import logging
import requests
from flask import Blueprint, render_template, request, current_app, flash, redirect, url_for
from typing import Optional

from app.models.product_model import ProductModel
from app.models.category_model import CategoryModel
from app.models.collection_model import CollectionModel
from app.utils.supabase_client import get_supabase

products_bp = Blueprint("products", __name__)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  INTERNAL HELPERS (HÀM TRỢ GIÚP NỘI BỘ)
# ═══════════════════════════════════════════════════════════════

def _get_ai_headers() -> dict:
    """Trả về Authorization header nếu Hugging Face Space đang ở chế độ Private."""
    token = current_app.config.get("HF_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _build_color_groups(variants: list, base_price: float) -> dict:
    """
    Gom nhóm product_variants theo màu sắc phục vụ trải nghiệm mua sắm Visual.
    Trả về cấu trúc dict: { color_name: { hex, sizes: [...] } }
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
    """Trả về None nếu chuỗi rỗng — tránh query DB với param trống hoặc lỗi cú pháp."""
    v = (val or "").strip()
    return v if v else None

# ═══════════════════════════════════════════════════════════════
#  STOREFRONT ROUTES (LUỒNG HIỂN THỊ TRANG KHÁCH HÀNG)
# ═══════════════════════════════════════════════════════════════

@products_bp.route("/")
def index():
    """Trang chủ Storefront — Nạp hình ảnh/video Bộ sưu tập và sản phẩm nổi bật."""
    try:
        # Lấy sản phẩm nổi bật trưng bày ra trang chủ
        res = ProductModel.get_all(page=1, per_page=8, admin_mode=False)
        featured = res.get("items", [])
    except Exception as e:
        logger.error(f"[index] Lỗi kéo sản phẩm nổi bật: {e}")
        featured = []

    try:
        # 🟢 ĐÃ FIX LOGIC: Thay thế hàm cũ bằng việc gọi CollectionModel lấy các chiến dịch đang hoạt động
        homepage_collections = CollectionModel.get_all(active_only=True)
    except Exception as e:
        logger.error(f"[index] Lỗi kéo bộ sưu tập trang chủ: {e}")
        homepage_collections = []

    # 🟢 TRUYỀN ĐÚNG BIẾN collections RA NGOÀI HTML KHỚP VỚI INDEX.HTML MỚI
    return render_template(
        "products/index.html",
        featured_products=featured,
        collections=homepage_collections
    )


@products_bp.route("/shop")
def shop():
    """
    Trang cửa hàng danh sách sản phẩm.
    Hỗ trợ bộ lọc động học: ?page= | ?category= | ?collection= | ?gender= | ?q=
    """
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    category_slug = _clean_str(request.args.get("category"))
    collection_slug = _clean_str(request.args.get("collection")) # 🟢 THÊM: Hứng bộ lọc Bộ sưu tập từ trang chủ ghim kéo thả
    gender = _clean_str(request.args.get("gender"))
    keyword = _clean_str(request.args.get("q"))

    products_list = []
    total_items = 0

    # 🟢 ĐÃ NÂNG CẤP: Nếu có bộ lọc collection, truy vấn bảng trung gian Nhiều - Nhiều
    if collection_slug:
        try:
            db = get_supabase()
            # Tìm ID bộ sưu tập từ slug trước công khai
            coll_res = db.table("collections").select("id").eq("slug", collection_slug).eq("is_active", True).limit(1).execute()
            if coll_res.data:
                coll_id = coll_res.data[0]["id"]
                # Truy vấn bảng ánh xạ và join sâu lấy thông tin sản phẩm
                offset = (page - 1) * 30
                res = db.table("collection_products")\
                        .select("products(*, categories(name, slug), product_images(*), product_variants(*))", count="exact")\
                        .eq("collection_id", coll_id)\
                        .range(offset, offset + 29)\
                        .execute()
                
                # Khử bóc tách lồng mảng dữ liệu do Supabase trả về
                raw_items = [item["products"] for item in (res.data or []) if item.get("products")]
                products_list = [ProductModel._format_product(p) for p in raw_items if p.get("deleted_at") is None and p.get("is_active") == True]
                total_items = res.count or len(products_list)
        except Exception as coll_err:
            logger.error(f"[shop] Lỗi nạp sản phẩm theo bộ sưu tập '{collection_slug}': {coll_err}")
    else:
        # Nếu là bộ lọc danh mục cứng hoặc tìm kiếm text thông thường
        try:
            result = ProductModel.get_all(
                page=page,
                per_page=30,  # Phục vụ hiệu ứng Load More mượt mà trên Mobile/PC
                category_slug=category_slug,
                gender=gender,
                keyword=keyword,
                admin_mode=False,
            )
            products_list = result.get("items", [])
            total_items = result.get("total", 0)
        except Exception as e:
            logger.error(f"[shop] Lỗi ProductModel.get_all: {e}")

    total_pages = max(1, (total_items + 29) // 30)

    return render_template(
        "products/shop.html",
        products=products_list,
        total=total_items,
        total_pages=total_pages,
        page=page,
        category=category_slug,
        collection=collection_slug, # Truyền ra ngoài để giữ trạng thái bộ lọc phân trang URL
        current_gender=gender,
        keyword=keyword,
    )


@products_bp.route("/product/<slug>")
def detail(slug: str):
    """Trang cấu hình thông tin chi tiết sản phẩm theo đường dẫn tĩnh (Slug)."""
    if not slug or slug in ("None", "null", "undefined", ""):
        flash("Đường dẫn sản phẩm không hợp lệ.", "warning")
        return redirect(url_for("products.shop"))

    try:
        product = ProductModel.get_by_slug(slug)
    except Exception as e:
        logger.error(f"[detail] Lỗi get_by_slug('{slug}'): {e}")
        product = None

    if not product:
        flash("Sản phẩm không tồn tại hoặc đã ngừng kinh doanh.", "warning")
        return redirect(url_for("products.shop"))

    # Gom nhóm biến thể (Kích cỡ, Số lượng tồn, Giá override) theo dải màu sắc trực quan
    product["color_groups"] = _build_color_groups(
        variants=product.get("product_variants") or [],
        base_price=float(product.get("price") or 0),
    )

    # Đề xuất sản phẩm liên quan (Cùng danh mục ngành hàng, loại trừ bản thân sản phẩm hiện tại)
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
#  AI VISUAL SEARCH (TÌM KIẾM BẰNG HÌNH ẢNH)
# ═══════════════════════════════════════════════════════════════

@products_bp.route("/visual-search", methods=["POST"])
def visual_search():
    """Tìm kiếm sản phẩm bằng hình ảnh qua Hugging Face AI Engine."""
    file = request.files["image"] if "image" in request.files else None
    if not file or not file.filename:
        flash("Vui lòng tải lên một hình ảnh để tìm kiếm.", "warning")
        return redirect(request.referrer or url_for("products.shop"))

    engine_url = current_app.config.get("AI_ENGINE_URL")
    if not engine_url:
        logger.error("[visual_search] AI_ENGINE_URL chưa được cấu hình.")
        flash("Hệ thống AI chưa được cấu hình. Vui lòng liên hệ quản trị viên.", "danger")
        return redirect(request.referrer or url_for("products.shop"))

    matched_products = []

    try:
        response = requests.post(
            f"{engine_url}/search",
            files={"image": (file.filename, file.stream, file.mimetype)},
            headers=_get_ai_headers(),
            timeout=20,
        )
        response.raise_for_status()

        ai_results = response.json().get("results", [])
        matched_product_ids = [item["id"] for item in ai_results if "id" in item]

        # Ánh xạ ID nhận từ mô hình AI ngược lại Database để đồng bộ Real-time kho hàng
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
                raw_data = db_res.data or []
                # Format dải cấu trúc ảnh bìa/biến thể
                matched_products = [ProductModel._format_product(p) for p in raw_data]
            except Exception as db_err:
                logger.error(f"[visual_search] Lỗi map DB: {db_err}")

        flash(
            f"Tìm thấy {len(matched_products)} thiết kế tương tự từ kho mẫu GUA Maison." if matched_products
            else "Không tìm thấy sản phẩm phù hợp với hình ảnh này.",
            "success" if matched_products else "info",
        )

    except requests.exceptions.Timeout:
        logger.error("[visual_search] AI Engine timeout.")
        flash("Hệ thống AI đang xử lý quá tải. Vui lòng thử lại sau.", "danger")
        return redirect(request.referrer or url_for("products.shop"))

    except Exception as e:
        logger.error(f"[visual_search] Lỗi không xác định: {e}", exc_info=True)
        flash("Lỗi kết nối đến máy chủ xử lý ảnh AI.", "danger")
        return redirect(request.referrer or url_for("products.shop"))

    return render_template(
        "products/shop.html",
        products=matched_products,
        total=len(matched_products),
        keyword="Kết quả Visual Search",
        category=None,
        collection=None,
        current_gender=None,
        page=1,
        total_pages=1,
    )


@products_bp.route("/collections")
def collections():
    """Trang Lookbook — Hiển thị TOÀN BỘ danh sách Bộ sưu tập chiến dịch đang kích hoạt."""
    try:
        # 🟢 ĐÃ FIX HOÀN TOÀN: Đổi cấu trúc gọi dữ liệu sang CollectionModel chuẩn xác
        all_colles = CollectionModel.get_all(active_only=True)
    except Exception as e:
        logger.error(f"[collections] Lỗi kéo danh sách bộ sưu tập Lookbook: {e}")
        all_colles = []

    return render_template("products/collections.html", collections=all_colles)

# ═══════════════════════════════════════════════════════════════
#  STATIC PAGES (TẤP TIN TINH TĨNH THƯƠNG HIỆU)
# ═══════════════════════════════════════════════════════════════

@products_bp.route("/about")
def about():
    """Trang giới thiệu câu chuyện thương hiệu GUA Maison."""
    return render_template("partials/about.html")


@products_bp.route("/contact")
def contact():
    """Trang liên hệ hỗ trợ vận hành và CSKH."""
    return render_template("partials/contact.html")


@products_bp.route('/size-guide')
def size_guide():
    """Bảng quy chuẩn thông số kích cỡ (Size Guide) sản phẩm thời trang."""
    return render_template('products/size_guide.html')