"""Business rules for Media Studio; this module knows neither Flask nor HTTP."""

from __future__ import annotations

import mimetypes
import re
import uuid
from urllib.parse import urlparse

from app.models.storefront_media_model import (
    MediaSaveResult,
    MediaSlot,
    MediaUpload,
)
from app.repositories.storefront_media_repository import StorefrontMediaRepository


class StorefrontMediaValidationError(ValueError):
    """A safe, user-facing validation failure with a stable machine code."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_media",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class StorefrontMediaService:
    IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "jfif", "webp", "gif", "avif"}
    VIDEO_EXTENSIONS = {"mp4", "webm", "mov"}
    CONTENT_TYPES = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "jfif": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
        "avif": "image/avif",
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mov": "video/quicktime",
    }
    MAX_IMAGE_BYTES = 4 * 1024 * 1024
    MAX_VIDEO_BYTES = 20 * 1024 * 1024
    EXTRA_UPLOAD_SLOTS = {"contact_hero_media_url"}

    SLOTS = (
        MediaSlot("login_image_url", "account", "Trang đăng nhập", "Ảnh dọc ở khu vực đăng nhập.", "/login", "3:4", False),
        MediaSlot("register_image_url", "account", "Trang đăng ký", "Ảnh dọc ở khu vực tạo tài khoản.", "/register", "3:4", False),
        MediaSlot("hero_banner_url", "home", "Hero trang chủ", "Media mở đầu trang chủ.", "/", "16:9", True),
        MediaSlot("banner2_url", "home", "Banner signature", "Khung chiến dịch sau bộ sưu tập.", "/", "8:3", True),
        MediaSlot("split_left_url", "home", "Banner đôi · trái", "Nửa trái của banner editorial.", "/", "4:5", True),
        MediaSlot("split_right_url", "home", "Banner đôi · phải", "Nửa phải của banner editorial.", "/", "4:5", True),
        MediaSlot("banner4_video_url", "home", "Best Sellers", "Nền khu vực sản phẩm bán chạy.", "/", "16:9", True),
        MediaSlot("shop_banner_url", "shop", "Hero trang Shop", "Media mở đầu danh sách sản phẩm.", "/shop", "3:1", True),
    )
    def __init__(self, repository: StorefrontMediaRepository | None = None) -> None:
        self.repository = repository or StorefrontMediaRepository()

    @classmethod
    def _slot(cls, key: str) -> MediaSlot | None:
        return next((slot for slot in cls.SLOTS if slot.key == key), None)

    @staticmethod
    def _extension(filename: str) -> str:
        name = str(filename or "").strip().lower()
        if "." not in name:
            return ""
        return re.sub(r"[^a-z0-9]", "", name.rsplit(".", 1)[-1])

    @classmethod
    def normalize_media_url(cls, value: str, *, allow_video: bool = True) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        if len(raw) > 2500 or any(ch in raw for ch in ("\x00", "\r", "\n")):
            raise StorefrontMediaValidationError(
                "URL media không hợp lệ.",
                code="invalid_url",
            )
        if raw.startswith("/static/"):
            return raw
        parsed = urlparse(raw)
        if parsed.scheme != "https" or not parsed.hostname:
            raise StorefrontMediaValidationError(
                "Media phải dùng URL HTTPS hợp lệ.",
                code="invalid_url",
            )
        clean_path = parsed.path.lower()
        ext = cls._extension(clean_path)
        if ext in cls.VIDEO_EXTENSIONS and not allow_video:
            raise StorefrontMediaValidationError(
                "Vị trí này chỉ chấp nhận hình ảnh.",
                code="video_not_allowed",
            )
        if ext and ext not in cls.IMAGE_EXTENSIONS | cls.VIDEO_EXTENSIONS:
            raise StorefrontMediaValidationError(
                "Định dạng media không được hỗ trợ.",
                code="unsupported_type",
            )
        return raw

    def upload(
        self,
        *,
        slot_key: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> MediaUpload:
        slot = self._slot(slot_key)
        if slot is None and slot_key not in self.EXTRA_UPLOAD_SLOTS:
            raise StorefrontMediaValidationError(
                "Vị trí media không hợp lệ. Hãy tải lại trang rồi thử lại.",
                code="invalid_slot",
            )
        ext = self._extension(filename)
        allowed = self.IMAGE_EXTENSIONS | (self.VIDEO_EXTENSIONS if slot is None or slot.allow_video else set())
        if ext not in allowed:
            allowed_labels = sorted(allowed)
            raise StorefrontMediaValidationError(
                "Định dạng tệp không phù hợp với vị trí này.",
                code="unsupported_type",
                details={"allowed_extensions": allowed_labels},
            )
        media_type = "video" if ext in self.VIDEO_EXTENSIONS else "image"
        size = len(content or b"")
        limit = self.MAX_VIDEO_BYTES if media_type == "video" else self.MAX_IMAGE_BYTES
        if size <= 0:
            raise StorefrontMediaValidationError(
                "Tệp rỗng hoặc không đọc được.",
                code="empty_file",
            )
        if size > limit:
            label = "20MB" if media_type == "video" else "4MB"
            raise StorefrontMediaValidationError(
                f"Tệp vượt giới hạn {label}. Hãy chọn tệp nhỏ hơn hoặc để trình duyệt tối ưu ảnh.",
                code="file_too_large",
                details={"max_bytes": limit, "actual_bytes": size, "media_type": media_type},
            )
        resolved_content_type = self.CONTENT_TYPES.get(ext)
        guessed, _ = mimetypes.guess_type(filename)
        resolved_content_type = resolved_content_type or guessed or content_type or "application/octet-stream"
        storage_path = f"media-studio/{slot_key}/{uuid.uuid4().hex}.{ext}"
        url = self.repository.upload(
            path=storage_path,
            content=content,
            content_type=resolved_content_type,
        )
        return MediaUpload(
            url=url,
            storage_path=storage_path,
            media_type=media_type,
            content_type=resolved_content_type,
            size=size,
        )

    def save(self, changes: dict[str, str]) -> MediaSaveResult:
        if not isinstance(changes, dict) or not changes:
            raise StorefrontMediaValidationError(
                "Không có thay đổi để lưu.",
                code="empty_changes",
            )
        if len(changes) > len(self.SLOTS):
            raise StorefrontMediaValidationError(
                "Payload media không hợp lệ.",
                code="invalid_payload",
            )
        clean: dict[str, str] = {}
        for key, value in changes.items():
            slot = self._slot(str(key))
            if slot is None:
                raise StorefrontMediaValidationError(
                    f"Vị trí '{key}' không hợp lệ.",
                    code="invalid_slot",
                )
            clean[slot.key] = self.normalize_media_url(value, allow_video=slot.allow_video)
        saved, updated_at = self.repository.save_settings(clean)
        result = {slot.key: str(saved.get(slot.key) or "") for slot in self.SLOTS}
        return MediaSaveResult(
            settings=result,
            changed_keys=tuple(clean.keys()),
            updated_at=updated_at,
        )
