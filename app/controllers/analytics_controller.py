"""
app/controllers/analytics_controller.py
======================================
Event Tracking System cho storefront MMESTLINE.

Nguyên tắc:
- Client chỉ được gửi: view, cart, wishlist.
- Không cho client gửi sold để tránh giả doanh thu.
- sold chỉ ghi từ backend sau khi đơn hàng được xác nhận COD/VNPay.
- Dùng Supabase Admin client để tránh RLS chặn RPC.
"""

import logging
import re
import time
from uuid import UUID

from flask import Blueprint, request, jsonify, session

from app import csrf
from app.utils.supabase_client import get_supabase_admin

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")
logger = logging.getLogger(__name__)


# Client-side events được phép nhận từ UI
VALID_CLIENT_EVENTS = {"view", "cart", "wishlist"}

VALID_CHANNELS = {
    "web",
    "pos",
    "tiktok",
    "shopee",
    "facebook",
    "instagram",
}

MAX_QTY = 50
MAX_REVENUE = 1_000_000_000

# Anti-spam memory đơn giản cho local/server process.
# Không thay thế rate-limit production, nhưng đủ giảm duplicate view do reload/script.
_EVENT_CACHE = {}
EVENT_TTL_SECONDS = 20


def _is_valid_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except Exception:
        return False


def _clean_string(value, default: str = "") -> str:
    value = str(value or default).strip()
    value = re.sub(r"\s+", " ", value)
    return value[:80]


def _clean_channel(value) -> str:
    channel = _clean_string(value, "web").lower()
    return channel if channel in VALID_CHANNELS else "web"


def _clean_source(value) -> str:
    source = _clean_string(value, "organic").lower()
    source = re.sub(r"[^a-z0-9_\-./:]", "", source)
    return source[:60] or "organic"


def _to_int(value, default: int = 1) -> int:
    try:
        value = int(value)
    except (ValueError, TypeError):
        value = default

    if value <= 0:
        value = default

    return min(value, MAX_QTY)


def _to_float(value, default: float = 0.0) -> float:
    try:
        value = float(value)
    except (ValueError, TypeError):
        value = default

    if value < 0:
        value = 0.0

    return min(value, MAX_REVENUE)


def _client_key() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.remote_addr
    return ip or "unknown"


def _is_duplicate_event(product_id: str, event_type: str, channel: str, source: str) -> bool:
    """
    Chặn duplicate ngắn hạn cho event view/wishlist/cart từ cùng client.
    """
    now = time.time()
    client = _client_key()
    key = f"{client}:{product_id}:{event_type}:{channel}:{source}"

    # Dọn cache nhẹ
    expired = [k for k, ts in _EVENT_CACHE.items() if now - ts > EVENT_TTL_SECONDS]
    for k in expired[:100]:
        _EVENT_CACHE.pop(k, None)

    last = _EVENT_CACHE.get(key)
    if last and now - last < EVENT_TTL_SECONDS:
        return True

    _EVENT_CACHE[key] = now
    return False


@analytics_bp.route("/track", methods=["POST"])
@csrf.exempt
def track_event():
    """
    Endpoint tracking từ UI.

    Payload hợp lệ:
    {
      "product_id": "uuid",
      "event_type": "view" | "cart" | "wishlist",
      "channel": "web",
      "source": "organic",
      "qty": 1
    }
    """
    try:
        data = request.get_json(silent=True) or {}

        product_id = str(data.get("product_id") or "").strip()
        if not product_id:
            return jsonify({"success": False, "error": "Missing product_id"}), 400

        if not _is_valid_uuid(product_id):
            return jsonify({"success": False, "error": "Invalid product_id"}), 400

        event_type = _clean_string(data.get("event_type")).lower()
        if event_type not in VALID_CLIENT_EVENTS:
            return jsonify({
                "success": False,
                "error": "Invalid or forbidden event_type"
            }), 400

        channel = _clean_channel(data.get("channel", "web"))
        source = _clean_source(data.get("source", "organic"))
        qty = _to_int(data.get("qty", 1), 1)

        # Client không được ghi doanh thu.
        revenue = 0.0

        if event_type == "view":
            qty = 1

        if _is_duplicate_event(product_id, event_type, channel, source):
            return jsonify({"success": True, "deduped": True}), 200

        db = get_supabase_admin()

        db.rpc("log_product_event", {
            "p_product_id": product_id,
            "p_channel": channel,
            "p_source": source,
            "p_event_type": event_type,
            "p_revenue": revenue,
            "p_qty": qty,
        }).execute()

        logger.debug(
            "[Analytics] event=%s product=%s channel=%s source=%s qty=%s user=%s",
            event_type,
            product_id,
            channel,
            source,
            qty,
            session.get("user_id"),
        )

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("[Analytics] Track event error: %s", e, exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal analytics engine error"
        }), 500