"""
app/services/chat_service.py
============================
GUAMAISON Smart AI Assistant

Bản nâng cấp:
- Không crash app nếu thiếu google-genai hoặc thiếu GEMINI_API_KEY.
- Gemini dùng để hiểu intent + trả lời câu hỏi mở linh hoạt hơn.
- Fallback local mạnh hơn khi chưa cấu hình Gemini.
- Hỗ trợ:
  + Chào hỏi / hỏi chung.
  + Tìm sản phẩm.
  + Gợi ý phối đồ.
  + Tư vấn size.
  + Tra cứu đơn hàng.
  + Chính sách đổi trả / vận chuyển / thanh toán / bảo quản.
  + Câu hỏi mở về GUAMAISON và thời trang.
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
import unicodedata
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None

from app.schemas.chat_schema import ChatResponse, ExtractedIntent, ProductSuggestion
from app.utils.supabase_client import get_supabase

load_dotenv()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# GEMINI CLIENT
# ═══════════════════════════════════════════════════════════════

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()
GEMINI_TEMPERATURE = float(os.environ.get("GEMINI_TEMPERATURE", "0.35") or 0.35)

if GEMINI_API_KEY and genai:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        logger.error("[ChatService] Không khởi tạo được Gemini client: %s", e, exc_info=True)
        client = None
elif GEMINI_API_KEY and not genai:
    logger.warning("[ChatService] Có GEMINI_API_KEY nhưng thiếu package google-genai.")
    client = None
else:
    logger.warning("[ChatService] Chưa cấu hình GEMINI_API_KEY. Chatbot dùng fallback local.")
    client = None


# ═══════════════════════════════════════════════════════════════
# MEMORY CONFIG
# ═══════════════════════════════════════════════════════════════

CONVERSATION_MEMORY: "OrderedDict[str, list[dict[str, str]]]" = OrderedDict()
SESSION_LAST_SEEN: dict[str, float] = {}

MAX_SESSIONS = int(os.environ.get("CHAT_MAX_SESSIONS", "400") or 400)
MAX_MESSAGES_PER_SESSION = int(os.environ.get("CHAT_MAX_MESSAGES", "14") or 14)
SESSION_TTL_SECONDS = int(os.environ.get("CHAT_SESSION_TTL_SECONDS", str(60 * 60 * 6)))


# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

BRAND_NAME = "GUAMAISON"
PLACEHOLDER_PRODUCT = "https://placehold.co/300x400/fef9ed/010101?text=GUAMAISON"

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
    "ao",
    "shirt",
    "tee",
    "t-shirt",
    "polo",
    "sơ mi",
    "so mi",
    "hoodie",
    "áo khoác",
    "ao khoac",
    "jacket",
    "blazer",
]

OUTFIT_BOTTOM_KEYWORDS = [
    "quần",
    "quan",
    "pants",
    "jean",
    "denim",
    "short",
    "cargo",
    "trouser",
    "chinos",
]

GENERAL_KEYWORDS = [
    "mới",
    "moi",
    "hot",
    "bán chạy",
    "ban chay",
    "best seller",
    "best-seller",
    "nổi bật",
    "noi bat",
    "đẹp",
    "dep",
    "mẫu",
    "mau",
    "sản phẩm",
    "san pham",
    "shop có gì",
    "shop co gi",
    "xem đồ",
    "xem do",
]

SEARCH_HINTS = {
    "áo khoác": ["áo khoác", "ao khoac", "jacket", "blazer", "outerwear"],
    "áo thun": ["áo thun", "ao thun", "tee", "t-shirt", "tshirt"],
    "áo polo": ["polo", "áo polo", "ao polo"],
    "áo sơ mi": ["sơ mi", "so mi", "shirt"],
    "hoodie": ["hoodie", "sweater", "sweatshirt"],
    "quần jean": ["jean", "denim", "quần jean", "quan jean"],
    "quần tây": ["quần tây", "quan tay", "trouser", "pants"],
    "quần short": ["short", "quần short", "quan short"],
    "quần cargo": ["cargo", "quần cargo", "quan cargo"],
    "váy": ["váy", "vay", "skirt"],
    "đầm": ["đầm", "dam", "dress"],
    "túi": ["túi", "tui", "bag"],
    "phụ kiện": ["phụ kiện", "phu kien", "accessory", "belt", "cap", "nón", "non"],
}

COLOR_HINTS = {
    "đen": ["đen", "den", "black"],
    "trắng": ["trắng", "trang", "white"],
    "kem": ["kem", "cream", "beige"],
    "xám": ["xám", "xam", "gray", "grey"],
    "nâu": ["nâu", "nau", "brown"],
    "xanh": ["xanh", "green", "blue"],
    "đỏ": ["đỏ", "do", "red"],
}

STYLE_HINTS = {
    "tối giản": ["tối giản", "toi gian", "minimal", "basic"],
    "streetwear": ["streetwear", "đường phố", "duong pho"],
    "đi làm": ["đi làm", "di lam", "office", "cong so", "công sở"],
    "đi chơi": ["đi chơi", "di choi", "weekend", "hẹn hò", "hen ho"],
    "sang trọng": ["sang trọng", "sang trong", "formal", "luxury"],
    "casual": ["casual", "thoải mái", "thoai mai"],
}

FAQ_KEYWORDS = {
    "payment": [
        "thanh toán", "thanh toan", "cod", "chuyển khoản", "chuyen khoan",
        "vnpay", "momo", "trả tiền", "tra tien", "quẹt thẻ", "quet the",
    ],
    "shipping": [
        "ship", "giao hàng", "giao hang", "vận chuyển", "van chuyen",
        "bao lâu", "bao lau", "phí ship", "phi ship", "freeship",
    ],
    "return": [
        "đổi trả", "doi tra", "hoàn hàng", "hoan hang", "trả hàng", "tra hang",
        "đổi size", "doi size", "lỗi", "loi", "bị rách", "bi rach",
    ],
    "contact": [
        "liên hệ", "lien he", "hotline", "facebook", "fanpage", "zalo",
        "địa chỉ", "dia chi", "cửa hàng", "cua hang",
    ],
    "care": [
        "giặt", "giat", "bảo quản", "bao quan", "ủi", "ui",
        "phai màu", "phai mau", "co rút", "co rut",
    ],
    "material": [
        "chất liệu", "chat lieu", "vải", "vai", "cotton", "poly", "lụa", "lua",
        "dày không", "day khong", "mỏng không", "mong khong",
    ],
    "buying": [
        "mua sao", "đặt hàng", "dat hang", "cách mua", "cach mua",
        "thêm giỏ", "them gio", "checkout", "giỏ hàng", "gio hang",
    ],
    "brand": [
        "guamaison là gì", "guamaison la gi", "shop bán gì", "shop ban gi",
        "phong cách", "phong cach", "thương hiệu", "thuong hieu",
    ],
}

POLICY_REPLY = (
    "GUAMAISON hỗ trợ đổi/trả trong 7 ngày nếu sản phẩm còn nguyên tem, chưa qua sử dụng và chưa giặt. "
    "Thời gian giao hàng thường từ 2–5 ngày tùy khu vực. "
    "Bạn có thể nhắn fanpage hoặc để lại thông tin đơn hàng để đội ngũ hỗ trợ kiểm tra nhanh hơn."
)

PROMOTION_REPLY = (
    "Ưu đãi có thể thay đổi theo từng chương trình. Bạn có thể thử mã WELCOME10 cho đơn hàng đầu tiên "
    "hoặc theo dõi trang chủ GUAMAISON để cập nhật mã giảm giá mới nhất."
)


# ═══════════════════════════════════════════════════════════════
# UTILS
# ═══════════════════════════════════════════════════════════════

def _safe_text(value: Any, max_len: int = 1200) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_len]


def _strip_accents(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return text


def _normalize(value: Any, max_len: int = 1200) -> str:
    text = _safe_text(value, max_len=max_len).lower()
    return _strip_accents(text)


def _clean_reply(value: Any, max_len: int = 900) -> str:
    text = _safe_text(value, max_len=max_len)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("**", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def _contains_any(normalized_text: str, keywords: list[str]) -> bool:
    haystack = normalized_text or ""
    return any(_normalize(k, 120) in haystack for k in keywords if k)


def _safe_price_number(value: Any) -> float:
    try:
        if isinstance(value, str):
            raw = re.sub(r"[^\d.]", "", value.replace(",", "."))
            return float(raw or 0)
        return float(value or 0)
    except Exception:
        return 0.0


def _format_vnd(value: Any) -> str:
    number = _safe_price_number(value)
    if number <= 0:
        return "Liên hệ"
    return f"{number:,.0f}".replace(",", ".") + " ₫"


def _extract_numbers(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d{2,4}", text or "")]


def _extract_phone(text: str) -> Optional[str]:
    compact = re.sub(r"[^\d]", "", text or "")
    match = re.search(r"(0\d{9,10})", compact)
    return match.group(1) if match else None


def _extract_order_code(text: str) -> Optional[str]:
    raw = (text or "").strip().upper()

    match = re.search(r"\b(ORD|POS|MM|DH|GM|GUA)[A-Z0-9\-]{4,30}\b", raw)
    if match:
        return match.group(0)

    match = re.search(
        r"\b[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\b",
        raw,
    )
    if match:
        return match.group(0)

    return None


def _extract_height_weight(text: str) -> tuple[Optional[int], Optional[int]]:
    normalized = _normalize(text)
    nums = _extract_numbers(normalized)

    height = None
    weight = None

    # Pattern rõ ràng: 1m70, 1m7
    m_height = re.search(r"\b1m(\d{1,2})\b", normalized)
    if m_height:
        tail = m_height.group(1)
        height = int("1" + tail) if len(tail) == 2 else int("17" + tail)

    # Pattern: 170cm, cao 170
    cm_match = re.search(r"(\d{3})\s*cm", normalized)
    if cm_match:
        height = int(cm_match.group(1))

    kg_match = re.search(r"(\d{2,3})\s*kg", normalized)
    if kg_match:
        weight = int(kg_match.group(1))

    for n in nums:
        if height is None and 130 <= n <= 220:
            height = n
        elif weight is None and 30 <= n <= 160:
            weight = n

    return height, weight


def _extract_price_range(text: str) -> dict[str, Optional[float]]:
    normalized = _normalize(text)
    result: dict[str, Optional[float]] = {"min_price": None, "max_price": None}

    def parse_money(raw: str) -> float:
        raw = raw.lower().strip().replace(",", ".")
        number_match = re.search(r"\d+(?:\.\d+)?", raw)
        if not number_match:
            return 0
        number = float(number_match.group(0))

        if "tr" in raw or "triệu" in raw or "trieu" in raw:
            return number * 1_000_000

        if "k" in raw or number < 10:
            return number * 1000

        return number

    under = re.search(r"(duoi|nho hon|toi da|khong qua)\s+([\d\.,]+\s*(?:k|tr|trieu|triệu)?)", normalized)
    if under:
        result["max_price"] = parse_money(under.group(2))

    over = re.search(r"(tren|tu|hon)\s+([\d\.,]+\s*(?:k|tr|trieu|triệu)?)", normalized)
    if over:
        result["min_price"] = parse_money(over.group(2))

    between = re.search(
        r"(tu)\s+([\d\.,]+\s*(?:k|tr|trieu|triệu)?)\s+(den|toi|-)\s+([\d\.,]+\s*(?:k|tr|trieu|triệu)?)",
        normalized,
    )
    if between:
        result["min_price"] = parse_money(between.group(2))
        result["max_price"] = parse_money(between.group(4))

    return result


def _extract_keywords_locally(message: str) -> list[str]:
    normalized = _normalize(message)
    keywords: list[str] = []

    for canonical, hints in SEARCH_HINTS.items():
        if _contains_any(normalized, hints):
            keywords.append(canonical)

    for canonical, hints in COLOR_HINTS.items():
        if _contains_any(normalized, hints):
            keywords.append(canonical)

    for canonical, hints in STYLE_HINTS.items():
        if _contains_any(normalized, hints):
            keywords.append(canonical)

    # Lấy cụm sau các động từ tìm kiếm nếu có.
    search_match = re.search(
        r"(tim|xem|co|muon|can|mua|kiem)\s+(.{2,80})",
        normalized,
    )
    if search_match:
        phrase = search_match.group(2)
        phrase = re.sub(
            r"\b(cho toi|giup toi|nhe|voi|duoc khong|khong|nao|dep|re|hot|moi)\b",
            " ",
            phrase,
        )
        phrase = re.sub(r"\s+", " ", phrase).strip()
        if 2 <= len(phrase) <= 60:
            keywords.append(phrase)

    # Dedupe giữ thứ tự.
    seen: set[str] = set()
    result: list[str] = []

    for kw in keywords:
        clean = _sanitize_keyword(kw)
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)

    return result[:8]


def _sanitize_keyword(keyword: Any) -> str:
    text = _safe_text(keyword, 80).lower()

    text = text.replace("%", " ").replace(",", " ").replace("(", " ").replace(")", " ")
    text = text.replace(";", " ").replace("*", " ").replace("[", " ").replace("]", " ")
    text = text.replace("{", " ").replace("}", " ").replace(":", " ")
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _sanitize_eq(value: Any, max_len: int = 80) -> str:
    text = _safe_text(value, max_len).upper()
    text = re.sub(r"[^A-Z0-9\-]", "", text)
    return text[:max_len]


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
            or row.get("image_url")
            or PLACEHOLDER_PRODUCT
        ),
        slug=str(row.get("slug") or row.get("id") or ""),
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


def _response(
    reply: str,
    intent: str = "general_chat",
    products: Optional[list[ProductSuggestion]] = None,
    action_data: Optional[dict[str, Any]] = None,
) -> dict:
    return _model_to_dict(ChatResponse(
        reply=_clean_reply(reply, 1000),
        intent=intent if intent in VALID_INTENTS else "general_chat",
        products=products or [],
        action_data=action_data or {},
    ))


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
        "XL": {"max_h": 188, "max_w": 90},
        "XXL": {"max_h": 205, "max_w": 115},
    }

    @classmethod
    def _cleanup_memory(cls) -> None:
        now = time.time()

        expired = [
            sid
            for sid, last_seen in list(SESSION_LAST_SEEN.items())
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
            return _response(
                reply="Bạn vui lòng nhập nội dung cần hỗ trợ nhé.",
                intent="error",
            )

        cls.save_to_memory(sid, "user", user_message)

        try:
            ai_data = cls._extract_intent_with_gemini(sid, user_message)
        except Exception as e:
            logger.warning("[ChatService] Gemini intent lỗi, dùng fallback local: %s", e)
            ai_data = cls._extract_intent_locally(user_message)

        ai_data = cls._enrich_intent_from_message(ai_data, user_message)

        response_data = ChatResponse(
            reply=_clean_reply(ai_data.reply or ""),
            intent=ai_data.intent if ai_data.intent in VALID_INTENTS else "general_chat",
            products=[],
            action_data={},
        )

        try:
            response_data = cls._handle_intent(
                ai_data=ai_data,
                response_data=response_data,
                original_message=user_message,
                session_id=sid,
            )
        except Exception as e:
            logger.error("[ChatService] Lỗi xử lý intent: %s", e, exc_info=True)
            response_data = ChatResponse(
                reply="Hệ thống đang xử lý chưa ổn định. Bạn thử lại sau ít phút nhé.",
                intent="error",
                products=[],
                action_data={},
            )

        response_data.reply = _clean_reply(response_data.reply, 1000)
        cls.save_to_memory(sid, "assistant", response_data.reply)

        return _model_to_dict(response_data)

    # ═══════════════════════════════════════════════════════════
    # INTENT EXTRACTION
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def _extract_intent_with_gemini(cls, session_id: str, message: str) -> ExtractedIntent:
        if not client or not types:
            raise RuntimeError("Gemini client chưa được cấu hình.")

        history = cls.get_history(session_id)

        chat_context = ""
        for item in history[-MAX_MESSAGES_PER_SESSION:-1]:
            speaker = "Khách" if item["role"] == "user" else "GUAMAISON Stylist"
            chat_context += f"{speaker}: {item['content']}\n"

        system_prompt = f"""
Bạn là GUAMAISON Stylist, trợ lý ảo cho website bán thời trang GUAMAISON.

Quy tắc trả lời:
- Luôn trả lời bằng tiếng Việt, tự nhiên, lịch sự, chuyên nghiệp.
- Không tự nhận là con người. Bạn là trợ lý ảo / AI Stylist của GUAMAISON.
- Trả lời ngắn gọn nhưng đủ ý, ưu tiên hỗ trợ khách mua hàng.
- Không bịa chính sách quá chi tiết. Nếu chưa chắc, hướng khách liên hệ GUAMAISON.
- Không dùng markdown phức tạp, không dùng HTML.
- Nếu khách hỏi ngoài thời trang/shop, vẫn có thể trả lời ngắn gọn nếu an toàn, rồi gợi ý quay lại nhu cầu mua sắm.
- Nếu câu hỏi cần dữ liệu sản phẩm, hãy phân loại search_product hoặc outfit_suggestion.

Intent hợp lệ:
- general_chat: Chào hỏi, hỏi chung, hỏi mở, tư vấn chung.
- search_product: Khách muốn tìm/xem/mua sản phẩm.
- outfit_suggestion: Khách muốn phối đồ, mặc gì, set đồ, đi chơi/đi làm/hẹn hò.
- size_advice: Khách hỏi size, số đo, chiều cao/cân nặng.
- order_tracking: Khách hỏi đơn hàng, mã đơn, số điện thoại, giao tới đâu.
- policy_info: Hỏi đổi trả, vận chuyển, thanh toán, bảo quản, chất liệu, liên hệ.
- promotion_info: Hỏi sale, voucher, ưu đãi, mã giảm giá.
- error: Tin nhắn không hợp lệ.

Yêu cầu JSON:
- reply: câu trả lời ngắn gọn, không HTML.
- intent: một trong các intent trên.
- keywords: từ khóa sản phẩm đã chuẩn hóa nếu có, ví dụ ["áo thun", "quần jean", "đen"].
- is_general_request: true nếu khách chỉ hỏi chung như "cho xem đồ mới", "shop có gì hot".
- height, weight: số nguyên nếu trích xuất được.
- phone, order_code: nếu trích xuất được.
"""

        prompt = (
            f"Lịch sử trò chuyện:\n{chat_context or 'Chưa có.'}\n\n"
            f"Tin nhắn mới của khách: {message}\n\n"
            "Hãy phân tích intent và trả JSON đúng schema."
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=ExtractedIntent,
                temperature=GEMINI_TEMPERATURE,
            ),
        )

        parsed = getattr(response, "parsed", None)

        if isinstance(parsed, ExtractedIntent):
            return parsed

        if isinstance(parsed, dict):
            return ExtractedIntent(**parsed)

        raise RuntimeError("Gemini trả về response.parsed không hợp lệ.")

    @classmethod
    def _extract_intent_locally(cls, message: str) -> ExtractedIntent:
        normalized = _normalize(message)

        phone = _extract_phone(message)
        order_code = _extract_order_code(message)
        height, weight = _extract_height_weight(message)

        if _contains_any(normalized, ["size", "sai", "cao", "nang", "kg", "cm", "vua", "mac co", "fit"]):
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

        if phone or order_code or _contains_any(
            normalized,
            ["don hang", "ma don", "tra don", "kiem tra don", "giao toi dau", "van don", "tracking"],
        ):
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

        if _contains_any(normalized, FAQ_KEYWORDS["return"] + FAQ_KEYWORDS["shipping"] + FAQ_KEYWORDS["payment"] + FAQ_KEYWORDS["contact"] + FAQ_KEYWORDS["care"] + FAQ_KEYWORDS["material"] + FAQ_KEYWORDS["buying"]):
            return ExtractedIntent(
                reply=cls._answer_faq_locally(message),
                intent="policy_info",
                keywords=[],
                is_general_request=False,
            )

        if _contains_any(normalized, ["khuyen mai", "voucher", "giam gia", "ma giam", "sale", "uu dai", "discount"]):
            return ExtractedIntent(
                reply="Mình kiểm tra ưu đãi phù hợp cho bạn nhé.",
                intent="promotion_info",
                keywords=[],
                is_general_request=False,
            )

        if _contains_any(normalized, ["phoi", "set do", "outfit", "mac gi", "mix", "di choi", "di lam", "hen ho", "du tiec"]):
            keywords = _extract_keywords_locally(message)
            return ExtractedIntent(
                reply="Mình gợi ý một set đồ phù hợp với phong cách GUAMAISON cho bạn nhé.",
                intent="outfit_suggestion",
                keywords=keywords,
                is_general_request=False,
            )

        keywords = _extract_keywords_locally(message)
        is_general = _contains_any(normalized, GENERAL_KEYWORDS)

        if keywords or is_general or _contains_any(normalized, ["xem", "tim", "co", "mau", "mua", "san pham"]):
            return ExtractedIntent(
                reply="Mình gửi bạn một vài sản phẩm phù hợp nhé.",
                intent="search_product",
                keywords=keywords,
                is_general_request=is_general or not keywords,
            )

        return ExtractedIntent(
            reply=cls._answer_general_locally(message),
            intent="general_chat",
            keywords=[],
            is_general_request=False,
        )

    @classmethod
    def _enrich_intent_from_message(cls, ai_data: ExtractedIntent, message: str) -> ExtractedIntent:
        normalized = _normalize(message)

        phone = ai_data.phone or _extract_phone(message)
        order_code = ai_data.order_code or _extract_order_code(message)
        height, weight = _extract_height_weight(message)

        if not ai_data.height and height:
            ai_data.height = height

        if not ai_data.weight and weight:
            ai_data.weight = weight

        if not ai_data.phone and phone:
            ai_data.phone = phone

        if not ai_data.order_code and order_code:
            ai_data.order_code = order_code

        local_keywords = _extract_keywords_locally(message)

        merged_keywords: list[str] = []
        for kw in list(ai_data.keywords or []) + local_keywords:
            clean = _sanitize_keyword(kw)
            if clean and clean not in merged_keywords:
                merged_keywords.append(clean)

        ai_data.keywords = merged_keywords[:8]

        if ai_data.intent == "general_chat":
            if phone or order_code:
                ai_data.intent = "order_tracking"
            elif _contains_any(normalized, ["size", "kg", "cm", "cao", "nang", "mac co"]):
                ai_data.intent = "size_advice"
            elif _contains_any(normalized, ["phoi", "outfit", "set do", "mac gi"]):
                ai_data.intent = "outfit_suggestion"
            elif local_keywords or _contains_any(normalized, ["tim", "xem", "mua", "co mau", "san pham"]):
                ai_data.intent = "search_product"
                ai_data.is_general_request = not bool(local_keywords)
            elif _contains_any(normalized, ["ship", "doi tra", "bao hanh", "thanh toan", "lien he", "chat lieu", "bao quan"]):
                ai_data.intent = "policy_info"

        return ai_data

    # ═══════════════════════════════════════════════════════════
    # INTENT HANDLERS
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def _handle_intent(
        cls,
        ai_data: ExtractedIntent,
        response_data: ChatResponse,
        original_message: str,
        session_id: str,
    ) -> ChatResponse:
        intent = response_data.intent

        if intent == "outfit_suggestion":
            return cls._fetch_outfit_from_db(ai_data, response_data)

        if intent == "size_advice":
            return cls._handle_size_advice(ai_data, response_data)

        if intent == "search_product":
            price_range = _extract_price_range(original_message)

            response_data = cls._fetch_products_from_db(
                keywords=ai_data.keywords or [],
                is_general=bool(ai_data.is_general_request),
                response_data=response_data,
                price_range=price_range,
            )

            if price_range.get("min_price") or price_range.get("max_price"):
                response_data.action_data["price_filter"] = price_range

            return response_data

        if intent == "order_tracking":
            return cls._handle_order_tracking(
                phone=ai_data.phone,
                order_code=ai_data.order_code,
                response_data=response_data,
            )

        if intent == "policy_info":
            response_data.reply = cls._answer_faq_locally(original_message)
            return response_data

        if intent == "promotion_info":
            response_data.reply = PROMOTION_REPLY
            return response_data

        response_data.reply = cls._answer_general_chat(
            session_id=session_id,
            message=original_message,
            fallback=response_data.reply,
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
                "Để tư vấn size chuẩn hơn, bạn cho GUAMAISON xin chiều cao và cân nặng nhé. "
                "Ví dụ: mình cao 170cm nặng 60kg."
            )
            response_data.action_data = {}
            return response_data

        rec_size = "XXL"

        for size, limits in cls.SIZE_CHART.items():
            if int(height) <= limits["max_h"] and int(weight) <= limits["max_w"]:
                rec_size = size
                break

        response_data.reply = (
            f"Với chiều cao {height}cm và cân nặng {weight}kg, GUAMAISON gợi ý bạn chọn size {rec_size}. "
            "Nếu bạn thích mặc rộng thoải mái hơn, có thể cân nhắc tăng thêm 1 size."
        )

        response_data.action_data = {
            "height": height,
            "weight": weight,
            "recommended_size": rec_size,
        }

        return response_data

    # ═══════════════════════════════════════════════════════════
    # GENERAL / FAQ ANSWERS
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def _answer_general_chat(cls, session_id: str, message: str, fallback: str = "") -> str:
        if client and types:
            try:
                return cls._answer_general_with_gemini(session_id, message)
            except Exception as e:
                logger.warning("[ChatService] Gemini general answer lỗi: %s", e)

        return fallback or cls._answer_general_locally(message)

    @classmethod
    def _answer_general_with_gemini(cls, session_id: str, message: str) -> str:
        history = cls.get_history(session_id)

        chat_context = ""
        for item in history[-MAX_MESSAGES_PER_SESSION:]:
            speaker = "Khách" if item["role"] == "user" else "GUAMAISON Stylist"
            chat_context += f"{speaker}: {item['content']}\n"

        system_prompt = f"""
Bạn là AI Stylist của GUAMAISON, website bán thời trang.

Hãy trả lời câu hỏi của khách:
- Tiếng Việt tự nhiên, lịch sự, chuyên nghiệp.
- Không HTML, không markdown dài.
- Không bịa thông tin nhạy cảm như địa chỉ cụ thể, tồn kho cụ thể, giá cụ thể nếu không có dữ liệu.
- Nếu khách hỏi ngoài phạm vi thời trang/shop, có thể trả lời ngắn gọn nếu an toàn, sau đó nhẹ nhàng gợi ý quay lại nhu cầu mua sắm/thời trang.
- Độ dài tối đa 4 câu.
"""

        prompt = (
            f"Lịch sử:\n{chat_context or 'Chưa có.'}\n\n"
            f"Câu hỏi hiện tại: {message}\n\n"
            "Trả lời ngắn gọn, hữu ích."
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.55,
            ),
        )

        text = getattr(response, "text", "") or ""
        return _clean_reply(text or "Mình đã nhận được câu hỏi của bạn. GUAMAISON có thể hỗ trợ thêm về sản phẩm, size hoặc phối đồ nhé.", 900)

    @classmethod
    def _answer_general_locally(cls, message: str) -> str:
        normalized = _normalize(message)

        if _contains_any(normalized, ["chao", "hello", "hi", "alo", "hey"]):
            return "Chào bạn, GUAMAISON Stylist sẵn sàng hỗ trợ bạn tìm sản phẩm, chọn size, phối đồ hoặc kiểm tra đơn hàng."

        if _contains_any(normalized, ["cam on", "thanks", "thank you", "ok", "oke"]):
            return "GUAMAISON rất vui được hỗ trợ bạn. Bạn cần xem thêm sản phẩm, tư vấn size hay phối đồ không?"

        if _contains_any(normalized, FAQ_KEYWORDS["brand"]):
            return (
                "GUAMAISON là cửa hàng thời trang theo phong cách tối giản, hiện đại và dễ ứng dụng mỗi ngày. "
                "Mình có thể giúp bạn tìm sản phẩm, gợi ý outfit hoặc chọn size phù hợp."
            )

        if _contains_any(normalized, ["ban la ai", "ai vay", "bot", "stylist"]):
            return "Mình là GUAMAISON Stylist, trợ lý ảo hỗ trợ bạn tìm sản phẩm, chọn size, phối đồ và kiểm tra thông tin đơn hàng."

        return (
            "Mình có thể hỗ trợ bạn về sản phẩm, size, phối đồ, đơn hàng, vận chuyển, đổi trả hoặc ưu đãi. "
            "Bạn mô tả nhu cầu cụ thể hơn một chút, mình sẽ tư vấn sát hơn nhé."
        )

    @classmethod
    def _answer_faq_locally(cls, message: str) -> str:
        normalized = _normalize(message)

        if _contains_any(normalized, FAQ_KEYWORDS["payment"]):
            return (
                "GUAMAISON hỗ trợ các hình thức thanh toán tùy cấu hình website, thường gồm thanh toán khi nhận hàng hoặc thanh toán online. "
                "Bạn có thể kiểm tra phương thức khả dụng ở bước thanh toán trước khi xác nhận đơn."
            )

        if _contains_any(normalized, FAQ_KEYWORDS["shipping"]):
            return (
                "Thời gian giao hàng thường từ 2–5 ngày tùy khu vực. "
                "Phí vận chuyển và ưu đãi freeship sẽ hiển thị ở bước thanh toán nếu chương trình đang áp dụng."
            )

        if _contains_any(normalized, FAQ_KEYWORDS["return"]):
            return (
                "GUAMAISON hỗ trợ đổi/trả trong 7 ngày nếu sản phẩm còn nguyên tem, chưa qua sử dụng và chưa giặt. "
                "Với lỗi sản phẩm hoặc đổi size, bạn nên liên hệ sớm kèm mã đơn để được kiểm tra nhanh."
            )

        if _contains_any(normalized, FAQ_KEYWORDS["contact"]):
            return (
                "Bạn có thể liên hệ GUAMAISON qua trang Liên hệ, fanpage hoặc email hỗ trợ của shop. "
                "Nếu cần kiểm tra đơn hàng, bạn gửi giúp mình mã đơn hoặc số điện thoại đặt hàng nhé."
            )

        if _contains_any(normalized, FAQ_KEYWORDS["care"]):
            return (
                "Để giữ form và màu sản phẩm tốt hơn, bạn nên giặt nhẹ, lộn trái khi giặt, tránh ngâm lâu, tránh sấy nhiệt cao và ủi ở mức nhiệt phù hợp với chất liệu."
            )

        if _contains_any(normalized, FAQ_KEYWORDS["material"]):
            return (
                "Chất liệu có thể khác nhau theo từng sản phẩm. Bạn mở trang chi tiết sản phẩm để xem mô tả chất liệu, hoặc gửi tên sản phẩm để mình hỗ trợ kiểm tra phù hợp hơn."
            )

        if _contains_any(normalized, FAQ_KEYWORDS["buying"]):
            return (
                "Bạn chọn sản phẩm, chọn size/màu nếu có, thêm vào giỏ hàng rồi tiến hành thanh toán. "
                "Nếu chưa chắc size, bạn gửi chiều cao và cân nặng để mình tư vấn trước nhé."
            )

        return POLICY_REPLY

    # ═══════════════════════════════════════════════════════════
    # DATABASE HELPERS
    # ═══════════════════════════════════════════════════════════

    @classmethod
    def _base_product_query(cls):
        db = get_supabase()

        return (
            db.table("products")
            .select("id, name, price, thumbnail_url, slug, description, search_keywords, created_at")
            .eq("is_active", True)
            .is_("deleted_at", "null")
        )

    @classmethod
    def _base_product_query_safe(cls):
        db = get_supabase()

        return (
            db.table("products")
            .select("id, name, price, thumbnail_url, slug, created_at")
            .eq("is_active", True)
            .is_("deleted_at", "null")
        )

    @classmethod
    def _fetch_latest_products(cls, limit: int = 4) -> list[dict[str, Any]]:
        try:
            res = (
                cls._base_product_query_safe()
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            return res.data or []

        except Exception as e:
            logger.error("[ChatService] Lỗi lấy sản phẩm mới: %s", e, exc_info=True)
            return []

    @classmethod
    def _apply_price_filter(cls, rows: list[dict[str, Any]], price_range: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
        if not price_range:
            return rows

        min_price = price_range.get("min_price")
        max_price = price_range.get("max_price")

        if not min_price and not max_price:
            return rows

        filtered: list[dict[str, Any]] = []

        for row in rows:
            price = _safe_price_number(row.get("price"))

            if min_price and price < float(min_price):
                continue

            if max_price and price > float(max_price):
                continue

            filtered.append(row)

        return filtered

    @classmethod
    def _search_products_by_keywords(
        cls,
        keywords: list[str],
        limit: int = 4,
        price_range: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        clean_keywords = [_sanitize_keyword(k) for k in keywords if _sanitize_keyword(k)]
        clean_keywords = clean_keywords[:8]

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
                .limit(max(limit * 2, 8))
                .execute()
            )

            rows = _dedupe_products(res.data or [])
            rows = cls._apply_price_filter(rows, price_range)

            return rows[:limit]

        except Exception as e:
            logger.warning("[ChatService] Search mở rộng lỗi, fallback name-only: %s", e)

            collected: list[dict[str, Any]] = []

            for kw in clean_keywords:
                try:
                    res = (
                        cls._base_product_query_safe()
                        .ilike("name", f"%{kw}%")
                        .order("created_at", desc=True)
                        .limit(limit)
                        .execute()
                    )
                    collected.extend(res.data or [])
                except Exception:
                    continue

            rows = _dedupe_products(collected)
            rows = cls._apply_price_filter(rows, price_range)

            return rows[:limit]

    @classmethod
    def _fetch_products_from_db(
        cls,
        keywords: list[str],
        is_general: bool,
        response_data: ChatResponse,
        price_range: Optional[dict[str, Any]] = None,
    ) -> ChatResponse:
        products_data: list[dict[str, Any]] = []

        if is_general:
            products_data = cls._fetch_latest_products(limit=4)
            response_data.reply = "GUAMAISON gửi bạn một vài thiết kế mới nhất đang có trên web nhé."
        else:
            products_data = cls._search_products_by_keywords(
                keywords=keywords,
                limit=4,
                price_range=price_range,
            )

        if not products_data:
            products_data = cls._fetch_latest_products(limit=4)

            if products_data:
                response_data.reply = (
                    "Mẫu bạn tìm hiện chưa có kết quả khớp hoàn toàn. "
                    "GUAMAISON gợi ý bạn một vài thiết kế mới nhất để tham khảo nhé."
                )
            else:
                response_data.reply = (
                    "Hiện hệ thống chưa tìm thấy sản phẩm phù hợp. "
                    "Bạn mô tả rõ hơn như loại áo/quần, màu sắc, mức giá hoặc phong cách mong muốn nhé."
                )

        response_data.products = [
            _product_suggestion_from_row(row)
            for row in products_data[:4]
        ]

        response_data.action_data = {
            "keywords": keywords[:8],
            "is_general_request": bool(is_general),
        }

        return response_data

    @classmethod
    def _fetch_outfit_from_db(
        cls,
        ai_data: ExtractedIntent,
        response_data: ChatResponse,
    ) -> ChatResponse:
        try:
            style_keywords = ai_data.keywords or []

            top_keywords = _dedupe_text(OUTFIT_TOP_KEYWORDS + style_keywords)
            bottom_keywords = _dedupe_text(OUTFIT_BOTTOM_KEYWORDS + style_keywords)

            top_items = cls._search_products_by_keywords(top_keywords, limit=2)
            bottom_items = cls._search_products_by_keywords(bottom_keywords, limit=2)

            outfit_items = _dedupe_products(top_items + bottom_items)

            if len(outfit_items) < 2:
                latest = cls._fetch_latest_products(limit=4)
                outfit_items = _dedupe_products(outfit_items + latest)

            if len(outfit_items) >= 2:
                response_data.reply = (
                    "GUAMAISON gợi ý bạn một set đồ dễ mặc nhưng vẫn có điểm nhấn. "
                    "Bạn có thể phối một item phần trên với một item phần dưới để tạo tổng thể gọn, hiện đại và dễ ứng dụng."
                )

                response_data.products = [
                    _product_suggestion_from_row(row)
                    for row in outfit_items[:4]
                ]

                response_data.action_data = {
                    "style_keywords": style_keywords[:8],
                }

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
                "Bạn cho GUAMAISON xin số điện thoại đặt hàng hoặc mã đơn hàng để mình kiểm tra nhé."
            )
            return response_data

        db = get_supabase()

        try:
            query = db.table("orders").select(
                "id, order_number, code, status, total_amount, created_at, customer_phone, phone"
            )

            if order_code:
                code = _sanitize_eq(order_code)

                if not code:
                    response_data.reply = "Mã đơn hàng chưa hợp lệ. Bạn kiểm tra lại mã đơn giúp mình nhé."
                    return response_data

                try:
                    query = query.or_(
                        f"order_number.eq.{code},code.eq.{code},id.eq.{code}"
                    )
                except Exception:
                    query = db.table("orders").select(
                        "id, order_number, code, status, total_amount, created_at, customer_phone, phone"
                    ).eq("id", code)

            elif phone:
                clean_phone = re.sub(r"[^\d]", "", phone)
                query = query.or_(
                    f"customer_phone.eq.{clean_phone},phone.eq.{clean_phone}"
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
                f"GUAMAISON đã kiểm tra đơn {order_display}. "
                f"Trạng thái hiện tại: {status_text}. "
                f"Tổng tiền: {total_fmt}."
            )

            response_data.action_data = {
                "order_id": order.get("id"),
                "order_code": order_display,
                "status": order.get("status"),
                "status_text": status_text,
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


def _dedupe_text(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        clean = _sanitize_keyword(item)
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)

    return result