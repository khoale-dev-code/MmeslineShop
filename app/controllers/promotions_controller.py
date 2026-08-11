"""Thin storefront controller for GUAMAISON vouchers."""

from __future__ import annotations

import io
import logging

import segno
from flask import Blueprint, abort, redirect, render_template, send_file, url_for

from app.repositories.coupon_repository import CouponRepository, CouponRepositoryError
from app.services.coupon_service import CouponService

promotions_bp = Blueprint("promotions", __name__)
logger = logging.getLogger(__name__)


def _service() -> CouponService:
    return CouponService(CouponRepository.public())


@promotions_bp.route("/vouchers")
@promotions_bp.route("/promotions")
def index():
    data_unavailable = False
    try:
        coupons = _service().public_list()
    except CouponRepositoryError:
        logger.exception("Không tải được voucher storefront")
        coupons, data_unavailable = [], True
    return render_template(
        "coupons/index.html",
        coupons=coupons,
        featured_coupon=coupons[0] if coupons else None,
        data_unavailable=data_unavailable,
    )


@promotions_bp.route("/vouchers/<code>")
@promotions_bp.route("/promotions/<code>")
def detail(code: str):
    normalized = CouponService.normalize_code(code)
    if not normalized:
        return redirect(url_for("promotions.index"))
    try:
        coupon = _service().public_detail(normalized)
    except CouponRepositoryError:
        logger.exception("Không tải được voucher %s", normalized)
        abort(503)
    if not coupon:
        abort(404)
    return render_template("coupons/detail.html", coupon=coupon)


@promotions_bp.route("/api/coupons/qr/<code>")
def generate_qr(code: str):
    normalized = CouponService.normalize_code(code)
    if not normalized:
        return "Mã voucher không hợp lệ", 400
    try:
        qr = segno.make_qr(normalized, error="h")
        image = io.BytesIO()
        qr.save(image, kind="png", scale=9, dark="#171413", light="#fffaf5", border=2)
        image.seek(0)
        return send_file(
            image,
            mimetype="image/png",
            as_attachment=False,
            download_name=f"{normalized}_qr.png",
            max_age=3600,
        )
    except Exception:
        logger.exception("Không tạo được QR cho %s", normalized)
        return "Lỗi tạo mã QR", 500

