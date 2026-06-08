"""
app/controllers/admin/orders.py
===============================

MMESTLINE Admin Orders Controller

Chức năng:
- Danh sách đơn hàng WEB / POS.
- Xuất danh sách đơn hàng CSV.
- Chi tiết đơn hàng.
- Cập nhật trạng thái xử lý đơn.
- Tạo vận đơn.
- Webhook GHN.
- Self ship.
- Cập nhật phí ship.
- Cập nhật địa chỉ.
- Cập nhật trạng thái thanh toán.
- Lịch sử đơn hàng.
"""

from __future__ import annotations

import csv
import hmac
import hashlib
import io
import logging
from datetime import datetime
from typing import Any, Optional

from app import csrf
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    current_app,
    make_response,
)

from app.models.order_model import OrderModel
from app.models.shipment_model import ShipmentModel
from app.middleware.auth_required import admin_required
from app.services.shipping_service import ShippingService

from ._blueprint import admin_bp
from ._helpers import handle_errors, _args, _form, _paginate, _total_pages

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# CONFIG / STATE MACHINE
# ═══════════════════════════════════════════════════════════════

_TRANSITIONS = {
    "confirm": ("pending", "confirmed"),
    "pack": ("confirmed", "packed"),
}


# ═══════════════════════════════════════════════════════════════
# DB HELPERS
# ═══════════════════════════════════════════════════════════════

def _db():
    from app.utils.supabase_client import get_supabase
    return get_supabase()


def _db_admin():
    """
    Dùng service role nếu project đã cấu hình get_supabase_admin().
    Nếu chưa có thì fallback về get_supabase() để không crash.
    """
    try:
        from app.utils.supabase_client import get_supabase_admin
        return get_supabase_admin()
    except Exception:
        return _db()


def _first_row(response: Any) -> Optional[dict]:
    data = getattr(response, "data", None) or []
    return data[0] if data else None


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


def _csv_safe(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def _parse_created_at(value: Any) -> str:
    raw = _safe_str(value)
    if not raw:
        return ""

    try:
        return raw[:16].replace("T", " ")
    except Exception:
        return raw


def _get_order_code(order: dict) -> str:
    return order.get("code") or str(order.get("id", ""))[:8].upper()


def _get_customer_name(order: dict) -> str:
    if order.get("customer_name"):
        return order.get("customer_name")

    user = order.get("users") or {}
    if isinstance(user, dict) and user.get("full_name"):
        return user.get("full_name")

    shipping_address = order.get("shipping_address") or {}
    if isinstance(shipping_address, dict) and shipping_address.get("full_name"):
        return shipping_address.get("full_name")

    return "Khách lẻ"


def _get_customer_phone(order: dict) -> str:
    if order.get("customer_phone"):
        return order.get("customer_phone")

    user = order.get("users") or {}
    if isinstance(user, dict) and user.get("phone"):
        return user.get("phone")

    shipping_address = order.get("shipping_address") or {}
    if isinstance(shipping_address, dict) and shipping_address.get("phone"):
        return shipping_address.get("phone")

    return ""


def _get_cashier_name(order: dict) -> str:
    return order.get("cashier_name") or order.get("staff_name") or ""


def _fetch_orders_for_export(status: Optional[str] = None, keyword: Optional[str] = None) -> list[dict]:
    """
    Lấy dữ liệu xuất CSV.
    Ưu tiên gọi trực tiếp Supabase để có các field POS mới.
    """
    db = _db_admin()

    query = db.table("orders").select(
        "*, users(email, full_name, phone), "
        "order_items(*, products(id, name, thumbnail_url))"
    )

    if status:
        query = query.eq("status", status)

    if keyword:
        safe_kw = keyword.replace(",", " ").strip()
        query = query.or_(
            f"code.ilike.%{safe_kw}%,"
            f"customer_name.ilike.%{safe_kw}%,"
            f"customer_phone.ilike.%{safe_kw}%"
        )

    res = (
        query
        .order("created_at", desc=True)
        .limit(5000)
        .execute()
    )

    return res.data or []


# ═══════════════════════════════════════════════════════════════
# DANH SÁCH ĐƠN HÀNG
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/orders")
@admin_required
@handle_errors("Lỗi tải danh sách đơn hàng.", "admin.dashboard")
def orders():
    args = _args()
    page, per_page, _ = _paginate(args)

    status = args.get("status", "").strip() or None
    keyword = args.get("q", "").strip() or None

    result = OrderModel.get_all(
        page=page,
        per_page=per_page,
        status=status,
        keyword=keyword,
    )

    return render_template(
        "admin/order/orders.html",
        orders=result.get("items", []),
        total=result.get("total", 0),
        page=page,
        total_pages=_total_pages(result.get("total", 0), per_page),
        current_status=status,
        current_q=keyword or "",
    )


# ═══════════════════════════════════════════════════════════════
# XUẤT ĐƠN HÀNG CSV
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/orders/export")
@admin_required
@handle_errors("Lỗi xuất danh sách đơn hàng.", "admin.orders")
def orders_export():
    """
    Endpoint này sửa lỗi BuildError:
    url_for('admin.orders_export').

    Xuất CSV để dùng được ngay, không phụ thuộc openpyxl/pandas.
    """
    status = request.args.get("status", "").strip() or None
    keyword = request.args.get("q", "").strip() or None

    orders_data = _fetch_orders_for_export(status=status, keyword=keyword)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Ma don",
        "Ngay tao",
        "Kenh ban",
        "Trang thai don",
        "Trang thai thanh toan",
        "Phuong thuc thanh toan",
        "Khach hang",
        "So dien thoai",
        "Thu ngan",
        "Tam tinh",
        "Giam gia",
        "Phi van chuyen",
        "VAT",
        "Tong tien",
        "Tien khach dua",
        "Tien thoi",
        "So san pham",
        "Giao hang sau",
        "VAT enabled",
        "Ghi chu",
    ])

    for order in orders_data:
        items = order.get("order_items") or []

        writer.writerow([
            _csv_safe(_get_order_code(order)),
            _csv_safe(_parse_created_at(order.get("created_at"))),
            _csv_safe(order.get("sales_channel") or order.get("source") or "web"),
            _csv_safe(order.get("status")),
            _csv_safe(order.get("payment_status")),
            _csv_safe(order.get("payment_method")),
            _csv_safe(_get_customer_name(order)),
            _csv_safe(_get_customer_phone(order)),
            _csv_safe(_get_cashier_name(order)),
            _safe_float(order.get("subtotal_amount"), 0),
            _safe_float(order.get("discount_amount"), 0),
            _safe_float(order.get("shipping_fee"), 0),
            _safe_float(order.get("vat_amount"), 0),
            _safe_float(order.get("total_amount"), 0),
            _safe_float(order.get("cash_received"), 0),
            _safe_float(order.get("change_amount"), 0),
            len(items),
            "yes" if order.get("delivery_later") else "no",
            "yes" if order.get("vat_enabled") else "no",
            _csv_safe(order.get("order_notes") or order.get("order_note")),
        ])

    csv_text = "\ufeff" + output.getvalue()
    filename = f"mmestline_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    response = make_response(csv_text)
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"

    return response


# ═══════════════════════════════════════════════════════════════
# CHI TIẾT ĐƠN HÀNG
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/orders/<order_id>")
@admin_required
@handle_errors("Lỗi tải chi tiết đơn hàng.", "admin.orders")
def order_detail(order_id: str):
    order = OrderModel.get_by_id(order_id)

    if not order:
        flash("Đơn hàng không tồn tại.", "danger")
        return redirect(url_for("admin.orders"))

    shipment = ShipmentModel.get_by_order_id(order_id)

    if shipment:
        order["shipments"] = shipment

    providers = ShippingService.list_providers(active_only=True)

    provider_info = {}
    if shipment and shipment.get("provider"):
        provider_info = ShippingService.get_provider_display(shipment["provider"])

    loyalty_transactions = _load_order_loyalty_transactions(order)

    return render_template(
        "admin/order/order_detail.html",
        order=order,
        providers=providers,
        provider_info=provider_info,
        loyalty_transactions=loyalty_transactions,
    )


def _load_order_loyalty_transactions(order: dict) -> list[dict]:
    """
    Trang order_detail mới có block loyalty_transactions.
    Hàm này giúp template không lỗi nếu bảng loyalty_transactions không tồn tại.
    """
    try:
        db = _db_admin()
        order_id = order.get("id")
        order_code = order.get("code")

        filters = []
        if order_id:
            filters.append(f"reference_id.eq.{order_id}")
        if order_code:
            filters.append(f"reference_id.eq.{order_code}")

        if not filters:
            return []

        res = (
            db.table("loyalty_transactions")
            .select("*")
            .or_(",".join(filters))
            .order("created_at", desc=True)
            .execute()
        )

        return res.data or []

    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
# XÁC NHẬN VÀ ĐÓNG GÓI
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/orders/<order_id>/confirm", methods=["POST"])
@admin_required
def confirm_order(order_id: str):
    return _transition_order(order_id, "confirm")


@admin_bp.route("/orders/<order_id>/pack", methods=["POST"])
@admin_required
def pack_order(order_id: str):
    return _transition_order(order_id, "pack")


def _transition_order(order_id: str, action: str):
    required_status, next_status = _TRANSITIONS[action]

    order = OrderModel.get_by_id(order_id)

    if not order:
        return jsonify({
            "success": False,
            "message": "Đơn hàng không tồn tại.",
        })

    if order.get("status") != required_status:
        label = {
            "confirm": "Xác nhận",
            "pack": "Đóng gói",
        }.get(action, "Cập nhật")

        return jsonify({
            "success": False,
            "message": (
                f"Không thể {label}: đơn đang ở trạng thái "
                f"'{order.get('status')}', cần '{required_status}'."
            ),
        })

    success = OrderModel.update_status(order_id, next_status)

    if success:
        logger.info("[Order %s] %s → %s", order_id[:8], required_status, next_status)
        return jsonify({
            "success": True,
            "new_status": next_status,
        })

    return jsonify({
        "success": False,
        "message": "Lỗi cập nhật trạng thái. Vui lòng thử lại.",
    })


# ═══════════════════════════════════════════════════════════════
# TẠO VẬN ĐƠN
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/orders/<order_id>/fulfill", methods=["POST"])
@admin_required
def fulfill_order(order_id: str):
    data = request.get_json(silent=True) or {}
    provider = _safe_str(data.get("provider"), "mock")

    order = OrderModel.get_by_id(order_id)

    if not order:
        return jsonify({
            "success": False,
            "message": "Đơn hàng không tồn tại.",
        })

    if order.get("status") != "packed":
        return jsonify({
            "success": False,
            "message": (
                "Yêu cầu 'Đã đóng gói' để tạo vận đơn. "
                f"Hiện tại: '{order.get('status')}'."
            ),
        })

    shipment_data = _build_shipment_data(order_id, order, provider)
    shipment = ShipmentModel.create_shipment(shipment_data)

    if not shipment:
        return jsonify({
            "success": False,
            "message": "Lỗi khởi tạo dữ liệu vận chuyển nội bộ.",
        })

    payload = _build_shipping_payload(shipment_data)
    api_result = ShippingService.create_order(
        provider,
        payload,
        shipment_db_id=shipment["id"],
    )

    if api_result.get("success"):
        update_data = {
            "tracking_code": api_result.get("tracking_code"),
            "actual_shipping_fee": float(api_result.get("fee", 0)),
            "status": "waiting_pickup",
            "raw_response": api_result.get("raw_response", {}),
            "shipped_at": datetime.now().isoformat(),
        }

        if api_result.get("expected_delivery"):
            update_data["expected_delivery_at"] = api_result.get("expected_delivery")

        db = _db_admin()
        db.table("shipments").update(update_data).eq("id", shipment["id"]).execute()

        ShipmentModel.log_event(
            shipment_id=shipment["id"],
            status="waiting_pickup",
            description=(
                f"Đã tạo vận đơn thành công qua {provider.upper()}. "
                "Đang chờ bưu tá lấy hàng."
            ),
            raw_data=api_result.get("raw_response", {}),
        )

        OrderModel.update_status(order_id, "shipped")

        logger.info(
            "[Order %s] Fulfill thành công | Tracking: %s",
            order_id[:8],
            api_result.get("tracking_code"),
        )

        return jsonify({
            "success": True,
            "message": f"Bắn đơn sang {provider.upper()} thành công.",
            "tracking_code": api_result.get("tracking_code"),
            "actual_fee": api_result.get("fee"),
        })

    error_desc = api_result.get("message", "Unknown API Error")

    ShipmentModel.log_event(
        shipment_id=shipment["id"],
        status="failed",
        description=f"Lỗi API {provider.upper()}: {error_desc}",
        raw_data=api_result.get("raw_response", {}),
    )

    return jsonify({
        "success": False,
        "message": f"Lỗi từ {provider.upper()}: {error_desc}",
    })


# ═══════════════════════════════════════════════════════════════
# WEBHOOK GHN
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/webhook/ghn", methods=["POST"])
@csrf.exempt
def webhook_ghn():
    secret = current_app.config.get("GHN_WEBHOOK_SECRET", "")

    if secret:
        received_checksum = request.headers.get("X-Checksum", "")
        expected = hmac.new(
            secret.encode(),
            request.data,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(received_checksum, expected):
            logger.warning("[Webhook GHN] Chữ ký không hợp lệ, bỏ qua.")
            return jsonify({"message": "Invalid signature"}), 401

    payload = request.get_json(silent=True)

    if not payload:
        return jsonify({"message": "Empty payload"}), 400

    tracking_code = payload.get("OrderCode", "")
    ghn_status = payload.get("Status", "")
    description = payload.get("Description", ghn_status)
    location = payload.get("Warehouse", "")

    if not tracking_code or not ghn_status:
        return jsonify({"message": "Missing OrderCode or Status"}), 400

    internal_status = _map_ghn_status(ghn_status)

    try:
        db = _db_admin()
        res = (
            db.table("shipments")
            .select("id, order_id, cod_amount")
            .eq("tracking_code", tracking_code)
            .limit(1)
            .execute()
        )

        shipment = _first_row(res)

        if not shipment:
            return jsonify({"message": "Shipment not found"}), 404

    except Exception as exc:
        logger.error("[Webhook GHN] DB error tracking_code=%s: %s", tracking_code, exc)
        return jsonify({"message": "Database error"}), 500

    ShipmentModel.log_event(
        shipment_id=shipment["id"],
        status=internal_status,
        description=description,
        location=location,
        raw_data=payload,
    )

    order_id = shipment["order_id"]

    if internal_status == "delivered":
        OrderModel.update_status(order_id, "completed")
        logger.info("[Webhook GHN] Order %s → completed", order_id[:8])

        if _safe_float(shipment.get("cod_amount")) > 0:
            OrderModel.update_payment_status(
                order_id,
                "paid",
                f"COD_{tracking_code}",
            )
            logger.info("[Webhook GHN] Order %s → auto paid via COD", order_id[:8])

    elif internal_status in ("failed", "returned"):
        logger.warning("[Webhook GHN] Giao thất bại! tracking=%s", tracking_code)
        OrderModel.update_status(order_id, internal_status)

    return jsonify({"message": "OK"}), 200


def _map_ghn_status(ghn_status: str) -> str:
    mapping = {
        "picking": "shipping",
        "picked": "shipping",
        "storing": "shipping",
        "transporting": "shipping",
        "sorting": "shipping",
        "delivering": "shipping",
        "money_collect_delivering": "shipping",
        "delivered": "delivered",
        "delivery_fail": "failed",
        "waiting_to_return": "returned",
        "return": "returned",
        "returned": "returned",
        "cancel": "cancelled",
    }

    return mapping.get(_safe_str(ghn_status).lower(), "shipping")


# ═══════════════════════════════════════════════════════════════
# SELF SHIP
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/orders/<order_id>/self-delivered", methods=["POST"])
@admin_required
def self_delivered(order_id: str):
    order = OrderModel.get_by_id(order_id)

    if not order:
        return jsonify({
            "success": False,
            "message": "Đơn hàng không tồn tại.",
        })

    if order.get("status") != "shipped":
        return jsonify({
            "success": False,
            "message": f"Đơn phải ở trạng thái 'shipped'. Hiện: '{order.get('status')}'.",
        })

    shipment = ShipmentModel.get_by_order_id(order_id)

    if not shipment or shipment.get("provider") != "self_ship":
        return jsonify({
            "success": False,
            "message": "Chỉ áp dụng cho đơn tự giao (Self Ship).",
        })

    tracking_code = shipment.get("tracking_code", "")

    ShipmentModel.log_event(
        shipment_id=shipment["id"],
        status="delivered",
        description=f"Admin xác nhận giao thành công. Mã: {tracking_code}.",
    )

    OrderModel.update_status(order_id, "completed")
    logger.info("[Order %s] shipped → completed (self_ship)", order_id[:8])

    is_cod = _safe_str(order.get("payment_method")).upper() in {
        "COD",
        "TIỀN MẶT",
        "CASH",
    }

    if is_cod and order.get("payment_status") != "paid":
        OrderModel.update_payment_status(
            order_id,
            "paid",
            f"SELFSHIP_COD_{tracking_code}",
        )
        logger.info("[Order %s] auto paid via self_ship COD", order_id[:8])

    return jsonify({"success": True})


# ═══════════════════════════════════════════════════════════════
# CẬP NHẬT PHÍ SHIP
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/orders/<order_id>/update-ship-fee", methods=["POST"])
@admin_required
def update_ship_fee(order_id: str):
    order = OrderModel.get_by_id(order_id)

    if not order:
        return jsonify({
            "success": False,
            "message": "Đơn hàng không tồn tại.",
        })

    shipment = ShipmentModel.get_by_order_id(order_id)

    if not shipment or shipment.get("provider") != "self_ship":
        return jsonify({
            "success": False,
            "message": "Chỉ áp dụng cho đơn tự giao.",
        })

    data = request.get_json(silent=True) or {}
    fee = _safe_float(data.get("shipping_fee"), 0)
    sub_method = _safe_str(data.get("sub_method"), "staff")
    add_flag = bool(data.get("add_to_total", False))

    try:
        db = _db_admin()

        raw_response = shipment.get("raw_response") or {}
        if not isinstance(raw_response, dict):
            raw_response = {}

        db.table("shipments").update({
            "shipping_fee": fee,
            "raw_response": {
                **raw_response,
                "sub_method": sub_method,
            },
        }).eq("id", shipment["id"]).execute()

        if add_flag and fee > 0:
            new_total = _safe_float(order.get("total_amount")) + fee
            db.table("orders").update({
                "total_amount": new_total,
            }).eq("id", order_id).execute()

            logger.info(
                "[Order %s] total_amount +%s → %s",
                order_id[:8],
                fee,
                new_total,
            )

        ShipmentModel.log_event(
            shipment_id=shipment["id"],
            status=shipment.get("status", "shipped"),
            description=(
                f"Cập nhật phí ship: {fee:,.0f}₫ | {sub_method}"
                f"{' | Đã cộng vào tổng đơn' if add_flag and fee > 0 else ''}"
            ),
        )

        return jsonify({"success": True})

    except Exception as exc:
        logger.error("[Order %s] update_ship_fee error: %s", order_id[:8], exc)
        return jsonify({
            "success": False,
            "message": "Lỗi cập nhật. Vui lòng thử lại.",
        })


# ═══════════════════════════════════════════════════════════════
# CẬP NHẬT ĐỊA CHỈ & THANH TOÁN
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/orders/<order_id>/address", methods=["POST"])
@admin_required
@handle_errors("Cập nhật địa chỉ thất bại.", "admin.orders")
def edit_order_address(order_id: str):
    form = _form()

    address = {
        key: form.get(key)
        for key in (
            "full_name",
            "phone",
            "address",
            "city",
            "district",
            "ward",
            "ward_code",
            "district_id",
            "province_id",
        )
    }

    if OrderModel.update_shipping_address(order_id, address):
        flash("Đã cập nhật địa chỉ giao hàng!", "success")
    else:
        flash("Cập nhật địa chỉ thất bại.", "danger")

    return redirect(url_for("admin.order_detail", order_id=order_id))


@admin_bp.route("/orders/<order_id>/payment-status", methods=["POST"])
@admin_required
@handle_errors("Lỗi hệ thống.", "admin.orders")
def update_payment_status(order_id: str):
    new_status = _form().get("payment_status")

    if new_status not in {"paid", "pending", "failed", "refunded"}:
        flash("Trạng thái thanh toán không hợp lệ.", "danger")
        return redirect(url_for("admin.order_detail", order_id=order_id))

    txn_id = (
        f"MANUAL_ADMIN_{datetime.now().strftime('%H%M%S')}"
        if new_status == "paid"
        else None
    )

    if OrderModel.update_payment_status(
        order_id,
        payment_status=new_status,
        transaction_id=txn_id,
    ):
        flash("Đã cập nhật thanh toán thành công!", "success")
    else:
        flash("Cập nhật thanh toán thất bại.", "danger")

    return redirect(url_for("admin.order_detail", order_id=order_id))


# ═══════════════════════════════════════════════════════════════
# PRIVATE BUILDERS
# ═══════════════════════════════════════════════════════════════

def _build_shipment_data(order_id: str, order: dict, provider: str) -> dict:
    addr = order.get("shipping_address") or {}

    if order.get("delivery_later") and order.get("delivery_info"):
        delivery_info = order.get("delivery_info") or {}

        if isinstance(delivery_info, dict):
            addr = {
                "full_name": delivery_info.get("receiver_name") or order.get("customer_name") or "",
                "phone": delivery_info.get("receiver_phone") or order.get("customer_phone") or "",
                "address": delivery_info.get("address") or "",
                "city": delivery_info.get("city") or "",
                "district": delivery_info.get("district") or "",
                "ward_code": delivery_info.get("ward_code") or "",
                "district_id": delivery_info.get("district_id"),
                "province_id": delivery_info.get("province_id"),
            }

    items = order.get("order_items") or []

    total_weight = sum(
        _safe_int(item.get("quantity"), 1) * 250
        for item in items
    )

    weight_g = max(total_weight, 500)

    address_parts = [
        addr.get("address", ""),
        addr.get("district", ""),
        addr.get("city", ""),
    ]

    full_address = ", ".join([
        _safe_str(part)
        for part in address_parts
        if _safe_str(part)
    ])

    payment_method = _safe_str(order.get("payment_method")).upper()
    cod_amount = _safe_float(order.get("total_amount")) if payment_method == "COD" else 0

    return {
        "order_id": order_id,
        "provider": provider,
        "recipient_name": addr.get("full_name", ""),
        "recipient_phone": addr.get("phone", ""),
        "recipient_address": full_address,
        "recipient_ward_code": addr.get("ward_code", ""),
        "recipient_district_id": addr.get("district_id"),
        "recipient_province_id": addr.get("province_id"),
        "cod_amount": cod_amount,
        "shipping_fee": _safe_float(order.get("shipping_fee"), 0),
        "weight_g": weight_g,
        "dimensions_json": {
            "l": 20,
            "w": 15,
            "h": 10,
        },
        "status": "pending",
        "package_index": 1,
    }


def _build_shipping_payload(sd: dict) -> dict:
    return {
        "to_name": sd.get("recipient_name", ""),
        "to_phone": sd.get("recipient_phone", ""),
        "to_address": sd.get("recipient_address", ""),
        "cod_amount": sd.get("cod_amount", 0),
        "weight": sd.get("weight_g", 500),
    }


# ═══════════════════════════════════════════════════════════════
# LỊCH SỬ ĐƠN HÀNG
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/orders-history")
@admin_required
@handle_errors("Lỗi tải lịch sử đơn hàng.", "admin.dashboard")
def orders_history():
    args = _args()
    page, per_page, offset = _paginate(args)

    status = args.get("status", "").strip() or None
    source = args.get("source", "").strip() or None
    keyword = args.get("q", "").strip() or None

    try:
        db = _db_admin()

        query = db.table("orders").select(
            "*, users(full_name, email, phone)",
            count="exact",
        )

        if status:
            query = query.eq("status", status)

        if source:
            try:
                query = query.eq("sales_channel", source)
            except Exception:
                query = query.eq("source", source)

        if keyword:
            safe_kw = keyword.replace(",", " ").strip()
            query = query.or_(
                f"code.ilike.%{safe_kw}%,"
                f"customer_name.ilike.%{safe_kw}%,"
                f"customer_phone.ilike.%{safe_kw}%"
            )

        res = (
            query
            .order("created_at", desc=True)
            .range(offset, offset + per_page - 1)
            .execute()
        )

        orders_data = res.data or []
        total_count = res.count or 0
        total_pages = _total_pages(total_count, per_page)

    except Exception as exc:
        logger.error("[orders_history] Lỗi truy vấn DB: %s", exc)
        orders_data = []
        total_pages = 1

    return render_template(
        "admin/orders_history.html",
        orders=orders_data,
        current_page=page,
        total_pages=total_pages,
        current_status=status,
        current_source=source,
        current_q=keyword or "",
    )