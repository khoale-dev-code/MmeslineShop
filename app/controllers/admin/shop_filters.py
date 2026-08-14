"""HTTP controller for Shop Filter Settings."""

from __future__ import annotations

import logging

from flask import jsonify, render_template, request

from app.middleware.auth_required import admin_required
from app.services.shop_filter_service import (
    ShopFilterService,
    ShopFilterValidationError,
)

from ._blueprint import admin_bp

logger = logging.getLogger(__name__)


def _service() -> ShopFilterService:
    return ShopFilterService(admin=True)


def _json_error(message: str, status: int):
    return jsonify({"success": False, "message": message}), status


@admin_bp.get("/settings/shop-filters")
@admin_required
def shop_filter_settings_page():
    config = _service().configuration(include_inactive=True)
    return render_template("admin/settings/shop_filters.html", filter_config=config)


@admin_bp.get("/settings/shop-filters/api/config")
@admin_required
def shop_filter_config_api():
    return jsonify({"success": True, **_service().configuration(include_inactive=True)})


@admin_bp.post("/settings/shop-filters/api/groups")
@admin_required
def shop_filter_save_group_api():
    try:
        group = _service().save_group(request.get_json(silent=True) or {})
        return jsonify({"success": True, "group": group})
    except ShopFilterValidationError as exc:
        return _json_error(str(exc), 400)
    except Exception as exc:
        logger.exception("shop filter group save failed")
        return _json_error("Không thể lưu bộ lọc. Hãy kiểm tra migration Supabase.", 500)


@admin_bp.post("/settings/shop-filters/api/options")
@admin_required
def shop_filter_save_option_api():
    try:
        option = _service().save_option(request.get_json(silent=True) or {})
        return jsonify({"success": True, "option": option})
    except ShopFilterValidationError as exc:
        return _json_error(str(exc), 400)
    except Exception:
        logger.exception("shop filter option save failed")
        return _json_error("Không thể lưu giá trị lọc. Hãy kiểm tra migration Supabase.", 500)


@admin_bp.patch("/settings/shop-filters/api/groups/<group_id>/active")
@admin_required
def shop_filter_group_active_api(group_id: str):
    try:
        active = bool((request.get_json(silent=True) or {}).get("is_active"))
        _service().set_group_active(group_id, active)
        return jsonify({"success": True, "is_active": active})
    except ShopFilterValidationError as exc:
        return _json_error(str(exc), 404)
    except Exception:
        logger.exception("shop filter group active failed")
        return _json_error("Không thể cập nhật trạng thái bộ lọc.", 500)


@admin_bp.patch("/settings/shop-filters/api/options/<option_id>/active")
@admin_required
def shop_filter_option_active_api(option_id: str):
    try:
        active = bool((request.get_json(silent=True) or {}).get("is_active"))
        _service().set_option_active(option_id, active)
        return jsonify({"success": True, "is_active": active})
    except Exception:
        logger.exception("shop filter option active failed")
        return _json_error("Không thể cập nhật trạng thái giá trị lọc.", 500)
