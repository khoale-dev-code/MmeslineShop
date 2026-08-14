"""HTTP controller for GUAMAISON Analytics Intelligence v19.

Business calculations live in services and Supabase access lives in the
repository. POS routes remain in ``pos_controller.py``.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from flask import flash, jsonify, render_template, request, send_file

from app.middleware.auth_required import admin_required, permission_required
from app.models.report_models import ANALYTICS_VERSION, ReportFilters
from app.repositories.report_repository import ReportRepository
from app.services.report_analytics_service import ReportAnalyticsService
from app.services.report_export_service import ReportExportService

from ._blueprint import admin_bp


logger = logging.getLogger(__name__)
ALLOWED_CHANNELS = {"web", "pos", "shopee", "lazada", "tiktok_shop"}
MAX_REPORT_DAYS = 366


def _parse_date(value: Any, fallback: date) -> date:
    try:
        return datetime.strptime(str(value or "")[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return fallback


def _truthy(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_filters(source: dict[str, Any] | None = None) -> ReportFilters:
    today = date.today()
    source = source or {}
    end_date = min(_parse_date(source.get("end_date"), today), today)
    start_date = _parse_date(source.get("start_date"), end_date - timedelta(days=29))
    if start_date > end_date:
        start_date = end_date
    if (end_date - start_date).days + 1 > MAX_REPORT_DAYS:
        start_date = end_date - timedelta(days=MAX_REPORT_DAYS - 1)

    raw_channels = source.get("channels") or source.get("channel") or []
    if isinstance(raw_channels, str):
        raw_channels = [item.strip() for item in raw_channels.split(",")]
    channels = tuple(
        dict.fromkeys(
            str(item).strip().lower()
            for item in raw_channels
            if str(item).strip().lower() in ALLOWED_CHANNELS
        )
    )
    return ReportFilters(
        start_date=start_date,
        end_date=end_date,
        channels=channels,
        compare_previous=_truthy(source.get("compare_previous"), True),
    )


def _filters_from_query() -> ReportFilters:
    compare_values = request.args.getlist("compare_previous")
    return _parse_filters({
        "start_date": request.args.get("start_date"),
        "end_date": request.args.get("end_date"),
        "channels": request.args.getlist("channel"),
        "compare_previous": compare_values[-1] if compare_values else "0",
    })


def _build_report(filters: ReportFilters) -> dict[str, Any]:
    repository = ReportRepository()
    return ReportAnalyticsService(repository).build(filters)


def _empty_report(filters: ReportFilters, message: str) -> dict[str, Any]:
    return {
        "version": ANALYTICS_VERSION,
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "filters": filters.as_dict(),
            "tracking_is_realtime": False,
        },
        "kpis": {},
        "trend": {"period": "day", "points": []},
        "forecast": {"status": "insufficient", "points": [], "message": message},
        "channels": [],
        "funnel": [],
        "products": [],
        "marketplaces": [
            {"provider": key, "label": label, "status": "not_connected", "connected": False}
            for key, label in (
                ("shopee", "Shopee"),
                ("lazada", "Lazada"),
                ("tiktok_shop", "TikTok Shop"),
            )
        ],
        "data_quality": {"score": 0, "label": "Không tải được", "issues": [message]},
        "summary": {"bestsellers": 0, "accelerating": 0, "potential": 0, "stock_risk": 0, "forecast_ready": 0},
    }


@admin_bp.route("/reports", methods=["GET"])
@admin_required
@permission_required("reports.view")
def reports():
    filters = _filters_from_query()
    try:
        report = _build_report(filters)
    except Exception as exc:
        logger.exception("[analytics_controller] Cannot build report: %s", exc)
        flash("Không thể tải đầy đủ báo cáo. Hãy kiểm tra Supabase và thử lại.", "warning")
        report = _empty_report(filters, "Không kết nối được nguồn dữ liệu báo cáo.")
    return render_template(
        "admin/reports/index.html",
        report=report,
        filters=filters,
        export_sheets=ReportExportService.SHEETS,
        export_product_columns=ReportExportService.PRODUCT_COLUMNS,
        default_product_columns=ReportExportService.DEFAULT_PRODUCT_COLUMNS,
    )


@admin_bp.route("/reports/data", methods=["GET"])
@admin_required
@permission_required("reports.view")
def reports_data():
    try:
        report = _build_report(_filters_from_query())
        return jsonify({"success": True, "report": report})
    except Exception as exc:
        logger.exception("[analytics_controller] Data endpoint failed: %s", exc)
        return jsonify({"success": False, "message": "Không thể tải dữ liệu báo cáo."}), 503


def _export_request() -> tuple[ReportFilters, dict[str, Any]]:
    payload = request.get_json(silent=True) or {}
    filters = _parse_filters(payload.get("filters") or {})
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    return filters, config


@admin_bp.route("/reports/export/preview", methods=["POST"])
@admin_required
@permission_required("reports.view")
def preview_report_export():
    try:
        filters, config = _export_request()
        report = _build_report(filters)
        selection = ReportExportService.normalize_selection(config)
        preview = ReportExportService.preview(report, selection)
        return jsonify({"success": True, "preview": preview})
    except Exception as exc:
        logger.exception("[analytics_controller] Export preview failed: %s", exc)
        return jsonify({"success": False, "message": "Không thể tạo bản xem trước Excel."}), 503


@admin_bp.route("/reports/export", methods=["POST"])
@admin_required
@permission_required("reports.view")
def export_report():
    try:
        filters, config = _export_request()
        report = _build_report(filters)
        exporter = ReportExportService()
        selection = exporter.normalize_selection(config)
        workbook = exporter.build(report, selection)
        filename = f"GUAMAISON_Analytics_{filters.start_date:%Y%m%d}_{filters.end_date:%Y%m%d}.xlsx"
        return send_file(
            workbook,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            max_age=0,
        )
    except Exception as exc:
        logger.exception("[analytics_controller] Excel export failed: %s", exc)
        return jsonify({"success": False, "message": "Xuất Excel thất bại. Vui lòng thử lại."}), 503
