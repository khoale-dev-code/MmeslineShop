"""HTTP-only Admin endpoints for GUAMAISON Media Studio."""

from __future__ import annotations

import logging
import sys

from flask import jsonify, request

from app.models.product_model import ProductModel

from app.middleware.auth_required import admin_required, permission_required
from app.repositories.storefront_media_repository import StorefrontMediaRepositoryError
from app.services.storefront_media_service import (
    StorefrontMediaService,
    StorefrontMediaValidationError,
)
from ._blueprint import admin_bp

logger = logging.getLogger(__name__)


def _invalidate_storefront_cache() -> None:
    try:
        from app.models.setting_model import SettingModel
        SettingModel.invalidate_cache()
    except Exception:
        logger.debug("Media Studio could not invalidate SettingModel cache", exc_info=True)
    try:
        from app.context_processors import invalidate_shared_cache
        invalidate_shared_cache()
    except Exception:
        logger.debug("Media Studio could not invalidate shared cache", exc_info=True)
    for module_name in ("index", "__main__"):
        module = sys.modules.get(module_name)
        callback = getattr(module, "invalidate_global_context_cache", None) if module else None
        if callable(callback):
            try:
                callback()
            except Exception:
                logger.debug("Media Studio could not invalidate app cache", exc_info=True)


# GUAMAISON-home-editorial-v21-latest-products-catalog-api
@admin_bp.get("/settings/storefront-latest-products/catalog")
@admin_required
@permission_required("settings.manage")
def storefront_latest_products_catalog():
    keyword = str(request.args.get("q") or "").strip()[:100]
    raw_ids = str(request.args.get("ids") or "").strip()
    try:
        if raw_ids:
            product_ids = [item.strip() for item in raw_ids.split(",") if item.strip()][:12]
            products = [ProductModel.get_by_id(product_id) for product_id in product_ids]
        else:
            result = ProductModel.get_all(
                page=1,
                per_page=100,
                keyword=keyword or None,
                admin_mode=True,
            )
            products = result.get("items") or []
        items = []
        for product in products:
            if not isinstance(product, dict) or not product.get("id") or product.get("deleted_at"):
                continue
            active = str(product.get("is_active", "")).strip().lower() in {"true", "1", "yes", "on"}
            if not active:
                continue
            try:
                price_label = f"{float(product.get('price') or 0):,.0f}".replace(",", ".") + " ₫"
            except (TypeError, ValueError):
                price_label = ""
            items.append({
                "id": str(product.get("id")),
                "name": str(product.get("name") or "Sản phẩm"),
                "slug": str(product.get("slug") or ""),
                "sku": str(product.get("sku") or ""),
                "thumbnail_url": str(product.get("thumbnail_url") or product.get("image_url") or product.get("image") or ""),
                "price_label": price_label,
            })
        return jsonify({"ok": True, "items": items, "total": len(items)})
    except Exception:
        logger.exception("Latest-products catalog API failed")
        return jsonify({"ok": False, "message": "Không thể tải danh sách sản phẩm lúc này."}), 500


@admin_bp.post("/settings/storefront-media/upload")
@admin_required
@permission_required("settings.manage")
def storefront_media_upload():
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"ok": False, "message": "Chưa chọn tệp media."}), 400
    try:
        content = uploaded.read(StorefrontMediaService.MAX_VIDEO_BYTES + 1)
        result = StorefrontMediaService().upload(
            slot_key=request.form.get("slot_key", ""),
            filename=uploaded.filename,
            content_type=uploaded.content_type or "",
            content=content,
        )
        return jsonify(
            {
                "ok": True,
                "url": result.url,
                "path": result.storage_path,
                "media_type": result.media_type,
                "content_type": result.content_type,
                "size": result.size,
            }
        ), 201
    except StorefrontMediaValidationError as exc:
        logger.warning(
            "Media Studio rejected upload: code=%s slot=%s content_type=%s",
            exc.code,
            request.form.get("slot_key", ""),
            uploaded.content_type or "",
        )
        return jsonify(
            {
                "ok": False,
                "message": str(exc),
                "error_code": exc.code,
                "details": exc.details,
            }
        ), 422
    except StorefrontMediaRepositoryError:
        logger.exception("Media Studio upload failed")
        return jsonify({"ok": False, "message": "Không thể lưu tệp vào Supabase Storage."}), 502
    except Exception:
        logger.exception("Media Studio upload crashed")
        return jsonify({"ok": False, "message": "Không thể tải tệp lúc này."}), 500


@admin_bp.post("/settings/storefront-media/save")
@admin_required
@permission_required("settings.manage")
def storefront_media_save():
    data = request.get_json(silent=True) or {}
    changes = data.get("changes") if isinstance(data, dict) else None
    try:
        result = StorefrontMediaService().save(changes or {})
        _invalidate_storefront_cache()
        return jsonify(
            {
                "ok": True,
                "message": "Đã cập nhật giao diện cửa hàng.",
                "settings": result.settings,
                "changed_keys": result.changed_keys,
                "updated_at": result.updated_at,
            }
        )
    except StorefrontMediaValidationError as exc:
        return jsonify(
            {
                "ok": False,
                "message": str(exc),
                "error_code": exc.code,
                "details": exc.details,
            }
        ), 422
    except StorefrontMediaRepositoryError:
        logger.exception("Media Studio save failed")
        return jsonify({"ok": False, "message": "Không thể lưu cấu hình vào Supabase."}), 502
    except Exception:
        logger.exception("Media Studio save crashed")
        return jsonify({"ok": False, "message": "Không thể lưu cấu hình lúc này."}), 500
