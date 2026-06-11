"""
app/services/chat_service.py
============================
GUAMAISON Smart AI Assistant

Tính năng:
- Phân loại intent bằng Gemini nếu có GEMINI_API_KEY.
- Fallback local intent nếu Gemini lỗi/chưa cấu hình.
- Tư vấn size.
- Tìm sản phẩm.
- Gợi ý phối đồ.
- Tra cứu đơn hàng.
- Response đồng bộ với chat.html:
  {
    reply: str,
    intent: str,
    products: [],
    action_data: {}
  }
"""

from __future__ import annotations

import html
import logging
import os
import re
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.schemas.chat_schema import ChatResponse, ExtractedIntent, ProductSuggestion
from app.utils.supabase_client import get_supabase

load_dotenv()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# GEMINI CLIENT
# ═══════════════════════════════════════════════════════════════

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# Ưu tiên model ổn định. Có thể đổi trong .env:
# GEMINI_MODEL=gemini-2.0-flash
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()

if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        logger.error("[ChatService] Không khởi tạo được Gemini client: %s", e, exc_info=True)
        client = None
else:
    logger.warning("[ChatService] Chưa cấu hình GEMINI_API_KEY. Chatbot sẽ dùng fallback local intent.")
    client = None


# ═══════════════════════════════════════════════════════════════
# MEMORY CONFIG
# ═══════════════════════════════════════════════════════════════

CONVERSATION_MEMORY: "OrderedDict[str, list[dict[str, str]]]" = OrderedDict()
MAX_SESSIONS = 300
MAX_MESSAGES_PER_SESSION = 10
SESSION_TTL_SECONDS = 60 * 60 * 6
SESSION_LAST_SEEN: dict[str, float] = {}


# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

PLACEHOLDER_PRODUCT = "https://placehold.co/300x400/f7f9f2/1b4922?text=GUAMAISON"

VALID_INTENTS = {
    "general_chat",
    "search_product",
    "size_advice",
    "order_tracking",
    "policy_info",
    "promotion_info",
    "outfit_suggestion",
    "error",
}

OUTFIT_TOP_KEYWORDS = [
    "áo",
    "shirt",
    "tee",
    "t-shirt",
    "polo",
    "sơ mi",
    "hoodie",
    "jacket",
    "blazer",
]

OUTFIT_BOTTOM_KEYWORDS = [
    "quần",
    "pants",
    "jean",
    "short",
    "cargo",
    "trouser",
    "chinos",
]

GENERAL_KEYWORDS = [
    "mới",
    "hot",
    "bán chạy",
    "best seller",
    "best-seller",
    "nổi bật",
    "đẹp",
    "mẫu",
    "sản phẩm",
    "shop có gì",
    "xem đồ",
]

SEARCH_HINTS = {
    "áo khoác": ["áo khoác", "jacket", "blazer"],
    "áo thun": ["áo thun", "tee", "t-shirt"],
    "áo sơ mi": ["sơ mi", "shirt"],
    "quần jean": ["jean", "denim"],
    "quần tây": ["quần tây", "trouser", "pants"],
    "quần short": ["short"],
    "váy": ["váy", "dress", "skirt"],
    "đầm": ["đầm", "dress"],
    "túi": ["túi", "bag"],
    "phụ kiện": ["phụ kiện", "accessory", "belt", "cap"],
}

POLICY_REPLY = (
    "GUAMAISON hỗ trợ bạn như sau:<br>"
    "• <strong>Đổi trả:</strong> hỗ trợ trong 7 ngày nếu sản phẩm còn nguyên tem, chưa qua sử dụng.<br>"
    "• <strong>Vận chuyển:</strong> thời gian giao hàng thường từ 2–5 ngày tùy khu vực.<br>"
    "• <strong>Hỗ trợ:</strong> bạn có thể nhắn fanpage hoặc liên hệ bộ phận CSKH để được kiểm tra nhanh hơn."
)

PROMOTION_REPLY = (
    "Hiện GUAMAISON có thể áp dụng ưu đãi tùy chương trình đang chạy. "
    "Bạn có thể thử mã <strong>WELCOME10</strong> cho đơn hàng đầu tiên, hoặc theo dõi trang chủ để cập nhật ưu đãi mới nhất."
)


# ═══════════════════════════════════════════════════════════════
# UTILS
# ═══════════════════════════════════════════════════════════════

def _safe_text(value: Any, max_len: int = 1200) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_len]


def _safe_price_number(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _format_vnd(value: Any) -> str:
    number = _safe_price_number(value)
    if number <= 0:
        return "Liên hệ"
    return f"{number:,.0f}".replace(",", ".") + " ₫"


def _extract_numbers(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d{2,3}", text or "")]


def _extract_phone(text: str) -> Optional[str]:
    compact = re.sub(r"[^\d]", "", text or "")
    match = re.search(r"(0\d{9,10})", compact)
    return match.group(1) if match else None


def _extract_order_code(text: str) -> Optional[str]:
    """
    Hỗ trợ:
    - ORD123456
    - POS654321
    - 8 ký tự đầu UUID / mã đơn tự nhập
    """
    raw = (text or "").strip().upper()

    match = re.search(r"\b(ORD|POS|MM|DH)[A-Z0-9\-]{4,24}\b", raw)
    if match:
        return match.group(0)

    # UUID full
    match = re.search(
        r"\b[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\b",
        raw,
    )
    if match:
        return match.group(0)

    return None


def _sanitize_keyword(keyword: Any) -> str:
    text = _safe_text(keyword, 60).lower()

    # Chặn ký tự làm hỏng cú pháp PostgREST .or_()
    text = text.replace("%", " ").replace(",", " ").replace("(", " ").replace(")", " ")
    text = text.replace(";", " ").replace("*", " ").replace("[", " ").replace("]", " ")
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _model_to_dict(model: Any) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()

    if hasattr(model, "dict"):
        return model.dict()

    return dict(model or {})


def _product_suggestion_from_row(row: dict[str, Any]) -> ProductSuggestion:
    return ProductSuggestion(
        id=str(row.get("id") or ""),
        name=str(row.get("name") or "Sản phẩm GUAMAISON"),
        price=_format_vnd(row.get("price")),
        thumbnail_url=(
            row.get("thumbnail_url")
            or row.get("image")
            or PLACEHOLDER_PRODUCT
        ),
        slug=str(row.get("slug") or ""),
    )


def _dedupe_products(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        pid = str(row.get("id") or row.get("slug") or row.get("name") or "")
        if not pid or pid in seen:
            continue

        seen.add(pid)
        result.append(row)

    return result


# ═══════════════════════════════════════════════════════════════
# SERVICE
# ═══════════════════════════════════════════════════════════════

class AdvancedChatService:
    """
    Service chính cho /api/bot.
    """

    SIZE_CHART = {
        "S": {"max_h": 168, "max_w": 55},
        "M": {"max_h": 174, "max_w": 65},
        "L": {"max_h": 180, "max_w": 75},
        "XL": {"max_h": 190, "max_w": 90},
    }

    @classmethod
    def _cleanup_memory(cls) -> None:
        now = time.time()

        expired = [
            sid
            for sid, last_seen in SESSION_LAST_SEEN.items()
            if now - last_seen > SESSION_TTL_SECONDS
        ]

        for sid in expired:
            SESSION_LAST_SEEN.pop(sid, None)
            CONVERSATION_MEMORY.pop(sid, None)

        while len(CONVERSATION_MEMORY) > MAX_SESSIONS:
            sid, _ = CONVERSATION_MEMORY.popitem(last=False)
            SESSION_LAST_SEEN.pop(sid, None)

    @classmethod
    def get_history(cls, session_id: str) -> list[dict[str, str]]:
        sid = _safe_text(session_id, 120) or "anonymous_session"

        cls._cleanup_memory()
        SESSION_LAST_SEEN[sid] = time.time()

        if sid not in CONVERSATION_MEMORY:
            CONVERSATION_MEMORY[sid] = []

        CONVERSATION_MEMORY.move_to_end(sid)

        return CONVERSATION_MEMORY[sid]

    @classmethod
    def save_to_memory(cls, session_id: str, role: str, content: str) -> None:
        history = cls.get_history(session_id)

        history.append({
            "role": "assistant" if role == "assistant" else "user",
            "content": _safe_text(content, 1000),
        })

        if len(history) > MAX_MESSAGES_PER_SESSION:
            del history[:-MAX_MESSAGES_PER_SESSION]

    @classmethod
    def process_message(cls, session_id: str, message: str) -> dict:
        sid = _safe_text(session_id, 120) or "anonymous_session"
        user_message = _safe_text(message, 1200)

        if not user_message:
            return _model_to_dict(ChatResponse(
                reply="Bạn vui lòng nhập nội dung cần hỗ trợ nhé.",
                intent="error",
                products=[],
                action_data={},
            ))

        cls.save_to_memory(sid, "user", user_message)

        try:
            ai_data = cls._extract_intent_with_gemini(sid, user_message)
        except Exception as e:
            logger.warning("[ChatService] Gemini lỗi, dùng fallback local intent: %s", e)
            ai_data = cls._extract_intent_locally(user_message)

        response_data = ChatResponse(
            reply=ai_data.reply,
            intent=ai_data.intent if ai_data.intent in VALID_INTENTS else "general_chat",
            products=[],
            action_data={},
        )

        try:
            response_data = cls._handle_intent(ai_data, response_data)
        except Exception as e:
            logger.error("[ChatService] Lỗi xử lý intent: %s", e, exc_info=True)
            response_data = ChatResponse(
                reply="Hệ thống đang xử lý chưa ổn định. Bạn thử lại sau ít phút nhé.",
                intent="error",
                products=[],
                action_data={},
            )

        cls.save_to_memory(sid, "assistant", response_data.reply)
        return _model_to_dict(response_data)

    # ═══════════════════════════════════════════════════════════
    # INTENT EXTRACTION
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def _extract_intent_with_gemini(cls, session_id: str, message: str) -> ExtractedIntent:
        if not client:
            raise RuntimeError("Gemini client chưa được cấu hình.")

        history = cls.get_history(session_id)

        chat_context = ""
        for item in history[-MAX_MESSAGES_PER_SESSION:-1]:
            speaker = "Khách" if item["role"] == "user" else "GUAMAISON Stylist"
            chat_context += f"{speaker}: {item['content']}\n"

        system_prompt = """
Bạn là GUAMAISON Stylist, trợ lý ảo thời trang cho một website bán quần áo.

Giọng điệu:
- Sang trọng, tinh tế, gần gũi.
- Thuần Việt, không dùng quá nhiều từ tiếng Anh nếu không cần.
- Không tự nhận là GUA Maison. Luôn dùng thương hiệu GUAMAISON.

Nhiệm vụ:
1. Phân loại intent:
   - general_chat: Chào hỏi, hỏi chung.
   - search_product: Khách tìm sản phẩm cụ thể hoặc muốn xem mẫu.
   - outfit_suggestion: Khách muốn phối đồ, gợi ý set đồ, mặc gì đẹp.
   - size_advice: Khách hỏi size, có chiều cao/cân nặng/số đo.
   - order_tracking: Khách hỏi đơn hàng, mã đơn, số điện thoại.
   - policy_info: Hỏi đổi trả, vận chuyển, bảo hành, địa chỉ, chính sách.
   - promotion_info: Hỏi ưu đãi, voucher, khuyến mãi.

2. Với search_product:
   - keywords phải là loại trang phục/sản phẩm có thể tìm trong DB.
   - Ví dụ: “đi chơi cuối tuần” có thể chuyển thành ["áo thun", "quần jean", "áo khoác"].
   - Nếu khách chỉ nói “cho xem đồ mới”, đặt is_general_request=true.

3. Với size_advice:
   - Trích xuất height và weight nếu có.

4. Với order_tracking:
   - Trích xuất phone hoặc order_code nếu có.

Chỉ trả JSON đúng schema.
"""

        prompt = (
            f"Lịch sử trò chuyện:\n{chat_context or 'Chưa có.'}\n\n"
            f"Tin nhắn mới của khách: {message}\n\n"
            "Hãy phân tích intent và tạo câu trả lời ngắn gọn."
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=ExtractedIntent,
                temperature=0.25,
            ),
        )

        parsed = response.parsed

        if isinstance(parsed, ExtractedIntent):
            return parsed

        if isinstance(parsed, dict):
            return ExtractedIntent(**parsed)

        raise RuntimeError("Gemini trả về response.parsed không hợp lệ.")

    @classmethod
    def _extract_intent_locally(cls, message: str) -> ExtractedIntent:
        text = message.lower().strip()

        phone = _extract_phone(text)
        order_code = _extract_order_code(text)

        # Size
        nums = _extract_numbers(text)
        height = None
        weight = None

        for n in nums:
            if 130 <= n <= 210 and height is None:
                height = n
            elif 30 <= n <= 130 and weight is None:
                weight = n

        if any(k in text for k in ["size", "sai", "cao", "nặng", "kg", "cm", "vừa", "mặc cỡ"]):
            return ExtractedIntent(
                reply="Mình sẽ tư vấn size theo chiều cao và cân nặng của bạn nhé.",
                intent="size_advice",
                keywords=[],
                is_general_request=False,
                height=height,
                weight=weight,
                phone=phone,
                order_code=order_code,
            )

        # Order tracking
        if phone or order_code or any(k in text for k in ["đơn hàng", "mã đơn", "tra đơn", "kiểm tra đơn", "giao tới đâu"]):
            return ExtractedIntent(
                reply="Mình sẽ kiểm tra thông tin đơn hàng cho bạn.",
                intent="order_tracking",
                keywords=[],
                is_general_request=False,
                height=None,
                weight=None,
                phone=phone,
                order_code=order_code,
            )

        # Policy
        if any(k in text for k in ["đổi trả", "bảo hành", "vận chuyển", "ship", "freeship", "địa chỉ", "liên hệ"]):
            return ExtractedIntent(
                reply="Mình gửi bạn thông tin chính sách của GUAMAISON nhé.",
                intent="policy_info",
                keywords=[],
                is_general_request=False,
            )

        # Promotion
        if any(k in text for k in ["khuyến mãi", "voucher", "giảm giá", "mã giảm", "sale", "ưu đãi"]):
            return ExtractedIntent(
                reply="Mình kiểm tra ưu đãi phù hợp cho bạn nhé.",
                intent="promotion_info",
                keywords=[],
                is_general_request=False,
            )

        # Outfit
        if any(k in text for k in ["phối", "set đồ", "outfit", "mặc gì", "mix", "đi chơi", "đi làm", "hẹn hò"]):
            return ExtractedIntent(
                reply="Mình gợi ý một set đồ phù hợp với phong cách GUAMAISON cho bạn nhé.",
                intent="outfit_suggestion",
                keywords=[],
                is_general_request=False,
            )

        # Search product
        keywords = []
        for canonical, hints in SEARCH_HINTS.items():
            if any(h in text for h in hints):
                keywords.append(canonical)

        is_general = any(k in text for k in GENERAL_KEYWORDS)

        if keywords or is_general or any(k in text for k in ["xem", "tìm", "có", "mẫu"]):
            return ExtractedIntent(
                reply="Mình gửi bạn một vài sản phẩm phù hợp nhé.",
                intent="search_product",
                keywords=keywords,
                is_general_request=is_general or not keywords,
            )

        return ExtractedIntent(
            reply="Mình có thể hỗ trợ bạn tìm sản phẩm, chọn size, phối đồ hoặc kiểm tra đơn hàng.",
            intent="general_chat",
            keywords=[],
            is_general_request=False,
        )

    # ═══════════════════════════════════════════════════════════
    # INTENT HANDLERS
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def _handle_intent(
        cls,
        ai_data: ExtractedIntent,
        response_data: ChatResponse,
    ) -> ChatResponse:
        intent = response_data.intent

        if intent == "outfit_suggestion":
            return cls._fetch_outfit_from_db(response_data)

        if intent == "size_advice":
            return cls._handle_size_advice(ai_data, response_data)

        if intent == "search_product":
            return cls._fetch_products_from_db(
                keywords=ai_data.keywords or [],
                is_general=bool(ai_data.is_general_request),
                response_data=response_data,
            )

        if intent == "order_tracking":
            return cls._handle_order_tracking(
                phone=ai_data.phone,
                order_code=ai_data.order_code,
                response_data=response_data,
            )

        if intent == "policy_info":
            response_data.reply = POLICY_REPLY
            return response_data

        if intent == "promotion_info":
            response_data.reply = PROMOTION_REPLY
            return response_data

        response_data.reply = (
            response_data.reply
            or "Mình có thể hỗ trợ bạn tìm sản phẩm, chọn size, phối đồ hoặc kiểm tra đơn hàng."
        )

        return response_data

    @classmethod
    def _handle_size_advice(
        cls,
        ai_data: ExtractedIntent,
        response_data: ChatResponse,
    ) -> ChatResponse:
        height = ai_data.height
        weight = ai_data.weight

        if not height or not weight:
            response_data.reply = (
                "Để tư vấn size chuẩn hơn, bạn cho GUAMAISON xin "
                "<strong>chiều cao</strong> và <strong>cân nặng</strong> nhé. "
                "Ví dụ: “mình cao 170cm nặng 60kg”."
            )
            response_data.action_data = {}
            return response_data

        rec_size = "XL"

        for size, limits in cls.SIZE_CHART.items():
            if height <= limits["max_h"] and weight <= limits["max_w"]:
                rec_size = size
                break

        response_data.reply = (
            f"Với chiều cao <strong>{height}cm</strong> và cân nặng <strong>{weight}kg</strong>, "
            f"GUAMAISON gợi ý bạn chọn size <strong>{rec_size}</strong>. "
            "Nếu bạn thích mặc rộng thoải mái hơn, có thể cân nhắc tăng thêm 1 size."
        )

        response_data.action_data = {
            "height": height,
            "weight": weight,
            "recommended_size": rec_size,
        }

        return response_data

    # ═══════════════════════════════════════════════════════════
    # DATABASE HELPERS
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def _base_product_query(cls):
        db = get_supabase()

        return (
            db.table("products")
            .select("id, name, price, thumbnail_url, slug")
            .eq("is_active", True)
            .is_("deleted_at", "null")
        )

    @classmethod
    def _fetch_latest_products(cls, limit: int = 3) -> list[dict[str, Any]]:
        try:
            res = (
                cls._base_product_query()
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            return res.data or []

        except Exception as e:
            logger.error("[ChatService] Lỗi lấy sản phẩm mới: %s", e, exc_info=True)
            return []

    @classmethod
    def _search_products_by_keywords(
        cls,
        keywords: list[str],
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        clean_keywords = [_sanitize_keyword(k) for k in keywords if _sanitize_keyword(k)]
        clean_keywords = clean_keywords[:6]

        if not clean_keywords:
            return []

        try:
            or_conditions = ",".join(
                [
                    f"name.ilike.%{kw}%,description.ilike.%{kw}%,search_keywords.ilike.%{kw}%"
                    for kw in clean_keywords
                ]
            )

            res = (
                cls._base_product_query()
                .or_(or_conditions)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            return res.data or []

        except Exception as e:
            logger.warning("[ChatService] Search theo keyword lỗi: %s", e)

            # Fallback tìm từng keyword riêng để tránh vỡ toàn bộ query
            collected: list[dict[str, Any]] = []

            for kw in clean_keywords:
                try:
                    res = (
                        cls._base_product_query()
                        .ilike("name", f"%{kw}%")
                        .order("created_at", desc=True)
                        .limit(limit)
                        .execute()
                    )
                    collected.extend(res.data or [])
                except Exception:
                    continue

            return _dedupe_products(collected)[:limit]

    @classmethod
    def _fetch_products_from_db(
        cls,
        keywords: list[str],
        is_general: bool,
        response_data: ChatResponse,
    ) -> ChatResponse:
        products_data: list[dict[str, Any]] = []

        if is_general:
            products_data = cls._fetch_latest_products(limit=3)
            response_data.reply = "GUAMAISON gửi bạn một vài thiết kế mới nhất đang có trên web nhé."
        else:
            products_data = cls._search_products_by_keywords(keywords, limit=3)

        if not products_data:
            products_data = cls._fetch_latest_products(limit=3)

            if products_data:
                response_data.reply = (
                    "Mẫu bạn tìm hiện chưa có kết quả thật khớp hoàn toàn. "
                    "GUAMAISON gợi ý bạn một vài thiết kế mới nhất để tham khảo nhé."
                )
            else:
                response_data.reply = (
                    "Hiện hệ thống chưa tìm thấy sản phẩm phù hợp. "
                    "Bạn có thể mô tả rõ hơn như áo, quần, màu sắc hoặc phong cách mong muốn nhé."
                )

        response_data.products = [
            _product_suggestion_from_row(row)
            for row in products_data[:3]
        ]

        return response_data

    @classmethod
    def _fetch_outfit_from_db(cls, response_data: ChatResponse) -> ChatResponse:
        """
        Gợi ý 1 áo + 1 quần.
        Nếu không đủ data, fallback về sản phẩm mới.
        """
        try:
            top_items = cls._search_products_by_keywords(OUTFIT_TOP_KEYWORDS, limit=1)
            bottom_items = cls._search_products_by_keywords(OUTFIT_BOTTOM_KEYWORDS, limit=1)

            outfit_items = _dedupe_products(top_items + bottom_items)

            if len(outfit_items) < 2:
                latest = cls._fetch_latest_products(limit=3)
                outfit_items = _dedupe_products(outfit_items + latest)

            if len(outfit_items) >= 2:
                response_data.reply = (
                    "GUAMAISON gợi ý bạn một set đồ dễ mặc nhưng vẫn có điểm nhấn: "
                    "một item phần trên phối cùng item phần dưới để tạo tổng thể gọn, hiện đại và dễ ứng dụng."
                )

                response_data.products = [
                    _product_suggestion_from_row(row)
                    for row in outfit_items[:3]
                ]

            else:
                response_data.reply = (
                    "Hiện mình chưa đủ dữ liệu sản phẩm để phối một set hoàn chỉnh. "
                    "Bạn có thể xem một vài mẫu mới nhất của GUAMAISON trước nhé."
                )

        except Exception as e:
            logger.error("[ChatService] Lỗi phối đồ: %s", e, exc_info=True)

        return response_data

    @classmethod
    def _handle_order_tracking(
        cls,
        phone: Optional[str],
        order_code: Optional[str],
        response_data: ChatResponse,
    ) -> ChatResponse:
        if not phone and not order_code:
            response_data.reply = (
                "Bạn cho GUAMAISON xin <strong>số điện thoại đặt hàng</strong> "
                "hoặc <strong>mã đơn hàng</strong> để mình kiểm tra nhé."
            )
            return response_data

        db = get_supabase()

        try:
            query = db.table("orders").select(
                "id, order_number, code, status, total_amount, created_at, customer_phone, phone"
            )

            if order_code:
                code = order_code.upper()

                # Ưu tiên order_number/code, fallback id nếu người dùng nhập UUID.
                try:
                    query = query.or_(
                        f"order_number.eq.{code},code.eq.{code},id.eq.{code}"
                    )
                except Exception:
                    query = db.table("orders").select(
                        "id, order_number, code, status, total_amount, created_at, customer_phone, phone"
                    ).eq("id", code)

            elif phone:
                query = query.or_(
                    f"customer_phone.eq.{phone},phone.eq.{phone}"
                )

            res = query.order("created_at", desc=True).limit(1).execute()
            orders = res.data or []

            if not orders:
                response_data.reply = (
                    "GUAMAISON chưa tìm thấy đơn hàng khớp với thông tin này. "
                    "Bạn kiểm tra lại số điện thoại hoặc mã đơn giúp mình nhé."
                )
                return response_data

            order = orders[0]

            status_map = {
                "pending": "Chờ xác nhận",
                "confirmed": "Đã xác nhận",
                "packed": "Đã đóng gói",
                "shipping": "Đang vận chuyển",
                "shipped": "Đang giao hàng",
                "delivered": "Đã giao hàng",
                "completed": "Hoàn tất",
                "cancelled": "Đã hủy",
                "failed": "Giao thất bại",
                "returned": "Đã hoàn hàng",
            }

            order_display = (
                order.get("order_number")
                or order.get("code")
                or str(order.get("id", ""))[:8].upper()
            )

            status_text = status_map.get(order.get("status"), order.get("status") or "Đang cập nhật")
            total_fmt = _format_vnd(order.get("total_amount"))

            response_data.reply = (
                "<div class='rounded-xl border border-emerald-100 bg-emerald-50/60 p-3 mb-2'>"
                "<div class='flex justify-between gap-3 border-b border-emerald-100 pb-2 mb-2'>"
                "<span class='text-[10px] font-black uppercase tracking-widest text-emerald-700'>Mã đơn</span>"
                f"<span class='text-xs font-black text-emerald-950'>{html.escape(str(order_display))}</span>"
                "</div>"
                "<div class='flex justify-between gap-3 text-[13px]'>"
                "<span class='text-emerald-700'>Trạng thái:</span>"
                f"<span class='font-black text-emerald-900'>{html.escape(str(status_text))}</span>"
                "</div>"
                "<div class='mt-1 flex justify-between gap-3 text-[13px]'>"
                "<span class='text-emerald-700'>Tổng tiền:</span>"
                f"<span class='font-black text-emerald-950'>{html.escape(total_fmt)}</span>"
                "</div>"
                "</div>"
                "GUAMAISON đã kiểm tra xong trạng thái đơn hàng của bạn."
            )

            response_data.action_data = {
                "order_id": order.get("id"),
                "order_code": order_display,
                "status": order.get("status"),
                "total_amount": order.get("total_amount"),
            }

            return response_data

        except Exception as e:
            logger.error("[ChatService] Lỗi tra cứu đơn hàng: %s", e, exc_info=True)

            response_data.reply = (
                "Hệ thống đang chưa kiểm tra được đơn hàng lúc này. "
                "Bạn thử lại sau ít phút hoặc liên hệ GUAMAISON để được hỗ trợ nhanh hơn nhé."
            )

            return response_data