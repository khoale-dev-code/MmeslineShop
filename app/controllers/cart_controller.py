"""
app/controllers/cart_controller.py
==================================
Quản lý giỏ hàng, checkout, coupon, phí vận chuyển và thanh toán.

Logic chuẩn:
- COD:
  tạo đơn -> ghi inventory/analytics/coupon -> clear cart -> success.

- VNPAY:
  tạo đơn pending -> lưu session pending -> redirect VNPay.
  Không ghi SALE/inventory/coupon_usage trước khi VNPay thành công.

- SEPAY:
  tạo đơn pending -> hiển thị QR/chuyển khoản.
  Không ghi SALE/inventory/coupon_usage ở checkout.
  Webhook SePay sẽ xác nhận paid và finalize đơn.
"""

import logging
import os
from urllib.parse import quote_plus

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)

from app.models.cart_model import CartSelection
from app.models.order_model import OrderModel
from app.models.address_model import AddressModel
from app.models.setting_model import SettingModel
from app.services.cart_service import cart_service
from app.services.vnpay_service import VNPayService
from app.repositories.coupon_repository import CouponRepository, CouponRepositoryError
from app.services.coupon_service import CouponService
from app.middleware.auth_required import login_required
from app.utils.supabase_client import get_supabase_admin

cart_bp = Blueprint("cart", __name__, url_prefix="/cart")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

ALLOWED_PAYMENT_METHODS = {"COD", "VNPAY", "SEPAY"}
DEFAULT_SHIPPING_FEE = 30000


# ═══════════════════════════════════════════════════════════════
# COMMON HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_user_id() -> str:
    return str(session.get("user_id") or "")


def _to_int(value, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        return default


def _to_float(value, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _clean_text(value: str | None) -> str:
    value = (value or "").strip()
    if value.lower() in {"none", "null", "undefined", "nan"}:
        return ""
    return value


def _safe_redirect_shop():
    return redirect("/shop")


def _safe_redirect_home():
    return redirect("/")


def calculate_cart_total(items: list) -> float:
    return cart_service.calculate_total(items or [])


def _wants_json() -> bool:
    return bool(
        request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.accept_mimetypes.best == "application/json"
    )


def _current_cart_selection(user_id: str) -> CartSelection:
    return cart_service.resolve_checkout_selection(
        user_id=user_id,
        selection_id=session.get("cart_selection_id_v10"),
        fallback=session.get("cart_selection_v10_fallback"),
    )


def _get_item_unit_price(item: dict) -> float:
    variant = item.get("product_variants") or {}
    product = item.get("products") or {}

    price = variant.get("price_override")
    if price is None:
        price = product.get("price", 0)

    return _to_float(price)


def _get_dynamic_shipping(province_name: str) -> dict:
    """
    Tính phí ship theo cấu hình store_settings.shipping_rules.rules.

    Fallback:
    - Không có tỉnh: 30.000đ
    - Không match rule: 30.000đ
    """
    try:
        settings = SettingModel.get_settings() or {}
        shipping_rules = settings.get("shipping_rules", {}).get("rules", []) or []
    except Exception as e:
        logger.warning("[Shipping] Không đọc được settings, dùng phí mặc định: %s", e)
        shipping_rules = []

    if not province_name:
        return {"fee": DEFAULT_SHIPPING_FEE, "warning": ""}

    def _normalize(s: str) -> str:
        return (
            (s or "")
            .lower()
            .replace("thành phố", "")
            .replace("tỉnh", "")
            .replace("tp.", "")
            .replace("tp ", "")
            .strip()
        )

    req_prov = _normalize(province_name)

    for rule in shipping_rules:
        rule_prov = _normalize(rule.get("province", ""))

        if rule_prov and (rule_prov in req_prov or req_prov in rule_prov):
            return {
                "fee": _to_float(rule.get("fee"), DEFAULT_SHIPPING_FEE),
                "warning": rule.get("warning", "") or "",
            }

    return {"fee": DEFAULT_SHIPPING_FEE, "warning": ""}


# ═══════════════════════════════════════════════════════════════
# COUPON HELPERS
# ═══════════════════════════════════════════════════════════════

# GUAMAISON-PROMOTION-SYNC-V17
def _coupon_service() -> CouponService:
    return CouponService(CouponRepository.admin())


def _validate_coupon(
    coupon_code: str,
    cart_total: float,
    *,
    user_id: str,
    items: list,
) -> dict:
    """Delegate every web coupon rule to the shared promotion service."""
    try:
        return _coupon_service().validate_for_checkout(
            coupon_code,
            user_id=user_id,
            items=items,
            subtotal=cart_total,
            channel="web",
        ).to_dict()
    except CouponRepositoryError as exc:
        logger.warning("[Coupon] Repository unavailable: %s", exc)
        return {
            "valid": False,
            "coupon_id": None,
            "code": "",
            "discount_amount": 0.0,
            "discount": 0.0,
            "free_shipping": False,
            "message": "Hệ thống khuyến mãi đang bận.",
        }

# ═══════════════════════════════════════════════════════════════
# ORDER SIDE EFFECTS
# ═══════════════════════════════════════════════════════════════

def _order_effects_already_done(order_id: str) -> bool:
    """
    Chặn ghi inventory_logs trùng nếu một luồng bị gọi lại.
    """
    if not order_id:
        return False

    try:
        res = (
            get_supabase_admin()
            .table("inventory_logs")
            .select("id")
            .eq("reference_id", str(order_id))
            .eq("change_type", "SALE")
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


def _safe_confirm_order_effects(
    order_id: str,
    user_id: str,
    items: list,
    coupon_id: str | None = None,
    discount_amount: float = 0,
    source: str = "organic",
    note_prefix: str = "Khách mua qua Web",
) -> None:
    """
    Chỉ chạy khi đơn đã được xác nhận.

    COD:
    - chạy ngay sau tạo đơn.

    VNPay:
    - chạy trong payment_controller khi response_code == 00.

    SePay:
    - chạy trong sepay webhook khi giao dịch chuyển khoản khớp.

    Không để lỗi phụ làm hỏng checkout.
    """
    if not order_id or not user_id:
        return

    if _order_effects_already_done(order_id):
        logger.info("[OrderEffects] Đã xử lý trước đó, bỏ qua order_id=%s", order_id)
        return

    db_admin = get_supabase_admin()
    short_order_id = str(order_id)[:8].upper()

    for item in items or []:
        product = item.get("products") or {}
        variant = item.get("product_variants") or {}

        product_id = item.get("product_id")
        variant_id = item.get("variant_id")
        quantity = max(1, _to_int(item.get("quantity"), 1))

        if not product_id:
            continue

        price = _get_item_unit_price(item)
        old_stock = _to_int(variant.get("stock"), 0)
        new_stock = max(0, old_stock - quantity)

        try:
            db_admin.table("inventory_logs").insert({
                "product_id": product_id,
                "variant_id": variant_id,
                "change_type": "SALE",
                "quantity_changed": -quantity,
                "stock_after": new_stock,
                "reference_id": str(order_id),
                "note": f"{note_prefix} - Đơn hàng {short_order_id}",
                "created_by": user_id,
            }).execute()
        except Exception as e:
            logger.warning(
                "[Inventory] Không ghi được inventory_logs product_id=%s order_id=%s: %s",
                product_id,
                order_id,
                e,
            )

        try:
            db_admin.rpc("log_product_event", {
                "p_product_id": product_id,
                "p_channel": "web",
                "p_source": source,
                "p_event_type": "sold",
                "p_revenue": price * quantity,
                "p_qty": quantity,
            }).execute()
        except Exception as e:
            logger.warning(
                "[Analytics] Không ghi được sold event product_id=%s order_id=%s: %s",
                product_id,
                order_id,
                e,
            )

    if coupon_id:
        try:
            db_admin.table("coupon_usages").insert({
                "coupon_id": coupon_id,
                "user_id": user_id,
                "order_id": str(order_id),
                "discount_amount": float(discount_amount or 0),
            }).execute()
        except Exception as e:
            logger.warning("[Coupon] Không ghi được coupon_usages order_id=%s: %s", order_id, e)


# Public alias nếu controller khác muốn import
confirm_order_effects = _safe_confirm_order_effects


# ═══════════════════════════════════════════════════════════════
# ADDRESS / CHECKOUT HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_user_checkout_data(user_id: str) -> tuple[list, float, list, dict | None]:
    selection = _current_cart_selection(user_id)
    items = cart_service.items_for_selection(user_id, selection)
    total = calculate_cart_total(items)
    addresses = AddressModel.get_user_addresses(user_id) or []
    default_address = next(
        (addr for addr in addresses if addr.get("is_default")),
        addresses[0] if addresses else None,
    )

    return items, total, addresses, default_address


def _select_address(addresses: list, address_id: str | None, default_address: dict | None) -> dict | None:
    if address_id:
        found = next(
            (addr for addr in addresses if str(addr.get("id")) == str(address_id)),
            None,
        )
        if found:
            return found

    return default_address


def _build_address_snapshot(address: dict) -> dict:
    return {
        "full_name": address.get("full_name"),
        "phone": address.get("phone"),
        "address": address.get("address_line"),
        "ward": address.get("ward") or address.get("ward_name"),
        "district": address.get("district") or address.get("district_name"),
        "city": address.get("province") or address.get("province_name"),
    }


def _normalize_payment_method(value: str | None) -> str:
    method = _clean_text(value).upper() or "COD"
    return method if method in ALLOWED_PAYMENT_METHODS else "COD"


def _save_pending_payment_session(order_id: str, method: str, user_id: str, coupon_id: str | None, discount_amount: float) -> None:
    """
    Lưu thông tin phụ cho return browser-based như VNPay.
    Với SePay webhook server-to-server không nên phụ thuộc session,
    nhưng vẫn lưu để trang QR/polling có thể dùng nếu cần.
    """
    key = f"{method.lower()}_pending_order_{order_id}"
    session[key] = {
        "user_id": user_id,
        "coupon_id": coupon_id,
        "discount_amount": float(discount_amount or 0),
    }
    session.modified = True


def _build_vietqr_url(order: dict, amount: float, transfer_content: str) -> str:
    """
    Tạo URL ảnh VietQR.

    Bắt buộc có:
    - SEPAY_BANK_CODE
    - SEPAY_BANK_ACCOUNT

    Ví dụ:
    SEPAY_BANK_CODE=MB
    SEPAY_BANK_ACCOUNT=0123456789
    SEPAY_ACCOUNT_NAME=GUAMAISON
    """
    bank_code = _clean_text(os.getenv("SEPAY_BANK_CODE"))
    account_no = _clean_text(os.getenv("SEPAY_BANK_ACCOUNT"))
    account_name = _clean_text(os.getenv("SEPAY_ACCOUNT_NAME", "GUAMAISON"))

    if not bank_code or not account_no:
        logger.warning(
            "[SePay QR] Thiếu cấu hình QR. SEPAY_BANK_CODE=%s | SEPAY_BANK_ACCOUNT=%s",
            bool(bank_code),
            bool(account_no),
        )
        return ""

    amount_int = int(float(amount or 0))

    return (
        f"https://img.vietqr.io/image/{quote_plus(bank_code)}-{quote_plus(account_no)}-compact2.png"
        f"?amount={amount_int}"
        f"&addInfo={quote_plus(transfer_content)}"
        f"&accountName={quote_plus(account_name)}"
    )


# ═══════════════════════════════════════════════════════════════
# CART ROUTES
# ═══════════════════════════════════════════════════════════════

@cart_bp.route("/")
@login_required
def index():
    user_id = _get_user_id()

    try:
        cart_page = cart_service.get_page(
            user_id=user_id,
            page=_to_int(request.args.get("page"), 1),
            per_page=_to_int(request.args.get("per_page"), 24),
            query=_clean_text(request.args.get("q")),
        )

        return render_template(
            "cart/cart.html",
            items=list(cart_page.items),
            cart_page=cart_page.to_template(),
            total=0,
        )

    except Exception as e:
        logger.exception("[Cart.index] Lỗi tải giỏ hàng: %s", e)
        flash("Đã xảy ra lỗi khi tải giỏ hàng.", "danger")
        return _safe_redirect_shop()


@cart_bp.route("/add", methods=["POST"])
@login_required
def add_to_cart():
    user_id = _get_user_id()
    data = request.form if request.form else (request.get_json(silent=True) or {})

    product_id = data.get("product_id")
    variant_id = data.get("variant_id")
    quantity = max(1, _to_int(data.get("quantity"), 1))

    wants_json = _wants_json()

    if not product_id or not variant_id:
        message = "Vui lòng chọn đầy đủ Màu sắc và Kích thước trước khi thêm vào túi hàng."
        if wants_json:
            return jsonify({"success": False, "message": message}), 400

        flash(message, "warning")
        return redirect(request.referrer or "/shop")

    try:
        result = cart_service.add_item(
            user_id=user_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
        )

        if wants_json:
            payload = result.to_dict()
            payload["cart_count"] = cart_service.get_count(user_id)
            return jsonify(payload), 200 if result.success else 400

        flash(result.message, "success" if result.success else "danger")

    except Exception as e:
        logger.exception("[Cart.add_to_cart] Lỗi backend: %s", e)

        if wants_json:
            return jsonify({
                "success": False,
                "message": "Hệ thống đang bận, thao tác chưa thành công.",
            }), 500

        flash("Hệ thống đang bận, thao tác chưa thành công.", "danger")

    return redirect(request.referrer or url_for("cart.index"))


@cart_bp.route("/update/<item_id>", methods=["POST"])
@login_required
def update_quantity(item_id: str):
    user_id = _get_user_id()
    data = request.form if request.form else (request.get_json(silent=True) or {})
    quantity = _to_int(data.get("quantity"), 1)

    wants_json = _wants_json()

    try:
        result = cart_service.update_quantity(user_id, item_id, quantity)

        if wants_json:
            payload = result.to_dict()
            payload["cart_count"] = cart_service.get_count(user_id)
            return jsonify(payload), 200 if result.success else 400

        flash(result.message, "success" if result.success else "danger")

    except Exception as e:
        logger.exception("[Cart.update_quantity] Lỗi: %s", e)

        if wants_json:
            return jsonify({"success": False, "message": "Không thể cập nhật giỏ hàng."}), 500

        flash("Đã xảy ra lỗi khi cập nhật số lượng.", "danger")

    return redirect(url_for("cart.index"))


@cart_bp.route("/remove/<item_id>", methods=["POST"])
@login_required
def remove_item(item_id):
    user_id = _get_user_id()
    wants_json = _wants_json()

    try:
        result = cart_service.remove_item(user_id, item_id)

        if wants_json:
            payload = result.to_dict()
            payload["cart_count"] = cart_service.get_count(user_id)
            return jsonify(payload), 200 if result.success else 400

        flash(result.message, "success" if result.success else "danger")

    except Exception as e:
        logger.exception("[Cart.remove_item] Lỗi: %s", e)

        if wants_json:
            return jsonify({"success": False, "message": "Không thể xóa sản phẩm."}), 500

        flash("Lỗi hệ thống khi xóa sản phẩm.", "danger")

    return redirect(url_for("cart.index"))


@cart_bp.route("/selection-summary", methods=["POST"])
@login_required
def selection_summary():
    user_id = _get_user_id()
    selection = cart_service.selection_from_payload(request.get_json(silent=True) or {})
    try:
        summary = cart_service.get_summary(user_id, selection)
        return jsonify({"success": True, **summary.to_dict()})
    except Exception as e:
        logger.exception("[Cart.selection_summary] Lỗi: %s", e)
        return jsonify({"success": False, "message": "Không thể tính phần đã chọn."}), 500


@cart_bp.route("/bulk-remove", methods=["POST"])
@login_required
def bulk_remove():
    user_id = _get_user_id()
    data = request.get_json(silent=True) or request.form.to_dict(flat=True)
    selection = cart_service.selection_from_payload(data)
    try:
        result = cart_service.remove_selection(user_id, selection)
        payload = result.to_dict()
        payload["cart_count"] = cart_service.get_count(user_id)
        return jsonify(payload), 200 if result.success else 400
    except Exception as e:
        logger.exception("[Cart.bulk_remove] Lỗi: %s", e)
        return jsonify({"success": False, "message": "Không thể xóa các sản phẩm đã chọn."}), 500


@cart_bp.route("/variants/<item_id>", methods=["GET"])
@login_required
def item_variants(item_id: str):
    try:
        editor = cart_service.get_variant_editor(_get_user_id(), item_id)
        if not editor:
            return jsonify({"success": False, "message": "Sản phẩm không còn trong giỏ."}), 404
        return jsonify({"success": True, **editor})
    except Exception as e:
        logger.exception("[Cart.item_variants] Lỗi: %s", e)
        return jsonify({"success": False, "message": "Không thể tải phân loại sản phẩm."}), 500


@cart_bp.route("/change-variant/<item_id>", methods=["POST"])
@login_required
def change_variant(item_id: str):
    data = request.get_json(silent=True) or request.form.to_dict(flat=True)
    variant_id = _clean_text(data.get("target_variant_id") or data.get("variant_id"))
    if not variant_id:
        return jsonify({"success": False, "message": "Vui lòng chọn size và màu."}), 400

    try:
        result = cart_service.change_variant(_get_user_id(), item_id, variant_id)
        return jsonify(result.to_dict()), 200 if result.success else 400
    except Exception as e:
        logger.exception("[Cart.change_variant] Lỗi: %s", e)
        return jsonify({"success": False, "message": "Không thể đổi phân loại sản phẩm."}), 500


@cart_bp.route("/prepare-checkout", methods=["POST"])
@login_required
def prepare_checkout():
    user_id = _get_user_id()
    data = request.get_json(silent=True) or request.form.to_dict(flat=True)
    selection = cart_service.selection_from_payload(data)

    try:
        selection_id, fallback, summary = cart_service.prepare_checkout(user_id, selection)
        if summary.line_count <= 0:
            message = "Vui lòng chọn ít nhất một sản phẩm để thanh toán."
            if _wants_json():
                return jsonify({"success": False, "message": message}), 400
            flash(message, "warning")
            return redirect(url_for("cart.index"))

        session["cart_selection_id_v10"] = selection_id
        session["cart_selection_v10_fallback"] = fallback
        session.modified = True
        checkout_url = url_for("cart.checkout")

        if _wants_json():
            return jsonify({"success": True, "redirect": checkout_url, **summary.to_dict()})
        return redirect(checkout_url)
    except Exception as e:
        logger.exception("[Cart.prepare_checkout] Lỗi: %s", e)
        message = "Không thể chuẩn bị phần sản phẩm đã chọn."
        if _wants_json():
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return redirect(url_for("cart.index"))


# ═══════════════════════════════════════════════════════════════
# COUPON / SHIPPING API
# ═══════════════════════════════════════════════════════════════

@cart_bp.route("/apply-coupon", methods=["POST"])
@login_required
def apply_coupon():
    user_id = _get_user_id()
    req_data = request.get_json(silent=True) or {}
    coupon_code = _clean_text(req_data.get("code")).upper()

    if not coupon_code:
        return jsonify({"valid": False, "error": "Vui lòng nhập mã khuyến mãi."}), 400

    try:
        items = cart_service.items_for_selection(user_id, _current_cart_selection(user_id))

        if not items:
            return jsonify({"valid": False, "error": "Giỏ hàng của bạn đang trống."}), 400

        cart_total = calculate_cart_total(items)
        coupon_result = _validate_coupon(coupon_code, cart_total, user_id=user_id, items=items)

        if not coupon_result["coupon_id"]:
            return jsonify({
                "valid": False,
                "error": coupon_result.get("message") or "Mã giảm giá không hợp lệ hoặc chưa đủ điều kiện.",
            }), 400

        discount = coupon_result["discount_amount"]

        return jsonify({
            "valid": True,
            "discount": discount,
            "final_total": cart_total - discount,
            "coupon_id": coupon_result["coupon_id"],
            "code": coupon_result["code"],
            "message": coupon_result.get("message"),
            "free_shipping": bool(coupon_result.get("free_shipping")),
        })

    except Exception as e:
        logger.exception("[Cart.apply_coupon] Lỗi: %s", e)
        return jsonify({
            "valid": False,
            "error": "Hệ thống khuyến mãi đang bận, vui lòng thử lại.",
        }), 500


@cart_bp.route("/calculate-shipping", methods=["POST"])
@login_required
def calculate_shipping():
    try:
        data = request.get_json(silent=True) or {}
        request_province = _clean_text(data.get("province"))
        ship_info = _get_dynamic_shipping(request_province)

        return jsonify({
            "success": True,
            "shipping_fee": ship_info["fee"],
            "warning": ship_info["warning"],
        })

    except Exception as e:
        logger.exception("[Cart.calculate_shipping] Lỗi: %s", e)
        return jsonify({
            "success": False,
            "shipping_fee": DEFAULT_SHIPPING_FEE,
            "warning": "",
        }), 500


# ═══════════════════════════════════════════════════════════════
# CHECKOUT
# ═══════════════════════════════════════════════════════════════

@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    user_id = _get_user_id()

    try:
        items, total, addresses, default_address = _get_user_checkout_data(user_id)
    except Exception as e:
        logger.exception("[Checkout] Không tải được dữ liệu checkout: %s", e)
        flash("Không thể tải dữ liệu thanh toán. Vui lòng thử lại.", "danger")
        return redirect(url_for("cart.index"))

    if not items:
        flash("Vui lòng chọn sản phẩm trước khi thanh toán.", "warning")
        return _safe_redirect_shop()

    if request.method == "POST":
        form = dict(request.form)

        address_id = form.get("address_id")
        payment_method = _normalize_payment_method(form.get("payment_method"))
        order_notes = _clean_text(form.get("order_notes"))
        coupon_code = _clean_text(form.get("coupon_code")).upper()

        selected_address = _select_address(addresses, address_id, default_address)

        if not selected_address:
            flash("Vui lòng thiết lập địa chỉ giao hàng trước khi thanh toán.", "danger")
            return redirect(url_for("profile.addresses"))

        address_snapshot = _build_address_snapshot(selected_address)

        coupon_result = _validate_coupon(coupon_code, total, user_id=user_id, items=items)
        coupon_id = coupon_result["coupon_id"]
        discount_amount = coupon_result["discount_amount"]

        ship_info = _get_dynamic_shipping(address_snapshot.get("city", ""))
        shipping_fee = _to_float(ship_info.get("fee"), DEFAULT_SHIPPING_FEE)
        if coupon_result.get("free_shipping"):
            shipping_fee = 0.0
        final_total = max(0, total - discount_amount + shipping_fee)

        try:
            order = OrderModel.create_order(
                user_id=user_id,
                items=items,
                total=final_total,
                address=address_snapshot,
                shipping_fee=shipping_fee,
                discount_amount=discount_amount,
                payment_method=payment_method,
                order_notes=order_notes,
            )

            if not order or not order.get("id"):
                flash("Lỗi tạo đơn hàng. Vui lòng liên hệ CSKH.", "danger")
                return redirect(url_for("cart.checkout"))

            order_id = str(order["id"])
            short_order_id = order_id[:8].upper()

            # ─────────────────────────────────────────────
            # VNPAY: tạo đơn pending -> redirect gateway
            # ─────────────────────────────────────────────
            if payment_method == "VNPAY":
                _save_pending_payment_session(
                    order_id=order_id,
                    method="VNPAY",
                    user_id=user_id,
                    coupon_id=coupon_id,
                    discount_amount=discount_amount,
                )

                try:
                    vnpay_url = VNPayService.create_payment_url(
                        order_id=order_id,
                        amount=final_total,
                        ip_address=request.remote_addr or "127.0.0.1",
                        order_desc=f"Thanh toan don hang {short_order_id}",
                    )
                    return redirect(vnpay_url)

                except Exception as e:
                    logger.exception("[VNPay] Không tạo được URL thanh toán: %s", e)
                    flash("Không thể khởi tạo thanh toán VNPay. Vui lòng thử lại.", "danger")
                    return redirect(url_for("cart.checkout"))

            # ─────────────────────────────────────────────
            # SEPAY: tạo đơn pending -> hiển thị QR
            # webhook xác nhận paid sau
            # ─────────────────────────────────────────────
            if payment_method == "SEPAY":
                _save_pending_payment_session(
                    order_id=order_id,
                    method="SEPAY",
                    user_id=user_id,
                    coupon_id=coupon_id,
                    discount_amount=discount_amount,
                )

                return redirect(url_for("cart.sepay_qr", order_id=order_id))

            # ─────────────────────────────────────────────
            # COD: xác nhận đơn ngay
            # ─────────────────────────────────────────────
            _safe_confirm_order_effects(
                order_id=order_id,
                user_id=user_id,
                items=items,
                coupon_id=coupon_id,
                discount_amount=discount_amount,
                source="cod",
                note_prefix="Khách đặt COD qua Web",
            )

            cart_service.remove_purchased_items(user_id, items)
            cart_service.delete_checkout_selection(
                user_id,
                session.get("cart_selection_id_v10"),
            )
            session.pop("cart_selection_id_v10", None)
            session.pop("cart_selection_v10_fallback", None)
            session.modified = True

            flash("🎉 Đơn hàng của bạn đã được ghi nhận thành công!", "success")
            return redirect(url_for("cart.order_success", order_id=order_id))

        except Exception as e:
            logger.exception("[Checkout] Lỗi hệ thống: %s", e)
            flash("Đã xảy ra lỗi nghiêm trọng khi xử lý đơn hàng. Vui lòng thử lại.", "danger")

    return render_template(
        "cart/checkout.html",
        items=items,
        total=total,
        default_address=default_address,
        addresses=addresses,
        payment_methods=sorted(ALLOWED_PAYMENT_METHODS),
    )


# ═══════════════════════════════════════════════════════════════
# SEPAY QR PAGE
# ═══════════════════════════════════════════════════════════════

@cart_bp.route("/sepay-qr/<order_id>")
@login_required
def sepay_qr(order_id):
    user_id = _get_user_id()
    order = OrderModel.get_by_id(order_id)

    if not order:
        flash("Không tìm thấy đơn hàng.", "danger")
        return redirect(url_for("cart.index"))

    if str(order.get("user_id")) != user_id:
        flash("Bạn không có quyền xem đơn hàng này.", "danger")
        return redirect(url_for("cart.index"))

    amount = _to_float(order.get("total_amount"), 0)
    transfer_content = f"GUAMAISON {order_id}"

    qr_image_url = _build_vietqr_url(
        order=order,
        amount=amount,
        transfer_content=transfer_content,
    )

    return render_template(
        "cart/sepay_qr.html",
        order=order,
        amount=amount,
        transfer_content=transfer_content,
        qr_image_url=qr_image_url,
        bank_code=_clean_text(os.getenv("SEPAY_BANK_CODE")),
        bank_account=_clean_text(os.getenv("SEPAY_BANK_ACCOUNT")),
        bank_name=_clean_text(os.getenv("SEPAY_BANK_NAME")),
        account_name=_clean_text(os.getenv("SEPAY_ACCOUNT_NAME", "GUAMAISON")),
    )


@cart_bp.route("/payment-status/<order_id>", methods=["GET"])
@login_required
def payment_status(order_id):
    """
    Dùng cho trang QR SePay polling trạng thái.
    Frontend có thể gọi mỗi 3-5 giây.
    """
    user_id = _get_user_id()
    order = OrderModel.get_by_id(order_id)

    if not order or str(order.get("user_id")) != user_id:
        return jsonify({"success": False, "message": "Order not found"}), 404

    return jsonify({
        "success": True,
        "order_id": order_id,
        "payment_method": order.get("payment_method"),
        "payment_status": order.get("payment_status"),
        "status": order.get("status"),
        "is_paid": order.get("payment_status") == "paid",
        "redirect_url": url_for("cart.order_success", order_id=order_id),
    })


# ═══════════════════════════════════════════════════════════════
# ORDER SUCCESS
# ═══════════════════════════════════════════════════════════════

@cart_bp.route("/order-success/<order_id>")
@login_required
def order_success(order_id):
    user_id = _get_user_id()
    order = OrderModel.get_by_id(order_id)

    if not order:
        return _safe_redirect_home()

    if str(order.get("user_id")) != user_id:
        flash("Bạn không có quyền xem đơn hàng này.", "danger")
        return _safe_redirect_home()

    return render_template("cart/order_success.html", order=order)
