"""
app/controllers/admin/products.py
=================================
Tích hợp quản lý: Products (Sản phẩm & Biến thể), Categories (Danh mục ngành hàng cứng),
và Campaign Collections (Bộ sưu tập hình ảnh/video kéo thả trang chủ).

BẢN CẬP NHẬT:
- Loại bỏ dấu ngoặc nhọn thừa gây crash SyntaxError ở cuối file.
- Ép hàm hiển thị danh sách bộ sưu tập chạy qua admin_mode=True để xử lý triệt để lỗi ẩn hình do RLS.
- FIX LOGIC (HOTFIX): Bắt đúng tên trường category_id và collection_id từ Form HTML và dùng Admin Client.
"""

import logging
from flask import render_template, redirect, url_for, flash, request, current_app
from app.utils.supabase_client import get_supabase_admin
from app.models.product_model import ProductModel
from app.models.category_model import CategoryModel
from app.models.collection_model import CollectionModel
from app.middleware.auth_required import admin_required

from . import admin_bp
from ._helpers import (
    handle_errors, _args, _form, _getlist, _filelist,
    _db, _paginate, _total_pages, _allowed_file, SLUG_RE,
)

logger = logging.getLogger(__name__)

# ── Form parsing ─────────────────────────────────────────────────

def _product_data_from_form(form: dict) -> dict:
    tags_raw = form.get("tags", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

    slug = form.get("slug", "").strip()
    if not slug and form.get("name"):
        slug = ProductModel.generate_slug(form.get("name"))

    return {
        "name": form.get("name", "").strip(),
        "slug": slug,
        "description": form.get("description", ""),
        "price": float(form.get("price", 0)),
        "thumbnail_url": form.get("thumbnail_url", "").strip() or None,
        "is_featured": "is_featured" in form,
        "is_active": "is_active" in form,
        "meta_title": form.get("meta_title", "").strip() or None,
        "meta_description": form.get("meta_description", "").strip() or None, 
        "gender": form.get("gender", "").strip() or None,
        "tags": tags,
    }

# ── Image helpers ────────────────────────────────────────────────

def _extract_image_urls() -> list[str]:
    seen, result = set(), []
    for raw in _getlist("image_urls"):
        u = raw.strip()
        if u and u not in seen:
            seen.add(u)
            result.append(u)
    return result


def _handle_images_on_save(pid: str, form_dict: dict) -> None:
    uploaded = []
    for file in _filelist("image_files"):
        if file and _allowed_file(file.filename):
            try:
                url = ProductModel.upload_to_storage(
                    file.read(), file.filename, file.content_type or "image/jpeg"
                )
                if url:
                    uploaded.append(url)
            except Exception:
                pass

    all_urls = list(dict.fromkeys(uploaded + _extract_image_urls()))
    if not (all_urls or form_dict.get("_images_synced")):
        return

    ProductModel.sync_images(pid, all_urls)
    images = ProductModel.get_images(pid)
    thumb = next((img for img in images if img.get("is_primary")), images[0] if images else None)
    if thumb:
        ProductModel.update(pid, {"thumbnail_url": thumb["url"]})

# ── Variant helpers ───────────────────────────────────────────────

def _save_product_variants(db, pid: str) -> None:
    db.table("product_variants").delete().eq("product_id", pid).execute()

    sizes = _getlist("v_size[]")
    colors = _getlist("v_color[]")
    hexes = _getlist("v_color_hex[]")
    stocks = _getlist("v_stock[]")
    prices = _getlist("v_price_override[]")

    total_stock, variants = 0, []

    for i in range(len(sizes)):
        s, c = sizes[i].strip(), colors[i].strip() if i < len(colors) else ""
        if not s or not c:
            continue

        stk = _safe_int(stocks[i] if i < len(stocks) else "")
        po = _safe_float(prices[i] if i < len(prices) else "")
        
        hex_color = hexes[i].strip() if i < len(hexes) else ""
        if not hex_color.startswith("#"):
            hex_color = None

        total_stock += stk
        variants.append({
            "product_id": pid,
            "size": s,
            "color_name": c,
            "color_hex": hex_color,
            "stock": stk,
            "price_override": po,
        })

    if variants:
        db.table("product_variants").insert(variants).execute()
    db.table("products").update({"stock": total_stock}).eq("id", pid).execute()


def _safe_int(val: str) -> int:
    try: return max(0, int(float(val.strip())))
    except Exception: return 0


def _safe_float(val: str):
    try: return float(val.strip()) if val.strip() else None
    except Exception: return None

# ── Products Routes ────────────────────────────────────────────────────────
@admin_bp.route("/products")
@admin_required
@handle_errors("Lỗi tải sản phẩm.")
def products():
    args = _args()
    per_page_cfg = current_app.config.get("ADMIN_PRODUCTS_PER_PAGE", 15)
    page, per_page, _ = _paginate(args, per_page_cfg)
    keyword = args.get("q", "").strip()
    status = args.get("status", "").strip()

    # 🟢 FIX TẠI ĐÂY: Dùng Admin Client để bypass RLS, lấy full data mảng trung gian
    db = get_supabase_admin() 
    query = db.table("products").select("*, product_categories(categories(id, name)), collection_products(collections(id, name)), barcode", count="exact")

    if keyword:
        query = query.or_(f"name.ilike.%{keyword}%,barcode.ilike.%{keyword}%")

    if status == "active":
        query = query.eq("is_active", True).is_("deleted_at", "null")
    elif status == "hidden":
        query = query.eq("is_active", False).is_("deleted_at", "null")
    elif status == "deleted":
        query = query.filter("deleted_at", "not.is", "null")
    else:
        query = query.is_("deleted_at", "null")

    start, end = (page - 1) * per_page, page * per_page - 1
    try:
        res = query.order("created_at", desc=True).range(start, end).execute()
        products_list = res.data or []
        total = res.count or 0
    except Exception as e:
        products_list, total = [], 0
        current_app.logger.error(f"[Admin Products] Lỗi truy vấn: {e}")

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
    colles = CollectionModel.get_all(admin_mode=True)
    
    if request.method == "POST":
        form = _form()
        prod_payload = _product_data_from_form(form)
        
        prod = ProductModel.create(prod_payload)
        if prod:
            pid = prod["id"]
            
            # 🟢 FIX TẠI ĐÂY: Ép hàm phụ trợ dùng Admin Client để không bị chặn lưu Variants
            db = get_supabase_admin()
            _handle_images_on_save(pid, form)
            _save_product_variants(db, pid)
            
            c_ids = _getlist("category_ids[]") or _getlist("category_ids")
            if not c_ids and form.get("category_id"): 
                c_ids = [form.get("category_id")]
                
            coll_ids = _getlist("collection_ids[]") or _getlist("collection_ids")
            if not coll_ids and form.get("collection_id"): 
                coll_ids = [form.get("collection_id")]
            
            ProductModel.sync_categories(pid, c_ids)
            ProductModel.sync_collections(pid, coll_ids)
            
            flash(f"Đã thêm: {form.get('name', '').strip()}", "success")
            return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", product=None, cats=cats, colles=colles)


@admin_bp.route("/products/edit/<pid>", methods=["GET", "POST"])
@admin_required
@handle_errors("Lỗi cập nhật.", "admin.products")
def edit_product(pid):
    product = ProductModel.get_by_id(pid)
    cats = CategoryModel.get_all()
    colles = CollectionModel.get_all(admin_mode=True)
    
    if not product:
        flash("Sản phẩm không tồn tại.", "danger")
        return redirect(url_for("admin.products"))

    if request.method == "POST":
        form = _form()
        prod_payload = _product_data_from_form(form)
        
        is_updated = ProductModel.update(pid, prod_payload)
        if is_updated:
            
            # 🟢 FIX TẠI ĐÂY: Ép hàm phụ trợ dùng Admin Client
            db = get_supabase_admin()
            _handle_images_on_save(pid, form)
            _save_product_variants(db, pid)
            
            c_ids = _getlist("category_ids[]") or _getlist("category_ids")
            if not c_ids and form.get("category_id"): 
                c_ids = [form.get("category_id")]
                
            coll_ids = _getlist("collection_ids[]") or _getlist("collection_ids")
            if not coll_ids and form.get("collection_id"): 
                coll_ids = [form.get("collection_id")]
            
            ProductModel.sync_categories(pid, c_ids)
            ProductModel.sync_collections(pid, coll_ids)
            
            flash("Lưu sản phẩm thành công!", "success")
            return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", product=product, cats=cats, colles=colles)


@admin_bp.route("/products/delete/<pid>", methods=["POST"])
@admin_required
@handle_errors("Lỗi khi xóa.", "admin.products")
def delete_product(pid):
    if ProductModel.delete(pid, permanent=False):
        flash("Đã đưa sản phẩm vào thùng rác (Ngừng hiển thị).", "success")
    else:
        flash("Lỗi khi xóa.", "danger")
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/upload-async", methods=["POST"])
@admin_required
def upload_product_image_async():
    """API hỗ trợ tải ảnh lên trực tiếp từ giao diện bằng AJAX"""
    if "file" not in request.files:
        return {"error": "Không tìm thấy file ảnh dữ liệu."}, 400
        
    file = request.files["file"]
    if file and file.filename and _allowed_file(file.filename):
        try:
            url = ProductModel.upload_to_storage(
                file.read(), file.filename, file.content_type or "image/jpeg"
            )
            if url:
                return {"url": url}, 200
        except Exception as e:
            return {"error": str(e)}, 500
            
    return {"error": "Định dạng file ảnh không được hệ thống hỗ trợ."}, 400

# ===================================================================
#  CORE CATEGORIES ROUTES (DANH MỤC THUẦN TEXT - SIÊU NHẸ DỰ ÁN)
# ===================================================================

@admin_bp.route("/categories")
@admin_required
def categories():
    return render_template("admin/categories.html", cats=CategoryModel.get_all())


@admin_bp.route("/categories/add", methods=["POST"])
@admin_required
def add_category():
    form = _form()
    name = form.get("name", "").strip()
    slug = form.get("slug", "").strip() or CategoryModel.generate_slug(name)
    description = form.get("description", "").strip()
    is_active = "is_active" in form

    if name:
        CategoryModel.create({
            "name": name,
            "slug": slug,
            "description": description,
            "is_active": is_active
        })
        flash(f"Đã thêm danh mục: {name}", "success")
    else:
        flash("Tên danh mục trống không hợp lệ.", "danger")
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
        name = form.get("name", "").strip()
        slug = form.get("slug", "").strip() or CategoryModel.generate_slug(name)
        description = form.get("description", "").strip()
        is_active = "is_active" in form

        if name:
            CategoryModel.update(cat_id, {
                "name": name,
                "slug": slug,
                "description": description,
                "is_active": is_active
            })
            flash("Cập nhật danh mục thành công!", "success")
            return redirect(url_for("admin.categories"))
        else:
            flash("Tên không hợp lệ.", "danger")

    return render_template("admin/category_form.html", cat=cat)


@admin_bp.route("/categories/delete/<cat_id>", methods=["POST"])
@admin_required
@handle_errors("Lỗi xóa danh mục.", "admin.categories")
def delete_category(cat_id):
    CategoryModel.delete(cat_id)
    flash("Đã xóa danh mục khỏi hệ thống.", "success")
    return redirect(url_for("admin.categories"))

# ===================================================================
#  CAMPAIGN COLLECTIONS ROUTES (BỘ SƯU TẬP TRANG CHỦ - KÉO THẢ VISUAL)
# ===================================================================

@admin_bp.route("/collections")
@admin_required
def collections():
    return render_template("admin/collections.html", colles=CollectionModel.get_all(admin_mode=True))


@admin_bp.route("/collections/add", methods=["GET", "POST"])
@admin_required
@handle_errors("Lỗi thêm bộ sưu tập.", "admin.collections")
def add_collection():
    if request.method == "POST":
        form = _form()
        name = form.get("name", "").strip()
        slug = form.get("slug", "").strip() or CategoryModel.generate_slug(name)
        description = form.get("description", "").strip()
        is_active = "is_active" in form
        show_on_home = "show_on_home" in form

        image_url, video_url = None, None
        ext_url = form.get("external_url", "").strip()

        if ext_url:
            if ext_url.lower().endswith('.mp4') or 'video' in ext_url.lower(): video_url = ext_url
            else: image_url = ext_url
        elif "collection_media" in request.files:
            file = request.files["collection_media"]
            if file and file.filename:
                url = CollectionModel.upload_media(file.read(), file.filename, file.content_type)
                if url:
                    if "video" in (file.content_type or ""): video_url = url
                    else: image_url = url

        if name:
            CollectionModel.create({
                "name": name, "slug": slug, "description": description,
                "is_active": is_active, "show_on_home": show_on_home,
                "image_url": image_url, "video_url": video_url
            })
            flash(f"Đã thêm bộ sưu tập: {name}", "success")
            return redirect(url_for("admin.collections"))

    return render_template("admin/collection_form.html", cat=None)


@admin_bp.route("/collections/edit/<cid>", methods=["GET", "POST"])
@admin_required
@handle_errors("Lỗi cập nhật lookbook.", "admin.collections")
def edit_collection(cid):
    cat = CollectionModel.get_by_id(cid)
    if not cat:
        flash("Bộ sưu tập không tồn tại.", "danger")
        return redirect(url_for("admin.collections"))

    if request.method == "POST":
        form = _form()
        name = form.get("name", "").strip()
        slug = form.get("slug", "").strip() or CategoryModel.generate_slug(name)
        description = form.get("description", "").strip()
        is_active = "is_active" in form
        show_on_home = "show_on_home" in form

        image_url, video_url = cat.get("image_url"), cat.get("video_url")
        ext_url = form.get("external_url", "").strip()

        if ext_url:
            if ext_url.lower().endswith('.mp4') or 'video' in ext_url.lower():
                video_url, image_url = ext_url, None
            else:
                image_url, video_url = ext_url, None
        elif "collection_media" in request.files:
            file = request.files["collection_media"]
            if file and file.filename:
                url = CollectionModel.upload_media(file.read(), file.filename, file.content_type)
                if url:
                    if "video" in (file.content_type or ""): video_url, image_url = url, None
                    else: image_url, video_url = url, None

        if name:
            CollectionModel.update(cid, {
                "name": name, "slug": slug, "description": description,
                "is_active": is_active, "show_on_home": show_on_home,
                "image_url": image_url, "video_url": video_url
            })
            flash("Cập nhật bộ sưu tập thành công!", "success")
            return redirect(url_for("admin.collections"))

    return render_template("admin/collection_form.html", cat=cat)


@admin_bp.route("/collections/delete/<cid>", methods=["POST"])
@admin_required
def delete_collection(cid):
    CollectionModel.delete(cid)
    flash("Đã xóa bộ sưu tập.", "success")
    return redirect(url_for("admin.collections"))


@admin_bp.route("/collections/update-homepage", methods=["POST"])
@admin_required
def update_homepage_layout():
    home_ids = request.form.getlist("home_cats[]")
    db = get_supabase_admin()
    try:
        db.table("collections").update({"show_on_home": False, "sort_order": 0}).eq("show_on_home", True).execute()
        for index, cid in enumerate(home_ids):
            db.table("collections").update({"show_on_home": True, "sort_order": index + 1}).eq("id", cid).execute()
        flash("Đã lưu cấu hình kéo thả Lookbook trang chủ!", "success")
    except Exception as e:
        current_app.logger.error(f"Lỗi kéo thả: {e}")
        flash("Lỗi kết nối gộp luồng.", "danger")
    return redirect(url_for("admin.collections"))