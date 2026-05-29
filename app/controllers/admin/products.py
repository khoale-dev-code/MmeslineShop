"""
app/controllers/admin/products.py
Tích hợp: Variants, SEO, Soft Delete, Filter.
"""

import logging
from flask import render_template, redirect, url_for, flash, request, current_app

from app.models.product_model import ProductModel
from app.models.category_model import CategoryModel
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
        "category_id": form.get("category_id") or None,
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
        
        # 🔴 BẢN CẬP NHẬT: Không ép mặc định thành #1a1a1a nữa
        hex_color = hexes[i].strip() if i < len(hexes) else ""
        if not hex_color.startswith("#"):
            hex_color = None  # Để rỗng (null) để Model xử lý tự động

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

# ── Routes ────────────────────────────────────────────────────────


@admin_bp.route("/products")
@admin_required
@handle_errors("Lỗi tải sản phẩm.")
def products():
    args = _args()
    per_page_cfg = current_app.config.get("ADMIN_PRODUCTS_PER_PAGE", 15)
    page, per_page, _ = _paginate(args, per_page_cfg)
    keyword = args.get("q", "").strip()
    status = args.get("status", "").strip()

    db = _db()
    query = db.table("products").select("*, categories(name), barcode", count="exact")

    if keyword:
        # Tìm theo tên hoặc barcode
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
    if request.method == "POST":
        form = _form()
        prod = ProductModel.create(_product_data_from_form(form))
        if prod:
            pid = prod["id"]
            _handle_images_on_save(pid, form)
            _save_product_variants(_db(), pid)
            flash(f"Đã thêm: {form.get('name', '').strip()}", "success")
            return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", product=None, cats=cats)

@admin_bp.route("/products/edit/<pid>", methods=["GET", "POST"])
@admin_required
@handle_errors("Lỗi cập nhật.", "admin.products")
def edit_product(pid):
    product = ProductModel.get_by_id(pid)
    cats = CategoryModel.get_all()
    if not product:
        flash("Sản phẩm không tồn tại.", "danger")
        return redirect(url_for("admin.products"))

    if request.method == "POST":
        form = _form()
        
         
        is_updated = ProductModel.update(pid, _product_data_from_form(form))
        
        if is_updated:
            _handle_images_on_save(pid, form)
            _save_product_variants(_db(), pid)
            flash("Lưu sản phẩm thành công!", "success")
            return redirect(url_for("admin.products"))
        else:
            # Nếu thất bại, giữ người dùng lại form và báo lỗi cho họ biết
            flash("Cập nhật thất bại. Vui lòng kiểm tra lỗi cấu trúc cột hoặc quyền RLS trong Terminal!", "danger")

    product["images"] = ProductModel.get_images(pid)
    return render_template("admin/product_form.html", product=product, cats=cats)

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
# ── Categories Routes ──────────────────


@admin_bp.route("/categories")
@admin_required
def categories():
    return render_template("admin/categories.html", cats=CategoryModel.get_all())


@admin_bp.route("/categories/add", methods=["POST"])
@admin_required
def add_category():
    form = _form()
    name = form.get("name", "").strip()
    slug = form.get("slug", "").strip() or ProductModel.generate_slug(name)
    
    # 🔴 ĐÃ THÊM: Hứng dữ liệu từ giao diện Admin
    description = form.get("description", "").strip()
    is_active = "is_active" in form
    show_on_home = "show_on_home" in form
    
    external_url = form.get("external_url", "").strip()
    image_url = None
    video_url = None

    # Xử lý: Ưu tiên nhận link dán vào
    if external_url:
        if external_url.lower().endswith('.mp4') or 'video' in external_url.lower():
            video_url = external_url
        else:
            image_url = external_url
            
    # Xử lý: Hứng file upload từ máy tính
    elif "category_media" in request.files:
        file = request.files["category_media"]
        if file and file.filename:
            url = CategoryModel.upload_media(file.read(), file.filename, file.content_type)
            if url:
                if "video" in (file.content_type or ""):
                    video_url = url
                else:
                    image_url = url

    if name and slug:
        # 🔴 ĐÃ THÊM: Lưu các trường mới vào Database
        CategoryModel.create({
            "name": name,
            "slug": slug,
            "description": description,
            "is_active": is_active,
            "show_on_home": show_on_home,
            "image_url": image_url,
            "video_url": video_url
        })
        flash(f"Đã thêm danh mục: {name}", "success")
    else:
        flash("Tên danh mục không hợp lệ.", "danger")
        
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
        slug = form.get("slug", "").strip() or ProductModel.generate_slug(name)
        
        # 🔴 ĐÃ THÊM: Hứng dữ liệu từ giao diện Admin
        description = form.get("description", "").strip()
        is_active = "is_active" in form
        show_on_home = "show_on_home" in form
        
        external_url = form.get("external_url", "").strip()
        image_url = None
        video_url = None

        if external_url:
            if external_url.lower().endswith('.mp4') or 'video' in external_url.lower():
                video_url = external_url
            else:
                image_url = external_url
        elif "category_media" in request.files:
            file = request.files["category_media"]
            if file and file.filename:
                url = CategoryModel.upload_media(file.read(), file.filename, file.content_type)
                if url:
                    if "video" in (file.content_type or ""):
                        video_url = url
                    else:
                        image_url = url

        if name and slug:
            # 🔴 ĐÃ THÊM: Lưu các trường mới vào Database
            CategoryModel.update(cat_id, {
                "name": name,
                "slug": slug,
                "description": description,
                "is_active": is_active,
                "show_on_home": show_on_home,
                "image_url": image_url,
                "video_url": video_url
            })
            flash("Cập nhật danh mục thành công!", "success")
            return redirect(url_for("admin.categories"))
        else:
            flash("Tên danh mục không hợp lệ.", "danger")

    return render_template("admin/category_form.html", cat=cat)


@admin_bp.route("/categories/delete/<cat_id>", methods=["POST"])
@admin_required
@handle_errors("Lỗi xóa danh mục.", "admin.categories")
def delete_category(cat_id):
    CategoryModel.delete(cat_id)
    flash("Đã xóa danh mục.", "success")
    return redirect(url_for("admin.categories"))
