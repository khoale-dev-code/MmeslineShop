"""
app/controllers/ai_controller.py
================================
MMESTLINE – Styling Lab / Outfit Recommendation API

Endpoints:
- GET  /styling-lab
- GET  /api/recommend_outfit/health
- POST /api/recommend_outfit

Ghi chú:
- ai_bp chỉ nên register khi ENABLE_AI=true.
- Chatbot /api/bot nằm ở chat_controller.py, không nằm trong file này.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import requests
from flask import Blueprint, current_app, jsonify, render_template, request

from app import csrf
from app.models.product_model import ProductModel

ai_bp = Blueprint("ai", __name__)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# CONFIG / STYLE METADATA
# ═══════════════════════════════════════════════════════════════

STYLE_PROFILES: dict[str, dict[str, str]] = {
    "streetwear": {
        "label": "Streetwear Culture",
        "desc": "Năng động · Đô thị · Cá tính",
        "color": "#1b4922",
        "accent": "#c99e14",
        "icon": "🏙️",
    },
    "minimalist": {
        "label": "Clean Minimalist",
        "desc": "Tinh tế · Tối giản · Vượt thời gian",
        "color": "#1b4922",
        "accent": "#c99e14",
        "icon": "◻",
    },
    "techwear": {
        "label": "Technical Gear",
        "desc": "Chức năng · Hiện đại · Tương lai",
        "color": "#1b4922",
        "accent": "#c99e14",
        "icon": "⚙",
    },
    "smart_casual": {
        "label": "Smart Casual",
        "desc": "Lịch sự · Thoải mái · Linh hoạt",
        "color": "#1b4922",
        "accent": "#c99e14",
        "icon": "✦",
    },
}

_VIBE_SLUGS: dict[str, list[str]] = {
    "streetwear": ["streetwear", "urban", "hip-hop", "ao-thun", "quan-jean", "cargo"],
    "minimalist": ["minimalist", "basics", "essential", "ao-so-mi", "quan-tay"],
    "techwear": ["techwear", "technical", "outdoor", "jacket", "cargo"],
    "smart_casual": ["smart-casual", "office", "formal", "ao-so-mi", "blazer", "quan-tay"],
}

_VIBE_ORDER = ["streetwear", "minimalist", "techwear", "smart_casual"]

_SHAPE_AFFINITY: dict[str, list[float]] = {
    "inverted_triangle": [0.85, 0.75, 0.90, 0.70],
    "rectangle": [0.90, 0.85, 0.85, 0.80],
    "triangle": [0.75, 0.90, 0.70, 0.85],
    "hourglass": [0.80, 0.95, 0.75, 0.90],
}

_PLACEHOLDER_IMG = "https://placehold.co/600x800/f7f9f2/1b4922?text=MMESTLINE"

_SUPABASE_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_CACHE_TTL = 60


# ═══════════════════════════════════════════════════════════════
# FALLBACK MOCK
# ═══════════════════════════════════════════════════════════════

_MOCK: dict[str, list[dict[str, Any]]] = {
    "streetwear": [
        {
            "id": "MOCK-SW-1",
            "name": "Cargo Ripstop Pants",
            "category": "Bottoms",
            "price": 1490000,
            "match_score": 97,
            "reason": "Silhouette rộng cân bằng tỉ lệ hình thể.",
            "image": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=600&q=80",
            "badge": "Best Match",
            "slug": "",
        },
        {
            "id": "MOCK-SW-2",
            "name": "Oversized Tee Washed",
            "category": "Tops",
            "price": 690000,
            "match_score": 93,
            "reason": "Fit oversize linh hoạt, chất washed vintage.",
            "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&q=80",
            "badge": "Trending",
            "slug": "",
        },
        {
            "id": "MOCK-SW-3",
            "name": "Crossbody Nylon Bag",
            "category": "Accessories",
            "price": 950000,
            "match_score": 88,
            "reason": "Utility tạo điểm nhấn, chất liệu bền.",
            "image": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=600&q=80",
            "badge": None,
            "slug": "",
        },
        {
            "id": "MOCK-SW-4",
            "name": "Cap Embroidery Logo",
            "category": "Headwear",
            "price": 450000,
            "match_score": 82,
            "reason": "Hoàn thiện look, logo subtle.",
            "image": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=600&q=80",
            "badge": None,
            "slug": "",
        },
    ],
    "minimalist": [
        {
            "id": "MOCK-MN-1",
            "name": "Slim Tapered Trousers",
            "category": "Bottoms",
            "price": 1290000,
            "match_score": 96,
            "reason": "Đường cắt tapered kéo dài đôi chân.",
            "image": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=600&q=80",
            "badge": "Best Match",
            "slug": "",
        },
        {
            "id": "MOCK-MN-2",
            "name": "Mock-Neck Ribbed Top",
            "category": "Tops",
            "price": 790000,
            "match_score": 91,
            "reason": "Cổ mock-neck tôn đường nét cơ thể.",
            "image": "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=600&q=80",
            "badge": "New",
            "slug": "",
        },
        {
            "id": "MOCK-MN-3",
            "name": "Tote Bag Canvas",
            "category": "Accessories",
            "price": 650000,
            "match_score": 85,
            "reason": "Đối trọng visual với outfit đơn giản.",
            "image": "https://images.unsplash.com/photo-1612902456551-b373f88abc67?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1612902456551-b373f88abc67?w=600&q=80",
            "badge": None,
            "slug": "",
        },
        {
            "id": "MOCK-MN-4",
            "name": "Leather Belt Minimal",
            "category": "Accessories",
            "price": 390000,
            "match_score": 79,
            "reason": "Định nghĩa eo, tạo tỉ lệ 2/3 chuẩn.",
            "image": "https://images.unsplash.com/photo-1624222247344-550fb60fe8ff?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1624222247344-550fb60fe8ff?w=600&q=80",
            "badge": None,
            "slug": "",
        },
    ],
    "techwear": [
        {
            "id": "MOCK-TW-1",
            "name": "Shell Jogger Pants",
            "category": "Bottoms",
            "price": 1890000,
            "match_score": 98,
            "reason": "Chất liệu kỹ thuật, nhiều túi zipper.",
            "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80",
            "badge": "Best Match",
            "slug": "",
        },
        {
            "id": "MOCK-TW-2",
            "name": "Zip Jacket Technical",
            "category": "Outerwear",
            "price": 2490000,
            "match_score": 94,
            "reason": "Panel 3D, hệ thống zip điều chỉnh thông gió.",
            "image": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600&q=80",
            "badge": "Premium",
            "slug": "",
        },
        {
            "id": "MOCK-TW-3",
            "name": "Modular Chest Rig",
            "category": "Accessories",
            "price": 1150000,
            "match_score": 89,
            "reason": "Utility layering, tăng chức năng lưu trữ.",
            "image": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&q=80",
            "badge": "Utility",
            "slug": "",
        },
        {
            "id": "MOCK-TW-4",
            "name": "Tactical Boots Low",
            "category": "Footwear",
            "price": 2100000,
            "match_score": 87,
            "reason": "Đế chunky hoàn thiện silhouette techwear.",
            "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80",
            "badge": None,
            "slug": "",
        },
    ],
    "smart_casual": [
        {
            "id": "MOCK-SC-1",
            "name": "Chino Slim Stretch",
            "category": "Bottoms",
            "price": 1190000,
            "match_score": 95,
            "reason": "Co giãn 4 chiều, màu earth tone đa dụng.",
            "image": "https://images.unsplash.com/photo-1598971861713-54ad16a7e72e?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1598971861713-54ad16a7e72e?w=600&q=80",
            "badge": "Best Match",
            "slug": "",
        },
        {
            "id": "MOCK-SC-2",
            "name": "Oxford Button-Down",
            "category": "Tops",
            "price": 890000,
            "match_score": 90,
            "reason": "Vải oxford texture, tucked/untucked linh hoạt.",
            "image": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=600&q=80",
            "badge": "Versatile",
            "slug": "",
        },
        {
            "id": "MOCK-SC-3",
            "name": "Leather Loafers Suede",
            "category": "Footwear",
            "price": 1750000,
            "match_score": 86,
            "reason": "Suede sang trọng, mũi vuông hiện đại.",
            "image": "https://images.unsplash.com/photo-1614252369475-531eba835eb1?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1614252369475-531eba835eb1?w=600&q=80",
            "badge": None,
            "slug": "",
        },
        {
            "id": "MOCK-SC-4",
            "name": "Watch Minimalist 36mm",
            "category": "Accessories",
            "price": 2900000,
            "match_score": 83,
            "reason": "Mặt số elegant, dây da tonal cohesive.",
            "image": "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?w=600&q=80",
            "thumbnail_url": "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?w=600&q=80",
            "badge": "Luxury",
            "slug": "",
        },
    ],
}


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except Exception:
        return default


def _normalize_vibe(value: Any) -> str:
    vibe = str(value or "streetwear").strip().lower()
    return vibe if vibe in STYLE_PROFILES else "streetwear"


def _hf_headers() -> dict[str, str]:
    token = current_app.config.get("HF_TOKEN", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _strip_data_uri(image_b64: str) -> str:
    text = str(image_b64 or "").strip()

    if "," in text and text.lower().startswith("data:"):
        return text.split(",", 1)[1].strip()

    return text


def _analyze_image(image_b64: str) -> dict[str, Any] | None:
    """
    Gửi base64 ảnh đến AI engine /analyze-style.
    Nếu engine không cấu hình hoặc timeout, trả None để fallback.
    """
    engine_url = current_app.config.get("AI_ENGINE_URL", "")

    if not engine_url:
        logger.info("[MMESTLINE AI] AI_ENGINE_URL chưa cấu hình, bỏ qua phân tích ảnh.")
        return None

    clean_b64 = _strip_data_uri(image_b64)

    if not clean_b64:
        return None

    try:
        resp = requests.post(
            f"{engine_url.rstrip('/')}/analyze-style",
            json={"image": clean_b64},
            headers=_hf_headers(),
            timeout=12,
        )

        if resp.status_code != 200:
            logger.warning("[MMESTLINE AI] /analyze-style HTTP %s: %s", resp.status_code, resp.text[:300])
            return None

        result = resp.json() or {}

        logger.info(
            "[MMESTLINE AI] analyze-style OK shape=%s vibe=%s conf=%s",
            (result.get("body") or {}).get("shape"),
            result.get("suggested_vibe"),
            result.get("confidence"),
        )

        return result

    except requests.exceptions.Timeout:
        logger.warning("[MMESTLINE AI] /analyze-style timeout.")
        return None

    except Exception as e:
        logger.error("[MMESTLINE AI] Lỗi analyze-style: %s", e, exc_info=True)
        return None


def _body_score_bonus(body: dict[str, Any] | None, vibe: str) -> int:
    if not body:
        return 0

    shape = str(body.get("shape") or "rectangle").strip().lower()
    affinity = _SHAPE_AFFINITY.get(shape, [0.85] * 4)

    try:
        idx = _VIBE_ORDER.index(vibe)
        return round((affinity[idx] - 0.80) * 20)
    except Exception:
        return 0


def _get_product_image(product: dict[str, Any]) -> str:
    """
    Lấy ảnh sản phẩm an toàn từ nhiều schema:
    - thumbnail_url
    - image
    - product_images[].url
    - images[].url
    """
    thumb = product.get("thumbnail_url") or product.get("image")
    if thumb:
        return str(thumb)

    images = product.get("images") or product.get("product_images") or []

    if isinstance(images, list):
        primary = next(
            (
                img
                for img in images
                if isinstance(img, dict) and img.get("is_primary") and (img.get("url") or img.get("image_url"))
            ),
            None,
        )

        first = next(
            (
                img
                for img in images
                if isinstance(img, dict) and (img.get("url") or img.get("image_url"))
            ),
            None,
        )

        selected = primary or first

        if isinstance(selected, dict):
            return selected.get("url") or selected.get("image_url") or _PLACEHOLDER_IMG

    return _PLACEHOLDER_IMG


def _get_category_name(product: dict[str, Any]) -> str:
    """
    Hỗ trợ nhiều dạng:
    - product["categories"] = {"name": "..."}
    - product["category"] = {"name": "..."} hoặc string
    - product["category_name"]
    - product["category_list"] = [{"name": "..."}]
    - product["product_categories"] = [{"categories": {"name": "..."}}]
    """
    if product.get("category_name"):
        return str(product["category_name"])

    category = product.get("categories") or product.get("category")

    if isinstance(category, dict):
        return category.get("name") or category.get("label") or "MMESTLINE"

    if isinstance(category, str):
        return category

    category_list = product.get("category_list") or []
    if isinstance(category_list, list) and category_list:
        first = category_list[0]
        if isinstance(first, dict):
            return first.get("name") or "MMESTLINE"

    product_categories = product.get("product_categories") or []
    if isinstance(product_categories, list) and product_categories:
        first_row = product_categories[0]
        if isinstance(first_row, dict):
            nested = first_row.get("categories")
            if isinstance(nested, dict):
                return nested.get("name") or "MMESTLINE"

    return "MMESTLINE"


def _short_reason(product: dict[str, Any], vibe: str) -> str:
    description = (
        product.get("short_description")
        or product.get("description")
        or product.get("description_html")
        or ""
    )

    description = str(description).replace("\n", " ").strip()

    if description:
        return description[:120]

    fallback = {
        "streetwear": "Phù hợp với outfit năng động, cá tính và dễ phối hằng ngày.",
        "minimalist": "Thiết kế tối giản, dễ phối và giữ được cảm giác tinh tế.",
        "techwear": "Form hiện đại, hợp phong cách tiện dụng và nhiều lớp.",
        "smart_casual": "Cân bằng giữa lịch sự và thoải mái cho nhiều hoàn cảnh.",
    }

    return fallback.get(vibe, "Phù hợp với nhiều phong cách khác nhau.")


def _normalise_product(
    product: dict[str, Any],
    rank: int,
    vibe: str,
    body: dict[str, Any] | None,
) -> dict[str, Any]:
    base = max(70, 98 - rank * 5)
    score = base + random.randint(-2, 2) + _body_score_bonus(body, vibe)
    score = max(70, min(99, score))

    price = _safe_int(product.get("price"), 0)
    image_url = _get_product_image(product)
    category_name = _get_category_name(product)

    badge_map = {
        0: "Best Match",
        1: "Top Pick",
        2: "Stylist Choice",
    }

    return {
        "id": str(product.get("id") or ""),
        "name": str(product.get("name") or "Sản phẩm MMESTLINE"),
        "category": category_name,
        "price": price,
        "match_score": score,
        "reason": _short_reason(product, vibe),
        "image": image_url,
        "thumbnail_url": image_url,
        "badge": product.get("badge") or badge_map.get(rank),
        "slug": str(product.get("slug") or ""),
    }


def _query_products_by_slug(slug: str) -> list[dict[str, Any]]:
    """
    Tương thích nhiều phiên bản ProductModel.get_all:
    - category_slug=...
    - category=...
    - không hỗ trợ lọc thì fallback get_all rồi lọc ngoài.
    """
    try:
        result = ProductModel.get_all(
            page=1,
            per_page=20,
            category_slug=slug,
        )
        return result.get("items", []) if isinstance(result, dict) else []
    except TypeError:
        pass
    except Exception as e:
        logger.warning("[MMESTLINE AI] get_all category_slug=%s lỗi: %s", slug, e)

    try:
        result = ProductModel.get_all(
            page=1,
            per_page=20,
            category=slug,
        )
        return result.get("items", []) if isinstance(result, dict) else []
    except TypeError:
        pass
    except Exception as e:
        logger.warning("[MMESTLINE AI] get_all category=%s lỗi: %s", slug, e)

    try:
        result = ProductModel.get_all(
            page=1,
            per_page=60,
        )
        items = result.get("items", []) if isinstance(result, dict) else []

        filtered = []

        for item in items:
            if not isinstance(item, dict):
                continue

            slugs = []

            category = item.get("categories") or item.get("category")
            if isinstance(category, dict):
                slugs.append(str(category.get("slug") or "").lower())
            elif isinstance(category, str):
                slugs.append(category.lower())

            for cat in item.get("category_list") or []:
                if isinstance(cat, dict):
                    slugs.append(str(cat.get("slug") or "").lower())

            for row in item.get("product_categories") or []:
                if isinstance(row, dict):
                    nested = row.get("categories")
                    if isinstance(nested, dict):
                        slugs.append(str(nested.get("slug") or "").lower())

            if slug.lower() in slugs:
                filtered.append(item)

        return filtered

    except Exception as e:
        logger.error("[MMESTLINE AI] fallback get_all lỗi: %s", e, exc_info=True)
        return []


def _fetch_supabase(vibe: str) -> list[dict[str, Any]]:
    now = time.monotonic()
    cached = _SUPABASE_CACHE.get(vibe)

    if cached and (now - cached[0]) < _CACHE_TTL:
        return cached[1]

    collected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for slug in _VIBE_SLUGS.get(vibe, [vibe]):
        items = _query_products_by_slug(slug)

        for item in items:
            if not isinstance(item, dict):
                continue

            product_id = str(item.get("id") or "")
            if product_id and product_id in seen_ids:
                continue

            if product_id:
                seen_ids.add(product_id)

            collected.append(item)

        logger.info("[MMESTLINE AI] vibe=%s slug=%s -> %d sản phẩm", vibe, slug, len(items))

        if len(collected) >= 8:
            break

    _SUPABASE_CACHE[vibe] = (now, collected)
    return collected


def _build_recommendations(
    vibe: str,
    body: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], str]:
    real_products = _fetch_supabase(vibe)

    if real_products:
        random.shuffle(real_products)

        cards = [
            _normalise_product(product, index, vibe, body)
            for index, product in enumerate(real_products[:4])
        ]

        cards.sort(key=lambda item: item["match_score"], reverse=True)

        if cards:
            cards[0]["badge"] = "Best Match"

        return cards, "supabase"

    mock = [dict(item) for item in _MOCK.get(vibe, _MOCK["streetwear"])]

    if len(mock) > 1:
        head = mock[:1]
        tail = mock[1:]
        random.shuffle(tail)
        mock = head + tail

    bonus = _body_score_bonus(body, vibe)

    for item in mock:
        item["match_score"] = max(70, min(99, _safe_int(item.get("match_score"), 80) + bonus))
        item["thumbnail_url"] = item.get("thumbnail_url") or item.get("image") or _PLACEHOLDER_IMG

    return mock[:4], "mock"


def _weighted_overall_score(cards: list[dict[str, Any]]) -> int:
    if not cards:
        return 0

    scores = [_safe_int(card.get("match_score"), 0) for card in cards]

    if len(scores) == 1:
        return scores[0]

    second = scores[1] if len(scores) > 1 else scores[0]
    rest = scores[2:] if len(scores) > 2 else [second]
    rest_avg = sum(rest) / max(len(rest), 1)

    return round(0.50 * scores[0] + 0.30 * second + 0.20 * rest_avg)


def _response_error(message: str, status_code: int = 400):
    return jsonify({
        "status": "error",
        "message": message,
        "data": [],
    }), status_code


# ═══════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════

@ai_bp.route("/styling-lab", methods=["GET"])
def styling_lab_page():
    return render_template("features/styling_lab.html")


@ai_bp.route("/api/recommend_outfit/health", methods=["GET"])
def recommend_outfit_health():
    return jsonify({
        "status": "online",
        "service": "MMESTLINE Styling Lab",
        "endpoint": "/api/recommend_outfit",
        "vibes": list(STYLE_PROFILES.keys()),
        "ai_engine_configured": bool(current_app.config.get("AI_ENGINE_URL")),
    })


@ai_bp.route("/api/recommend_outfit/cache/clear", methods=["POST"])
@csrf.exempt
def clear_recommendation_cache():
    _SUPABASE_CACHE.clear()

    return jsonify({
        "status": "success",
        "message": "Recommendation cache cleared.",
    })


@ai_bp.route("/api/recommend_outfit", methods=["POST"])
@csrf.exempt
def recommend_outfit():
    try:
        payload = request.get_json(silent=True) or {}

        vibe = _normalize_vibe(payload.get("vibe"))
        user_vibe = vibe

        image_b64 = payload.get("image_b64") or payload.get("image") or payload.get("photo")
        product_id = payload.get("product_id")

        body_data: dict[str, Any] | None = None
        suggested_vibe: str | None = None
        image_analyzed = False
        auto_vibe = False

        if image_b64:
            ai_result = _analyze_image(str(image_b64))

            if ai_result and ai_result.get("status") != "error":
                body_data = ai_result.get("body") if isinstance(ai_result.get("body"), dict) else None
                suggested_vibe = ai_result.get("suggested_vibe")
                confidence = _safe_float(ai_result.get("confidence"), 0)

                image_analyzed = True

                if suggested_vibe in STYLE_PROFILES and confidence >= 0.75:
                    vibe = suggested_vibe
                    auto_vibe = True

        recommendations, source = _build_recommendations(vibe, body_data)

        return jsonify({
            "status": "success",
            "vibe": vibe,
            "requested_vibe": user_vibe,
            "source": source,
            "product_id": product_id,
            "image_analyzed": image_analyzed,
            "body_data": body_data,
            "suggested_vibe": suggested_vibe,
            "auto_vibe": auto_vibe,
            "style_profile": STYLE_PROFILES[vibe],
            "total_look_price": sum(_safe_int(item.get("price"), 0) for item in recommendations),
            "overall_match": _weighted_overall_score(recommendations),
            "data": recommendations,
        }), 200

    except Exception as e:
        logger.error("[MMESTLINE AI] recommend_outfit lỗi: %s", e, exc_info=True)

        return _response_error(
            "Không thể xử lý yêu cầu. Vui lòng thử lại sau.",
            500,
        )