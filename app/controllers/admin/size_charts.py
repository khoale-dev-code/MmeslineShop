"""CRUD bảng size sản phẩm trong admin."""

from __future__ import annotations

import logging

from flask import flash, redirect, render_template, request, url_for

from app.middleware.auth_required import admin_required
from app.models.size_chart_model import SizeChartModel
from app.services.audit_service import AuditService

from ._blueprint import admin_bp

logger = logging.getLogger(__name__)


def _read_image(current_url: str = "") -> tuple[str, bool, str]:
    """Ưu tiên file upload, sau đó URL nhập tay, cuối cùng giữ ảnh hiện tại."""
    image_url = SizeChartModel._safe_url(request.form.get("image_url"))
    uploaded = False
    file = request.files.get("image")

    if file and file.filename:
        payload = file.read()
        if not payload:
            return "", False, "Tệp ảnh đang trống."
        image_url = SizeChartModel.upload_image(
            payload,
            file.filename,
            file.content_type,
        )
        if not image_url:
            return "", False, "Ảnh không hợp lệ, lớn hơn 10 MB hoặc tải lên thất bại."
        uploaded = True

    image_url = image_url or SizeChartModel._safe_url(current_url)
    if not image_url:
        return "", uploaded, "Vui lòng tải ảnh bảng size hoặc nhập URL ảnh https hợp lệ."
    return image_url, uploaded, ""


def _audit(action: str, chart_id: str, old_values=None, new_values=None) -> None:
    try:
        AuditService.log_action(
            action=action,
            table_name="store_settings:size_charts",
            record_id=chart_id,
            old_values=old_values,
            new_values=new_values,
        )
    except Exception as exc:
        logger.warning("[Size Charts] Không ghi được audit log: %s", exc)


@admin_bp.route("/size-charts", methods=["GET"])
@admin_required
def size_charts_page():
    charts = SizeChartModel.get_all(force_reload=True)
    usage = SizeChartModel.usage_counts([chart.get("name") for chart in charts])
    for chart in charts:
        chart["usage_count"] = usage.get(SizeChartModel._name_key(chart.get("name")), 0)
    return render_template("admin/size_charts/index.html", size_charts=charts)


@admin_bp.route("/size-charts/create", methods=["POST"])
@admin_required
def create_size_chart():
    image_url, uploaded, error = _read_image()
    if error:
        flash(error, "danger")
        return redirect(url_for("admin.size_charts_page"))

    success, chart, message = SizeChartModel.create(
        name=request.form.get("name"),
        image_url=image_url,
        is_active="is_active" in request.form,
    )
    if not success:
        if uploaded:
            SizeChartModel.delete_image_from_url(image_url)
        flash(message, "danger")
        return redirect(url_for("admin.size_charts_page"))

    _audit("CREATE", chart["id"], new_values=chart)
    flash(f"Đã tạo bảng size “{chart['name']}”. Dùng đúng tên này làm tag sản phẩm.", "success")
    return redirect(url_for("admin.size_charts_page"))


@admin_bp.route("/size-charts/<chart_id>/update", methods=["POST"])
@admin_required
def update_size_chart(chart_id: str):
    current = SizeChartModel.get_by_id(chart_id, force_reload=True)
    if not current:
        flash("Bảng size không tồn tại.", "danger")
        return redirect(url_for("admin.size_charts_page"))

    image_url, uploaded, error = _read_image(current.get("image_url") or "")
    if error:
        flash(error, "danger")
        return redirect(url_for("admin.size_charts_page"))

    success, old_chart, new_chart, message = SizeChartModel.update(
        chart_id,
        name=request.form.get("name"),
        image_url=image_url,
        is_active="is_active" in request.form,
    )
    if not success:
        if uploaded:
            SizeChartModel.delete_image_from_url(image_url)
        flash(message, "danger")
        return redirect(url_for("admin.size_charts_page"))

    if old_chart.get("image_url") != image_url:
        SizeChartModel.delete_image_from_url(old_chart.get("image_url"))

    old_name = old_chart.get("name") or ""
    new_name = new_chart.get("name") or ""
    migration = SizeChartModel.rename_product_tag(old_name, new_name)
    _audit("UPDATE", chart_id, old_values=old_chart, new_values=new_chart)

    if migration.get("failed"):
        flash(
            f"Đã cập nhật bảng size nhưng có {migration['failed']} sản phẩm chưa đổi được tag. "
            "Vui lòng mở lại các sản phẩm này và chọn bảng size mới.",
            "warning",
        )
    elif migration.get("updated"):
        flash(
            f"Đã cập nhật bảng size và đổi tag trên {migration['updated']} sản phẩm liên kết.",
            "success",
        )
    else:
        flash("Đã cập nhật bảng size.", "success")
    return redirect(url_for("admin.size_charts_page"))


@admin_bp.route("/size-charts/<chart_id>/delete", methods=["POST"])
@admin_required
def delete_size_chart(chart_id: str):
    chart = SizeChartModel.get_by_id(chart_id, force_reload=True)
    if not chart:
        flash("Bảng size không tồn tại.", "danger")
        return redirect(url_for("admin.size_charts_page"))

    usage = SizeChartModel.usage_counts([chart.get("name")])
    used_count = usage.get(SizeChartModel._name_key(chart.get("name")), 0)
    if used_count > 0:
        flash(
            f"Chưa thể xóa vì còn {used_count} sản phẩm mang tag “{chart['name']}”. "
            "Hãy bỏ hoặc đổi bảng size trên các sản phẩm đó trước.",
            "warning",
        )
        return redirect(url_for("admin.size_charts_page"))

    success, deleted, message = SizeChartModel.delete(chart_id)
    if not success:
        flash(message, "danger")
        return redirect(url_for("admin.size_charts_page"))

    SizeChartModel.delete_image_from_url(deleted.get("image_url"))
    _audit("DELETE", chart_id, old_values=deleted)
    flash(f"Đã xóa bảng size “{deleted['name']}” cùng ảnh được quản lý bởi hệ thống.", "success")
    return redirect(url_for("admin.size_charts_page"))
