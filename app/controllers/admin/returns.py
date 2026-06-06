"""
app/controllers/admin/returns.py
Quản lý yêu cầu đổi / trả hàng.
"""
from app.utils.supabase_client import get_supabase_admin
import logging
from flask import render_template, redirect, url_for, flash, session

from app.models.order_model import OrderModel
from app.middleware.auth_required import admin_required

from ._blueprint import admin_bp
from ._helpers import handle_errors, _args, _form, _db, _paginate, _total_pages

logger = logging.getLogger(__name__)

_RETURN_STATUSES = ("pending", "approved", "rejected", "refunded")

# ── Helpers ───────────────────────────────────────────────────────


def _count_by_status() -> dict:
    counts = {}

    try:
        db = get_supabase_admin()

        for s in _RETURN_STATUSES:
            r = (
                db.table("return_requests")
                .select("id", count="exact")
                .eq("status", s)
                .execute()
            )
            counts[s] = r.count or 0

        counts["all"] = sum(counts.values())

    except Exception as e:
        logger.error(f"[returns] Lỗi đếm return_requests theo status: {e}")
        counts = {"all": 0, **{s: 0 for s in _RETURN_STATUSES}}

    return counts
# ── Routes ────────────────────────────────────────────────────────


@admin_bp.route("/returns")
@admin_required
@handle_errors("Lỗi tải danh sách yêu cầu đổi/trả.", "admin.dashboard")
def return_requests():
    args = _args()
    page, per_page, _ = _paginate(args)
    status_filter = args.get("status", "").strip() or None

    result = OrderModel.get_return_requests(page=page, per_page=per_page, status=status_filter)
    tab_counts = _count_by_status()

    return render_template(
        "admin/return_requests.html",
        returns=result["items"],
        total=result["total"],
        page=page,
        total_pages=_total_pages(result["total"], per_page),
        current_status=status_filter or "all",
        tab_counts=tab_counts,
    )


@admin_bp.route("/returns/<rr_id>")
@admin_required
@handle_errors("Lỗi tải chi tiết yêu cầu.", "admin.return_requests")
def return_request_detail(rr_id: str):
    rr = OrderModel.get_return_request_by_id(rr_id)
    if not rr:
        flash("Yêu cầu không tồn tại.", "danger")
        return redirect(url_for("admin.return_requests"))
    return render_template("admin/return_request_detail.html", rr=rr)


@admin_bp.route("/returns/<rr_id>/approve", methods=["POST"])
@admin_required
@handle_errors("Lỗi duyệt yêu cầu.", "admin.return_requests")
def approve_return(rr_id: str):
    admin_note = _form().get("admin_note", "").strip()
    ok, msg = OrderModel.approve_return(rr_id, _admin_id(), admin_note)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("admin.return_request_detail", rr_id=rr_id))


@admin_bp.route("/returns/<rr_id>/reject", methods=["POST"])
@admin_required
@handle_errors("Lỗi từ chối yêu cầu.", "admin.return_requests")
def reject_return(rr_id: str):
    admin_note = _form().get("admin_note", "").strip()
    ok, msg = OrderModel.reject_return(rr_id, _admin_id(), admin_note)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("admin.return_request_detail", rr_id=rr_id))


@admin_bp.route("/returns/<rr_id>/refund", methods=["POST"])
@admin_required
@handle_errors("Lỗi xác nhận hoàn tiền.", "admin.return_requests")
def complete_refund(rr_id: str):
    raw = _form().get("refund_amount", "").strip()
    refund_amount = float(raw) if raw else None
    ok, msg = OrderModel.complete_refund(rr_id, _admin_id(), refund_amount)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for("admin.return_request_detail", rr_id=rr_id))

# ── Private ───────────────────────────────────────────────────────


def _admin_id() -> str:
    from flask import session
    return session.get("user_id", "unknown")
