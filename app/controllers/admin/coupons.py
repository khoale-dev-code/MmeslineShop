"""Thin HTTP controller for Admin promotion management."""

from __future__ import annotations

import logging

from flask import flash, redirect, render_template, request, url_for

from app.middleware.auth_required import admin_required
from app.repositories.coupon_repository import CouponRepository, CouponRepositoryError, CouponRepositoryUnavailable
from app.services.coupon_service import CouponConflictError, CouponNotFoundError, CouponService, CouponValidationError

from ._blueprint import admin_bp

logger = logging.getLogger(__name__)


def _service() -> CouponService:
    return CouponService(CouponRepository.admin())


def _page_number() -> int:
    try:
        return max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        return 1


def _form_lists() -> tuple[list[str], list[str]]:
    return request.form.getlist("category_ids"), request.form.getlist("product_ids")


def _render_form(service: CouponService, *, coupon: dict | None = None, form_data: dict | None = None, status: int = 200):
    options = service.form_options()
    return render_template(
        "admin/coupons_form.html",
        coupon=coupon,
        form_data=form_data,
        categories=list(options.categories),
        products=list(options.products),
        form_options_warning=options.warning,
    ), status


@admin_bp.route("/coupons")
@admin_required
def coupons():
    service = _service()
    page, per_page = _page_number(), 20
    filter_mode = str(request.args.get("filter") or "all").strip().lower()
    if filter_mode not in {"all", "active", "expired", "percent", "fixed", "free_shipping"}:
        filter_mode = "all"
    try:
        rows, total = service.admin_page(page, per_page, filter_mode)
    except CouponRepositoryUnavailable:
        logger.exception("Không tải được danh sách coupon")
        flash("Kết nối dữ liệu tạm thời gián đoạn. Vui lòng tải lại trang.", "danger")
        rows, total = [], 0
    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template(
        "admin/coupons.html",
        coupons=rows,
        total=total,
        page=page,
        total_pages=total_pages,
        now=service.now_iso(),
        filter_mode=filter_mode,
    )


@admin_bp.route("/coupons/add", methods=["GET", "POST"])
@admin_required
def add_coupon():
    service = _service()
    if request.method == "GET":
        return _render_form(service)

    form = request.form.to_dict()
    category_ids, product_ids = _form_lists()
    try:
        created = service.create(form, category_ids, product_ids)
        flash(f"Đã tạo mã '{created.get('code')}' và đồng bộ với storefront.", "success")
        return redirect(url_for("admin.coupons"))
    except (CouponValidationError, CouponConflictError) as exc:
        flash(str(exc), "danger")
        form["scope_ids"] = category_ids if form.get("scope") == "category" else product_ids
        return _render_form(service, form_data=form, status=422)
    except CouponRepositoryUnavailable:
        logger.exception("Kết nối Supabase bị gián đoạn khi tạo coupon")
        flash("Kết nối dữ liệu bị gián đoạn; voucher chưa được lưu. Hãy thử lại.", "danger")
        form["scope_ids"] = category_ids if form.get("scope") == "category" else product_ids
        return _render_form(service, form_data=form, status=503)
    except CouponRepositoryError:
        logger.exception("Không tạo được coupon")
        flash("Không thể tạo voucher; mọi thay đổi dở dang đã được hoàn tác.", "danger")
        return _render_form(service, form_data=form, status=500)


@admin_bp.route("/coupons/edit/<coupon_id>", methods=["GET", "POST"])
@admin_required
def edit_coupon(coupon_id: str):
    service = _service()
    if request.method == "POST":
        form = request.form.to_dict()
        category_ids, product_ids = _form_lists()
        try:
            service.update(coupon_id, form, category_ids, product_ids)
            flash("Đã cập nhật voucher và đồng bộ điều kiện áp dụng.", "success")
            return redirect(url_for("admin.coupons"))
        except (CouponValidationError, CouponConflictError) as exc:
            flash(str(exc), "danger")
            form.update({"id": coupon_id, "scope_ids": category_ids if form.get("scope") == "category" else product_ids})
            return _render_form(service, coupon=form, status=422)
        except CouponRepositoryUnavailable:
            logger.exception("Kết nối Supabase bị gián đoạn khi cập nhật coupon %s", coupon_id)
            flash("Kết nối dữ liệu bị gián đoạn; thay đổi chưa được lưu trọn vẹn và đã được hoàn tác khi có thể.", "danger")
            form.update({"id": coupon_id, "scope_ids": category_ids if form.get("scope") == "category" else product_ids})
            return _render_form(service, coupon=form, status=503)
        except CouponRepositoryError:
            logger.exception("Không cập nhật được coupon %s", coupon_id)
            flash("Không thể cập nhật voucher; thay đổi dở dang đã được hoàn tác khi có thể.", "danger")
            return redirect(url_for("admin.edit_coupon", coupon_id=coupon_id))

    try:
        coupon = service.admin_form_coupon(coupon_id)
        return _render_form(service, coupon=coupon)
    except CouponNotFoundError:
        flash("Voucher không tồn tại.", "danger")
        return redirect(url_for("admin.coupons"))
    except CouponRepositoryUnavailable:
        flash("Không tải được voucher do kết nối dữ liệu bị gián đoạn.", "danger")
        return redirect(url_for("admin.coupons"))


@admin_bp.route("/coupons/delete/<coupon_id>", methods=["POST"])
@admin_required
def delete_coupon(coupon_id: str):
    try:
        _service().delete(coupon_id)
        flash("Đã xóa voucher.", "success")
    except CouponNotFoundError:
        flash("Voucher không tồn tại.", "warning")
    except CouponRepositoryError:
        logger.exception("Không xóa được coupon %s", coupon_id)
        flash("Không thể xóa voucher lúc này.", "danger")
    return redirect(url_for("admin.coupons"))


@admin_bp.route("/coupons/<coupon_id>/toggle", methods=["POST"])
@admin_required
def toggle_coupon(coupon_id: str):
    try:
        code, active = _service().toggle(coupon_id)
        flash(f"Đã {'bật' if active else 'tắt'} mã '{code}'.", "success")
    except CouponNotFoundError:
        flash("Voucher không tồn tại.", "warning")
    except CouponRepositoryError:
        logger.exception("Không đổi được trạng thái coupon %s", coupon_id)
        flash("Không thể cập nhật trạng thái voucher.", "danger")
    return redirect(url_for("admin.coupons"))


@admin_bp.route("/coupons/<coupon_id>/usages")
@admin_required
def coupon_usages(coupon_id: str):
    try:
        coupon, usages = _service().usage_history(coupon_id)
    except CouponNotFoundError:
        flash("Voucher không tồn tại.", "danger")
        return redirect(url_for("admin.coupons"))
    except CouponRepositoryError:
        flash("Không tải được lịch sử sử dụng.", "danger")
        return redirect(url_for("admin.coupons"))
    return render_template(
        "admin/coupon_usages.html",
        coupon=coupon,
        usages=usages,
        used_count=len(usages),
        total_discount=sum(float(row.get("discount_amount") or 0) for row in usages),
    )
