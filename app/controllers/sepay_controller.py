"""
app/controllers/sepay_controller.py
==================================
Webhook nhận giao dịch từ SePay.

Luồng:
- Nhận webhook giao dịch ngân hàng.
- Xác thực API Key.
- Parse nội dung chuyển khoản để tìm order_id.
- Kiểm tra số tiền.
- Cập nhật đơn hàng paid.
- Ghi payment log.
- Finalize đơn hàng: inventory_logs, analytics, coupon_usages.
"""

import logging
import os
import re
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, session

from app import csrf
from app.models.order_model import OrderModel
from app.models.cart_model import CartModel
from app.utils.supabase_client import get_supabase_admin

sepay_bp = Blueprint("sepay", __name__, url_prefix="/api/sepay")
logger = logging.getLogger(__name__)


def _db():
    return get_supabase_admin()


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _to_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        return default

def _auth_ok() -> bool:
    expected = os.getenv("SEPAY_WEBHOOK_API_KEY", "").strip()
    if not expected:
        logger.warning("[SePay] Missing SEPAY_WEBHOOK_API_KEY")
        return False

    auth = request.headers.get("Authorization", "").strip()
    x_key = (
        request.headers.get("X-API-Key", "")
        or request.headers.get("X-SePay-Key", "")
    ).strip()

    candidates = {
        auth,
        auth.replace("Apikey", "").replace("ApiKey", "").replace("Bearer", "").strip(),
        x_key,
    }

    return expected in candidates


def _extract_order_id(content: str) -> str | None:
    """
    Nội dung chuyển khoản nên chứa mã đơn dạng:
    GUAMAISON <order_id>
    hoặc
    DH <order_id>
    hoặc
    ORDER <order_id>

    Vì order_id Supabase thường là UUID, regex bắt UUID.
    """
    content = content or ""

    uuid_match = re.search(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        content,
    )
    if uuid_match:
        return uuid_match.group(0)

    # Fallback nếu bạn dùng mã ngắn 8 ký tự trong nội dung CK.
    short_match = re.search(r"(?:DH|ORDER|GUAMAISON)\s*([A-Z0-9]{6,12})", content.upper())
    if short_match:
        return short_match.group(1)

    return None


def _payment_exists(provider: str, transaction_id: str | None) -> bool:
    if not transaction_id:
        return False

    try:
        res = (
            _db()
            .table("payments")
            .select("id")
            .eq("provider", provider)
            .eq("transaction_id", transaction_id)
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception as e:
        logger.warning("[SePay] Không kiểm tra được payment duplicate: %s", e)
        return False


def _log_payment(order_id: str, transaction_id: str, amount: float, raw: dict, status="success"):
    try:
        if _payment_exists("sepay", transaction_id):
            logger.info("[SePay] Payment đã tồn tại, bỏ qua. transaction_id=%s", transaction_id)
            return

        _db().table("payments").insert({
            "order_id": order_id,
            "provider": "sepay",
            "transaction_id": transaction_id,
            "amount": amount,
            "status": status,
            "raw_response": raw,
            "paid_at": _now_iso() if status == "success" else None,
        }).execute()

    except Exception as e:
        logger.error("[SePay] Lỗi ghi payments order_id=%s: %s", order_id, e)


def _order_effects_already_done(order_id: str) -> bool:
    try:
        res = (
            _db()
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


def _finalize_order_effects(order_id: str, user_id: str):
    """
    Ghi inventory/analytics sau khi xác nhận đã nhận tiền.
    """
    if _order_effects_already_done(order_id):
        return

    db = _db()
    items = OrderModel.get_order_items_for_effects(order_id)
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
                "note": f"Khách thanh toán SePay - Đơn hàng {short_order_id}",
                "created_by": user_id,
            }).execute()
        except Exception as e:
            logger.warning("[SePay] Không ghi được inventory_logs: %s", e)

        try:
            db.rpc("log_product_event", {
                "p_product_id": product_id,
                "p_channel": "web",
                "p_source": "sepay",
                "p_event_type": "sold",
                "p_revenue": _to_float(unit_price) * quantity,
                "p_qty": quantity,
            }).execute()
        except Exception as e:
            logger.warning("[SePay] Không ghi được analytics sold: %s", e)


def _extract_payload_fields(payload: dict):
    """
    SePay webhook payload có thể khác nhau tùy cấu hình/tài liệu.
    Hàm này map linh hoạt các key thường gặp.
    """
    transaction_id = str(
        payload.get("id")
        or payload.get("transaction_id")
        or payload.get("reference")
        or payload.get("sepay_transaction_id")
        or ""
    ).strip()

    content = str(
        payload.get("content")
        or payload.get("description")
        or payload.get("transaction_content")
        or payload.get("transfer_content")
        or ""
    )

    transfer_type = str(
        payload.get("transferType")
        or payload.get("transfer_type")
        or payload.get("type")
        or ""
    ).lower()

    amount = (
        payload.get("transferAmount")
        or payload.get("amount")
        or payload.get("creditAmount")
        or payload.get("credit_amount")
        or 0
    )

    return {
        "transaction_id": transaction_id,
        "content": content,
        "transfer_type": transfer_type,
        "amount": _to_float(amount),
    }


@sepay_bp.route("/webhook", methods=["POST"])
@csrf.exempt
def webhook():
    if not _auth_ok():
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}

    try:
        info = _extract_payload_fields(payload)

        transaction_id = info["transaction_id"]
        content = info["content"]
        amount = info["amount"]
        transfer_type = info["transfer_type"]

        logger.info(
            "[SePay] Webhook transaction_id=%s amount=%s type=%s content=%s",
            transaction_id,
            amount,
            transfer_type,
            content,
        )

        # Chỉ xử lý tiền vào. Nếu payload không có type thì vẫn cho qua.
        if transfer_type and transfer_type not in ("in", "credit", "deposit", "receive"):
            return jsonify({"success": True, "message": "Ignored non-credit transaction"}), 200

        order_id = _extract_order_id(content)
        if not order_id:
            logger.warning("[SePay] Không tìm thấy order_id trong nội dung chuyển khoản: %s", content)
            return jsonify({"success": True, "message": "No order id matched"}), 200

        order = OrderModel.get_by_id(order_id)
        if not order:
            logger.warning("[SePay] Không tìm thấy order_id=%s", order_id)
            return jsonify({"success": True, "message": "Order not found"}), 200

        order_total = _to_float(order.get("total_amount"), 0)
        user_id = str(order.get("user_id") or "")

        if order.get("payment_status") == "paid":
            _log_payment(order_id, transaction_id, amount, payload, status="success")
            return jsonify({"success": True, "message": "Order already paid"}), 200

        if amount + 1 < order_total:
            logger.warning(
                "[SePay] Số tiền chưa đủ. order_id=%s paid=%s required=%s",
                order_id,
                amount,
                order_total,
            )
            _log_payment(order_id, transaction_id, amount, payload, status="underpaid")
            return jsonify({"success": True, "message": "Underpaid"}), 200

        OrderModel.mark_payment_paid(
            order_id=order_id,
            transaction_id=transaction_id,
            status="pending",
        )

        _log_payment(order_id, transaction_id, amount, payload, status="success")
        _finalize_order_effects(order_id, user_id)

        try:
            CartModel.clear_cart(user_id)
        except Exception as e:
            logger.warning("[SePay] Không clear được cart user_id=%s: %s", user_id, e)

        return jsonify({"success": True, "message": "Payment confirmed"}), 200

    except Exception as e:
        logger.error("[SePay] Webhook error: %s", e, exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500