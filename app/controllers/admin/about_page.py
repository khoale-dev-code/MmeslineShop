"""HTTP controller for the structured About-page editor."""

from __future__ import annotations

import logging

from flask import jsonify, render_template, request, session

from app.middleware.auth_required import admin_required, permission_required
from app.services.about_page_service import (
    AboutPageService,
    AboutPageValidationError,
    ContentPageConflictError,
    ContentPageRepositoryError,
    ContentPageSchemaMissingError,
)
from app.services.audit_service import AuditService

from ._blueprint import admin_bp

logger = logging.getLogger(__name__)


def _current_user_id() -> str | None:
    value = session.get("user_id")
    return str(value) if value else None


def _json_body() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise AboutPageValidationError("Dữ liệu gửi lên không hợp lệ.")
    return payload


def _version(payload: dict) -> int:
    try:
        value = int(payload.get("version") or 0)
    except (TypeError, ValueError) as exc:
        raise AboutPageValidationError("Phiên bản bản nháp không hợp lệ.") from exc
    if value < 1:
        raise AboutPageValidationError("Hãy chạy migration và tải lại trang trước khi chỉnh sửa.")
    return value


def _error_response(exc: Exception):
    if isinstance(exc, AboutPageValidationError):
        return jsonify(success=False, message=str(exc)), 400
    if isinstance(exc, ContentPageConflictError):
        return jsonify(success=False, conflict=True, message=str(exc)), 409
    if isinstance(exc, ContentPageSchemaMissingError):
        return jsonify(success=False, schema_ready=False, message=str(exc)), 503
    logger.error("[About admin] %s", exc, exc_info=True)
    return jsonify(success=False, message="Không thể xử lý nội dung About lúc này."), 500


def _audit(action: str, record_id: str, new_values: dict | None = None) -> None:
    try:
        AuditService.log_action(
            action=action,
            table_name="content_pages",
            record_id=record_id,
            new_values=new_values or {},
        )
    except Exception as exc:
        logger.warning("[About admin] Không ghi được audit log: %s", exc)


@admin_bp.route("/content/about", methods=["GET"])
@admin_required
@permission_required("settings.view")
def about_page_editor():
    state = AboutPageService.get_editor_state(_current_user_id())
    return render_template("admin/about/index.html", editor_state=state)


@admin_bp.route("/content/about/preview", methods=["GET"])
@admin_required
@permission_required("settings.view")
def about_page_preview():
    state = AboutPageService.get_editor_state(_current_user_id())
    return render_template(
        "partials/about.html",
        about=state["content"],
        about_preview=True,
    )


@admin_bp.route("/content/about/draft", methods=["POST"])
@admin_required
@permission_required("settings.manage")
def save_about_page_draft():
    try:
        payload = _json_body()
        result = AboutPageService.save_draft(
            payload.get("content"),
            _version(payload),
            _current_user_id(),
        )
        _audit("UPDATE_DRAFT", AboutPageService.SLUG, {"draft_version": result["draft_version"]})
        return jsonify(success=True, message="Đã lưu bản nháp About.", **result)
    except (AboutPageValidationError, ContentPageConflictError, ContentPageSchemaMissingError, ContentPageRepositoryError) as exc:
        return _error_response(exc)


@admin_bp.route("/content/about/publish", methods=["POST"])
@admin_required
@permission_required("settings.manage")
def publish_about_page():
    try:
        payload = _json_body()
        result = AboutPageService.publish(
            _version(payload),
            _current_user_id(),
        )
        _audit("PUBLISH", AboutPageService.SLUG, {"published_version": result["published_version"]})
        return jsonify(success=True, message="Trang About đã được xuất bản.", **result)
    except (AboutPageValidationError, ContentPageConflictError, ContentPageSchemaMissingError, ContentPageRepositoryError) as exc:
        return _error_response(exc)


@admin_bp.route("/content/about/reset", methods=["POST"])
@admin_required
@permission_required("settings.manage")
def reset_about_page_draft():
    try:
        payload = _json_body()
        result = AboutPageService.reset_draft(
            _version(payload),
            _current_user_id(),
        )
        _audit("RESET_DRAFT", AboutPageService.SLUG, {"draft_version": result["draft_version"]})
        return jsonify(success=True, message="Đã khôi phục nội dung mặc định vào bản nháp.", **result)
    except (AboutPageValidationError, ContentPageConflictError, ContentPageSchemaMissingError, ContentPageRepositoryError) as exc:
        return _error_response(exc)


@admin_bp.route("/content/about/upload", methods=["POST"])
@admin_required
@permission_required("settings.manage")
def upload_about_page_image():
    try:
        uploaded = request.files.get("image")
        if not uploaded or not uploaded.filename:
            raise AboutPageValidationError("Vui lòng chọn một tệp ảnh.")
        url = AboutPageService.upload_image(
            uploaded.read(),
            uploaded.filename,
            uploaded.content_type,
        )
        return jsonify(success=True, message="Đã tải ảnh lên.", url=url)
    except (AboutPageValidationError, ContentPageSchemaMissingError, ContentPageRepositoryError) as exc:
        return _error_response(exc)
