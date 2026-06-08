"""
app/schemas/chat_schema.py
===========================
Schema dữ liệu cho MMESTLINE AI Chatbot.
Tương thích Pydantic v1/v2.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(
        default="anonymous_session",
        description="ID phiên chat để AI quản lý context hội thoại."
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1200,
        description="Tin nhắn người dùng gửi lên."
    )


class ProductSuggestion(BaseModel):
    id: str
    name: str
    price: str
    thumbnail_url: str
    slug: str


class ChatResponse(BaseModel):
    reply: str = Field(
        ...,
        description="Câu trả lời hiển thị cho người dùng."
    )
    intent: str = Field(
        default="general_chat",
        description="Intent: general_chat, search_product, size_advice, outfit_suggestion, order_tracking, policy_info, promotion_info, error."
    )
    products: List[ProductSuggestion] = Field(
        default_factory=list,
        description="Danh sách sản phẩm gợi ý."
    )
    action_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dữ liệu bổ sung như size, chiều cao/cân nặng, đơn hàng."
    )


class ExtractedIntent(BaseModel):
    reply: str = Field(
        default="Mình có thể hỗ trợ bạn tìm sản phẩm, chọn size hoặc gợi ý phối đồ."
    )

    intent: str = Field(
        default="general_chat",
        description="general_chat, search_product, size_advice, order_tracking, policy_info, promotion_info, outfit_suggestion"
    )

    keywords: List[str] = Field(
        default_factory=list,
        description="Từ khóa sản phẩm đã được chuẩn hóa."
    )

    is_general_request: bool = Field(
        default=False,
        description="True nếu khách hỏi chung chung như xem đồ mới, mẫu hot."
    )

    height: Optional[int] = None
    weight: Optional[int] = None
    phone: Optional[str] = None
    order_code: Optional[str] = None