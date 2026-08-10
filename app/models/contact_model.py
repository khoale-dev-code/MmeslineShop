"""Pure data objects for the GUAMAISON Contact Center."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


DEFAULT_CONTACT_TOPICS = (
    "Hỗ trợ đơn hàng",
    "Tư vấn sản phẩm",
    "Đổi trả / bảo hành",
    "Hợp tác thương mại",
    "Góp ý thương hiệu",
    "Khác",
)


@dataclass(frozen=True)
class ContactPageSettings:
    id: str
    eyebrow: str
    title: str
    accent_text: str
    description: str
    form_eyebrow: str
    form_title: str
    form_description: str
    map_title: str
    address: str
    contact_email: str
    contact_phone: str
    business_hours: str
    response_note: str
    map_embed_url: str
    directions_url: str
    theme: str
    topics: tuple[str, ...]
    updated_at: Optional[str]

    @classmethod
    def defaults(cls) -> "ContactPageSettings":
        return cls(
            id="primary",
            eyebrow="Customer care · GUAMAISON",
            title="Kết nối cùng",
            accent_text="GUAMAISON",
            description=(
                "Cần tư vấn sản phẩm, hỗ trợ đơn hàng hay muốn hợp tác cùng chúng tôi? "
                "Hãy để lại lời nhắn, đội ngũ GUAMAISON sẽ phản hồi sớm nhất."
            ),
            form_eyebrow="Gửi lời nhắn",
            form_title="Chúng tôi luôn lắng nghe.",
            form_description=(
                "Điền thông tin bên dưới. GUAMAISON sẽ liên hệ qua email hoặc số điện thoại bạn cung cấp."
            ),
            map_title="GUAMAISON Studio",
            address="TP. Hồ Chí Minh, Việt Nam",
            contact_email="support@guamaison.vn",
            contact_phone="+84 90 123 4567",
            business_hours="09:00 – 21:00 · Thứ Hai – Chủ Nhật",
            response_note="Phản hồi dự kiến trong vòng 24 giờ làm việc.",
            map_embed_url="",
            directions_url="https://www.google.com/maps",
            theme="ink",
            topics=DEFAULT_CONTACT_TOPICS,
            updated_at=None,
        )

    @classmethod
    def from_record(cls, record: dict[str, Any] | None) -> "ContactPageSettings":
        default = cls.defaults()
        if not record:
            return default
        raw_topics = record.get("topics")
        if isinstance(raw_topics, str):
            raw_topics = raw_topics.splitlines()
        topics = tuple(
            str(item).strip()
            for item in (raw_topics if isinstance(raw_topics, list) else default.topics)
            if str(item).strip()
        ) or default.topics
        return cls(
            id=str(record.get("id") or default.id),
            eyebrow=str(record.get("eyebrow") or default.eyebrow),
            title=str(record.get("title") or default.title),
            accent_text=str(record.get("accent_text") or default.accent_text),
            description=str(record.get("description") or default.description),
            form_eyebrow=str(record.get("form_eyebrow") or default.form_eyebrow),
            form_title=str(record.get("form_title") or default.form_title),
            form_description=str(record.get("form_description") or default.form_description),
            map_title=str(record.get("map_title") or default.map_title),
            address=str(record.get("address") or default.address),
            contact_email=str(record.get("contact_email") or default.contact_email),
            contact_phone=str(record.get("contact_phone") or default.contact_phone),
            business_hours=str(record.get("business_hours") or default.business_hours),
            response_note=str(record.get("response_note") or default.response_note),
            map_embed_url=str(record.get("map_embed_url") or ""),
            directions_url=str(record.get("directions_url") or default.directions_url),
            theme=str(record.get("theme") or default.theme),
            topics=topics,
            updated_at=record.get("updated_at"),
        )


@dataclass(frozen=True)
class ContactMessage:
    id: str
    full_name: str
    email: str
    phone: str
    topic: str
    message: str
    status: str
    is_unread: bool
    admin_note: str
    created_at: Optional[str]
    last_viewed_at: Optional[str]
    replied_at: Optional[str]
    updated_at: Optional[str]

    @classmethod
    def from_record(cls, record: dict[str, Any] | None) -> "ContactMessage | None":
        if not record or not record.get("id"):
            return None
        return cls(
            id=str(record["id"]),
            full_name=str(record.get("full_name") or ""),
            email=str(record.get("email") or ""),
            phone=str(record.get("phone") or ""),
            topic=str(record.get("topic") or "Khác"),
            message=str(record.get("message") or ""),
            status=str(record.get("status") or "new"),
            is_unread=bool(record.get("is_unread")),
            admin_note=str(record.get("admin_note") or ""),
            created_at=record.get("created_at"),
            last_viewed_at=record.get("last_viewed_at"),
            replied_at=record.get("replied_at"),
            updated_at=record.get("updated_at"),
        )


@dataclass(frozen=True)
class ContactReply:
    id: str
    contact_message_id: str
    admin_user_id: Optional[str]
    subject: str
    body_text: str
    status: str
    error_message: Optional[str]
    created_at: Optional[str]
    sent_at: Optional[str]

    @classmethod
    def from_record(cls, record: dict[str, Any] | None) -> "ContactReply | None":
        if not record or not record.get("id"):
            return None
        return cls(
            id=str(record["id"]),
            contact_message_id=str(record.get("contact_message_id") or ""),
            admin_user_id=(str(record["admin_user_id"]) if record.get("admin_user_id") else None),
            subject=str(record.get("subject") or ""),
            body_text=str(record.get("body_text") or ""),
            status=str(record.get("status") or "processing"),
            error_message=(str(record["error_message"]) if record.get("error_message") else None),
            created_at=record.get("created_at"),
            sent_at=record.get("sent_at"),
        )


@dataclass(frozen=True)
class ContactMessagePage:
    rows: tuple[ContactMessage, ...]
    page: int
    per_page: int
    total: int
    total_pages: int


@dataclass(frozen=True)
class ContactSubmissionResult:
    code: str
    message_id: Optional[str]
