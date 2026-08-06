"""Trang quản lý navbar, mega menu sản phẩm và footer của storefront."""

from __future__ import annotations

import logging
import sys

from flask import jsonify, render_template, request

from app.middleware.auth_required import admin_required
from app.models.category_model import CategoryModel
from app.models.collection_model import CollectionModel
from app.models.navigation_model import NavigationModel
from app.services.audit_service import AuditService
from app.utils.supabase_client import get_supabase_admin

from ._blueprint import admin_bp

logger = logging.getLogger(__name__)


def _invalidate_navigation_cache() -> None:
    """Đẩy cấu hình mới ra storefront ngay sau khi lưu."""
    try:
        from app.context_processors import invalidate_shared_cache

        invalidate_shared_cache()
    except Exception as exc:
        logger.debug("[Admin Menus] Không xoá được shared cache: %s", exc)

    for module_name in ("index", "__main__"):
        module = sys.modules.get(module_name)
        invalidate = getattr(module, "invalidate_global_context_cache", None) if module else None
        if callable(invalidate):
            try:
                invalidate()
            except Exception as exc:
                logger.warning("[Admin Menus] Không xoá được cache %s: %s", module_name, exc)


@admin_bp.route("/menus", methods=["GET"])
@admin_required
def menus_page():
    try:
        config = NavigationModel.get_config(force_reload=True)
        categories = CategoryModel.get_all(admin_mode=True)
        collections = CollectionModel.get_all(admin_mode=True)
        try:
            product_response = (
                get_supabase_admin()
                .table("products")
                .select("id,name,slug,is_active")
                .is_("deleted_at", "null")
                .order("name")
                .limit(500)
                .execute()
            )
            products = product_response.data or []
        except Exception as product_exc:
            logger.warning("[Admin Menus] Không tải được danh sách sản phẩm: %s", product_exc)
            products = []
        return render_template(
            "admin/menus/index.html",
            menu_config=config,
            categories=categories,
            collections=collections,
            products=products,
        )
    except Exception as exc:
        logger.error("[Admin Menus] Không tải được trang: %s", exc, exc_info=True)
        return render_template(
            "admin/menus/index.html",
            menu_config=NavigationModel.normalize_config({}),
            categories=[],
            collections=[],
            products=[],
            load_error="Không thể tải cấu hình hiện tại. Trang đang dùng dữ liệu mặc định.",
        )


@admin_bp.route("/menus/update", methods=["POST"])
@admin_required
def update_menus():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({
            "success": False,
            "message": "Dữ liệu menu không đúng định dạng.",
        }), 400

    try:
        old_config = NavigationModel.get_config()
        success, normalized = NavigationModel.save_config(payload)

        if not success:
            return jsonify({
                "success": False,
                "message": "Không thể lưu cấu hình menu vào cơ sở dữ liệu.",
            }), 500

        _invalidate_navigation_cache()

        try:
            AuditService.log_action(
                action="UPDATE",
                table_name="store_settings",
                record_id="navigation",
                old_values=old_config,
                new_values=normalized,
            )
        except Exception as audit_exc:
            logger.warning("[Admin Menus] Không ghi được audit log: %s", audit_exc)

        return jsonify({
            "success": True,
            "message": "Đã cập nhật menu và kiểm tra lại liên kết sản phẩm/nhóm sản phẩm.",
            "navigation": normalized,
        })
    except Exception as exc:
        logger.error("[Admin Menus] Lưu cấu hình thất bại: %s", exc, exc_info=True)
        return jsonify({
            "success": False,
            "message": "Có lỗi hệ thống khi lưu menu. Vui lòng thử lại.",
        }), 500
