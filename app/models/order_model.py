"""
app/models/order_model.py
=========================
Quản lý vòng đời đơn hàng, thống kê tài chính, logistics và hỗ trợ vận hành cho GUA Maison.

CHANGELOG (Tối ưu hóa Lazy Initialization Toàn diện):
  - Khởi chạy cơ chế Lazy Initialization qua hai cổng _db() (Public) và _db_admin() (Bypass RLS).
  - Di chuyển toàn bộ các hàm nghiệp vụ quản trị, thống kê Dashboard sang kênh Admin Client.
  - Fix lỗi PGRST204: Loại bỏ cột 'size' không tồn tại khi insert order_items.
  - unit_price tính đúng: ưu tiên variant.price_override, fallback về products.price.
  - variant_label và product_name được snapshot ngay tại thời điểm create_order.
  - Fix lỗi Schema: Không query/update các cột ảo (refunded_amount, is_return_requested).
"""

import logging
from collections import defaultdict, Counter
from datetime import datetime, timezone
from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)


class OrderModel:

    # ═══════════════════════════════════════════════════════════════
    #  LAZY INITIALIZATION HELPERS (KHỞI TẠO LƯỜI THEO PHÂN VÙNG QUYỀN)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _db():
        """Khởi tạo lười Client công khai (Dành cho khách hàng tra cứu đơn hàng)"""
        return get_supabase()

    @staticmethod
    def _db_admin():
        """Khởi tạo lười Client quyền Admin (Bypass RLS, bảo đảm nạp stats tài chính chính xác)"""
        return get_supabase_admin()

    # ═══════════════════════════════════════════════════════════════
    #  TẠO ĐƠN HÀNG (Dành cho Checkout)
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
        Khởi tạo đơn hàng với đầy đủ snapshot về phí ship, giảm giá,
        product_name và variant_label. Không insert cột 'size' (không tồn tại trong DB).
        """
        db = OrderModel._db_admin() # Dùng quyền admin để bảo đảm luôn khởi tạo đơn hàng thành công
        try:
            # ── 1. Tạo bản ghi orders ────────────────────────────────
            order_data = {
                "user_id": user_id,
                "total_amount": float(total),
                "shipping_fee": float(shipping_fee),
                "discount_amount": float(discount_amount),
                "shipping_address": address,
                "status": "pending",
                "payment_method": payment_method.upper(),
                "payment_status": "pending",
                "order_notes": order_notes,
            }

            r = db.table("orders").insert(order_data).execute()
            if not r.data:
                logger.error("[OrderModel.create_order] insert orders trả về rỗng.")
                return {}

            order = r.data[0]
            order_id = order["id"]

            # ── 2. Build order_items — đúng schema, có snapshot ─────
            order_items = []
            for item in items:
                product = item.get("products") or {}
                variant = item.get("product_variants") or {}

                price_override = variant.get("price_override")
                unit_price = float(price_override) if price_override else float(product.get("price", 0))

                product_name = product.get("name") or "Sản phẩm"
                color = (variant.get("color_name") or "").strip()
                size  = (variant.get("size") or "").strip()
                if color and size:
                    variant_label = f"{color} - Size {size}"
                elif color:
                    variant_label = color
                elif size:
                    variant_label = f"Size {size}"
                else:
                    variant_label = None

                order_items.append({
                    "order_id":      order_id,
                    "product_id":    item.get("product_id"),
                    "variant_id":    item.get("variant_id") or None,
                    "quantity":      int(item.get("quantity", 1)),
                    "unit_price":    unit_price,
                    "product_name":  product_name,    
                    "variant_label": variant_label,   
                })

            if order_items:
                db.table("order_items").insert(order_items).execute()

            return order

        except Exception as e:
            logger.exception("Lỗi tạo đơn hàng: %s", e)
            return {}

    # ═══════════════════════════════════════════════════════════════
    #  THỐNG KÊ DASHBOARD (ĐÃ CHUYỂN TOÀN BỘ SANG ADMIN CLIENT)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_stats() -> dict:
        """Tính toán các chỉ số kinh doanh cốt lõi (Bypass RLS tránh lỗi mảng rỗng [])."""
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
            try:
                refunds_res = (
                    db.table("return_requests")
                    .select("order_id, refund_amount")
                    .eq("status", "refunded")
                    .execute()
                )
                refunds_map = defaultdict(float)
                for r_req in (refunds_res.data or []):
                    if r_req.get("refund_amount"):
                        refunds_map[r_req["order_id"]] += float(r_req["refund_amount"])
            except Exception:
                refunds_map = defaultdict(float)

            # 1. THỐNG KÊ DOANH THU & ĐƠN HÀNG
            r = (
                db.table("orders")
                .select(
                    "id, total_amount, shipping_fee, status, payment_method, payment_status, "
                    "created_at, users(full_name, email)"
                )
                .order("created_at", desc=True)
                .limit(500)
                .execute()
            )

            orders = r.data or []
            stats["total_orders"] = len(orders)
            stats["_orders"] = orders[:8]

            status_counts = Counter()
            monthly_revenue = defaultdict(float)
            valid_orders = []
            vnpay_paid = []
            pending_count = 0

            for o in orders:
                status         = o.get("status", "pending")
                amount         = float(o.get("total_amount", 0))
                refunded       = refunds_map.get(o["id"], 0.0)
                payment_method = o.get("payment_method", "").upper()
                payment_status = o.get("payment_status", "pending")

                status_counts[status] += 1

                is_delivered = status in ("delivered", "completed")
                is_paid      = payment_status == "paid"

                if is_delivered or is_paid:
                    net_rev = amount - refunded
                    stats["total_revenue"] += net_rev
                    valid_orders.append(o)

                    if payment_method == "VNPAY":
                        vnpay_paid.append(o)

                    if o.get("created_at"):
                        month = o["created_at"][:7]  # YYYY-MM
                        monthly_revenue[month] += net_rev

                if status == "pending" and (payment_method == "COD" or is_paid):
                    pending_count += 1

            stats["pending"]       = pending_count
            stats["vnpay_orders"]  = len(vnpay_paid)
            if valid_orders:
                stats["vnpay_ratio"] = round((len(vnpay_paid) / len(valid_orders)) * 100, 1)

            stats["vnpay_recent"]  = sorted(vnpay_paid, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
            stats["status_chart"]  = [{"status": k, "count": v} for k, v in status_counts.items()]
            stats["monthly"]       = [
                {"month": k, "revenue": round(v)}
                for k, v in sorted(monthly_revenue.items())[-6:]
            ]

            # 2. ĐỔI TRẢ
            try:
                rr = db.table("return_requests").select("id", count="exact").eq("status", "pending").execute()
                stats["pending_returns"] = rr.count or 0
            except Exception:
                pass

            # 3. LOGISTICS & TÀI CHÍNH VẬN CHUYỂN
            shipments_res = (
                db.table("shipments")
                .select("status, created_at, shipped_at, delivered_at, shipping_fee, actual_shipping_fee")
                .execute()
            )
            shipments = shipments_res.data or []

            total_shipped   = len(shipments)
            delivered_count = sum(1 for s in shipments if s["status"] == "delivered")
            returned_count  = sum(1 for s in shipments if s["status"] in ("returned", "failed", "cancelled"))

            for s in shipments:
                if s["status"] != "cancelled":
                    stats["shipping_collected"]   += float(s.get("shipping_fee") or 0)
                    stats["actual_shipping_cost"] += float(s.get("actual_shipping_fee") or 0)

            stats["logistics_profit_loss"] = stats["shipping_collected"] - stats["actual_shipping_cost"]
            stats["net_revenue"]           = stats["total_revenue"] + stats["logistics_profit_loss"]

            stats["delivery_success"] = round((delivered_count / total_shipped * 100), 1) if total_shipped > 0 else 0
            stats["return_rate"]      = round((returned_count  / total_shipped * 100), 1) if total_shipped > 0 else 0

            total_days       = 0
            valid_deliveries = 0
            for s in shipments:
                if s["status"] == "delivered" and s.get("shipped_at") and s.get("delivered_at"):
                    try:
                        start = datetime.fromisoformat(s["shipped_at"].replace("Z", "+00:00"))
                        end   = datetime.fromisoformat(s["delivered_at"].replace("Z", "+00:00"))
                        total_days += (end - start).total_seconds() / 86400.0
                        valid_deliveries += 1
                    except Exception:
                        pass

            stats["avg_time"] = round((total_days / valid_deliveries), 1) if valid_deliveries > 0 else 0

        except Exception as e:
            logger.exception("Lỗi lấy thống kê Dashboard: %s", e)

        return stats

    # ═══════════════════════════════════════════════════════════════
    #  QUẢN LÝ ĐƠN HÀNG (CHI TIẾT & DANH SÁCH)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_by_id(order_id: str):
        db = OrderModel._db_admin() # Dùng admin client để nạp thông tin chi tiết đơn không bị chặn RLS
        try:
            r = (
                db.table("orders")
                .select(
                    "*, users(full_name, email, phone), "
                    "order_items(*, products(id, name, thumbnail_url, slug), product_variants(*))"
                )
                .eq("id", order_id)
                .single()
                .execute()
            )
            order = r.data
            if not order:
                return None

            try:
                rr = (
                    db.table("return_requests")
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
            logger.error("Lỗi get_by_id cho đơn %s: %s", order_id, e)
            return None

    @staticmethod
    def get_all(page: int = 1, per_page: int = 20, status: str = None, keyword: str = None):
        db = OrderModel._db_admin() # Thao tác Admin Workspace sử dụng Admin Client
        offset = (page - 1) * per_page
        try:
            query = (
                db.table("orders")
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
                kw_lower = kw.lower()
                query = query.or_(
                    f"id.ilike.%{kw_lower}%,"
                    f"shipping_address->>phone.ilike.%{kw}%,"
                    f"shipping_address->>full_name.ilike.%{kw}%"
                )

            r = query.range(offset, offset + per_page - 1).execute()
            return {"items": r.data or [], "total": r.count or 0}
        except Exception as e:
            logger.error("Lỗi lấy danh sách đơn hàng: %s", e)
            return {"items": [], "total": 0}

    @staticmethod
    def get_user_orders(user_id: str):
        db = OrderModel._db() # Sử dụng Public Client tra cứu đơn hàng cá nhân của User đã authenticate
        try:
            r = (
                db.table("orders")
                .select("*, order_items(*, products(id, name, thumbnail_url, slug), product_variants(*))")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return r.data or []
        except Exception as e:
            logger.error("Lỗi lấy đơn hàng user %s: %s", user_id, e)
            return []

    @staticmethod
    def get_user_orders_paginated(user_id: str, page: int = 1, per_page: int = 10) -> dict:
        db = OrderModel._db()
        offset = (page - 1) * per_page
        try:
            r = (
                db.table("orders")
                .select(
                    "*, order_items(*, products(id, name, thumbnail_url, slug), product_variants(*))",
                    count="exact",
                )
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .range(offset, offset + per_page - 1)
                .execute()
            )
            total       = r.count or 0
            total_pages = max(1, -(-total // per_page))
            return {
                "items": r.data or [],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": total_pages,
                    "has_prev": page > 1,
                    "has_next": page < total_pages,
                },
            }
        except Exception as e:
            logger.error("Lỗi lấy đơn hàng phân trang user %s: %s", user_id, e)
            return {
                "items": [],
                "pagination": {
                    "page": 1, "per_page": per_page, "total": 0,
                    "total_pages": 1, "has_prev": False, "has_next": False,
                },
            }

    # ═══════════════════════════════════════════════════════════════
    #  CẬP NHẬT TRẠNG THÁI & HOTLINE (DÙNG ADMIN CLIENT)
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def update_status(order_id: str, status: str) -> bool:
        db = OrderModel._db_admin()
        try:
            db.table("orders").update({"status": status}).eq("id", order_id).execute()
            return True
        except Exception as e:
            logger.error("Lỗi cập nhật trạng thái đơn %s: %s", order_id, e)
            return False

    @staticmethod
    def update_payment_status(order_id: str, payment_status: str, transaction_id: str = None) -> bool:
        db = OrderModel._db_admin()
        try:
            payload = {"payment_status": payment_status}
            if transaction_id:
                payload["transaction_id"] = transaction_id
            db.table("orders").update(payload).eq("id", order_id).execute()
            return True
        except Exception as e:
            logger.error("Lỗi cập nhật thanh toán đơn %s: %s", order_id, e)
            return False

    @staticmethod
    def update_shipping_address(order_id: str, new_address: dict) -> bool:
        db = OrderModel._db_admin()
        try:
            db.table("orders").update({"shipping_address": new_address}).eq("id", order_id).execute()
            return True
        except Exception as e:
            logger.error("Lỗi sửa địa chỉ Hotline cho đơn %s: %s", order_id, e)
            return False

    # ═══════════════════════════════════════════════════════════════
    #  HỦY ĐƠN & ĐỔI TRẢ — KHÁCH HÀNG & ADMIN
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def cancel_order_by_user(order_id: str, user_id: str) -> tuple[bool, str]:
        db = OrderModel._db_admin() # Dùng admin để bypass các hạn chế RLS update trạng thái phía client
        try:
            order_res = (
                db.table("orders")
                .select("created_at, status")
                .eq("id", order_id)
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            if not order_res.data:
                return False, "Không tìm thấy đơn hàng."

            order = order_res.data
            if order["status"] != "pending":
                return False, "Đơn hàng đã được xử lý, không thể tự hủy."

            created_time = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00"))
            hours_passed = (datetime.now(timezone.utc) - created_time).total_seconds() / 3600

            if hours_passed > 3:
                return False, "Đã quá 3 giờ kể từ lúc đặt. Vui lòng liên hệ Hotline để hủy."

            db.table("orders").update({"status": "cancelled"}).eq("id", order_id).execute()
            return True, "Đã hủy đơn hàng thành công."
        except Exception as e:
            logger.error("Lỗi hủy đơn user: %s", e)
            return False, "Lỗi hệ thống."

    @staticmethod
    def request_return(order_id: str, user_id: str, reason: str, image_url: str) -> tuple[bool, str]:
        db = OrderModel._db_admin()
        try:
            order_res = (
                db.table("orders")
                .select("status")
                .eq("id", order_id)
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            if not order_res.data:
                return False, "Không tìm thấy đơn hàng."

            if order_res.data["status"] not in ("delivered", "completed"):
                return False, "Chỉ đơn hàng đã giao thành công mới được yêu cầu đổi/trả."

            existing = (
                db.table("return_requests")
                .select("id, status")
                .eq("order_id", order_id)
                .in_("status", ["pending", "approved", "refunded"])
                .execute()
            )
            if existing.data:
                return False, "Bạn đã có yêu cầu đổi/trả đang được xử lý cho đơn này."

            db.table("return_requests").insert({
                "order_id": order_id,
                "user_id": user_id,
                "reason": reason,
                "image_url": image_url,
                "status": "pending",
            }).execute()

            return True, "Yêu cầu đổi/trả đã được ghi nhận. Đội ngũ GUA sẽ liên hệ bạn trong 24 giờ."
        except Exception as e:
            logger.error("Lỗi gửi yêu cầu đổi/trả: %s", e)
            return False, "Lỗi hệ thống."

    @staticmethod
    def get_return_requests(page: int = 1, per_page: int = 20, status: str = None) -> dict:
        db = OrderModel._db_admin()
        offset = (page - 1) * per_page
        try:
            query = (
                db.table("return_requests")
                .select(
                    "*, orders(id, total_amount, payment_status, payment_method), "
                    "users(full_name, email, phone)",
                    count="exact",
                )
                .order("requested_at", desc=True)
            )
            if status:
                query = query.eq("status", status)

            r = query.range(offset, offset + per_page - 1).execute()
            return {"items": r.data or [], "total": r.count or 0}
        except Exception as e:
            logger.error("Lỗi lấy return_requests: %s", e)
            return {"items": [], "total": 0}

    @staticmethod
    def get_return_request_by_id(rr_id: str) -> dict | None:
        db = OrderModel._db_admin()
        try:
            r = (
                db.table("return_requests")
                .select("*, orders(*, order_items(*, products(name, thumbnail_url))), users(full_name, email, phone)")
                .eq("id", rr_id)
                .single()
                .execute()
            )
            return r.data
        except Exception:
            return None

    @staticmethod
    def approve_return(rr_id: str, admin_user_id: str, admin_note: str = "") -> tuple[bool, str]:
        db = OrderModel._db_admin()
        try:
            rr = db.table("return_requests").select("status").eq("id", rr_id).single().execute().data
            if not rr:
                return False, "Yêu cầu không tồn tại."
            if rr["status"] != "pending":
                return False, f"Yêu cầu đang ở trạng thái '{rr['status']}', không thể duyệt."

            db.table("return_requests").update({
                "status": "approved",
                "reviewed_by": admin_user_id,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "admin_note": admin_note.strip() or None,
            }).eq("id", rr_id).execute()

            return True, "Đã duyệt yêu cầu đổi/trả. Tiến hành liên hệ khách hàng để nhận lại hàng."
        except Exception as e:
            logger.error("Lỗi duyệt return_request %s: %s", rr_id, e)
            return False, "Lỗi hệ thống."

    @staticmethod
    def reject_return(rr_id: str, admin_user_id: str, admin_note: str) -> tuple[bool, str]:
        db = OrderModel._db_admin()
        try:
            if not admin_note or not admin_note.strip():
                return False, "Vui lòng nhập lý do từ chối."

            rr = (
                db.table("return_requests")
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

            db.table("return_requests").update({
                "status": "rejected",
                "reviewed_by": admin_user_id,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "admin_note": admin_note.strip(),
            }).eq("id", rr_id).execute()

            return True, "Đã từ chối yêu cầu. Khách hàng có thể gửi lại nếu muốn."
        except Exception as e:
            logger.error("Lỗi từ chối return_request %s: %s", rr_id, e)
            return False, "Lỗi hệ thống."

    @staticmethod
    def complete_refund(rr_id: str, admin_user_id: str, refund_amount: float = None) -> tuple[bool, str]:
        db = OrderModel._db_admin()
        try:
            rr = (
                db.table("return_requests")
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
                db.table("orders")
                .select("total_amount, payment_status")
                .eq("id", order_id)
                .single()
                .execute()
                .data
            )
            if not order:
                return False, "Không tìm thấy đơn hàng liên quan."

            past_refunds = (
                db.table("return_requests")
                .select("refund_amount")
                .eq("order_id", order_id)
                .eq("status", "refunded")
                .execute()
                .data
            )
            already_refunded = sum(float(pr.get("refund_amount") or 0) for pr in (past_refunds or []))

            total_amount   = float(order["total_amount"])
            max_refundable = total_amount - already_refunded

            if refund_amount is None:
                refund_amount = max_refundable
            else:
                refund_amount = float(refund_amount)
                if refund_amount > max_refundable:
                    return False, f"Số tiền hoàn ({refund_amount:,.0f}đ) vượt quá mức tối đa cho phép ({max_refundable:,.0f}đ)."

            db.table("return_requests").update({
                "status": "refunded",
                "refund_amount": refund_amount,
                "refunded_at": datetime.now(timezone.utc).isoformat(),
                "reviewed_by": admin_user_id,
            }).eq("id", rr_id).execute()

            return True, f"Đã xác nhận hoàn tiền {refund_amount:,.0f}đ thành công."
        except Exception as e:
            logger.error("Lỗi complete_refund %s: %s", rr_id, e)
            return False, "Lỗi hệ thống."