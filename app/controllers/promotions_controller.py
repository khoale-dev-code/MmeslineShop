"""
app/controllers/promotions_controller.py
========================================
Quản lý trang Voucher / Khuyến mãi dành cho khách hàng Storefront.

Route chính:
- /vouchers
- /promotions

Route chi tiết:
- /vouchers/<code>
- /promotions/<code>

Route QR:
- /api/coupons/qr/<code>
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import segno
from flask import Blueprint, render_template, send_file, redirect, url_for

from app.utils.supabase_client import get_supabase


promotions_bp = Blueprint("promotions", __name__)
logger = logging.getLogger(__name__)


# =========================
# Helpers
# =========================

def _now_iso() -> str:
    """
    Dùng UTC ISO để so sánh với Supabase timestamp.
    Nếu DB của bạn lưu timezone, UTC sẽ ổn định hơn datetime.now().
    """
    return datetime.now(timezone.utc).isoformat()


def _safe_code(code: Any) -> str:
    """
    Chuẩn hóa mã voucher để query DB và tạo QR.
    """
    if not code:
        return ""

    return str(code).strip().upper()


def _fetch_active_coupons() -> list[dict]:
    """
    Lấy danh sách coupon đang hoạt động:
    - is_active = true
    - chưa hết hạn hoặc không có expires_at
    - sắp xếp mới nhất trước
    """
    db = get_supabase()
    now_str = _now_iso()

    res = (
        db.table("coupons")
        .select("*")
        .eq("is_active", True)
        .or_(f"expires_at.is.null,expires_at.gt.{now_str}")
        .order("created_at", desc=True)
        .execute()
    )

    return res.data or []


def _fetch_coupon_by_code(code: str, active_only: bool = True) -> Optional[dict]:
    """
    Lấy chi tiết coupon theo code.

    active_only=True:
    - chỉ lấy coupon đang bật
    - chưa hết hạn hoặc không có hạn
    """
    normalized_code = _safe_code(code)

    if not normalized_code:
        return None

    db = get_supabase()
    query = (
        db.table("coupons")
        .select("*")
        .eq("code", normalized_code)
    )

    if active_only:
        now_str = _now_iso()
        query = (
            query
            .eq("is_active", True)
            .or_(f"expires_at.is.null,expires_at.gt.{now_str}")
        )

    res = query.limit(1).execute()
    data = res.data or []

    return data[0] if data else None


def _render_coupon_list(coupons: list[dict]):
    """
    Render danh sách voucher.

    File template hiện bạn đang dùng:
    app/templates/coupons/index.html
    """
    return render_template("coupons/index.html", coupons=coupons)


def _render_coupon_detail(coupon: dict):
    """
    Render chi tiết voucher.

    File template hiện bạn đang dùng:
    app/templates/coupons/detail.html
    """
    return render_template("coupons/detail.html", coupon=coupon)


# =========================
# Public routes
# =========================

@promotions_bp.route("/vouchers")
@promotions_bp.route("/promotions")
def index():
    """
    Hiển thị danh sách voucher / khuyến mãi đang hoạt động.

    Dùng 2 route để:
    - Navbar mới bấm /vouchers chạy được.
    - Link cũ /promotions vẫn không bị hỏng.
    """
    try:
        coupons = _fetch_active_coupons()
        return _render_coupon_list(coupons)

    except Exception as exc:
        logger.exception("Lỗi tải danh sách voucher storefront: %s", exc)

        # Fallback an toàn để UI không crash.
        return _render_coupon_list([])


@promotions_bp.route("/vouchers/<code>")
@promotions_bp.route("/promotions/<code>")
def detail(code: str):
    """
    Hiển thị chi tiết một voucher cụ thể.

    Hỗ trợ cả:
    - /vouchers/<code>
    - /promotions/<code>
    """
    normalized_code = _safe_code(code)

    if not normalized_code:
      return redirect(url_for("promotions.index"))

    try:
        coupon = _fetch_coupon_by_code(normalized_code, active_only=True)

        if not coupon:
            logger.warning("Không tìm thấy voucher hoặc voucher đã hết hạn: %s", normalized_code)
            return render_template("404.html"), 404

        return _render_coupon_detail(coupon)

    except Exception as exc:
        logger.exception("Lỗi tải chi tiết voucher %s: %s", normalized_code, exc)
        return render_template("404.html"), 404


@promotions_bp.route("/api/coupons/qr/<code>")
def generate_qr(code: str):
    """
    Tạo QR Code PNG từ mã voucher.

    Dùng cho:
    app/templates/coupons/detail.html

    Ví dụ:
    /api/coupons/qr/SUMMER20
    """
    normalized_code = _safe_code(code)

    if not normalized_code:
        return "Mã voucher không hợp lệ", 400

    try:
        qr = segno.make_qr(normalized_code, error="h")

        img_io = io.BytesIO()
        qr.save(
            img_io,
            kind="png",
            scale=10,
            dark="#241207",
            light="#fffaf5",
            border=2,
        )
        img_io.seek(0)

        return send_file(
            img_io,
            mimetype="image/png",
            as_attachment=False,
            download_name=f"{normalized_code}_qr.png",
            max_age=3600,
        )

    except Exception as exc:
        logger.exception("Lỗi tạo QR code cho voucher %s: %s", normalized_code, exc)
        return "Lỗi tạo mã QR", 500