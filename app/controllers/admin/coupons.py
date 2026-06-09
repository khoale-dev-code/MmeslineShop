"""
app/controllers/admin/coupons.py
================================
Quản lý Voucher / Coupon trong Admin.

Fix chính:
- Admin write dùng Supabase service role để tránh lỗi RLS:
  permission denied for table coupons / code 42501.
- Chuẩn hóa code voucher không dấu, viết hoa, chỉ giữ A-Z, 0-9, _, -.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from flask import render_template, redirect, url_for, flash, request

from app.middleware.auth_required import admin_required
from app.utils.supabase_client import get_supabase_admin

from ._blueprint import admin_bp
from ._helpers import (
    handle_errors,
    _args,
    _form,
    _getlist,
    _db,
    _paginate,
    _total_pages,
    _now_iso,
)

logger = logging.getLogger(__name__)


# ── DB helpers ────────────────────────────────────────────────────

def _db_admin():
    """
    Client ghi dữ liệu cho admin.

    Bắt buộc dùng service role key để bypass RLS khi:
    - insert coupons
    - update coupons
    - delete coupons
    - insert/delete coupon_categories, coupon_products
    - đọc các bảng admin bị RLS chặn
    """
    return get_supabase_admin()


def _normalize_coupon_code(value: Any) -> str:
    """
    Chuẩn hóa mã voucher:
    - bỏ dấu tiếng Việt
    - viết hoa
    - bỏ khoảng trắng
    - chỉ giữ A-Z, 0-9, _, -
    """
    raw = str(value or "").strip()

    normalized = unicodedata.normalize("NFD", raw)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = normalized.upper()
    normalized = normalized.replace("Đ", "D")
    normalized = re.sub(r"[^A-Z0-9_-]", "", normalized)

    return normalized


def _empty_to_none(value: Any):
    value = str(value or "").strip()
    return value if value else None


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def _to_float_or_none(value: Any):
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except Exception:
        return None


def _to_int_or_none(value: Any):
    try:
        if value is None or str(value).strip() == "":
            return None

        number = int(float(value))
        return number if number > 0 else None
    except Exception:
        return None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _form_bool(form: dict, key: str, default: bool = False) -> bool:
    """
    Checkbox HTML:
    - checked thường gửi "on" hoặc "1"
    - unchecked không gửi key
    """
    if key not in form:
        return default

    value = str(form.get(key) or "").strip().lower()
    return value in {"1", "true", "on", "yes", "checked"}


def _attach_used_count(db, coupons: list) -> list:
    if not coupons:
        return coupons

    ids = [c.get("id") for c in coupons if c.get("id")]
    count_map = {cid: 0 for cid in ids}

    if not ids:
        return coupons

    try:
        rows = (
            db.table("coupon_usages")
            .select("coupon_id")
            .in_("coupon_id", ids)
            .execute()
            .data
            or []
        )

        for row in rows:
            coupon_id = row.get("coupon_id")
            if coupon_id in count_map:
                count_map[coupon_id] += 1

    except Exception as e:
        logger.warning("Không đếm được coupon_usages: %s", e)

    for c in coupons:
        c["used_count"] = count_map.get(c.get("id"), 0)

    return coupons


def _coupon_scope(db, coupon_id: str) -> tuple[str, list]:
    cats = (
        db.table("coupon_categories")
        .select("category_id")
        .eq("coupon_id", coupon_id)
        .execute()
        .data
        or []
    )

    prods = (
        db.table("coupon_products")
        .select("product_id")
        .eq("coupon_id", coupon_id)
        .execute()
        .data
        or []
    )

    if cats:
        return "category", [c["category_id"] for c in cats]

    if prods:
        return "product", [p["product_id"] for p in prods]

    return "all", []


def _save_coupon_scope(db, coupon_id: str, form: dict) -> None:
    """
    Lưu phạm vi áp dụng:
    - all
    - category
    - product

    Lưu ý: dùng db admin vì bảng phụ thường cũng bị RLS.
    """
    db.table("coupon_categories").delete().eq("coupon_id", coupon_id).execute()
    db.table("coupon_products").delete().eq("coupon_id", coupon_id).execute()

    scope = form.get("scope", "all")

    if scope == "category":
        rows = [
            {"coupon_id": coupon_id, "category_id": cid}
            for cid in _getlist("category_ids")
            if cid
        ]

        if rows:
            db.table("coupon_categories").insert(rows).execute()

    elif scope == "product":
        rows = [
            {"coupon_id": coupon_id, "product_id": pid}
            for pid in _getlist("product_ids")
            if pid
        ]

        if rows:
            db.table("coupon_products").insert(rows).execute()


def _coupon_data_from_form(form: dict) -> dict:
    discount_type = form.get("discount_type", "percent") or "percent"

    if discount_type not in {"percent", "fixed", "free_shipping"}:
        discount_type = "percent"

    discount_value = _to_float(form.get("discount_value"), 0)
    min_order_value = _to_float(form.get("min_order_value"), 0)
    max_discount = _to_float_or_none(form.get("max_discount"))

    if discount_type == "free_shipping":
        discount_value = 0

    if discount_type == "fixed":
        max_discount = None

    applicable_channel = form.get("applicable_channel", "all") or "all"
    if applicable_channel not in {"all", "web", "pos"}:
        applicable_channel = "all"

    return {
        "description": str(form.get("description", "") or "").strip(),
        "discount_type": discount_type,
        "discount_value": discount_value,
        "min_order_value": min_order_value,
        "max_discount": max_discount,
        "usage_limit": _to_int_or_none(form.get("usage_limit")),
        "usage_per_user": _to_int_or_none(form.get("usage_per_user")),
        "expires_at": _empty_to_none(form.get("expires_at")),
        "starts_at": _empty_to_none(form.get("starts_at")),
        "is_stackable": _form_bool(form, "is_stackable", False),
        "is_active": _form_bool(form, "is_active", True),
        "image_url": _empty_to_none(form.get("image_url")),
        "applicable_channel": applicable_channel,
        "min_loyalty_points": _to_int(form.get("min_loyalty_points"), 0),
    }


def _coupon_form_context(db) -> dict:
    return {
        "categories": db.table("categories").select("*").execute().data or [],
        "products": (
            db.table("products")
            .select("id, name, thumbnail_url, price")
            .execute()
            .data
            or []
        ),
    }


def _find_coupon_by_code(db, code: str):
    if not code:
        return None

    res = (
        db.table("coupons")
        .select("id, code")
        .eq("code", code)
        .limit(1)
        .execute()
    )

    rows = res.data or []
    return rows[0] if rows else None


# ── Routes ────────────────────────────────────────────────────────

@admin_bp.route("/coupons")
@admin_required
@handle_errors("Lỗi tải khuyến mãi.")
def coupons():
    args = _args()
    page, per_page, offset = _paginate(args)
    filter_mode = args.get("filter", "all").strip().lower()
    now_str = _now_iso()

    # Dùng admin để tránh RLS chặn khi đọc coupon_usages / coupons trong admin.
    db = _db_admin()

    query = (
        db.table("coupons")
        .select("*", count="exact")
        .order("created_at", desc=True)
    )

    if filter_mode == "active":
        query = query.eq("is_active", True).or_(f"expires_at.is.null,expires_at.gt.{now_str}")
    elif filter_mode == "expired":
        query = query.lt("expires_at", now_str)
    elif filter_mode in ("percent", "fixed", "free_shipping"):
        query = query.eq("discount_type", filter_mode)

    r = query.range(offset, offset + per_page - 1).execute()
    coupons_list = _attach_used_count(db, r.data or [])

    return render_template(
        "admin/coupons.html",
        coupons=coupons_list,
        total=r.count or 0,
        page=page,
        total_pages=_total_pages(r.count or 0, per_page),
        now=now_str,
        filter_mode=filter_mode,
    )


@admin_bp.route("/coupons/add", methods=["GET", "POST"])
@admin_required
def add_coupon():
    db = _db_admin()
    ctx = _coupon_form_context(db)

    if request.method == "POST":
        form = _form()
        code = _normalize_coupon_code(form.get("code"))

        if not code:
            flash("Mã khuyến mãi không hợp lệ. Vui lòng dùng chữ không dấu, số, dấu gạch ngang hoặc gạch dưới.", "danger")
            return render_template("admin/coupons_form.html", coupon=None, **ctx)

        try:
            exists = _find_coupon_by_code(db, code)
            if exists:
                flash(f"Mã '{code}' đã tồn tại. Vui lòng dùng mã khác.", "danger")
                return render_template("admin/coupons_form.html", coupon=None, **ctx)

            payload = {
                "code": code,
                **_coupon_data_from_form(form),
            }

            res = db.table("coupons").insert(payload).execute()
            created_rows = res.data or []

            if not created_rows:
                flash("Không thể tạo voucher. Supabase không trả về dữ liệu sau khi insert.", "danger")
                return render_template("admin/coupons_form.html", coupon=None, **ctx)

            cid = created_rows[0]["id"]

            _save_coupon_scope(db, cid, form)

            flash(f"Đã tạo mã '{code}' thành công!", "success")
            return redirect(url_for("admin.coupons"))

        except Exception as e:
            logger.error("Lỗi tạo coupon: %s", e, exc_info=True)
            flash("Lỗi khi tạo mã. Vui lòng kiểm tra quyền Supabase, mã bị trùng hoặc dữ liệu không hợp lệ.", "danger")

    return render_template("admin/coupons_form.html", coupon=None, **ctx)


@admin_bp.route("/coupons/edit/<coupon_id>", methods=["GET", "POST"])
@admin_required
def edit_coupon(coupon_id):
    db = _db_admin()
    ctx = _coupon_form_context(db)

    if request.method == "POST":
        form = _form()
        code = _normalize_coupon_code(form.get("code"))

        if not code:
            flash("Mã khuyến mãi không hợp lệ.", "danger")
            return redirect(url_for("admin.edit_coupon", coupon_id=coupon_id))

        try:
            exists = _find_coupon_by_code(db, code)

            if exists and str(exists.get("id")) != str(coupon_id):
                flash(f"Mã '{code}' đã được sử dụng cho voucher khác.", "danger")
                return redirect(url_for("admin.edit_coupon", coupon_id=coupon_id))

            data = {
                "code": code,
                **_coupon_data_from_form(form),
            }

            db.table("coupons").update(data).eq("id", coupon_id).execute()
            _save_coupon_scope(db, coupon_id, form)

            flash("Đã cập nhật mã thành công!", "success")
            return redirect(url_for("admin.coupons"))

        except Exception as e:
            logger.error("Lỗi cập nhật coupon %s: %s", coupon_id, e, exc_info=True)
            flash("Lỗi cập nhật mã.", "danger")

    coupon = (
        db.table("coupons")
        .select("*")
        .eq("id", coupon_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not coupon:
        flash("Mã khuyến mãi không tồn tại.", "danger")
        return redirect(url_for("admin.coupons"))

    coupon = coupon[0]

    scope_str, scope_ids = _coupon_scope(db, coupon_id)
    coupon["scope"] = scope_str
    coupon["scope_ids"] = scope_ids
    coupon["used_count"] = _attach_used_count(db, [coupon])[0].get("used_count", 0)

    return render_template("admin/coupons_form.html", coupon=coupon, **ctx)


@admin_bp.route("/coupons/delete/<coupon_id>", methods=["POST"])
@admin_required
@handle_errors("Lỗi khi xóa mã.", "admin.coupons")
def delete_coupon(coupon_id):
    db = _db_admin()

    # Xóa bảng phụ trước để tránh lỗi FK nếu DB không cascade.
    try:
        db.table("coupon_categories").delete().eq("coupon_id", coupon_id).execute()
    except Exception as e:
        logger.warning("Không xóa được coupon_categories của coupon %s: %s", coupon_id, e)

    try:
        db.table("coupon_products").delete().eq("coupon_id", coupon_id).execute()
    except Exception as e:
        logger.warning("Không xóa được coupon_products của coupon %s: %s", coupon_id, e)

    db.table("coupons").delete().eq("id", coupon_id).execute()

    flash("Đã xóa mã giảm giá.", "success")
    return redirect(url_for("admin.coupons"))


@admin_bp.route("/coupons/<coupon_id>/toggle", methods=["POST"])
@admin_required
@handle_errors("Lỗi cập nhật trạng thái.", "admin.coupons")
def toggle_coupon(coupon_id):
    db = _db_admin()

    rows = (
        db.table("coupons")
        .select("is_active, code")
        .eq("id", coupon_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not rows:
        flash("Mã không tồn tại.", "danger")
        return redirect(url_for("admin.coupons"))

    coupon = rows[0]
    new_state = not bool(coupon.get("is_active"))

    db.table("coupons").update({"is_active": new_state}).eq("id", coupon_id).execute()

    flash(f"Đã {'bật' if new_state else 'tắt'} mã '{coupon.get('code')}'.", "success")
    return redirect(url_for("admin.coupons"))


@admin_bp.route("/coupons/<coupon_id>/usages")
@admin_required
@handle_errors("Lỗi tải lịch sử sử dụng.", "admin.coupons")
def coupon_usages(coupon_id):
    db = _db_admin()

    rows = (
        db.table("coupons")
        .select("*")
        .eq("id", coupon_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not rows:
        flash("Mã không tồn tại.", "danger")
        return redirect(url_for("admin.coupons"))

    coupon = rows[0]

    usages = (
        db.table("coupon_usages")
        .select("*, users(full_name, email), orders(id, total_amount, created_at)")
        .eq("coupon_id", coupon_id)
        .order("used_at", desc=True)
        .execute()
        .data
        or []
    )

    return render_template(
        "admin/coupon_usages.html",
        coupon=coupon,
        usages=usages,
        used_count=len(usages),
        total_discount=sum(float(u.get("discount_amount") or 0) for u in usages),
    )