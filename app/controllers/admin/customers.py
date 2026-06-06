"""
app/controllers/admin/customers.py
==================================
Quản lý khách hàng trong Admin.

Fix / cải thiện:
- Không dùng _db() anon client cho dữ liệu nội bộ admin.
- Dùng get_supabase_admin() cho users, user_addresses, orders, loyalty_transactions.
- Không select/update các cột không tồn tại như avatar_url, updated_at.
- Danh sách khách hàng không query địa chỉ theo kiểu N+1 nữa.
- Search được theo tên, email, phone.
- Validate form kỹ hơn.
- Chặn thao tác nhầm lên tài khoản admin/staff.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from flask import render_template, redirect, url_for, flash, request
import logging

from app.middleware.auth_required import admin_required
from app.utils.supabase_client import get_supabase_admin

from ._blueprint import admin_bp
from ._helpers import handle_errors, _form

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

CUSTOMER_LIST_FIELDS = (
    "id, email, full_name, phone, role, "
    "points, total_spent, member_tier, is_suspended, created_at"
)

CUSTOMER_DETAIL_FIELDS = (
    "id, email, full_name, phone, role, "
    "points, total_spent, member_tier, is_suspended, created_at"
)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _db_admin():
    """Service role client cho admin controllers."""
    return get_supabase_admin()


def _clean_text(value: Any, max_len: int | None = None) -> str:
    text = str(value or "").strip()

    if max_len is not None:
        text = text[:max_len]

    return text


def _clean_phone(value: Any) -> str | None:
    phone = _clean_text(value, max_len=30)

    if not phone:
        return None

    return phone


def _clean_search_query(value: Any) -> str:
    """
    Làm sạch search query trước khi đưa vào PostgREST or_.

    Tránh ký tự làm hỏng cú pháp:
    - comma
    - parentheses
    """
    q = _clean_text(value, max_len=80)

    for ch in [",", "(", ")", "{", "}", "[", "]"]:
        q = q.replace(ch, " ")

    return " ".join(q.split())


def _safe_int(
    value: Any,
    default: int = 0,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    try:
        number = int(value)
    except Exception:
        number = default

    if min_value is not None:
        number = max(min_value, number)

    if max_value is not None:
        number = min(max_value, number)

    return number


def _get_customer_or_none(user_id: str) -> dict | None:
    if not user_id:
        return None

    try:
        res = (
            _db_admin()
            .table("users")
            .select(CUSTOMER_DETAIL_FIELDS)
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        user = res.data[0] if res.data else None

        if not user:
            return None

        if user.get("role") != "customer":
            logger.warning(
                "[customers] Chặn thao tác customer route với non-customer user_id=%s role=%s",
                user_id,
                user.get("role"),
            )
            return None

        return user

    except Exception as e:
        logger.error(
            "[customers] _get_customer_or_none error user_id=%s: %s",
            user_id,
            e,
            exc_info=True,
        )
        return None


def _get_default_addresses_map(user_ids: list[str]) -> dict[str, dict]:
    """
    Lấy địa chỉ mặc định cho nhiều user trong một query.
    Tránh N+1 query khi render danh sách khách hàng.
    """
    if not user_ids:
        return {}

    try:
        res = (
            _db_admin()
            .table("user_addresses")
            .select("*")
            .in_("user_id", user_ids)
            .eq("is_default", True)
            .execute()
        )

        rows = res.data or []
        return {
            row["user_id"]: row
            for row in rows
            if row.get("user_id")
        }

    except Exception as e:
        logger.error("[customers] Lỗi lấy default addresses: %s", e, exc_info=True)
        return {}


def _get_customer_order_count(user_id: str) -> int:
    try:
        res = (
            _db_admin()
            .table("orders")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return int(res.count or 0)

    except Exception as e:
        logger.error("[customers] Lỗi đếm orders user_id=%s: %s", user_id, e, exc_info=True)
        return 0


def _get_customer_orders(user_id: str, limit: int = 20) -> list[dict]:
    try:
        res = (
            _db_admin()
            .table("orders")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    except Exception as e:
        logger.error("[customers] Lỗi lấy orders user_id=%s: %s", user_id, e, exc_info=True)
        return []


def _get_loyalty_history(user_id: str, limit: int = 15) -> list[dict]:
    try:
        res = (
            _db_admin()
            .table("loyalty_transactions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    except Exception as e:
        logger.error("[customers] Lỗi lấy loyalty history user_id=%s: %s", user_id, e, exc_info=True)
        return []


def _format_duplicate_error(e: Exception) -> bool:
    err_msg = str(e).lower()

    return (
        "duplicate key value" in err_msg
        or "users_phone_key" in err_msg
        or "unique constraint" in err_msg
    )


# ═══════════════════════════════════════════════════════════════
# LIST
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/customers")
@admin_required
@handle_errors("Lỗi tải danh sách khách hàng.")
def customers():
    """
    Danh sách khách hàng.

    Query params:
    - q: tìm theo full_name, email, phone
    """
    db = _db_admin()

    search_query = _clean_search_query(request.args.get("q", ""))

    query = (
        db.table("users")
        .select(CUSTOMER_LIST_FIELDS)
        .eq("role", "customer")
        .order("created_at", desc=True)
    )

    if search_query:
        query = query.or_(
            "full_name.ilike.%{0}%,email.ilike.%{0}%,phone.ilike.%{0}%".format(search_query)
        )

    users = query.execute().data or []

    user_ids = [u["id"] for u in users if u.get("id")]
    default_address_map = _get_default_addresses_map(user_ids)

    for user in users:
        user["default_address"] = default_address_map.get(user.get("id"))

    return render_template(
        "admin/customers.html",
        customers=users,
        users=users,
        q=search_query,
    )


# ═══════════════════════════════════════════════════════════════
# EDIT / VIEW DETAIL
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/customers/edit/<user_id>", methods=["GET", "POST"])
@admin_required
@handle_errors("Lỗi tải thông tin khách hàng.", "admin.customers")
def edit_customer(user_id):
    db = _db_admin()

    customer = _get_customer_or_none(user_id)

    if not customer:
        flash("Không tìm thấy khách hàng hoặc tài khoản này không phải khách hàng.", "error")
        return redirect(url_for("admin.customers"))

    if request.method == "POST":
        form = _form()

        full_name = _clean_text(form.get("full_name"), max_len=150)
        phone = _clean_phone(form.get("phone"))

        try:
            payload = {
                "full_name": full_name or None,
                "phone": phone,
            }

            (
                db.table("users")
                .update(payload)
                .eq("id", user_id)
                .eq("role", "customer")
                .execute()
            )

            flash("Cập nhật hồ sơ khách hàng thành công.", "success")

        except Exception as e:
            if _format_duplicate_error(e):
                flash("Số điện thoại này đã được đăng ký cho một tài khoản khác.", "error")
            else:
                logger.error("[edit_customer] Lỗi cập nhật user_id=%s: %s", user_id, e, exc_info=True)
                flash("Có lỗi xảy ra khi lưu thông tin. Vui lòng thử lại.", "error")

        return redirect(url_for("admin.edit_customer", user_id=user_id))

    order_count = _get_customer_order_count(user_id)
    user_orders = _get_customer_orders(user_id, limit=20)
    loyalty_history = _get_loyalty_history(user_id, limit=15)

    return render_template(
        "admin/customer_form.html",
        customer=customer,
        order_count=order_count,
        loyalty_history=loyalty_history,
        user_orders=user_orders,
    )


# ═══════════════════════════════════════════════════════════════
# ADJUST POINTS
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/customers/adjust-points/<user_id>", methods=["POST"])
@admin_required
@handle_errors("Lỗi điều chỉnh điểm khách hàng.", "admin.customers")
def adjust_customer_points(user_id):
    customer = _get_customer_or_none(user_id)

    if not customer:
        flash("Không tìm thấy khách hàng hoặc tài khoản này không phải khách hàng.", "error")
        return redirect(url_for("admin.customers"))

    form = _form()

    action_type = _clean_text(form.get("action_type"))
    amount = _safe_int(form.get("amount"), default=0, min_value=1, max_value=1_000_000)
    description = _clean_text(form.get("description"), max_len=255)

    if action_type not in {"add", "deduct"}:
        flash("Loại thao tác điểm không hợp lệ.", "error")
        return redirect(url_for("admin.edit_customer", user_id=user_id))

    if amount <= 0 or not description:
        flash("Số điểm và lý do là bắt buộc.", "error")
        return redirect(url_for("admin.edit_customer", user_id=user_id))

    final_amount = amount if action_type == "add" else -amount
    txn_type = "MANUAL_BONUS" if action_type == "add" else "MANUAL_DEDUCT"
    expires_at = (
        (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        if action_type == "add"
        else None
    )

    try:
        (
            _db_admin()
            .table("loyalty_transactions")
            .insert({
                "user_id": user_id,
                "amount": final_amount,
                "transaction_type": txn_type,
                "description": f"[Admin] {description}",
                "expires_at": expires_at,
            })
            .execute()
        )

        flash(
            f"Đã {'tặng thêm' if action_type == 'add' else 'trừ'} {amount} điểm thành công.",
            "success",
        )

    except Exception as e:
        logger.error("[adjust_customer_points] Lỗi user_id=%s: %s", user_id, e, exc_info=True)
        flash("Lỗi hệ thống khi điều chỉnh điểm.", "error")

    return redirect(url_for("admin.edit_customer", user_id=user_id))


# ═══════════════════════════════════════════════════════════════
# DELETE
# ═══════════════════════════════════════════════════════════════

@admin_bp.route("/customers/delete/<user_id>", methods=["POST"])
@admin_required
@handle_errors("Lỗi xóa khách hàng.", "admin.customers")
def delete_customer(user_id):
    """
    Xóa khách hàng.

    Lưu ý:
    - Chỉ cho phép xóa role='customer'.
    - Không xóa admin/staff qua route này.
    - Nếu DB có FK chặn xóa cứng, bạn nên đổi sang khóa tài khoản bằng is_suspended=True.
    """
    customer = _get_customer_or_none(user_id)

    if not customer:
        flash("Không tìm thấy khách hàng hoặc tài khoản này không phải khách hàng.", "error")
        return redirect(url_for("admin.customers"))

    try:
        (
            _db_admin()
            .table("users")
            .delete()
            .eq("id", user_id)
            .eq("role", "customer")
            .execute()
        )

        flash("Đã xóa khách hàng.", "success")

    except Exception as e:
        logger.error("[delete_customer] Lỗi khi xóa user_id=%s: %s", user_id, e, exc_info=True)
        flash(
            "Không thể xóa khách hàng vì có thể còn đơn hàng/dữ liệu liên quan. "
            "Bạn nên khóa tài khoản thay vì xóa cứng.",
            "error",
        )

    return redirect(url_for("admin.customers"))