"""
app/models/order_model.py
=========================
Quản lý vòng đời đơn hàng, thống kê tài chính, logistics và hỗ trợ vận hành cho GUAMAISON.

Điểm cập nhật:
- Fix lỗi thụt lề get_user_orders / get_user_orders_paginated.
- Dùng Admin Client cho server-side để tránh RLS permission denied.
- create_order snapshot product_name, variant_label, unit_price đúng schema.
- Thêm helpers phục vụ VNPay:
  + mark_payment_paid
  + mark_payment_failed
  + get_order_items_for_effects
- Không ghi inventory/analytics trong model này; phần đó nên xử lý ở controller/service sau khi đơn được xác nhận.
"""

import logging
from collections import defaultdict, Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)


class OrderModel:
    ORDER_TABLE = "orders"
    ORDER_ITEM_TABLE = "order_items"
    RETURN_TABLE = "return_requests"
    SHIPMENT_TABLE = "shipments"

    # ═══════════════════════════════════════════════════════════════
    # DB CLIENTS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _db():
        """Public client. Giữ lại để tương thích, nhưng server-side ưu tiên _db_admin()."""
        return get_supabase()

    @staticmethod
    def _db_admin():
        """Admin client bypass RLS cho các thao tác server-side."""
        return get_supabase_admin()

    @staticmethod
    def _rows(result: Any) -> List[Dict[str, Any]]:
        data = getattr(result, "data", None)
        return data if isinstance(data, list) else []

    @staticmethod
    def _one(result: Any) -> Optional[Dict[str, Any]]:
        data = getattr(result, "data", None)
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and data:
            return data[0]
        return None

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        try:
            if value is None or value == "":
                return default
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _build_variant_label(variant: dict) -> Optional[str]:
        color = (variant.get("color_name") or variant.get("color") or "").strip()
        size = (variant.get("size") or variant.get("size_name") or "").strip()

        if color and size:
            return f"{color} - Size {size}"
        if color:
            return color
        if size:
            return f"Size {size}"
        return None

    @staticmethod
    def _unit_price(product: dict, variant: dict) -> float:
        price_override = variant.get("price_override")

        if price_override is not None and price_override != "":
            return OrderModel._to_float(price_override)

        return OrderModel._to_float(product.get("price"))

    # ═══════════════════════════════════════════════════════════════
    # CREATE ORDER
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def create_order(
        user_id: str,
        items: list,
        total: float,
        address: dict,
        shipping_fee: float = 0,
        discount_amount: float = 0,
        payment_method: str = "COD",
        order_notes: str = None,
    ) -> dict:
        """
        Tạo đơn hàng và order_items.

        Lưu ý:
        - VNPay vẫn tạo đơn pending.
        - Không trừ kho/ghi inventory tại đây.
        - Không ghi coupon usage tại đây.
        """
        db = OrderModel._db_admin()

        if not user_id:
            logger.error("[OrderModel.create_order] Thiếu user_id.")
            return {}

        if not items:
            logger.error("[OrderModel.create_order] Không có sản phẩm.")
            return {}

        payment_method = (payment_method or "COD").upper()

        try:
            order_data = {
                "user_id": user_id,
                "total_amount": float(total or 0),
                "shipping_fee": float(shipping_fee or 0),
                "discount_amount": float(discount_amount or 0),
                "shipping_address": address or {},
                "status": "pending",
                "payment_method": payment_method,
                "payment_status": "pending",
                "order_notes": order_notes,
            }

            order_res = db.table(OrderModel.ORDER_TABLE).insert(order_data).execute()
            order = OrderModel._one(order_res)

            if not order:
                logger.error("[OrderModel.create_order] Insert orders trả về rỗng.")
                return {}

            order_id = order.get("id")
            order_items = []

            for item in items:
                product = item.get("products") or {}
                variant = item.get("product_variants") or {}

                product_id = item.get("product_id")
                variant_id = item.get("variant_id") or None
                quantity = OrderModel._to_int(item.get("quantity"), 1)

                if not product_id or quantity <= 0:
                    continue

                unit_price = OrderModel._unit_price(product, variant)
                product_name = product.get("name") or item.get("product_name") or "Sản phẩm"
                variant_label = OrderModel._build_variant_label(variant)

                order_items.append({
                    "order_id": order_id,
                    "product_id": product_id,
                    "variant_id": variant_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "product_name": product_name,
                    "variant_label": variant_label,
                })

            if not order_items:
                logger.error("[OrderModel.create_order] Không build được order_items.")
                try:
                    db.table(OrderModel.ORDER_TABLE).delete().eq("id", order_id).execute()
                except Exception:
                    pass
                return {}

            item_res = db.table(OrderModel.ORDER_ITEM_TABLE).insert(order_items).execute()
            inserted_items = OrderModel._rows(item_res)

            if not inserted_items:
                logger.error("[OrderModel.create_order] Insert order_items trả về rỗng.")
                try:
                    db.table(OrderModel.ORDER_TABLE).delete().eq("id", order_id).execute()
                except Exception:
                    pass
                return {}

            order["order_items"] = inserted_items
            return order

        except Exception as e:
            logger.exception("[OrderModel.create_order] Lỗi tạo đơn hàng: %s", e)
            return {}

    # ═══════════════════════════════════════════════════════════════
    # PAYMENT HELPERS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def update_payment_status(order_id: str, payment_status: str, transaction_id: str = None) -> bool:
        db = OrderModel._db_admin()

        try:
            payload = {"payment_status": payment_status}

            if transaction_id:
                payload["transaction_id"] = transaction_id

            db.table(OrderModel.ORDER_TABLE).update(payload).eq("id", order_id).execute()
            return True

        except Exception as e:
            logger.error("[OrderModel.update_payment_status] Lỗi đơn %s: %s", order_id, e)
            return False

    @staticmethod
    def mark_payment_paid(
        order_id: str,
        transaction_id: str = None,
        status: str = "pending",
    ) -> bool:
        """
        Dùng cho VNPay return success.
        payment_status=paid, status mặc định pending để admin xử lý tiếp.
        """
        db = OrderModel._db_admin()

        try:
            payload = {
                "payment_status": "paid",
                "status": status,
            }

            if transaction_id:
                payload["transaction_id"] = transaction_id

            db.table(OrderModel.ORDER_TABLE).update(payload).eq("id", order_id).execute()
            return True

        except Exception as e:
            logger.error("[OrderModel.mark_payment_paid] Lỗi đơn %s: %s", order_id, e)
            return False

    @staticmethod
    def mark_payment_failed(order_id: str, reason: str = None) -> bool:
        """
        Dùng cho VNPay return fail/cancel.
        Không hủy đơn cứng nếu bạn muốn cho khách thanh toán lại;
        hiện tại đặt payment_status=failed.
        """
        db = OrderModel._db_admin()

        try:
            payload = {
                "payment_status": "failed",
            }

            if reason:
                payload["order_notes"] = reason

            db.table(OrderModel.ORDER_TABLE).update(payload).eq("id", order_id).execute()
            return True

        except Exception as e:
            logger.error("[OrderModel.mark_payment_failed] Lỗi đơn %s: %s", order_id, e)
            return False

    # ═══════════════════════════════════════════════════════════════
    # READ ORDER
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_by_id(order_id: str):
        db = OrderModel._db_admin()

        if not order_id:
            return None

        try:
            result = (
                db.table(OrderModel.ORDER_TABLE)
                .select(
                    "*, users(full_name, email, phone), "
                    "order_items(*, products(id, name, thumbnail_url, slug), product_variants(*))"
                )
                .eq("id", order_id)
                .single()
                .execute()
            )

            order = result.data
            if not order:
                return None

            try:
                rr = (
                    db.table(OrderModel.RETURN_TABLE)
                    .select("*")
                    .eq("order_id", order_id)
                    .order("requested_at", desc=True)
                    .limit(1)
                    .execute()
                )
                order["return_request"] = rr.data[0] if rr.data else None
            except Exception:
                order["return_request"] = None

            return order

        except Exception as e:
            logger.error("[OrderModel.get_by_id] Lỗi đơn %s: %s", order_id, e)
            return None

    @staticmethod
    def get_order_items_for_effects(order_id: str) -> List[Dict[str, Any]]:
        """
        Lấy order_items để controller/payment return ghi inventory/analytics.
        """
        db = OrderModel._db_admin()

        try:
            result = (
                db.table(OrderModel.ORDER_ITEM_TABLE)
                .select("*, products(id, name, price, thumbnail_url, slug), product_variants(*)")
                .eq("order_id", order_id)
                .execute()
            )
            return OrderModel._rows(result)

        except Exception as e:
            logger.error("[OrderModel.get_order_items_for_effects] Lỗi đơn %s: %s", order_id, e)
            return []

    @staticmethod
    def get_user_orders(user_id: str):
        """
        Khách xem đơn hàng cá nhân.
        Dùng admin client + lọc user_id để tránh RLS chặn nhưng vẫn bảo đảm chỉ trả về đơn của user.
        """
        db = OrderModel._db_admin()

        if not user_id:
            return []

        try:
            result = (
                db.table(OrderModel.ORDER_TABLE)
                .select("*, order_items(*, products(id, name, thumbnail_url, slug), product_variants(*))")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []

        except Exception as e:
            logger.error("[OrderModel.get_user_orders] Lỗi user %s: %s", user_id, e)
            return []

    @staticmethod
    def get_user_orders_paginated(user_id: str, page: int = 1, per_page: int = 10) -> dict:
        db = OrderModel._db_admin()

        if not user_id:
            return {
                "items": [],
                "pagination": {
                    "page": 1,
                    "per_page": per_page,
                    "total": 0,
                    "total_pages": 1,
                    "pages": 1,
                    "has_prev": False,
                    "has_next": False,
                },
            }

        page = max(1, int(page or 1))
        per_page = max(1, int(per_page or 10))
        offset = (page - 1) * per_page

        try:
            result = (
                db.table(OrderModel.ORDER_TABLE)
                .select(
                    "*, order_items(*, products(id, name, thumbnail_url, slug), product_variants(*))",
                    count="exact",
                )
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .range(offset, offset + per_page - 1)
                .execute()
            )

            total = result.count or 0
            total_pages = max(1, -(-total // per_page))

            return {
                "items": result.data or [],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": total_pages,
                    "pages": total_pages,
                    "has_prev": page > 1,
                    "has_next": page < total_pages,
                },
            }

        except Exception as e:
            logger.error("[OrderModel.get_user_orders_paginated] Lỗi user %s: %s", user_id, e)
            return {
                "items": [],
                "pagination": {
                    "page": 1,
                    "per_page": per_page,
                    "total": 0,
                    "total_pages": 1,
                    "pages": 1,
                    "has_prev": False,
                    "has_next": False,
                },
            }

    # ═══════════════════════════════════════════════════════════════
    # ADMIN LIST / DASHBOARD
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_all(page: int = 1, per_page: int = 20, status: str = None, keyword: str = None):
        db = OrderModel._db_admin()
        page = max(1, int(page or 1))
        per_page = max(1, int(per_page or 20))
        offset = (page - 1) * per_page

        try:
            query = (
                db.table(OrderModel.ORDER_TABLE)
                .select(
                    "*, users(email, full_name, phone), order_items(*, products(id, name, thumbnail_url))",
                    count="exact",
                )
                .order("created_at", desc=True)
            )

            if status:
                query = query.eq("status", status)

            if keyword:
                kw = keyword.strip().lstrip("#")
                query = query.or_(
                    f"id.ilike.%{kw}%,"
                    f"shipping_address->>phone.ilike.%{kw}%,"
                    f"shipping_address->>full_name.ilike.%{kw}%"
                )

            result = query.range(offset, offset + per_page - 1).execute()
            return {"items": result.data or [], "total": result.count or 0}

        except Exception as e:
            logger.error("[OrderModel.get_all] Lỗi lấy danh sách đơn hàng: %s", e)
            return {"items": [], "total": 0}

    @staticmethod
    def get_stats() -> dict:
        db = OrderModel._db_admin()

        stats = {
            "total_orders": 0,
            "total_revenue": 0,
            "net_revenue": 0,
            "pending": 0,
            "vnpay_orders": 0,
            "vnpay_ratio": 0,
            "monthly": [],
            "status_chart": [],
            "_orders": [],
            "vnpay_recent": [],
            "pending_returns": 0,
            "delivery_success": 0,
            "return_rate": 0,
            "avg_time": 0,
            "shipping_collected": 0,
            "actual_shipping_cost": 0,
            "logistics_profit_loss": 0,
        }

        try:
            refunds_map = defaultdict(float)

            try:
                refunds_res = (
                    db.table(OrderModel.RETURN_TABLE)
                    .select("order_id, refund_amount")
                    .eq("status", "refunded")
                    .execute()
                )

                for rr in refunds_res.data or []:
                    if rr.get("refund_amount"):
                        refunds_map[rr["order_id"]] += float(rr["refund_amount"])
            except Exception:
                pass

            order_res = (
                db.table(OrderModel.ORDER_TABLE)
                .select(
                    "id, total_amount, shipping_fee, status, payment_method, payment_status, "
                    "created_at, users(full_name, email)"
                )
                .order("created_at", desc=True)
                .limit(500)
                .execute()
            )

            orders = order_res.data or []
            stats["total_orders"] = len(orders)
            stats["_orders"] = orders[:8]

            status_counts = Counter()
            monthly_revenue = defaultdict(float)
            valid_orders = []
            vnpay_paid = []
            pending_count = 0

            for order in orders:
                status = order.get("status", "pending")
                amount = float(order.get("total_amount") or 0)
                refunded = refunds_map.get(order["id"], 0.0)
                payment_method = (order.get("payment_method") or "").upper()
                payment_status = order.get("payment_status", "pending")

                status_counts[status] += 1

                is_delivered = status in ("delivered", "completed")
                is_paid = payment_status == "paid"

                if is_delivered or is_paid:
                    net_rev = max(0, amount - refunded)
                    stats["total_revenue"] += net_rev
                    valid_orders.append(order)

                    if payment_method == "VNPAY":
                        vnpay_paid.append(order)

                    if order.get("created_at"):
                        month = order["created_at"][:7]
                        monthly_revenue[month] += net_rev

                if status == "pending" and (payment_method == "COD" or is_paid):
                    pending_count += 1

            stats["pending"] = pending_count
            stats["vnpay_orders"] = len(vnpay_paid)

            if valid_orders:
                stats["vnpay_ratio"] = round((len(vnpay_paid) / len(valid_orders)) * 100, 1)

            stats["vnpay_recent"] = sorted(
                vnpay_paid,
                key=lambda x: x.get("created_at", ""),
                reverse=True,
            )[:5]

            stats["status_chart"] = [
                {"status": key, "count": value}
                for key, value in status_counts.items()
            ]

            stats["monthly"] = [
                {"month": key, "revenue": round(value)}
                for key, value in sorted(monthly_revenue.items())[-6:]
            ]

            try:
                rr_count = (
                    db.table(OrderModel.RETURN_TABLE)
                    .select("id", count="exact")
                    .eq("status", "pending")
                    .execute()
                )
                stats["pending_returns"] = rr_count.count or 0
            except Exception:
                pass

            try:
                shipments_res = (
                    db.table(OrderModel.SHIPMENT_TABLE)
                    .select("status, created_at, shipped_at, delivered_at, shipping_fee, actual_shipping_fee")
                    .execute()
                )
                shipments = shipments_res.data or []
            except Exception:
                shipments = []

            total_shipped = len(shipments)
            delivered_count = sum(1 for s in shipments if s.get("status") == "delivered")
            returned_count = sum(
                1 for s in shipments
                if s.get("status") in ("returned", "failed", "cancelled")
            )

            for shipment in shipments:
                if shipment.get("status") != "cancelled":
                    stats["shipping_collected"] += float(shipment.get("shipping_fee") or 0)
                    stats["actual_shipping_cost"] += float(shipment.get("actual_shipping_fee") or 0)

            stats["logistics_profit_loss"] = stats["shipping_collected"] - stats["actual_shipping_cost"]
            stats["net_revenue"] = stats["total_revenue"] + stats["logistics_profit_loss"]
            stats["delivery_success"] = round((delivered_count / total_shipped * 100), 1) if total_shipped else 0
            stats["return_rate"] = round((returned_count / total_shipped * 100), 1) if total_shipped else 0

            total_days = 0.0
            valid_deliveries = 0

            for shipment in shipments:
                if (
                    shipment.get("status") == "delivered"
                    and shipment.get("shipped_at")
                    and shipment.get("delivered_at")
                ):
                    try:
                        start = datetime.fromisoformat(shipment["shipped_at"].replace("Z", "+00:00"))
                        end = datetime.fromisoformat(shipment["delivered_at"].replace("Z", "+00:00"))

                        total_days += (end - start).total_seconds() / 86400.0
                        valid_deliveries += 1
                    except Exception:
                        pass

            stats["avg_time"] = round((total_days / valid_deliveries), 1) if valid_deliveries else 0

        except Exception as e:
            logger.exception("[OrderModel.get_stats] Lỗi lấy thống kê Dashboard: %s", e)

        return stats

    # ═══════════════════════════════════════════════════════════════
    # UPDATE STATUS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def update_status(order_id: str, status: str) -> bool:
        db = OrderModel._db_admin()

        try:
            db.table(OrderModel.ORDER_TABLE).update({"status": status}).eq("id", order_id).execute()
            return True

        except Exception as e:
            logger.error("[OrderModel.update_status] Lỗi đơn %s: %s", order_id, e)
            return False

    @staticmethod
    def update_shipping_address(order_id: str, new_address: dict) -> bool:
        db = OrderModel._db_admin()

        try:
            db.table(OrderModel.ORDER_TABLE).update({"shipping_address": new_address}).eq("id", order_id).execute()
            return True

        except Exception as e:
            logger.error("[OrderModel.update_shipping_address] Lỗi đơn %s: %s", order_id, e)
            return False

    # ═══════════════════════════════════════════════════════════════
    # CANCEL / RETURN
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def cancel_order_by_user(order_id: str, user_id: str) -> Tuple[bool, str]:
        db = OrderModel._db_admin()

        try:
            order_res = (
                db.table(OrderModel.ORDER_TABLE)
                .select("created_at, status")
                .eq("id", order_id)
                .eq("user_id", user_id)
                .single()
                .execute()
            )

            order = order_res.data
            if not order:
                return False, "Không tìm thấy đơn hàng."

            if order["status"] != "pending":
                return False, "Đơn hàng đã được xử lý, không thể tự hủy."

            created_time = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))
            hours_passed = (datetime.now(timezone.utc) - created_time).total_seconds() / 3600

            if hours_passed > 3:
                return False, "Đã quá 3 giờ kể từ lúc đặt. Vui lòng liên hệ Hotline để hủy."

            db.table(OrderModel.ORDER_TABLE).update({"status": "cancelled"}).eq("id", order_id).execute()
            return True, "Đã hủy đơn hàng thành công."

        except Exception as e:
            logger.error("[OrderModel.cancel_order_by_user] Lỗi: %s", e)
            return False, "Lỗi hệ thống."

    @staticmethod
    def request_return(order_id: str, user_id: str, reason: str, image_url: str) -> Tuple[bool, str]:
        db = OrderModel._db_admin()

        try:
            order_res = (
                db.table(OrderModel.ORDER_TABLE)
                .select("status")
                .eq("id", order_id)
                .eq("user_id", user_id)
                .single()
                .execute()
            )

            order = order_res.data
            if not order:
                return False, "Không tìm thấy đơn hàng."

            if order["status"] not in ("delivered", "completed"):
                return False, "Chỉ đơn hàng đã giao thành công mới được yêu cầu đổi/trả."

            existing = (
                db.table(OrderModel.RETURN_TABLE)
                .select("id, status")
                .eq("order_id", order_id)
                .in_("status", ["pending", "approved", "refunded"])
                .execute()
            )

            if existing.data:
                return False, "Bạn đã có yêu cầu đổi/trả đang được xử lý cho đơn này."

            db.table(OrderModel.RETURN_TABLE).insert({
                "order_id": order_id,
                "user_id": user_id,
                "reason": reason,
                "image_url": image_url,
                "status": "pending",
            }).execute()

            return True, "Yêu cầu đổi/trả đã được ghi nhận. Đội ngũ GUAMAISON sẽ liên hệ bạn trong 24 giờ."

        except Exception as e:
            logger.error("[OrderModel.request_return] Lỗi: %s", e)
            return False, "Lỗi hệ thống."

    @staticmethod
    def get_return_requests(page: int = 1, per_page: int = 20, status: str = None) -> dict:
        db = OrderModel._db_admin()
        page = max(1, int(page or 1))
        per_page = max(1, int(per_page or 20))
        offset = (page - 1) * per_page

        try:
            query = (
                db.table(OrderModel.RETURN_TABLE)
                .select(
                    "*, orders(id, total_amount, payment_status, payment_method), "
                    "users(full_name, email, phone)",
                    count="exact",
                )
                .order("requested_at", desc=True)
            )

            if status:
                query = query.eq("status", status)

            result = query.range(offset, offset + per_page - 1).execute()
            return {"items": result.data or [], "total": result.count or 0}

        except Exception as e:
            logger.error("[OrderModel.get_return_requests] Lỗi: %s", e)
            return {"items": [], "total": 0}

    @staticmethod
    def get_return_request_by_id(rr_id: str) -> Optional[dict]:
        db = OrderModel._db_admin()

        try:
            result = (
                db.table(OrderModel.RETURN_TABLE)
                .select("*, orders(*, order_items(*, products(name, thumbnail_url))), users(full_name, email, phone)")
                .eq("id", rr_id)
                .single()
                .execute()
            )
            return result.data

        except Exception:
            return None

    @staticmethod
    def approve_return(rr_id: str, admin_user_id: str, admin_note: str = "") -> Tuple[bool, str]:
        db = OrderModel._db_admin()

        try:
            rr = (
                db.table(OrderModel.RETURN_TABLE)
                .select("status")
                .eq("id", rr_id)
                .single()
                .execute()
                .data
            )

            if not rr:
                return False, "Yêu cầu không tồn tại."

            if rr["status"] != "pending":
                return False, f"Yêu cầu đang ở trạng thái '{rr['status']}', không thể duyệt."

            db.table(OrderModel.RETURN_TABLE).update({
                "status": "approved",
                "reviewed_by": admin_user_id,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "admin_note": admin_note.strip() or None,
            }).eq("id", rr_id).execute()

            return True, "Đã duyệt yêu cầu đổi/trả. Tiến hành liên hệ khách hàng để nhận lại hàng."

        except Exception as e:
            logger.error("[OrderModel.approve_return] Lỗi %s: %s", rr_id, e)
            return False, "Lỗi hệ thống."

    @staticmethod
    def reject_return(rr_id: str, admin_user_id: str, admin_note: str) -> Tuple[bool, str]:
        db = OrderModel._db_admin()

        try:
            if not admin_note or not admin_note.strip():
                return False, "Vui lòng nhập lý do từ chối."

            rr = (
                db.table(OrderModel.RETURN_TABLE)
                .select("status, order_id")
                .eq("id", rr_id)
                .single()
                .execute()
                .data
            )

            if not rr:
                return False, "Yêu cầu không tồn tại."

            if rr["status"] != "pending":
                return False, f"Yêu cầu đang ở trạng thái '{rr['status']}', không thể từ chối."

            db.table(OrderModel.RETURN_TABLE).update({
                "status": "rejected",
                "reviewed_by": admin_user_id,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "admin_note": admin_note.strip(),
            }).eq("id", rr_id).execute()

            return True, "Đã từ chối yêu cầu. Khách hàng có thể gửi lại nếu muốn."

        except Exception as e:
            logger.error("[OrderModel.reject_return] Lỗi %s: %s", rr_id, e)
            return False, "Lỗi hệ thống."

    @staticmethod
    def complete_refund(rr_id: str, admin_user_id: str, refund_amount: float = None) -> Tuple[bool, str]:
        db = OrderModel._db_admin()

        try:
            rr = (
                db.table(OrderModel.RETURN_TABLE)
                .select("status, order_id")
                .eq("id", rr_id)
                .single()
                .execute()
                .data
            )

            if not rr:
                return False, "Yêu cầu không tồn tại."

            if rr["status"] != "approved":
                return False, "Yêu cầu phải ở trạng thái 'Đã duyệt' trước khi xác nhận hoàn tiền."

            order_id = rr["order_id"]

            order = (
                db.table(OrderModel.ORDER_TABLE)
                .select("total_amount, payment_status")
                .eq("id", order_id)
                .single()
                .execute()
                .data
            )

            if not order:
                return False, "Không tìm thấy đơn hàng liên quan."

            past_refunds = (
                db.table(OrderModel.RETURN_TABLE)
                .select("refund_amount")
                .eq("order_id", order_id)
                .eq("status", "refunded")
                .execute()
                .data
            )

            already_refunded = sum(
                float(item.get("refund_amount") or 0)
                for item in (past_refunds or [])
            )

            total_amount = float(order["total_amount"])
            max_refundable = total_amount - already_refunded

            if refund_amount is None:
                refund_amount = max_refundable
            else:
                refund_amount = float(refund_amount)

                if refund_amount > max_refundable:
                    return False, (
                        f"Số tiền hoàn ({refund_amount:,.0f}đ) vượt quá mức tối đa "
                        f"cho phép ({max_refundable:,.0f}đ)."
                    )

            db.table(OrderModel.RETURN_TABLE).update({
                "status": "refunded",
                "refund_amount": refund_amount,
                "refunded_at": datetime.now(timezone.utc).isoformat(),
                "reviewed_by": admin_user_id,
            }).eq("id", rr_id).execute()

            return True, f"Đã xác nhận hoàn tiền {refund_amount:,.0f}đ thành công."

        except Exception as e:
            logger.error("[OrderModel.complete_refund] Lỗi %s: %s", rr_id, e)
            return False, "Lỗi hệ thống."