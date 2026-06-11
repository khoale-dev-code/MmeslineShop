"""
app/controllers/admin/pos_controller.py
======================================

GUAMAISON POS Controller

Phiên bản POS đầy đủ:
- Trang POS bán hàng tại quầy.
- Load sản phẩm, biến thể, coupon, bảng giá.
- Tra cứu khách hàng theo SĐT.
- Thêm khách hàng mới nhanh từ POS.
- Ghi nhận nhân viên / thu ngân thanh toán đơn.
- Checkout POS:
  + Tiền mặt.
  + Chuyển khoản QR.
  + Coupon.
  + Dùng điểm loyalty.
  + Tích điểm loyalty.
  + Phí vận chuyển.
  + VAT / hóa đơn VAT.
  + Giao hàng sau.
  + Thuộc tính đơn hàng.
  + Ghi chú đơn hàng.
  + Tiền khách đưa / tiền thừa.
  + Trừ kho sản phẩm / biến thể.
- Polling trạng thái chuyển khoản.
- Webhook Casso tự xác nhận thanh toán.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Optional

from flask import jsonify, render_template, request, session

try:
    from flask_login import current_user
except Exception:  # pragma: no cover
    current_user = None

from app.middleware.auth_required import admin_required
from ._blueprint import admin_bp
from ._helpers import handle_errors

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

CASSO_SECRET = os.environ.get("CASSO_SECRET_KEY", "")
STORE_ACCOUNT = os.environ.get("POS_STORE_ACCOUNT", "4890440016335294")

BASE_EARN_RATE = int(os.environ.get("POS_BASE_EARN_RATE", 10000))
POINT_REDEEM_VALUE = int(os.environ.get("POS_POINT_REDEEM_VALUE", 100))
VAT_DEFAULT_RATE = float(os.environ.get("POS_VAT_DEFAULT_RATE", 0.08))

DEFAULT_PRICEBOOK = {
    "id": "default",
    "name": "Bảng giá mặc định",
    "is_default": True,
    "is_active": True,
}


# ═══════════════════════════════════════════════════════════════
# BASIC HELPERS
# ═══════════════════════════════════════════════════════════════

def _db():
    from app.utils.supabase_client import get_supabase
    return get_supabase()


def _db_admin():
    """
    Client service role chỉ dùng server-side.
    Dùng cho các thao tác POS cần ghi DB:
    - insert orders
    - insert order_items
    - update stock
    - loyalty transactions
    - update payment status
    """
    from app.utils.supabase_client import get_supabase_admin
    return get_supabase_admin()


def _now() -> datetime:
    return datetime.now()


def _now_iso() -> str:
    return _now().isoformat()


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "y",
        "enabled",
    }


def _money(value: Any) -> float:
    return max(0.0, _safe_float(value, 0.0))


def _normalize_phone(phone: Any) -> str:
    phone = _safe_str(phone)
    return re.sub(r"[^\d+]", "", phone)


def _first_row(response: Any) -> Optional[dict]:
    data = getattr(response, "data", None) or []
    return data[0] if data else None


def _generate_order_code() -> str:
    return f"POS{_now().strftime('%y%m%d%H%M%S')}"


def _json_error(message: str, status: int = 400, **extra):
    payload = {
        "success": False,
        "message": message,
    }
    payload.update(extra)
    return jsonify(payload), status


def _json_ok(**payload):
    payload.setdefault("success", True)
    return jsonify(payload)


def _format_vnd(value: Any) -> str:
    number = _safe_int(value)
    return f"{number:,.0f}".replace(",", ".") + "đ"


def calculate_points(amount: float) -> int:
    if BASE_EARN_RATE <= 0:
        return 0
    return max(0, int(float(amount or 0) / BASE_EARN_RATE))


def _extract_order_code(description: str) -> Optional[str]:
    match = re.search(r"POS\d{12}", str(description or "").upper())
    return match.group(0) if match else None


def _current_staff_info() -> dict:
    """
    Lấy nhân viên đang đăng nhập để lưu vào đơn POS.
    Hỗ trợ nhiều kiểu session/current_user khác nhau.
    """
    staff_id = None
    staff_name = None
    staff_email = None
    role = None

    try:
        if current_user and getattr(current_user, "is_authenticated", False):
            staff_id = getattr(current_user, "id", None)
            staff_name = (
                getattr(current_user, "full_name", None)
                or getattr(current_user, "name", None)
                or getattr(current_user, "username", None)
                or getattr(current_user, "email", None)
            )
            staff_email = getattr(current_user, "email", None)
            role = getattr(current_user, "role", None)
    except Exception:
        pass

    staff_id = (
        staff_id
        or session.get("user_id")
        or session.get("admin_id")
        or session.get("staff_id")
    )

    staff_name = (
        staff_name
        or session.get("user_name")
        or session.get("admin_name")
        or session.get("staff_name")
        or session.get("full_name")
        or session.get("email")
        or "Nhân viên POS"
    )

    staff_email = (
        staff_email
        or session.get("email")
        or session.get("admin_email")
        or session.get("staff_email")
    )

    role = (
        role
        or session.get("admin_role_slug")
        or session.get("user_role")
        or session.get("role")
        or "staff"
    )

    return {
        "id": staff_id,
        "name": staff_name,
        "email": staff_email,
        "role": role,
    }


def _safe_table_insert(db, table: str, payload: dict, fallback_payload: Optional[dict] = None) -> Optional[dict]:
    """
    Insert an toàn. Nếu bảng/cột optional lỗi, thử fallback tối thiểu.
    """
    try:
        res = db.table(table).insert(payload).execute()
        return _first_row(res)
    except Exception as exc:
        if fallback_payload is None:
            logger.info("[POS] insert %s skipped/failed: %s", table, exc)
            return None

        logger.info("[POS] insert %s fallback: %s", table, exc)
        res = db.table(table).insert(fallback_payload).execute()
        return _first_row(res)


def _safe_table_update(db, table: str, payload: dict, column: str, value: Any) -> bool:
    try:
        db.table(table).update(payload).eq(column, value).execute()
        return True
    except Exception as exc:
        logger.info("[POS] update %s skipped/failed: %s", table, exc)
        return False


# ═══════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════

def _load_pos_products() -> list[dict]:
    """
    Load sản phẩm cho POS.
    Dùng select tương đối đầy đủ cho barcode, SKU, stock, variants.
    Nếu DB thiếu sku/barcode ở products thì fallback select cơ bản.
    """
    db = _db_admin()

    full_select = (
        "id, name, slug, sku, barcode, price, compare_at_price, "
        "stock, thumbnail_url, is_active, deleted_at, "
        "product_variants("
        "id, product_id, size, color_name, color_hex, stock, "
        "price_override, compare_at_price, sku, barcode"
        ")"
    )

    fallback_select = (
        "id, name, slug, price, compare_at_price, "
        "stock, thumbnail_url, is_active, deleted_at, "
        "product_variants("
        "id, product_id, size, color_name, color_hex, stock, "
        "price_override, compare_at_price"
        ")"
    )

    try:
        res = (
            db.table("products")
            .select(full_select)
            .eq("is_active", True)
            .is_("deleted_at", "null")
            .order("name")
            .execute()
        )
    except Exception:
        logger.info("[POS] products sku/barcode columns may not exist. Fallback select used.")
        res = (
            db.table("products")
            .select(fallback_select)
            .eq("is_active", True)
            .is_("deleted_at", "null")
            .order("name")
            .execute()
        )

    products = res.data or []

    for product in products:
        variants = product.get("product_variants") or []

        if variants:
            product["stock"] = sum(_safe_int(v.get("stock")) for v in variants)
        else:
            product["stock"] = _safe_int(product.get("stock"))

        product["price"] = _money(product.get("price"))
        product.setdefault("sku", "")
        product.setdefault("barcode", "")

        for variant in variants:
            variant.setdefault("sku", "")
            variant.setdefault("barcode", "")
            variant["stock"] = _safe_int(variant.get("stock"))
            variant["price_override"] = _money(variant.get("price_override"))

    return products


def _load_pos_coupons() -> list[dict]:
    db = _db_admin()

    try:
        res = (
            db.table("coupons")
            .select(
                "id, code, discount_type, discount_value, "
                "max_discount, min_order_value, is_active, expires_at"
            )
            .eq("is_active", True)
            .execute()
        )
    except Exception:
        logger.info("[POS] coupons table unavailable.")
        return []

    rows = res.data or []
    now = _now()

    valid_rows = []

    for coupon in rows:
        expires_at = coupon.get("expires_at")

        if not expires_at:
            valid_rows.append(coupon)
            continue

        try:
            expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00")).replace(tzinfo=None)
            if expiry >= now:
                valid_rows.append(coupon)
        except Exception:
            valid_rows.append(coupon)

    return valid_rows


def _load_pricebooks() -> list[dict]:
    try:
        db = _db_admin()

        res = (
            db.table("price_books")
            .select("id, name, is_default, is_active")
            .eq("is_active", True)
            .order("is_default", desc=True)
            .execute()
        )

        rows = res.data or []
        return rows or [DEFAULT_PRICEBOOK]

    except Exception:
        logger.info("[POS] price_books table not configured.")
        return [DEFAULT_PRICEBOOK]


# ═══════════════════════════════════════════════════════════════
# CUSTOMER HELPERS
# ═══════════════════════════════════════════════════════════════

def _normalize_customer_payload(data: dict) -> dict:
    return {
        "phone": _normalize_phone(data.get("phone")),
        "full_name": _safe_str(data.get("full_name") or data.get("name")),
        "email": _safe_str(data.get("email")),
        "address": _safe_str(data.get("address")),
    }


def _find_customer_by_phone(db, phone: str) -> tuple[Optional[dict], Optional[str]]:
    """
    Ưu tiên bảng users. Nếu project có bảng customers riêng, fallback customers.
    """
    phone = _normalize_phone(phone)

    if not phone:
        return None, None

    try:
        res = (
            db.table("users")
            .select("id, full_name, email, phone, points, member_tier")
            .eq("phone", phone)
            .limit(1)
            .execute()
        )
        user = _first_row(res)
        if user:
            user["_source_table"] = "users"
            return user, "users"
    except Exception:
        logger.info("[POS] users lookup failed. Trying customers table.")

    try:
        res = (
            db.table("customers")
            .select("id, full_name, name, email, phone, points, member_tier")
            .eq("phone", phone)
            .limit(1)
            .execute()
        )
        customer = _first_row(res)
        if customer:
            customer["_source_table"] = "customers"
            if not customer.get("full_name"):
                customer["full_name"] = customer.get("name") or ""
            return customer, "customers"
    except Exception:
        logger.info("[POS] customers table lookup unavailable.")

    return None, None


def _create_customer(db, payload: dict) -> tuple[Optional[dict], str]:
    """
    Tạo khách hàng nhanh.
    Ưu tiên bảng users. Nếu users bắt buộc field khác và lỗi, thử customers.
    """
    phone = payload["phone"]
    full_name = payload["full_name"]
    email = payload["email"] or None
    address = payload["address"] or None

    existing, table = _find_customer_by_phone(db, phone)

    if existing:
        return {
            "id": existing.get("id"),
            "name": existing.get("full_name") or existing.get("name") or "",
            "phone": existing.get("phone") or phone,
            "email": existing.get("email") or "",
            "points": _safe_int(existing.get("points")),
            "tier": existing.get("member_tier") or "MEMBER",
            "source_table": table,
        }, "Khách hàng đã tồn tại."

    user_payload = {
        "full_name": full_name,
        "phone": phone,
        "email": email,
        "points": 0,
        "member_tier": "MEMBER",
        "created_at": _now_iso(),
    }

    if address:
        user_payload["address"] = address

    try:
        try:
            res = db.table("users").insert(user_payload).execute()
        except Exception:
            user_payload.pop("address", None)
            res = db.table("users").insert(user_payload).execute()

        user = _first_row(res)

        if user:
            return {
                "id": user.get("id"),
                "name": user.get("full_name") or full_name,
                "phone": user.get("phone") or phone,
                "email": user.get("email") or email or "",
                "points": _safe_int(user.get("points")),
                "tier": user.get("member_tier") or "MEMBER",
                "source_table": "users",
            }, "Đã thêm khách hàng mới."

    except Exception:
        logger.info("[POS] users insert failed. Trying customers table.")

    customer_payload = {
        "full_name": full_name,
        "name": full_name,
        "phone": phone,
        "email": email,
        "address": address,
        "points": 0,
        "member_tier": "MEMBER",
        "created_at": _now_iso(),
    }

    try:
        res = db.table("customers").insert(customer_payload).execute()
        customer = _first_row(res)

        if customer:
            return {
                "id": customer.get("id"),
                "name": customer.get("full_name") or customer.get("name") or full_name,
                "phone": customer.get("phone") or phone,
                "email": customer.get("email") or email or "",
                "points": _safe_int(customer.get("points")),
                "tier": customer.get("member_tier") or "MEMBER",
                "source_table": "customers",
            }, "Đã thêm khách hàng mới."

    except Exception as exc:
        logger.error("[POS] create customer failed: %s", exc, exc_info=True)

    return None, "Không tạo được khách hàng."


def _customer_name(customer: Optional[dict], fallback: str = "Khách mua tại quầy") -> str:
    if not customer:
        return fallback

    return (
        customer.get("full_name")
        or customer.get("name")
        or fallback
    )


def _customer_points(customer: Optional[dict]) -> int:
    if not customer:
        return 0
    return _safe_int(customer.get("points"))


# ═══════════════════════════════════════════════════════════════
# ROUTES: CUSTOMER
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/pos-lookup-customer", methods=["POST"])
@admin_required
def pos_lookup_customer():
    data = request.get_json(silent=True) or {}
    phone = _normalize_phone(data.get("phone", ""))

    if not phone:
        return _json_error("Vui lòng nhập số điện thoại.")

    try:
        db = _db_admin()
        customer, table = _find_customer_by_phone(db, phone)

        if not customer:
            return _json_error("Khách chưa có tài khoản thành viên.", 200)

        return _json_ok(
            id=customer.get("id"),
            name=_customer_name(customer, ""),
            email=customer.get("email") or "",
            phone=customer.get("phone") or phone,
            points=_customer_points(customer),
            tier=customer.get("member_tier") or "MEMBER",
            source_table=table,
        )

    except Exception as exc:
        logger.error("[pos_lookup_customer] %s", exc, exc_info=True)
        return _json_error("Lỗi hệ thống khi tra cứu khách hàng.", 500)


@admin_bp.route("/pos-create-customer", methods=["POST"])
@admin_required
def pos_create_customer():
    data = request.get_json(silent=True) or {}
    payload = _normalize_customer_payload(data)

    if not payload["phone"]:
        return _json_error("Vui lòng nhập số điện thoại khách hàng.")

    if not payload["full_name"]:
        return _json_error("Vui lòng nhập tên khách hàng.")

    try:
        db = _db_admin()
        customer, message = _create_customer(db, payload)

        if not customer:
            return _json_error(message, 500)

        return _json_ok(
            message=message,
            customer=customer,
        )

    except Exception as exc:
        logger.error("[pos_create_customer] %s", exc, exc_info=True)
        return _json_error("Lỗi hệ thống khi thêm khách hàng.", 500)


# ═══════════════════════════════════════════════════════════════
# ROUTE: POS TERMINAL
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/pos")
@admin_required
@handle_errors("Lỗi tải trang POS.", "admin.dashboard")
def pos_terminal():
    try:
        products = _load_pos_products()
        coupons = _load_pos_coupons()
        pricebooks = _load_pricebooks()
        staff_info = _current_staff_info()

    except Exception as exc:
        logger.error("[pos_terminal] %s", exc, exc_info=True)
        products, coupons, pricebooks = [], [], [DEFAULT_PRICEBOOK]
        staff_info = _current_staff_info()

    return render_template(
        "admin/pos/pos_terminal.html",
        products=products,
        coupons=coupons,
        pricebooks=pricebooks,
        staff_info=staff_info,
        pos_store_account=STORE_ACCOUNT,
        point_redeem_value=POINT_REDEEM_VALUE,
        base_earn_rate=BASE_EARN_RATE,
        vat_default_rate=VAT_DEFAULT_RATE,
    )


# ═══════════════════════════════════════════════════════════════
# CHECKOUT HELPERS
# ═══════════════════════════════════════════════════════════════

def _validate_items(db, items: list[dict]) -> tuple[bool, str, list[dict], float]:
    """
    Kiểm tra giỏ hàng:
    - product_id tồn tại
    - variant_id tồn tại nếu có
    - còn kho
    - giá hợp lệ
    """
    normalized_items: list[dict] = []
    subtotal = 0.0

    if not items:
        return False, "Giỏ hàng trống.", [], 0.0

    for raw in items:
        product_id = raw.get("product_id")
        variant_id = raw.get("variant_id") or None
        quantity = max(1, _safe_int(raw.get("quantity"), 1))
        unit_price = _money(raw.get("price"))
        display_name = _safe_str(raw.get("name"), "Sản phẩm")

        if not product_id:
            return False, "Thiếu product_id trong giỏ hàng.", [], 0.0

        if unit_price <= 0:
            return False, f"Giá sản phẩm {display_name} không hợp lệ.", [], 0.0

        if variant_id:
            v_res = (
                db.table("product_variants")
                .select("id, product_id, stock, price_override, size, color_name")
                .eq("id", variant_id)
                .limit(1)
                .execute()
            )
            variant = _first_row(v_res)

            if not variant:
                return False, f"Không tìm thấy biến thể của {display_name}.", [], 0.0

            available_stock = _safe_int(variant.get("stock"))

            if available_stock < quantity:
                return False, f"{display_name} chỉ còn {available_stock} sản phẩm.", [], 0.0

        else:
            p_res = (
                db.table("products")
                .select("id, stock")
                .eq("id", product_id)
                .limit(1)
                .execute()
            )
            product = _first_row(p_res)

            if not product:
                return False, f"Không tìm thấy sản phẩm {display_name}.", [], 0.0

            available_stock = _safe_int(product.get("stock"))

            if available_stock < quantity:
                return False, f"{display_name} chỉ còn {available_stock} sản phẩm.", [], 0.0

        line_total = unit_price * quantity
        subtotal += line_total

        normalized_items.append({
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "product_name": display_name,
            "line_total": line_total,
        })

    return True, "", normalized_items, subtotal


def _calculate_coupon_discount(
    db,
    coupon_id: Optional[str],
    subtotal: float,
    frontend_discount: float,
) -> tuple[float, Optional[str], str]:
    if subtotal <= 0:
        return 0.0, None, ""

    if not coupon_id:
        return min(max(frontend_discount, 0.0), subtotal), None, ""

    try:
        res = (
            db.table("coupons")
            .select(
                "id, code, discount_type, discount_value, "
                "max_discount, min_order_value, is_active, expires_at"
            )
            .eq("id", coupon_id)
            .limit(1)
            .execute()
        )
    except Exception:
        return 0.0, None, "Không đọc được mã giảm giá."

    coupon = _first_row(res)

    if not coupon or not coupon.get("is_active"):
        return 0.0, None, "Mã giảm giá không hợp lệ."

    expires_at = coupon.get("expires_at")

    if expires_at:
        try:
            expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00")).replace(tzinfo=None)
            if expiry < _now():
                return 0.0, None, "Mã giảm giá đã hết hạn."
        except Exception:
            pass

    min_order = _money(coupon.get("min_order_value"))

    if subtotal < min_order:
        return 0.0, coupon_id, f"Đơn tối thiểu {_format_vnd(min_order)} để dùng mã."

    value = _safe_float(coupon.get("discount_value"))
    max_discount = _money(coupon.get("max_discount"))

    if coupon.get("discount_type") == "percent":
        discount = subtotal * value / 100
    else:
        discount = value

    if max_discount > 0:
        discount = min(discount, max_discount)

    return min(max(discount, 0.0), subtotal), coupon_id, ""


def _calculate_vat(data: dict, taxable_amount: float) -> tuple[bool, float, float, dict]:
    vat_enabled = _safe_bool(
        data.get("vat_enabled")
        or data.get("invoice_vat")
        or data.get("vat_invoice")
    )

    vat_rate = _safe_float(data.get("vat_rate"), VAT_DEFAULT_RATE)

    if vat_rate > 1:
        vat_rate = vat_rate / 100

    vat_rate = max(0.0, min(vat_rate, 1.0))

    vat_info = (
        data.get("vat_info")
        or data.get("invoice_info")
        or data.get("vat_customer")
        or {}
    )

    if not isinstance(vat_info, dict):
        vat_info = {}

    vat_amount = taxable_amount * vat_rate if vat_enabled else 0.0

    return vat_enabled, vat_rate, vat_amount, vat_info


def _insert_order_items(db, rows: list[dict]) -> None:
    if not rows:
        return

    try:
        db.table("order_items").insert(rows).execute()
        return
    except Exception:
        logger.info("[POS] order_items optional product_name may not exist. Fallback insert.")

    fallback = []

    for row in rows:
        fallback.append({
            "order_id": row["order_id"],
            "product_id": row["product_id"],
            "variant_id": row.get("variant_id"),
            "quantity": row["quantity"],
            "unit_price": row["unit_price"],
        })

    db.table("order_items").insert(fallback).execute()


def _insert_order_note(db, order_id: str, note: str) -> None:
    if not note:
        return

    try:
        db.table("order_notes").insert({
            "order_id": order_id,
            "note": note,
            "note_type": "pos",
            "created_at": _now_iso(),
        }).execute()
    except Exception:
        logger.info("[POS] order_notes table not configured. Note skipped.")


def _insert_order_attributes(db, order_id: str, attributes: list[dict]) -> None:
    if not attributes:
        return

    rows = []

    for item in attributes:
        if not isinstance(item, dict):
            continue

        key = _safe_str(item.get("key") or item.get("name"))
        value = _safe_str(item.get("value"))

        if not key:
            continue

        rows.append({
            "order_id": order_id,
            "key": key,
            "value": value,
            "created_at": _now_iso(),
        })

    if not rows:
        return

    try:
        db.table("order_attributes").insert(rows).execute()
    except Exception:
        logger.info("[POS] order_attributes table not configured. Attributes skipped.")


def _insert_vat_invoice(db, order_id: str, vat_info: dict, vat_rate: float, vat_amount: float) -> None:
    if not vat_info:
        vat_info = {}

    payload = {
        "order_id": order_id,
        "company_name": vat_info.get("company_name") or "",
        "tax_code": vat_info.get("tax_code") or "",
        "company_address": vat_info.get("company_address") or vat_info.get("address") or "",
        "email": vat_info.get("email") or "",
        "vat_rate": vat_rate,
        "vat_amount": vat_amount,
        "status": "requested",
        "created_at": _now_iso(),
    }

    try:
        db.table("order_vat_invoices").insert(payload).execute()
    except Exception:
        logger.info("[POS] order_vat_invoices table not configured. VAT detail skipped.")


def _update_stock(db, items: list[dict]) -> None:
    for item in items:
        quantity = _safe_int(item["quantity"])

        if item.get("variant_id"):
            res = (
                db.table("product_variants")
                .select("stock")
                .eq("id", item["variant_id"])
                .limit(1)
                .execute()
            )
            row = _first_row(res)

            if row:
                new_stock = max(0, _safe_int(row.get("stock")) - quantity)
                db.table("product_variants").update({"stock": new_stock}).eq("id", item["variant_id"]).execute()

        else:
            res = (
                db.table("products")
                .select("stock")
                .eq("id", item["product_id"])
                .limit(1)
                .execute()
            )
            row = _first_row(res)

            if row:
                new_stock = max(0, _safe_int(row.get("stock")) - quantity)
                db.table("products").update({"stock": new_stock}).eq("id", item["product_id"]).execute()


def _update_customer_points(db, customer: dict, delta: int) -> None:
    if not customer or not customer.get("id") or delta == 0:
        return

    table = customer.get("_source_table") or "users"
    current_points = _safe_int(customer.get("points"))
    new_points = max(0, current_points + delta)

    try:
        db.table(table).update({"points": new_points}).eq("id", customer["id"]).execute()
        customer["points"] = new_points
    except Exception as exc:
        logger.info("[POS] update customer points skipped: %s", exc)


def _insert_loyalty_transaction(
    db,
    user_id: str,
    amount: int,
    transaction_type: str,
    description: str,
    reference_id: str,
    expires_at: Optional[str] = None,
) -> None:
    if not user_id or amount == 0:
        return

    payload = {
        "user_id": user_id,
        "amount": amount,
        "transaction_type": transaction_type,
        "description": description,
        "reference_id": reference_id,
    }

    if expires_at:
        payload["expires_at"] = expires_at

    try:
        db.table("loyalty_transactions").insert(payload).execute()
    except Exception:
        logger.info("[POS] loyalty_transactions table not configured. Transaction skipped.")


# ═══════════════════════════════════════════════════════════════
# CHECKOUT
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/pos-checkout", methods=["POST"])
@admin_required
def pos_checkout():
    data = request.get_json(silent=True) or {}

    items = data.get("items") or []
    method = _safe_str(data.get("payment_method"), "cash")

    if method not in {"cash", "transfer"}:
        return _json_error("Phương thức thanh toán không hợp lệ.")

    coupon_id = data.get("coupon_id") or None

    frontend_discount = _money(data.get("discount"))

    redeem_points = _safe_int(
        data.get("redeem_points", data.get("points_used", 0)),
        0,
    )

    customer_phone = _normalize_phone(data.get("customer_phone", ""))
    customer_name = _safe_str(data.get("customer_name"), "Khách mua tại quầy") or "Khách mua tại quầy"

    shipping_fee = _money(data.get("shipping_fee"))
    cash_received = _money(data.get("cash_received"))
    order_note = _safe_str(data.get("order_note") or data.get("note"))
    pricebook_id = data.get("pricebook_id") or "default"

    delivery_later = _safe_bool(data.get("delivery_later"))

    delivery_info = data.get("delivery_info") or {}

    if not isinstance(delivery_info, dict):
        delivery_info = {}

    order_attributes = data.get("order_attributes") or data.get("attributes") or []

    if not isinstance(order_attributes, list):
        order_attributes = []

    staff_info = _current_staff_info()
    cashier_id = data.get("cashier_id") or staff_info.get("id")
    cashier_name = data.get("cashier_name") or staff_info.get("name") or "Nhân viên POS"

    if not items:
        return _json_error("Giỏ hàng trống.")

    try:
        db = _db_admin()

        ok, message, normalized_items, subtotal = _validate_items(db, items)

        if not ok:
            return _json_error(message)

        customer, customer_table = _find_customer_by_phone(db, customer_phone)

        user_id = customer.get("id") if customer and customer_table == "users" else None
        customer_id = customer.get("id") if customer else None

        if customer:
            customer_name = _customer_name(customer, customer_name)

        current_points = _customer_points(customer)

        if redeem_points > 0:
            if not customer:
                return _json_error("Khách chưa có tài khoản thành viên để dùng điểm.")

            if current_points < redeem_points:
                return _json_error(f"Tài khoản chỉ có {current_points} điểm. Không đủ để trừ.")

        coupon_discount, valid_coupon_id, coupon_msg = _calculate_coupon_discount(
            db=db,
            coupon_id=coupon_id,
            subtotal=subtotal,
            frontend_discount=frontend_discount,
        )

        if coupon_msg and coupon_id:
            return _json_error(coupon_msg)

        point_discount = min(
            redeem_points * POINT_REDEEM_VALUE,
            max(0.0, subtotal - coupon_discount),
        )

        redeem_points = int(point_discount / POINT_REDEEM_VALUE) if point_discount > 0 else 0

        discount_before_vat = min(subtotal, coupon_discount + point_discount)
        taxable_amount = max(0.0, subtotal - discount_before_vat)

        vat_enabled, vat_rate, vat_amount, vat_info = _calculate_vat(data, taxable_amount)

        total_before_shipping = taxable_amount + vat_amount
        total = max(0.0, total_before_shipping + shipping_fee)

        if method == "cash" and cash_received > 0 and cash_received < total:
            return _json_error("Tiền khách đưa chưa đủ.")

        order_code = _generate_order_code()

        is_paid = method == "cash"
        payment_status = "paid" if is_paid else "pending"

        if method == "cash":
            order_status = "completed" if not delivery_later else "pending"
        else:
            order_status = "pending"

        point_message = ""

        if redeem_points > 0 and customer:
            _update_customer_points(db, customer, -redeem_points)

            _insert_loyalty_transaction(
                db=db,
                user_id=customer["id"],
                amount=-redeem_points,
                transaction_type="REDEEM_POS",
                description=f"Dùng điểm giảm giá đơn {order_code}",
                reference_id=order_code,
            )

        earned_points = calculate_points(total)

        if customer and earned_points > 0 and method == "cash":
            _update_customer_points(db, customer, earned_points)

            expires_at = (_now() + timedelta(days=365)).isoformat()

            _insert_loyalty_transaction(
                db=db,
                user_id=customer["id"],
                amount=earned_points,
                transaction_type="EARN_POS_CASH",
                description=f"Tích điểm đơn {order_code}",
                reference_id=order_code,
                expires_at=expires_at,
            )

            point_message = f" Đã tích {earned_points} điểm."

        elif customer and earned_points > 0 and method == "transfer":
            point_message = f" Sẽ cộng {earned_points} điểm khi nhận được tiền."

        order_payload_minimal = {
            "code": order_code,
            "user_id": user_id,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "sales_channel": "pos",
            "status": order_status,
            "payment_status": payment_status,
            "payment_method": method,
            "total_amount": total,
            "shipping_fee": shipping_fee,
            "discount_amount": discount_before_vat,
            "coupon_id": valid_coupon_id,
        }

        order_payload_full = {
            **order_payload_minimal,

            # Customer optional
            "customer_id": customer_id,

            # Money detail
            "subtotal_amount": subtotal,
            "vat_enabled": vat_enabled,
            "vat_rate": vat_rate,
            "vat_amount": vat_amount,
            "cash_received": cash_received if method == "cash" else 0,
            "change_amount": max(0.0, cash_received - total) if method == "cash" else 0,

            # POS meta
            "pricebook_id": pricebook_id,
            "delivery_later": delivery_later,
            "delivery_info": delivery_info,
            "order_notes": order_note,

            # Staff / cashier
            "cashier_id": cashier_id,
            "cashier_name": cashier_name,
            "staff_id": cashier_id,
            "staff_name": cashier_name,
        }

        order = _safe_table_insert(
            db=db,
            table="orders",
            payload=order_payload_full,
            fallback_payload=order_payload_minimal,
        )

        if not order:
            return _json_error("Không tạo được đơn hàng.", 500)

        order_id = order["id"]

        order_item_rows = []

        for item in normalized_items:
            order_item_rows.append({
                "order_id": order_id,
                "product_id": item["product_id"],
                "variant_id": item.get("variant_id") or None,
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "product_name": item["product_name"],
            })

        _insert_order_items(db, order_item_rows)
        _update_stock(db, normalized_items)
        _insert_order_note(db, order_id, order_note)
        _insert_order_attributes(db, order_id, order_attributes)

        if vat_enabled:
            _insert_vat_invoice(db, order_id, vat_info, vat_rate, vat_amount)

        message = "Thanh toán thành công." if is_paid else "Đã tạo đơn chuyển khoản, đang chờ thanh toán."
        message += point_message

        return _json_ok(
            order_id=order_id,
            order_code=order_code,
            message=message,
            invoice={
                "order_code": order_code,
                "date": _now().strftime("%d/%m/%Y %H:%M"),
                "payment_method": method,

                "customer_id": customer_id,
                "customer_name": customer_name,
                "customer_phone": customer_phone,

                "cashier_id": cashier_id,
                "cashier_name": cashier_name,

                "items": [
                    {
                        "name": item["product_name"],
                        "qty": item["quantity"],
                        "price": item["unit_price"],
                    }
                    for item in normalized_items
                ],

                "subtotal": subtotal,
                "coupon_discount": coupon_discount,
                "point_discount": point_discount,
                "discount": discount_before_vat,
                "redeem_points": redeem_points,
                "earned_points": earned_points if method == "cash" and customer else 0,

                "shipping_fee": shipping_fee,

                "vat_enabled": vat_enabled,
                "vat_rate": vat_rate,
                "vat_amount": vat_amount,

                "total": total,

                "cash_received": cash_received if method == "cash" else 0,
                "change_amount": max(0.0, cash_received - total) if method == "cash" else 0,

                "delivery_later": delivery_later,
                "delivery_info": delivery_info,

                "order_note": order_note,
                "pricebook_id": pricebook_id,
            },
        )

    except Exception as exc:
        logger.error("[pos_checkout] %s", exc, exc_info=True)
        return _json_error("Lỗi hệ thống khi thanh toán.", 500)


# ═══════════════════════════════════════════════════════════════
# PAYMENT POLLING
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/pos-check-payment/<order_id>")
@admin_required
def pos_check_payment(order_id: str):
    try:
        db = _db_admin()

        res = (
            db.table("orders")
            .select("id, code, payment_status, status")
            .eq("id", order_id)
            .limit(1)
            .execute()
        )

        order = _first_row(res)

        if not order:
            return jsonify({
                "paid": False,
                "message": "Không tìm thấy đơn.",
            })

        return jsonify({
            "paid": order.get("payment_status") == "paid",
            "status": order.get("status"),
            "order_code": order.get("code"),
        })

    except Exception as exc:
        logger.error("[pos_check_payment] %s", exc, exc_info=True)
        return jsonify({"paid": False})


# ═══════════════════════════════════════════════════════════════
# CASSO WEBHOOK
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/pos-webhook-casso", methods=["POST"])
def pos_webhook_casso():
    token = request.headers.get("Secure-Token", "")

    if CASSO_SECRET and token != CASSO_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    transactions = payload.get("data", [])

    if not transactions:
        return jsonify({
            "success": True,
            "processed": 0,
        })

    try:
        db = _db_admin()
        processed = 0

        for txn in transactions:
            bank_acc = str(txn.get("bank_sub_acc_id") or txn.get("subAccId") or "")
            amount = _safe_float(txn.get("amount"))
            description = str(txn.get("description") or "").upper()

            if bank_acc and bank_acc != STORE_ACCOUNT:
                continue

            if amount <= 0:
                continue

            order_code = _extract_order_code(description)

            if not order_code:
                continue

            res = (
                db.table("orders")
                .select("id, code, total_amount, payment_status, user_id, customer_id")
                .eq("code", order_code)
                .eq("sales_channel", "pos")
                .limit(1)
                .execute()
            )

            order = _first_row(res)

            if not order:
                continue

            if order.get("payment_status") == "paid":
                continue

            expected = _money(order.get("total_amount"))

            if abs(amount - expected) > 1000:
                logger.warning(
                    "[CASSO POS] Amount mismatch order=%s expected=%s received=%s",
                    order_code,
                    expected,
                    amount,
                )
                continue

            update_payload_full = {
                "payment_status": "paid",
                "status": "completed",
                "order_notes": f"Casso tự xác nhận | TID: {txn.get('tid', '')} | Nhận: {amount:,.0f}đ",
            }

            update_payload_minimal = {
                "payment_status": "paid",
                "status": "completed",
            }

            if not _safe_table_update(db, "orders", update_payload_full, "id", order["id"]):
                _safe_table_update(db, "orders", update_payload_minimal, "id", order["id"])

            customer_id = order.get("user_id") or order.get("customer_id")

            if customer_id:
                earned = calculate_points(expected)

                if earned > 0:
                    expires_at = (_now() + timedelta(days=365)).isoformat()

                    _insert_loyalty_transaction(
                        db=db,
                        user_id=customer_id,
                        amount=earned,
                        transaction_type="EARN_POS_TRANSFER",
                        description=f"Tích điểm POS - CK {order_code}",
                        reference_id=order_code,
                        expires_at=expires_at,
                    )

                    # Ưu tiên users. Nếu không update được, thử customers.
                    try:
                        user_res = (
                            db.table("users")
                            .select("points")
                            .eq("id", customer_id)
                            .limit(1)
                            .execute()
                        )
                        user = _first_row(user_res)
                        if user:
                            new_points = _safe_int(user.get("points")) + earned
                            db.table("users").update({"points": new_points}).eq("id", customer_id).execute()
                    except Exception:
                        try:
                            customer_res = (
                                db.table("customers")
                                .select("points")
                                .eq("id", customer_id)
                                .limit(1)
                                .execute()
                            )
                            customer = _first_row(customer_res)
                            if customer:
                                new_points = _safe_int(customer.get("points")) + earned
                                db.table("customers").update({"points": new_points}).eq("id", customer_id).execute()
                        except Exception:
                            logger.info("[CASSO POS] customer points update skipped.")

            processed += 1

        return jsonify({
            "success": True,
            "processed": processed,
        })

    except Exception as exc:
        logger.error("[pos_webhook_casso] %s", exc, exc_info=True)
        return jsonify({"error": "Internal error"}), 500