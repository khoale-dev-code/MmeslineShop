"""
app/schemas/chat_schema.py
===========================
Schema dữ liệu cho GUAMAISON AI Chatbot.

Tương thích Pydantic v1/v2.

Mục tiêu:
- Giữ response cố định cho frontend chat.html:
  {
    reply: str,
    intent: str,
    products: [],
    action_data: {}
  }

- Hỗ trợ Gemini phân tích câu hỏi linh hoạt hơn:
  + Tìm sản phẩm
  + Tư vấn size
  + Phối đồ
  + Tra cứu đơn hàng
  + Chính sách
  + Khuyến mãi
  + Câu hỏi mở / hỏi chung
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict, field_validator

    PYDANTIC_V2 = True
except Exception:
    from pydantic import validator

    ConfigDict = None
    PYDANTIC_V2 = False


# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

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

PLACEHOLDER_PRODUCT_IMAGE = "https://placehold.co/300x400/fef9ed/010101?text=GUAMAISON"


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _clean_text(value: Any, default: str = "", max_len: int = 1200) -> str:
    text = str(value or default).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_len]


def _clean_phone(value: Any) -> Optional[str]:
    if not value:
        return None

    phone = re.sub(r"[^\d]", "", str(value))

    if re.match(r"^0\d{9,10}$", phone):
        return phone

    return None


def _clean_order_code(value: Any) -> Optional[str]:
    if not value:
        return None

    text = str(value).strip().upper()
    text = re.sub(r"[^A-Z0-9\-]", "", text)

    return text[:40] if text else None


def _safe_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None

    try:
        return int(float(value))
    except Exception:
        return None


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None

    try:
        number = float(value)
        return number if number >= 0 else None
    except Exception:
        return None


def _clean_keywords(value: Any, max_items: int = 10) -> List[str]:
    if not value:
        return []

    if isinstance(value, str):
        raw_items = [value]
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = list(value) if hasattr(value, "__iter__") else []

    result: List[str] = []
    seen = set()

    for item in raw_items:
        text = _clean_text(item, max_len=80).lower()

        text = text.replace("%", " ")
        text = text.replace(",", " ")
        text = text.replace("(", " ")
        text = text.replace(")", " ")
        text = text.replace("[", " ")
        text = text.replace("]", " ")
        text = text.replace("{", " ")
        text = text.replace("}", " ")
        text = text.replace(";", " ")
        text = text.replace("*", " ")

        text = re.sub(r"\s+", " ", text).strip()

        if not text or text in seen:
            continue

        seen.add(text)
        result.append(text)

        if len(result) >= max_items:
            break

    return result


def _normalize_intent(value: Any) -> str:
    intent = _clean_text(value, default="general_chat", max_len=60).lower()

    if intent not in VALID_INTENTS:
        return "general_chat"

    return intent


# ═══════════════════════════════════════════════════════════════
# BASE MODEL
# ═══════════════════════════════════════════════════════════════

class CompatBaseModel(BaseModel):
    """
    BaseModel dùng chung để tương thích Pydantic v1/v2.
    - extra='ignore': Gemini hoặc frontend gửi dư field cũng không làm crash.
    - strip whitespace: tự cắt khoảng trắng cơ bản.
    """

    if PYDANTIC_V2:
        model_config = ConfigDict(
            extra="ignore",
            populate_by_name=True,
            str_strip_whitespace=True,
        )
    else:
        class Config:
            extra = "ignore"
            allow_population_by_field_name = True
            anystr_strip_whitespace = True


# ═══════════════════════════════════════════════════════════════
# REQUEST SCHEMA
# ═══════════════════════════════════════════════════════════════

class ChatRequest(CompatBaseModel):
    session_id: str = Field(
        default="anonymous_session",
        description="ID phiên chat để AI quản lý context hội thoại.",
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=1200,
        description="Tin nhắn người dùng gửi lên.",
    )

    if PYDANTIC_V2:
        @field_validator("session_id", mode="before")
        @classmethod
        def validate_session_id(cls, value: Any) -> str:
            session_id = _clean_text(value, default="anonymous_session", max_len=120)
            return session_id or "anonymous_session"

        @field_validator("message", mode="before")
        @classmethod
        def validate_message(cls, value: Any) -> str:
            message = _clean_text(value, max_len=1200)
            if not message:
                raise ValueError("Tin nhắn không được để trống.")
            return message

    else:
        @validator("session_id", pre=True, always=True)
        def validate_session_id(cls, value: Any) -> str:
            session_id = _clean_text(value, default="anonymous_session", max_len=120)
            return session_id or "anonymous_session"

        @validator("message", pre=True)
        def validate_message(cls, value: Any) -> str:
            message = _clean_text(value, max_len=1200)
            if not message:
                raise ValueError("Tin nhắn không được để trống.")
            return message


# ═══════════════════════════════════════════════════════════════
# PRODUCT SCHEMA
# ═══════════════════════════════════════════════════════════════

class ProductSuggestion(CompatBaseModel):
    id: str = Field(
        default="",
        description="ID sản phẩm.",
    )

    name: str = Field(
        default="Sản phẩm GUAMAISON",
        description="Tên sản phẩm.",
    )

    price: str = Field(
        default="Liên hệ",
        description="Giá đã format để hiển thị.",
    )

    thumbnail_url: str = Field(
        default=PLACEHOLDER_PRODUCT_IMAGE,
        description="Ảnh đại diện sản phẩm.",
    )

    slug: str = Field(
        default="",
        description="Slug sản phẩm để frontend link tới /product/<slug>.",
    )

    # Field mở rộng, không bắt buộc frontend dùng.
    category: Optional[str] = Field(
        default=None,
        description="Danh mục sản phẩm nếu có.",
    )

    color: Optional[str] = Field(
        default=None,
        description="Màu sản phẩm nếu có.",
    )

    stock_status: Optional[str] = Field(
        default=None,
        description="Trạng thái tồn kho nếu có.",
    )

    if PYDANTIC_V2:
        @field_validator("id", "name", "price", "thumbnail_url", "slug", mode="before")
        @classmethod
        def validate_product_text(cls, value: Any) -> str:
            return _clean_text(value, max_len=300)

        @field_validator("thumbnail_url", mode="after")
        @classmethod
        def validate_thumbnail_url(cls, value: str) -> str:
            return value or PLACEHOLDER_PRODUCT_IMAGE

        @field_validator("name", mode="after")
        @classmethod
        def validate_name(cls, value: str) -> str:
            return value or "Sản phẩm GUAMAISON"

        @field_validator("price", mode="after")
        @classmethod
        def validate_price(cls, value: str) -> str:
            return value or "Liên hệ"

    else:
        @validator("id", "name", "price", "thumbnail_url", "slug", pre=True)
        def validate_product_text(cls, value: Any) -> str:
            return _clean_text(value, max_len=300)

        @validator("thumbnail_url", always=True)
        def validate_thumbnail_url(cls, value: str) -> str:
            return value or PLACEHOLDER_PRODUCT_IMAGE

        @validator("name", always=True)
        def validate_name(cls, value: str) -> str:
            return value or "Sản phẩm GUAMAISON"

        @validator("price", always=True)
        def validate_price(cls, value: str) -> str:
            return value or "Liên hệ"


# ═══════════════════════════════════════════════════════════════
# RESPONSE SCHEMA
# ═══════════════════════════════════════════════════════════════

class ChatResponse(CompatBaseModel):
    reply: str = Field(
        ...,
        description="Câu trả lời hiển thị cho người dùng.",
    )

    intent: str = Field(
        default="general_chat",
        description=(
            "Intent: general_chat, search_product, size_advice, "
            "outfit_suggestion, order_tracking, policy_info, promotion_info, error."
        ),
    )

    products: List[ProductSuggestion] = Field(
        default_factory=list,
        description="Danh sách sản phẩm gợi ý.",
    )

    action_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dữ liệu bổ sung như size, chiều cao/cân nặng, đơn hàng, filter.",
    )

    if PYDANTIC_V2:
        @field_validator("reply", mode="before")
        @classmethod
        def validate_reply(cls, value: Any) -> str:
            reply = _clean_text(value, default="Mình có thể hỗ trợ bạn thêm nhé.", max_len=1500)
            return reply or "Mình có thể hỗ trợ bạn thêm nhé."

        @field_validator("intent", mode="before")
        @classmethod
        def validate_intent(cls, value: Any) -> str:
            return _normalize_intent(value)

    else:
        @validator("reply", pre=True, always=True)
        def validate_reply(cls, value: Any) -> str:
            reply = _clean_text(value, default="Mình có thể hỗ trợ bạn thêm nhé.", max_len=1500)
            return reply or "Mình có thể hỗ trợ bạn thêm nhé."

        @validator("intent", pre=True, always=True)
        def validate_intent(cls, value: Any) -> str:
            return _normalize_intent(value)


# ═══════════════════════════════════════════════════════════════
# GEMINI INTENT SCHEMA
# ═══════════════════════════════════════════════════════════════

class ExtractedIntent(CompatBaseModel):
    """
    Schema Gemini trả về sau khi phân tích tin nhắn khách.

    Field bắt buộc cho chat_service:
    - reply
    - intent
    - keywords
    - is_general_request
    - height
    - weight
    - phone
    - order_code

    Field mở rộng để bot hiểu câu hỏi linh hoạt hơn:
    - category
    - color
    - style
    - occasion
    - size
    - gender
    - topic
    - min_price
    - max_price
    - confidence
    """

    reply: str = Field(
        default="Mình có thể hỗ trợ bạn tìm sản phẩm, chọn size hoặc gợi ý phối đồ.",
        description="Câu trả lời ngắn gọn của AI, không cần HTML.",
    )

    intent: str = Field(
        default="general_chat",
        description=(
            "general_chat, search_product, size_advice, order_tracking, "
            "policy_info, promotion_info, outfit_suggestion, error."
        ),
    )

    keywords: List[str] = Field(
        default_factory=list,
        description="Từ khóa sản phẩm đã được chuẩn hóa, ví dụ: áo thun, quần jean, đen.",
    )

    is_general_request: bool = Field(
        default=False,
        description="True nếu khách hỏi chung như xem đồ mới, mẫu hot, shop có gì.",
    )

    height: Optional[int] = Field(
        default=None,
        description="Chiều cao khách hàng, đơn vị cm.",
    )

    weight: Optional[int] = Field(
        default=None,
        description="Cân nặng khách hàng, đơn vị kg.",
    )

    phone: Optional[str] = Field(
        default=None,
        description="Số điện thoại dùng để tra cứu đơn hàng.",
    )

    order_code: Optional[str] = Field(
        default=None,
        description="Mã đơn hàng dùng để tra cứu đơn.",
    )

    # Field mở rộng cho AI hiểu nhu cầu mua hàng tốt hơn.
    category: Optional[str] = Field(
        default=None,
        description="Loại sản phẩm chính, ví dụ: áo thun, áo khoác, quần jean.",
    )

    color: Optional[str] = Field(
        default=None,
        description="Màu khách quan tâm, ví dụ: đen, trắng, kem.",
    )

    style: Optional[str] = Field(
        default=None,
        description="Phong cách khách muốn, ví dụ: tối giản, streetwear, công sở.",
    )

    occasion: Optional[str] = Field(
        default=None,
        description="Hoàn cảnh sử dụng, ví dụ: đi chơi, đi làm, hẹn hò, dự tiệc.",
    )

    size: Optional[str] = Field(
        default=None,
        description="Size khách hỏi trực tiếp, ví dụ: S, M, L, XL.",
    )

    gender: Optional[str] = Field(
        default=None,
        description="Giới tính/phân khúc nếu khách nói rõ, ví dụ: nam, nữ, unisex.",
    )

    topic: Optional[str] = Field(
        default=None,
        description="Chủ đề FAQ nếu có: shipping, return, payment, care, material, contact, brand.",
    )

    min_price: Optional[float] = Field(
        default=None,
        description="Giá thấp nhất khách muốn tìm.",
    )

    max_price: Optional[float] = Field(
        default=None,
        description="Giá cao nhất khách muốn tìm.",
    )

    confidence: float = Field(
        default=0.75,
        ge=0,
        le=1,
        description="Độ tự tin của AI khi phân loại intent, từ 0 đến 1.",
    )

    if PYDANTIC_V2:
        @field_validator("reply", mode="before")
        @classmethod
        def validate_reply(cls, value: Any) -> str:
            reply = _clean_text(
                value,
                default="Mình có thể hỗ trợ bạn tìm sản phẩm, chọn size hoặc gợi ý phối đồ.",
                max_len=1200,
            )
            return reply or "Mình có thể hỗ trợ bạn tìm sản phẩm, chọn size hoặc gợi ý phối đồ."

        @field_validator("intent", mode="before")
        @classmethod
        def validate_intent(cls, value: Any) -> str:
            return _normalize_intent(value)

        @field_validator("keywords", mode="before")
        @classmethod
        def validate_keywords(cls, value: Any) -> List[str]:
            return _clean_keywords(value, max_items=10)

        @field_validator("height", mode="before")
        @classmethod
        def validate_height(cls, value: Any) -> Optional[int]:
            height = _safe_int(value)
            if height is None:
                return None
            return height if 120 <= height <= 230 else None

        @field_validator("weight", mode="before")
        @classmethod
        def validate_weight(cls, value: Any) -> Optional[int]:
            weight = _safe_int(value)
            if weight is None:
                return None
            return weight if 25 <= weight <= 200 else None

        @field_validator("phone", mode="before")
        @classmethod
        def validate_phone(cls, value: Any) -> Optional[str]:
            return _clean_phone(value)

        @field_validator("order_code", mode="before")
        @classmethod
        def validate_order_code(cls, value: Any) -> Optional[str]:
            return _clean_order_code(value)

        @field_validator(
            "category",
            "color",
            "style",
            "occasion",
            "size",
            "gender",
            "topic",
            mode="before",
        )
        @classmethod
        def validate_optional_text(cls, value: Any) -> Optional[str]:
            text = _clean_text(value, max_len=120)
            return text or None

        @field_validator("min_price", "max_price", mode="before")
        @classmethod
        def validate_price_range(cls, value: Any) -> Optional[float]:
            return _safe_float(value)

    else:
        @validator("reply", pre=True, always=True)
        def validate_reply(cls, value: Any) -> str:
            reply = _clean_text(
                value,
                default="Mình có thể hỗ trợ bạn tìm sản phẩm, chọn size hoặc gợi ý phối đồ.",
                max_len=1200,
            )
            return reply or "Mình có thể hỗ trợ bạn tìm sản phẩm, chọn size hoặc gợi ý phối đồ."

        @validator("intent", pre=True, always=True)
        def validate_intent(cls, value: Any) -> str:
            return _normalize_intent(value)

        @validator("keywords", pre=True, always=True)
        def validate_keywords(cls, value: Any) -> List[str]:
            return _clean_keywords(value, max_items=10)

        @validator("height", pre=True, always=True)
        def validate_height(cls, value: Any) -> Optional[int]:
            height = _safe_int(value)
            if height is None:
                return None
            return height if 120 <= height <= 230 else None

        @validator("weight", pre=True, always=True)
        def validate_weight(cls, value: Any) -> Optional[int]:
            weight = _safe_int(value)
            if weight is None:
                return None
            return weight if 25 <= weight <= 200 else None

        @validator("phone", pre=True, always=True)
        def validate_phone(cls, value: Any) -> Optional[str]:
            return _clean_phone(value)

        @validator("order_code", pre=True, always=True)
        def validate_order_code(cls, value: Any) -> Optional[str]:
            return _clean_order_code(value)

        @validator(
            "category",
            "color",
            "style",
            "occasion",
            "size",
            "gender",
            "topic",
            pre=True,
            always=True,
        )
        def validate_optional_text(cls, value: Any) -> Optional[str]:
            text = _clean_text(value, max_len=120)
            return text or None

        @validator("min_price", "max_price", pre=True, always=True)
        def validate_price_range(cls, value: Any) -> Optional[float]:
            return _safe_float(value)