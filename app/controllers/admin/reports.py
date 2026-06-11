"""
app/controllers/admin/reports.py
================================
Quản lý trang Báo cáo phân tích Omnichannel Analytics và API POS tại quầy.

Cải thiện:
- Dùng Supabase service role cho admin để tránh RLS/401.
- Query products/coupons có retry nhẹ khi Supabase bị Server disconnected.
- Trang reports không sập nếu products/coupons lỗi.
- POS order validate kỹ hơn.
- Tạo đơn POS có rollback mềm khi lỗi giữa chừng.
- Đồng bộ tồn kho biến thể + tồn kho sản phẩm.
- Ghi inventory_logs và analytics fail-safe.
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar

from flask import render_template, request, jsonify, session

from ._blueprint import admin_bp
from app.middleware.auth_required import admin_required
from app.models.report_model import ReportModel
from app.utils.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _db_admin():
    """
    Dùng service role client cho admin/reports/POS.
    Tránh lỗi RLS/401 khi đọc products, coupons, variants, orders.
    """
    return get_supabase_admin()


def _execute_with_retry(
    fn: Callable[[], T],
    *,
    fallback: T,
    label: str,
    retries: int = 2,
    delay: float = 0.35,
) -> T:
    """
    Retry nhẹ cho lỗi mạng Supabase/PostgREST.

    Lỗi hay gặp:
    - httpx.RemoteProtocolError: Server disconnected
    - timeout
    - connection reset
    """
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            msg = str(exc).lower()

            retryable = (
                "server disconnected" in msg
                or "remoteprotocolerror" in msg
                or "timeout" in msg
                or "connection" in msg
                or "temporarily unavailable" in msg
            )

            if not retryable or attempt >= retries:
                break

            sleep_time = delay * (attempt + 1)
            logger.warning(
                "[reports] %s lỗi kết nối, retry %s/%s sau %.2fs: %s",
                label,
                attempt + 1,
                retries,
                sleep_time,
                exc,
            )
            time.sleep(sleep_time)

    logger.error("[reports] %s thất bại: %s", label, last_error, exc_info=True)
    return fallback


def _safe_int(value: Any, default: int = 0, min_value: int | None = None, max_value: int | None = None) -> int:
    try:
        number = int(value)
    except Exception:
        number = default

    if min_value is not None:
        number = max(min_value, number)

    if max_value is not None:
        number = min(max_value, number)

    return number


def _safe_float(value: Any, default: float = 0.0, min_value: float | None = None, max_value: float | None = None) -> float:
    try:
        number = float(value)
    except Exception:
        number = default

    if min_value is not None:
        number = max(min_value, number)

    if max_value is not None:
        number = min(max_value, number)

    return number


def _clean_text(value: Any, max_len: int | None = None) -> str:
    text = str(value or "").strip()

    if max_len is not None:
        text = text[:max_len]

    return text


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_products_and_coupons(db) -> tuple[list[dict], list[dict]]:
    """
    Lấy products/coupons cho màn hình reports/POS.

    Nếu Supabase rớt kết nối thì trả list rỗng thay vì làm trang /admin/reports bị 500.
    """

    def query_products():
        res = (
            db.table("products")
            .select(
                "id, name, slug, brand, price, compare_at_price, cost_price, "
                "stock, sku, barcode, thumbnail_url, is_active, deleted_at, "
                "product_variants("
                "id, product_id, size, color_name, color_hex, stock, "
                "price_override, compare_at_price, cost_price, sku, barcode"
                ")"
            )
            .eq("is_active", True)
            .is_("deleted_at", "null")
            .order("name", desc=False)
            .limit(1000)
            .execute()
        )
        return res.data or []

    products = _execute_with_retry(
        query_products,
        fallback=[],
        label="query_products_for_reports_pos",
        retries=2,
    )

    now_str = _now_iso()

    def query_coupons():
        res = (
            db.table("coupons")
            .select(
                "id, code, discount_type, discount_value, "
                "max_discount, min_order_value, expires_at, is_active"
            )
            .eq("is_active", True)
            .or_(f"expires_at.is.null,expires_at.gt.{now_str}")
            .order("code", desc=False)
            .limit(300)
            .execute()
        )
        return res.data or []

    coupons = _execute_with_retry(
        query_coupons,
        fallback=[],
        label="query_coupons_for_reports_pos",
        retries=2,
    )

    return products, coupons


def _build_variant_label(variant: dict) -> str:
    color_label = _clean_text(variant.get("color_name"), max_len=80)
    size_label = _clean_text(variant.get("size"), max_len=80)

    if color_label and size_label:
        return f"{color_label} - Size {size_label}"

    if color_label:
        return color_label

    if size_label:
        return f"Size {size_label}"

    return "Mặc định"


def _recalculate_product_stock(db, product_id: str) -> int:
    """
    Tính lại tổng tồn kho sản phẩm = tổng stock của các biến thể.
    """
    if not product_id:
        return 0

    def query_variants():
        res = (
            db.table("product_variants")
            .select("stock")
            .eq("product_id", product_id)
            .execute()
        )
        return res.data or []

    rows = _execute_with_retry(
        query_variants,
        fallback=[],
        label=f"query_variant_stock:{product_id}",
        retries=1,
    )

    total_stock = sum(_safe_int(row.get("stock"), 0, min_value=0) for row in rows)

    try:
        (
            db.table("products")
            .update({"stock": total_stock})
            .eq("id", product_id)
            .execute()
        )
    except Exception as exc:
        logger.error("[reports/POS] Lỗi cập nhật tổng tồn kho product_id=%s: %s", product_id, exc, exc_info=True)

    return total_stock


def _safe_insert_inventory_log(
    db,
    *,
    product_id: str,
    variant_id: str,
    quantity_changed: int,
    stock_after: int,
    order_id: str,
    order_code: str,
) -> None:
    try:
        db.table("inventory_logs").insert({
            "product_id": product_id,
            "variant_id": variant_id,
            "change_type": "SALE",
            "quantity_changed": quantity_changed,
            "stock_after": stock_after,
            "reference_id": order_id,
            "note": f"Bán tại quầy POS - {order_code}",
            "created_by": str(session.get("user_id")) if session.get("user_id") else None,
            "created_at": _now_iso(),
        }).execute()
    except Exception as exc:
        logger.error("[Inventory Log] Lỗi ghi log POS order_id=%s: %s", order_id, exc, exc_info=True)


def _safe_log_product_event(
    db,
    *,
    product_id: str,
    revenue: float,
    quantity: int,
) -> None:
    try:
        db.rpc("log_product_event", {
            "p_product_id": product_id,
            "p_channel": "pos",
            "p_source": "direct",
            "p_event_type": "sold",
            "p_revenue": revenue,
            "p_qty": quantity,
        }).execute()
    except Exception as exc:
        logger.error("[POS Analytics] Lỗi gọi RPC log_product_event product_id=%s: %s", product_id, exc, exc_info=True)


def _soft_rollback_pos_order(db, order_id: str | None, variant_id: str | None, original_variant_stock: int | None) -> None:
    """
    Rollback mềm khi tạo POS lỗi giữa chừng.

    Vì Supabase REST không tự transaction trong đoạn này, rollback bằng best-effort:
    - trả lại stock variant nếu đã trừ
    - xóa order_items
    - xóa order
    """
    if not order_id:
        return

    try:
        if variant_id and original_variant_stock is not None:
            (
                db.table("product_variants")
                .update({"stock": original_variant_stock})
                .eq("id", variant_id)
                .execute()
            )
    except Exception as exc:
        logger.error("[POS rollback] Lỗi khôi phục stock variant_id=%s: %s", variant_id, exc, exc_info=True)

    try:
        db.table("order_items").delete().eq("order_id", order_id).execute()
    except Exception as exc:
        logger.error("[POS rollback] Lỗi xóa order_items order_id=%s: %s", order_id, exc, exc_info=True)

    try:
        db.table("orders").delete().eq("id", order_id).execute()
    except Exception as exc:
        logger.error("[POS rollback] Lỗi xóa order order_id=%s: %s", order_id, exc, exc_info=True)


# ═══════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/reports", methods=["GET"])
@admin_required
def reports():
    """
    Trang báo cáo admin.

    Không để lỗi products/coupons làm sập toàn bộ trang reports.
    """
    try:
        report_data = ReportModel.get_dashboard_reports() or {}
    except Exception as exc:
        logger.error("[reports] Lỗi tải dashboard reports: %s", exc, exc_info=True)
        report_data = {}

    stats = {
        "monthly": report_data.get("monthly_stats", []),
    }

    db = _db_admin()
    products, coupons = _get_products_and_coupons(db)

    return render_template(
        "admin/reports.html",
        report=report_data,
        stats=stats,
        products=products,
        coupons=coupons,
    )


@admin_bp.route("/reports/pos-order", methods=["POST"])
@admin_required
def create_pos_order():
    """
    API tạo đơn bán tại quầy POS.

    Payload kỳ vọng:
    {
      "product_id": "...",     optional, backend sẽ ưu tiên product_id từ variant
      "variant_id": "...",     required
      "quantity": 1,
      "discount": 0,
      "revenue": 199000
    }
    """
    data = request.get_json(silent=True) or {}

    requested_product_id = _clean_text(data.get("product_id"), max_len=80)
    variant_id = _clean_text(data.get("variant_id"), max_len=80)
    quantity = _safe_int(data.get("quantity"), default=1, min_value=1, max_value=999)
    discount = _safe_float(data.get("discount"), default=0.0, min_value=0.0)
    revenue = _safe_float(data.get("revenue"), default=0.0, min_value=0.0)

    if not variant_id:
        return jsonify({
            "success": False,
            "message": "Vui lòng chọn đúng biến thể màu/size trước khi thanh toán.",
        }), 400

    if quantity < 1:
        return jsonify({
            "success": False,
            "message": "Số lượng phải lớn hơn 0.",
        }), 400

    db = _db_admin()

    order_id: str | None = None
    original_variant_stock: int | None = None
    db_product_id: str | None = None

    try:
        # 1. Lấy biến thể + product snapshot
        variant_res = (
            db.table("product_variants")
            .select(
                "id, product_id, size, color_name, color_hex, stock, "
                "price_override, compare_at_price, cost_price, sku, barcode, "
                "products(id, name, price, compare_at_price, sku, barcode, is_active, deleted_at)"
            )
            .eq("id", variant_id)
            .limit(1)
            .execute()
        )

        if not variant_res.data:
            return jsonify({
                "success": False,
                "message": "Biến thể sản phẩm không tồn tại hoặc đã bị xóa.",
            }), 404

        variant = variant_res.data[0]
        product_info = variant.get("products") or {}

        db_product_id = str(variant.get("product_id") or product_info.get("id") or "")

        if not db_product_id:
            return jsonify({
                "success": False,
                "message": "Biến thể không liên kết với sản phẩm hợp lệ.",
            }), 400

        if requested_product_id and requested_product_id != db_product_id:
            logger.warning(
                "[POS] product_id từ client không khớp variant. client=%s db=%s variant=%s",
                requested_product_id,
                db_product_id,
                variant_id,
            )

        if product_info.get("deleted_at"):
            return jsonify({
                "success": False,
                "message": "Sản phẩm đã bị xóa, không thể bán.",
            }), 400

        if product_info.get("is_active") is False:
            return jsonify({
                "success": False,
                "message": "Sản phẩm đang tạm ẩn, không thể bán tại POS.",
            }), 400

        product_name = _clean_text(product_info.get("name"), max_len=220) or "Sản phẩm GUAMAISON"
        variant_label = _build_variant_label(variant)

        base_price = _safe_float(product_info.get("price"), default=0.0, min_value=0.0)
        unit_price = _safe_float(variant.get("price_override"), default=0.0, min_value=0.0) or base_price

        if unit_price <= 0:
            return jsonify({
                "success": False,
                "message": "Sản phẩm chưa có giá bán hợp lệ.",
            }), 400

        variant_stock = _safe_int(variant.get("stock"), default=0, min_value=0)
        original_variant_stock = variant_stock

        if variant_stock < quantity:
            return jsonify({
                "success": False,
                "message": f"Không đủ hàng. Phân loại '{variant_label}' chỉ còn {variant_stock} sản phẩm.",
            }), 400

        expected_revenue = max(0.0, (unit_price * quantity) - discount)

        # Cho phép lệch nhỏ do format tiền phía client, nhưng không cho lệch quá 1.000đ.
        if abs(revenue - expected_revenue) > 1000:
            logger.warning(
                "[POS] Revenue client lệch. client=%s expected=%s variant=%s",
                revenue,
                expected_revenue,
                variant_id,
            )
            revenue = expected_revenue

        if revenue < 0:
            return jsonify({
                "success": False,
                "message": "Tổng tiền không hợp lệ.",
            }), 400

        # 2. Tạo đơn POS
        order_id = str(uuid.uuid4())
        order_code = f"POS-{order_id.split('-')[0].upper()}"
        now = _now_iso()

        order_payload = {
            "id": order_id,
            "order_code": order_code,
            "total_amount": revenue,
            "shipping_fee": 0,
            "sales_channel": "pos",
            "status": "completed",
            "payment_status": "paid",
            "payment_method": "CASH",
            "created_at": now,
        }

        try:
            db.table("orders").insert(order_payload).execute()
        except Exception as exc:
            # Nếu bảng orders chưa có order_code hoặc created_at tự động, thử payload tối giản.
            msg = str(exc).lower()

            if "order_code" in msg or "created_at" in msg or "schema cache" in msg:
                logger.warning("[POS] Insert order payload đầy đủ lỗi, thử payload tối giản: %s", exc)

                minimal_order_payload = {
                    "id": order_id,
                    "total_amount": revenue,
                    "shipping_fee": 0,
                    "sales_channel": "pos",
                    "status": "completed",
                    "payment_status": "paid",
                    "payment_method": "CASH",
                }

                db.table("orders").insert(minimal_order_payload).execute()
            else:
                raise

        # 3. Tạo order item snapshot
        order_item_payload = {
            "order_id": order_id,
            "product_id": db_product_id,
            "variant_id": variant_id,
            "size": _clean_text(variant.get("size"), max_len=80) or None,
            "quantity": quantity,
            "unit_price": unit_price,
            "product_name": product_name,
            "variant_label": variant_label,
        }

        try:
            db.table("order_items").insert(order_item_payload).execute()
        except Exception as exc:
            # Nếu DB cũ thiếu product_name/variant_label thì fallback tối giản.
            msg = str(exc).lower()

            if "product_name" in msg or "variant_label" in msg or "schema cache" in msg:
                logger.warning("[POS] Insert order_items snapshot lỗi, thử payload tối giản: %s", exc)

                minimal_item_payload = {
                    "order_id": order_id,
                    "product_id": db_product_id,
                    "variant_id": variant_id,
                    "size": _clean_text(variant.get("size"), max_len=80) or None,
                    "quantity": quantity,
                    "unit_price": unit_price,
                }

                db.table("order_items").insert(minimal_item_payload).execute()
            else:
                raise

        # 4. Trừ tồn kho biến thể
        new_variant_stock = variant_stock - quantity

        (
            db.table("product_variants")
            .update({"stock": new_variant_stock})
            .eq("id", variant_id)
            .execute()
        )

        # 5. Đồng bộ tổng tồn sản phẩm
        total_product_stock = _recalculate_product_stock(db, db_product_id)

        # 6. Ghi log kho và analytics
        _safe_insert_inventory_log(
            db,
            product_id=db_product_id,
            variant_id=variant_id,
            quantity_changed=-quantity,
            stock_after=new_variant_stock,
            order_id=order_id,
            order_code=order_code,
        )

        _safe_log_product_event(
            db,
            product_id=db_product_id,
            revenue=revenue,
            quantity=quantity,
        )

        return jsonify({
            "success": True,
            "message": "Tạo đơn POS thành công.",
            "new_variant_stock": new_variant_stock,
            "new_product_stock": total_product_stock,
            "invoice": {
                "order_id": order_id,
                "order_code": order_code,
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "product_name": f"{product_name} ({variant_label})",
                "base_product_name": product_name,
                "variant_label": variant_label,
                "original_price": unit_price,
                "quantity": quantity,
                "discount": discount,
                "total": revenue,
            },
        })

    except Exception as exc:
        logger.exception("[POS Error] Lỗi hệ thống khi tạo đơn POS: %s", exc)

        _soft_rollback_pos_order(
            db,
            order_id=order_id,
            variant_id=variant_id,
            original_variant_stock=original_variant_stock,
        )

        if db_product_id:
            _recalculate_product_stock(db, db_product_id)

        return jsonify({
            "success": False,
            "message": "Lỗi hệ thống máy chủ khi tạo đơn POS. Vui lòng thử lại sau.",
        }), 500