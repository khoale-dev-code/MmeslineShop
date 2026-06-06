import logging
from typing import Any, Dict, List, Tuple

from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from pydantic import ValidationError

from app.schemas.favorite_schema import FavoriteToggleRequest
from app.services.favorite_service import FavoriteService
from app.models.user_model import UserModel

logger = logging.getLogger(__name__)

favorite_bp = Blueprint("favorite_bp", __name__)


def _safe_login_url() -> str:
    try:
        return url_for("auth.login")
    except Exception:
        return "/auth/login"


def _clean_name(value: Any) -> str:
    value = str(value or "").strip()

    if value.lower() in ("none", "null", "undefined", "nan"):
        return ""

    return value


def _get_current_user(user_id: str) -> Dict[str, Any]:
    try:
        user = UserModel.get_by_id(user_id) or {}
    except Exception:
        logger.warning("[FAVORITES] Không lấy được user.", exc_info=True)
        user = {}

    email = (user.get("email") or session.get("email") or "").strip().lower()

    full_name = (
        _clean_name(user.get("full_name"))
        or _clean_name(user.get("name"))
        or _clean_name(session.get("user_name"))
        or _clean_name(session.get("full_name"))
        or (email.split("@")[0] if email else "Khách hàng")
    )

    user["id"] = user.get("id") or user_id
    user["email"] = email
    user["full_name"] = full_name

    session["user_name"] = full_name
    session["full_name"] = full_name

    if email:
        session["email"] = email

    session.modified = True
    return user


def _normalize_wishlist_result(result: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    pagination = {
        "page": 1,
        "per_page": 24,
        "total": 0,
        "pages": 1,
        "has_next": False,
        "has_prev": False,
    }

    if isinstance(result, list):
        pagination["total"] = len(result)
        return result, pagination

    if isinstance(result, dict):
        items = result.get("items") or result.get("favorites") or result.get("data") or []

        if not isinstance(items, list):
            items = []

        pagination["page"] = int(result.get("page") or 1)
        pagination["per_page"] = int(result.get("per_page") or 24)
        pagination["total"] = int(result.get("total") or len(items))
        pagination["pages"] = int(result.get("pages") or 1)
        pagination["has_next"] = bool(result.get("has_next"))
        pagination["has_prev"] = bool(result.get("has_prev"))

        return items, pagination

    return [], pagination


@favorite_bp.route("/api/favorites/toggle", methods=["POST"])
def toggle_favorite():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "status": "error",
            "message": "Vui lòng đăng nhập"
        }), 401

    try:
        payload = request.get_json(silent=True) or {}
        req_data = FavoriteToggleRequest(**payload)

        result = FavoriteService.toggle_favorite(user_id, req_data.product_id)

        return jsonify(result), 200

    except ValidationError as exc:
        logger.warning("[FAVORITE VALIDATION_ERROR] %s", exc.errors())
        return jsonify({
            "status": "error",
            "message": "Dữ liệu đầu vào không hợp lệ"
        }), 400

    except ValueError as exc:
        return jsonify({
            "status": "error",
            "message": str(exc)
        }), 400

    except Exception as exc:
        logger.exception("[FAVORITE CONTROLLER_ERROR] %s", exc)
        return jsonify({
            "status": "error",
            "message": "Lỗi máy chủ nội bộ"
        }), 500


@favorite_bp.route("/profile/favorites", methods=["GET"])
def wishlist_page():
    user_id = session.get("user_id")

    if not user_id:
        flash("Vui lòng đăng nhập để xem danh sách yêu thích.", "warning")
        return redirect(_safe_login_url())

    try:
        page = max(1, int(request.args.get("page", 1)))
        current_user = _get_current_user(user_id)

        wishlist_result = FavoriteService.get_user_wishlist(user_id, page=page)
        favorites, pagination = _normalize_wishlist_result(wishlist_result)

        return render_template(
            "profile/favorites.html",
            favorites=favorites,
            pagination=pagination,
            current_user=current_user,
            user=current_user,
        )

    except ValueError:
        return render_template(
            "errors/400.html",
            message="Tham số trang không hợp lệ"
        ), 400

    except Exception as exc:
        logger.exception("[FAVORITES PAGE_ERROR] Failed to load wishlist page: %s", exc)
        return render_template(
            "errors/500.html",
            error=str(exc)
        ), 500