"""Business rules for the editable GUAMAISON About page."""

from __future__ import annotations

import copy
import logging
import re
from typing import Any
from urllib.parse import urlparse

from app.repositories.content_page_repository import (
    ContentPageConflictError,
    ContentPageRepository,
    ContentPageRepositoryError,
    ContentPageSchemaMissingError,
)

logger = logging.getLogger(__name__)


class AboutPageValidationError(ValueError):
    pass


class AboutPageService:
    SLUG = "about"
    MAX_IMAGE_BYTES = 10 * 1024 * 1024
    ALLOWED_IMAGE_MIMES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/avif",
    }
    SECTION_KEYS = ("hero", "marquee", "story", "gallery", "beliefs", "manifesto")

    DEFAULT_CONTENT: dict[str, Any] = {
        "schema_version": 1,
        "seo": {
            "title": "Về GUAMAISON | Wear Your Identity",
            "description": "Câu chuyện, tinh thần thiết kế và giá trị của GUAMAISON.",
        },
        "section_order": ["hero", "marquee", "story", "gallery", "beliefs", "manifesto"],
        "sections_enabled": {
            "hero": True,
            "marquee": True,
            "story": True,
            "gallery": True,
            "beliefs": True,
            "manifesto": True,
        },
        "hero": {
            "kicker": "About GUAMAISON",
            "title": "Wear\nYour\nIdentity",
            "description": (
                "GUAMAISON được tạo ra cho những người xem thời trang là một phần của bản sắc. "
                "Không ồn ào, không chạy theo số đông — mỗi thiết kế hướng đến sự tự tin, "
                "tính ứng dụng và dấu ấn riêng trong đời sống hằng ngày."
            ),
            "primary_cta": {"label": "Khám phá sản phẩm", "url": "/shop"},
            "secondary_cta": {"label": "Xem bộ sưu tập", "url": "/collections"},
            "primary_image": "https://i.pinimg.com/1200x/b0/4f/33/b04f339093b97588524f7fd2bc2cd40d.jpg",
            "primary_image_alt": "GUAMAISON campaign",
            "secondary_image": "https://i.pinimg.com/736x/0f/0f/b0/0f0fb0303be75a3c300b0e1dda62d467.jpg",
            "secondary_image_alt": "GUAMAISON details",
            "side_note": "Modern essentials\nwith attitude.",
        },
        "marquee": [
            "GUAMAISON",
            "Wear Your Identity",
            "Modern Essentials",
            "Confidence In Motion",
            "Made For Daily Expression",
        ],
        "story": {
            "kicker": "Our Story",
            "title": "Không chỉ là\nquần áo.",
            "body": (
                "Giữa nhịp sống hiện đại, trang phục không còn đơn thuần là thứ để mặc. "
                "Đó là cách bạn bước ra ngoài, giao tiếp với thế giới và khẳng định cá tính. "
                "GUAMAISON chọn hướng đi tối giản nhưng có chiều sâu: form dáng dễ mặc, "
                "chất liệu có chọn lọc và tinh thần thiết kế rõ ràng."
            ),
            "stats": [
                {"number": "01", "label": "Daily Wear"},
                {"number": "02", "label": "Clean Form"},
                {"number": "03", "label": "Identity"},
            ],
        },
        "gallery": [
            {"url": "https://i.pinimg.com/736x/1a/5f/cf/1a5fcf33b42c199589484a8bf3693aed.jpg", "alt": "GUAMAISON look 1"},
            {"url": "https://i.pinimg.com/1200x/05/41/10/05411050c5bd98ac71043fbe7f578f63.jpg", "alt": "GUAMAISON look 2"},
            {"url": "https://i.pinimg.com/736x/2c/64/ca/2c64cacf2aa9a07c931870daa00728e5.jpg", "alt": "GUAMAISON look 3"},
            {"url": "https://i.pinimg.com/1200x/65/55/d7/6555d7de5c7d81c9ec420d5e022ae10d.jpg", "alt": "GUAMAISON look 4"},
        ],
        "beliefs": {
            "kicker": "What We Believe",
            "title": "Phong cách là\nthái độ sống.",
            "body": (
                "GUAMAISON không theo đuổi sự phô trương. Chúng tôi tin vào những thiết kế "
                "đủ tinh tế để mặc mỗi ngày, đủ khác biệt để tạo dấu ấn, và đủ linh hoạt "
                "để đi cùng nhiều phiên bản của chính bạn."
            ),
            "image": "https://i.pinimg.com/1200x/85/52/e2/8552e2196c4fd3140193e4f589c9f018.jpg",
            "image_alt": "GUAMAISON atelier",
            "values": [
                {"number": "01", "title": "Tự tin", "text": "Trang phục phải khiến người mặc cảm thấy chắc chắn, thoải mái và làm chủ hình ảnh của mình."},
                {"number": "02", "title": "Bản sắc", "text": "Mỗi sản phẩm là nền tảng để bạn phối theo cá tính riêng, không bị đóng khung bởi xu hướng."},
                {"number": "03", "title": "Ứng dụng", "text": "Form dáng dễ mặc, dễ phối, phù hợp với nhiều nhịp sống và hoàn cảnh khác nhau."},
                {"number": "04", "title": "Chất lượng", "text": "Chú trọng chất liệu, đường may, độ bền và cảm giác khi mặc thay vì chỉ chạy theo hình ảnh."},
            ],
        },
        "manifesto": {
            "kicker": "GUAMAISON Manifesto",
            "title": "Wear Your\nIdentity",
            "body": "Không chỉ là thời trang. Đó là cách bạn chọn xuất hiện, cảm nhận và kể câu chuyện của mình.",
            "cta": {"label": "Bắt đầu mua sắm", "url": "/shop"},
            "image": "https://i.pinimg.com/1200x/02/76/ef/0276efb152ad7d095805a36cb76758e6.jpg",
            "image_alt": "GUAMAISON closing campaign",
        },
    }

    @staticmethod
    def _text(value: Any, default: str = "", max_length: int = 500, multiline: bool = False) -> str:
        text = str(value if value is not None else default).replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        if multiline:
            text = "\n".join(line.strip() for line in text.split("\n"))
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
        else:
            text = " ".join(text.split())
        return text[:max_length]

    @staticmethod
    def _bool(value: Any, default: bool = True) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def _url(cls, value: Any, default: str = "#", image: bool = False) -> str:
        text = cls._text(value, default, 1500)
        lowered = text.lower().replace("\n", "").replace("\r", "")
        if lowered.startswith(("javascript:", "data:", "vbscript:")):
            return default
        if text.startswith("/"):
            return text
        parsed = urlparse(text)
        if image:
            return text if parsed.scheme in {"http", "https"} and parsed.netloc else default
        if text.startswith(("#", "?")):
            return text
        return text if parsed.scheme in {"http", "https", "mailto", "tel"} else default

    @classmethod
    def _cta(cls, raw: Any, default: dict[str, str]) -> dict[str, str]:
        raw = raw if isinstance(raw, dict) else {}
        return {
            "label": cls._text(raw.get("label"), default["label"], 80),
            "url": cls._url(raw.get("url"), default["url"]),
        }

    @classmethod
    def normalize(cls, raw: Any) -> dict[str, Any]:
        source = raw if isinstance(raw, dict) else {}
        default = cls.DEFAULT_CONTENT

        seo = source.get("seo") if isinstance(source.get("seo"), dict) else {}
        hero = source.get("hero") if isinstance(source.get("hero"), dict) else {}
        story = source.get("story") if isinstance(source.get("story"), dict) else {}
        beliefs = source.get("beliefs") if isinstance(source.get("beliefs"), dict) else {}
        manifesto = source.get("manifesto") if isinstance(source.get("manifesto"), dict) else {}

        order = []
        for key in source.get("section_order") or default["section_order"]:
            key = cls._text(key, "", 30).lower()
            if key in cls.SECTION_KEYS and key not in order:
                order.append(key)
        order.extend(key for key in cls.SECTION_KEYS if key not in order)

        enabled_raw = source.get("sections_enabled") if isinstance(source.get("sections_enabled"), dict) else {}
        enabled = {
            key: cls._bool(enabled_raw.get(key), default["sections_enabled"][key])
            for key in cls.SECTION_KEYS
        }

        marquee = []
        for item in (source.get("marquee") if isinstance(source.get("marquee"), list) else default["marquee"]):
            text = cls._text(item, "", 90)
            if text and text not in marquee:
                marquee.append(text)
            if len(marquee) >= 12:
                break

        stats = []
        source_stats = story.get("stats") if isinstance(story.get("stats"), list) else default["story"]["stats"]
        for index, item in enumerate(source_stats[:6]):
            if not isinstance(item, dict):
                continue
            label = cls._text(item.get("label"), "", 80)
            if label:
                stats.append({
                    "number": cls._text(item.get("number"), f"{index + 1:02d}", 12),
                    "label": label,
                })

        gallery = []
        source_gallery = source.get("gallery") if isinstance(source.get("gallery"), list) else default["gallery"]
        for index, item in enumerate(source_gallery[:8]):
            if not isinstance(item, dict):
                continue
            fallback = default["gallery"][index % len(default["gallery"])]
            url = cls._url(item.get("url"), fallback["url"], image=True)
            if url:
                gallery.append({
                    "url": url,
                    "alt": cls._text(item.get("alt"), fallback["alt"], 140),
                })

        values = []
        source_values = beliefs.get("values") if isinstance(beliefs.get("values"), list) else default["beliefs"]["values"]
        for index, item in enumerate(source_values[:8]):
            if not isinstance(item, dict):
                continue
            title = cls._text(item.get("title"), "", 80)
            text = cls._text(item.get("text"), "", 500, multiline=True)
            if title and text:
                values.append({
                    "number": cls._text(item.get("number"), f"{index + 1:02d}", 12),
                    "title": title,
                    "text": text,
                })

        result = {
            "schema_version": 1,
            "seo": {
                "title": cls._text(seo.get("title"), default["seo"]["title"], 120),
                "description": cls._text(seo.get("description"), default["seo"]["description"], 240),
            },
            "section_order": order,
            "sections_enabled": enabled,
            "hero": {
                "kicker": cls._text(hero.get("kicker"), default["hero"]["kicker"], 80),
                "title": cls._text(hero.get("title"), default["hero"]["title"], 180, multiline=True),
                "description": cls._text(hero.get("description"), default["hero"]["description"], 900, multiline=True),
                "primary_cta": cls._cta(hero.get("primary_cta"), default["hero"]["primary_cta"]),
                "secondary_cta": cls._cta(hero.get("secondary_cta"), default["hero"]["secondary_cta"]),
                "primary_image": cls._url(hero.get("primary_image"), default["hero"]["primary_image"], image=True),
                "primary_image_alt": cls._text(hero.get("primary_image_alt"), default["hero"]["primary_image_alt"], 140),
                "secondary_image": cls._url(hero.get("secondary_image"), default["hero"]["secondary_image"], image=True),
                "secondary_image_alt": cls._text(hero.get("secondary_image_alt"), default["hero"]["secondary_image_alt"], 140),
                "side_note": cls._text(hero.get("side_note"), default["hero"]["side_note"], 160, multiline=True),
            },
            "marquee": marquee or list(default["marquee"]),
            "story": {
                "kicker": cls._text(story.get("kicker"), default["story"]["kicker"], 80),
                "title": cls._text(story.get("title"), default["story"]["title"], 180, multiline=True),
                "body": cls._text(story.get("body"), default["story"]["body"], 1200, multiline=True),
                "stats": stats or copy.deepcopy(default["story"]["stats"]),
            },
            "gallery": gallery or copy.deepcopy(default["gallery"]),
            "beliefs": {
                "kicker": cls._text(beliefs.get("kicker"), default["beliefs"]["kicker"], 80),
                "title": cls._text(beliefs.get("title"), default["beliefs"]["title"], 180, multiline=True),
                "body": cls._text(beliefs.get("body"), default["beliefs"]["body"], 1200, multiline=True),
                "image": cls._url(beliefs.get("image"), default["beliefs"]["image"], image=True),
                "image_alt": cls._text(beliefs.get("image_alt"), default["beliefs"]["image_alt"], 140),
                "values": values or copy.deepcopy(default["beliefs"]["values"]),
            },
            "manifesto": {
                "kicker": cls._text(manifesto.get("kicker"), default["manifesto"]["kicker"], 80),
                "title": cls._text(manifesto.get("title"), default["manifesto"]["title"], 180, multiline=True),
                "body": cls._text(manifesto.get("body"), default["manifesto"]["body"], 700, multiline=True),
                "cta": cls._cta(manifesto.get("cta"), default["manifesto"]["cta"]),
                "image": cls._url(manifesto.get("image"), default["manifesto"]["image"], image=True),
                "image_alt": cls._text(manifesto.get("image_alt"), default["manifesto"]["image_alt"], 140),
            },
        }
        return result

    @classmethod
    def get_published(cls) -> dict[str, Any]:
        try:
            page = ContentPageRepository.get_published(cls.SLUG)
            return cls.normalize(page.content if page else cls.DEFAULT_CONTENT)
        except (ContentPageSchemaMissingError, ContentPageRepositoryError) as exc:
            logger.warning("[AboutPageService] Dùng nội dung mặc định: %s", exc)
            return copy.deepcopy(cls.DEFAULT_CONTENT)

    @classmethod
    def get_editor_state(cls, user_id: str | None) -> dict[str, Any]:
        try:
            published = ContentPageRepository.get_published(cls.SLUG)
            draft = ContentPageRepository.get_draft(cls.SLUG)
            if not draft:
                seed = cls.normalize(published.content if published else cls.DEFAULT_CONTENT)
                draft = ContentPageRepository.create_draft(
                    cls.SLUG,
                    seed,
                    user_id,
                    published.version if published else 0,
                )
            return {
                "schema_ready": True,
                "content": cls.normalize(draft.content),
                "draft_version": draft.version,
                "published_version": published.version if published else 0,
                "updated_at": draft.updated_at,
                "published_at": published.published_at if published else None,
            }
        except ContentPageSchemaMissingError as exc:
            return {
                "schema_ready": False,
                "schema_error": str(exc),
                "content": copy.deepcopy(cls.DEFAULT_CONTENT),
                "draft_version": 0,
                "published_version": 0,
                "updated_at": None,
                "published_at": None,
            }
        except ContentPageRepositoryError as exc:
            logger.error("[AboutPageService] Không tải được editor state: %s", exc)
            return {
                "schema_ready": False,
                "schema_error": "Không thể kết nối dữ liệu About trên Supabase. Vui lòng thử lại sau.",
                "content": copy.deepcopy(cls.DEFAULT_CONTENT),
                "draft_version": 0,
                "published_version": 0,
                "updated_at": None,
                "published_at": None,
            }

    @classmethod
    def save_draft(cls, raw_content: Any, expected_version: Any, user_id: str | None) -> dict[str, Any]:
        if not isinstance(raw_content, dict):
            raise AboutPageValidationError("Nội dung About phải là một object JSON hợp lệ.")
        normalized = cls.normalize(raw_content)
        draft = ContentPageRepository.save_draft(
            cls.SLUG,
            normalized,
            int(expected_version or 0),
            user_id,
        )
        return {
            "content": cls.normalize(draft.content),
            "draft_version": draft.version,
            "updated_at": draft.updated_at,
        }

    @classmethod
    def reset_draft(cls, expected_version: Any, user_id: str | None) -> dict[str, Any]:
        return cls.save_draft(copy.deepcopy(cls.DEFAULT_CONTENT), expected_version, user_id)

    @classmethod
    def publish(cls, expected_draft_version: Any, user_id: str | None) -> dict[str, Any]:
        page = ContentPageRepository.publish(
            cls.SLUG,
            int(expected_draft_version or 0),
            user_id,
        )
        return {
            "content": cls.normalize(page.content),
            "published_version": page.version,
            "published_at": page.published_at,
        }

    @classmethod
    def upload_image(
        cls,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
    ) -> str:
        if not file_bytes:
            raise AboutPageValidationError("Tệp ảnh đang trống.")
        if len(file_bytes) > cls.MAX_IMAGE_BYTES:
            raise AboutPageValidationError("Ảnh About không được lớn hơn 10 MB.")

        mime = str(content_type or "").lower()
        if mime == "image/jpg":
            mime = "image/jpeg"
        if mime not in cls.ALLOWED_IMAGE_MIMES:
            raise AboutPageValidationError("Chỉ hỗ trợ JPG, PNG, WEBP, GIF hoặc AVIF.")

        signatures = {
            "image/jpeg": file_bytes.startswith(b"\xff\xd8\xff"),
            "image/png": file_bytes.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/gif": file_bytes.startswith((b"GIF87a", b"GIF89a")),
            "image/webp": len(file_bytes) >= 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP",
            "image/avif": len(file_bytes) >= 12 and file_bytes[4:8] == b"ftyp" and b"avif" in file_bytes[8:32],
        }
        if not signatures.get(mime, False):
            raise AboutPageValidationError("Nội dung tệp không khớp với định dạng ảnh đã chọn.")

        return ContentPageRepository.upload_image(file_bytes, filename, mime)


__all__ = [
    "AboutPageService",
    "AboutPageValidationError",
    "ContentPageConflictError",
    "ContentPageRepositoryError",
    "ContentPageSchemaMissingError",
]
