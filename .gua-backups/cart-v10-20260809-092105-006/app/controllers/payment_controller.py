"""
app/controllers/payment_controller.py
====================================
Xử lý kết quả thanh toán VNPay.

Logic chuẩn:
- Kiểm tra chữ ký VNPay.
- Ghi log payments bằng Supabase Admin client.
- Nếu thành công:
  + cập nhật orders.payment_status = paid
  + finalize đơn: inventory_logs, analytics, coupon_usages
  + clear cart
  + redirect order success
- Nếu thất bại:
  + cập nhật orders.payment_status = failed
  + không trừ kho, không clear cart
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, request, redirect, flash, session, url_for

from app.services.vnpay_service import VNPayService
from app.models.order_model import OrderModel
from app.models.cart_model import CartModel
from app.utils.supabase_client import get_supabase_admin

payment_bp = Blueprint("payment", __name__, url_prefix="/payment")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _to_int(value, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        return default


def _vnpay_amount(vnp_args: dict) -> float:
    """
    VNPay trả amount * 100.
    """
    return _to_float(vnp_args.get("vnp_Amount"), 0.0) / 100.0


def _db_admin():
    return get_supabase_admin()


def _payment_log_exists(order_id: str, transaction_id: str | None) -> bool:
    """
    Chặn ghi payment log trùng khi khách refresh trang return.
    """
    if not order_id:
        return False

    try:
        query = (
            _db_admin()
            .table("payments")
            .select("id")
            .eq("order_id", order_id)
            .limit(1)
        )

        if transaction_id:
            query = query.eq("transaction_id", transaction_id)

        result = query.execute()
        return bool(result.data)

    except Exception as e:
        logger.warning("[VNPay] Không kiểm tra được payment duplicate: %s", e)
        return False


def _log_payment(
    order_id: str,
    transaction_id: str | None,
    amount: float,
    status: str,
    raw_response: dict,
) -> None:
    """
    Ghi lịch sử giao dịch. Dùng admin client để tránh RLS.
    Không để lỗi ghi payments làm hỏng trải nghiệm khách.
    """
    if not order_id:
        return

    try:
        if _payment_log_exists(order_id, transaction_id):
            logger.info("[VNPay] Payment log đã tồn tại, bỏ qua ghi trùng. order_id=%s", order_id)
            return

        payload = {
            "order_id": order_id,
            "provider": "vnpay",
            "transaction_id": transaction_id,
            "amount": float(amount or 0),
            "status": status,
            "raw_response": raw_response,
            "paid_at": _now_iso() if status == "success" else None,
        }

        _db_admin().table("payments").insert(payload).execute()
        logger.info("[VNPay] Đã ghi payment log. order_id=%s status=%s", order_id, status)

    except Exception as e:
        logger.error("[VNPay] Lỗi ghi bảng payments cho đơn %s: %s", order_id, e)


def _order_effects_already_done(order_id: str) -> bool:
    """
    Chặn finalize lặp lại.

    Dựa vào inventory_logs.reference_id = order_id.
    Nếu bảng inventory_logs chưa có dữ liệu hoặc query lỗi thì trả False để vẫn cho finalize.
    """
    if not order_id:
        return False

    try:
        result = (
            _db_admin()
            .table("inventory_logs")
            .select("id")
            .eq("reference_id", str(order_id))
            .eq("change_type", "SALE")
            .limit(1)
            .execute()
        )
        return bool(result.data)

    except Exception as e:
        logger.warning("[VNPay] Không kiểm tra được inventory_logs duplicate: %s", e)
        return False


def _safe_confirm_order_effects(
    order_id: str,
    user_id: str,
    items: list,
    coupon_id: str | None = None,
    discount_amount: float = 0,
) -> None:
    """
    Tác vụ chỉ chạy sau khi đơn được xác nhận thanh toán:
    - ghi inventory_logs
    - ghi analytics sold
    - ghi coupon_usages

    Không để lỗi phụ làm sập luồng VNPay.
    """
    if not order_id or not user_id:
        return

    if _order_effects_already_done(order_id):
        logger.info("[VNPay] Order effects đã xử lý trước đó, bỏ qua. order_id=%s", order_id)
        return

    db = _db_admin()
    short_order_id = str(order_id)[:8].upper()

    for item in items or []:
        product = item.get("products") or {}
        variant = item.get("product_variants") or {}

        product_id = item.get("product_id")
        variant_id = item.get("variant_id")
        quantity = _to_int(item.get("quantity"), 1)

        unit_price = item.get("unit_price")
        if unit_price is None:
            unit_price = variant.get("price_override")
        if unit_price is None:
            unit_price = product.get("price", 0)

        old_stock = _to_int(variant.get("stock"), 0)
        new_stock = max(0, old_stock - quantity)

        if not product_id or quantity <= 0:
            continue

        try:
            db.table("inventory_logs").insert({
                "product_id": product_id,
                "variant_id": variant_id,
                "change_type": "SALE",
                "quantity_changed": -quantity,
                "stock_after": new_stock,
                "reference_id": str(order_id),
                "note": f"Khách thanh toán VNPay - Đơn hàng {short_order_id}",
                "created_by": user_id,
            }).execute()

        except Exception as e:
            logger.warning(
                "[VNPay] Không ghi được inventory_logs cho product_id=%s order_id=%s: %s",
                product_id,
                order_id,
                e,
            )

        try:
            db.rpc("log_product_event", {
                "p_product_id": product_id,
                "p_channel": "web",
                "p_source": "vnpay",
                "p_event_type": "sold",
                "p_revenue": _to_float(unit_price) * quantity,
                "p_qty": quantity,
            }).execute()

        except Exception as e:
            logger.warning(
                "[VNPay] Không ghi được analytics sold cho product_id=%s order_id=%s: %s",
                product_id,
                order_id,
                e,
            )

    if coupon_id:
        try:
            db.table("coupon_usages").insert({
                "coupon_id": coupon_id,
                "user_id": user_id,
                "order_id": str(order_id),
                "discount_amount": float(discount_amount or 0),
            }).execute()

        except Exception as e:
            logger.warning("[VNPay] Không ghi được coupon_usages order_id=%s: %s", order_id, e)


def _get_pending_vnpay_data(order_id: str) -> dict:
    """
    Lấy thông tin coupon pending từ session do cart_controller lưu trước khi redirect VNPay.
    Sau khi lấy thì pop để tránh dùng lại.
    """
    key = f"vnpay_pending_order_{order_id}"

    pending = session.pop(key, None) or {}
    session.modified = True

    return pending if isinstance(pending, dict) else {}


def _safe_clear_cart(user_id: str | None) -> None:
    if not user_id:
        return

    try:
        CartModel.clear_cart(str(user_id))
    except Exception as e:
        logger.error("[VNPay] Lỗi clear cart user_id=%s: %s", user_id, e)


def _safe_redirect_checkout():
    try:
        return redirect(url_for("cart.checkout"))
    except Exception:
        return redirect("/cart/checkout")


def _safe_redirect_success(order_id: str):
    try:
        return redirect(url_for("cart.order_success", order_id=order_id))
    except Exception:
        return redirect(f"/cart/order-success/{order_id}")


# ═══════════════════════════════════════════════════════════════
# VNPay Return
# ═══════════════════════════════════════════════════════════════

@payment_bp.route("/vnpay_return", methods=["GET"])
def vnpay_return():
    """
    Endpoint nhận kết quả trả về từ VNPay.
    """
    vnp_args = request.args.to_dict()

    try:
        result = VNPayService.parse_response(vnp_args)

        order_id = result.get("order_id")
        transaction_id = result.get("transaction_id")
        response_code = result.get("response_code")
        is_valid = bool(result.get("is_valid"))

        amount = _vnpay_amount(vnp_args)

        logger.info(
            "[VNPay Return] order_id=%s response_code=%s transaction_id=%s valid=%s amount=%s",
            order_id,
            response_code,
            transaction_id,
            is_valid,
            amount,
        )

        if not is_valid:
            logger.error("[VNPay Return] Checksum không hợp lệ. order_id=%s args=%s", order_id, vnp_args)
            flash("Dữ liệu thanh toán bị sai lệch. Vui lòng liên hệ hỗ trợ.", "danger")
            return redirect("/")

        if not order_id:
            flash("Không tìm thấy thông tin đơn hàng.", "danger")
            return redirect("/")

        order = OrderModel.get_by_id(order_id)
        if not order:
            logger.error("[VNPay Return] Không tìm thấy đơn hàng order_id=%s", order_id)
            flash("Không tìm thấy đơn hàng cần cập nhật.", "danger")
            return redirect("/")

        order_user_id = str(order.get("user_id") or "")
        order_total = _to_float(order.get("total_amount"), 0.0)
        current_payment_status = order.get("payment_status")

        # Ghi payment log trước, nhưng không để lỗi log làm hỏng luồng.
        payment_status_db = "success" if response_code == "00" else "failed"
        _log_payment(
            order_id=order_id,
            transaction_id=transaction_id,
            amount=amount,
            status=payment_status_db,
            raw_response=vnp_args,
        )

        # Có thể bật kiểm tra amount nếu muốn chặt hơn.
        # Cho lệch 1đ để tránh lỗi float.
        if response_code == "00" and order_total and abs(amount - order_total) > 1:
            logger.error(
                "[VNPay Return] Amount mismatch order_id=%s vnpay_amount=%s order_total=%s",
                order_id,
                amount,
                order_total,
            )
            OrderModel.mark_payment_failed(order_id, reason="VNPay amount mismatch")
            flash("Số tiền thanh toán không khớp đơn hàng. Vui lòng liên hệ hỗ trợ.", "danger")
            return redirect("/")

        if response_code == "00":
            # Nếu đã paid trước đó, không finalize lại.
            if current_payment_status == "paid":
                logger.info("[VNPay Return] Đơn đã paid trước đó, redirect success. order_id=%s", order_id)
                _safe_clear_cart(order_user_id or session.get("user_id"))
                flash("Đơn hàng đã được thanh toán thành công.", "success")
                return _safe_redirect_success(order_id)

            update_success = OrderModel.mark_payment_paid(
                order_id=order_id,
                transaction_id=transaction_id,
                status="pending",
            )

            if not update_success:
                logger.error("[VNPay Return] Không cập nhật được payment paid. order_id=%s", order_id)
                flash("Thanh toán thành công nhưng hệ thống chưa cập nhật kịp. Vui lòng liên hệ hỗ trợ.", "warning")
                return redirect("/")

            pending = _get_pending_vnpay_data(order_id)

            coupon_id = pending.get("coupon_id")
            discount_amount = pending.get("discount_amount", order.get("discount_amount") or 0)

            order_items = OrderModel.get_order_items_for_effects(order_id)

            _safe_confirm_order_effects(
                order_id=order_id,
                user_id=order_user_id or str(session.get("user_id") or ""),
                items=order_items,
                coupon_id=coupon_id,
                discount_amount=_to_float(discount_amount),
            )

            _safe_clear_cart(order_user_id or session.get("user_id"))

            flash("🎉 Thanh toán thành công! Cảm ơn bạn đã ủng hộ GUAMAISON.", "success")
            return _safe_redirect_success(order_id)

        # VNPay failed/cancelled.
        reason = f"VNPay failed with response_code={response_code}"
        OrderModel.mark_payment_failed(order_id, reason=reason)

        flash(f"Giao dịch không thành công hoặc đã bị hủy. Mã lỗi: {response_code}.", "warning")
        return _safe_redirect_checkout()

    except Exception as e:
        logger.error("[VNPay Return] Lỗi hệ thống: %s", e, exc_info=True)
        flash("Có lỗi kỹ thuật xảy ra khi xử lý thanh toán.", "danger")
        return redirect("/")