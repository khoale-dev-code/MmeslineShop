"""Business rules for Media Studio; this module knows neither Flask nor HTTP."""

from __future__ import annotations

import json
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
        # GUAMAISON-home-editorial-v21-media-slots
        MediaSlot("instagram_media_1_url", "social", "Instagram · 1", "Ảnh, GIF hoặc video cho lưới Instagram.", "/", "4:5", True),
        MediaSlot("instagram_media_2_url", "social", "Instagram · 2", "Ảnh, GIF hoặc video cho lưới Instagram.", "/", "4:5", True),
        MediaSlot("instagram_media_3_url", "social", "Instagram · 3", "Ảnh, GIF hoặc video cho lưới Instagram.", "/", "4:5", True),
        MediaSlot("instagram_media_4_url", "social", "Instagram · 4", "Ảnh, GIF hoặc video cho lưới Instagram.", "/", "4:5", True),
        MediaSlot("instagram_media_5_url", "social", "Instagram · 5", "Ảnh, GIF hoặc video cho lưới Instagram.", "/", "4:5", True),
        MediaSlot("instagram_media_6_url", "social", "Instagram · 6", "Ảnh, GIF hoặc video cho lưới Instagram.", "/", "4:5", True),
    )
    # GUAMAISON-home-editorial-v21-click-url-service
    CLICK_URL_KEYS = tuple(f"instagram_link_{index}_url" for index in range(1, 7))
    # GUAMAISON-home-editorial-v21-dynamic-instagram-service
    INSTAGRAM_ITEMS_KEY = "instagram_media_items"
    MAX_INSTAGRAM_ITEMS = 60
    MAX_GIF_BYTES = 10 * 1024 * 1024
    DYNAMIC_UPLOAD_RE = re.compile(r"instagram_dynamic_[A-Za-z0-9_-]{1,64}")
    # GUAMAISON-home-editorial-v21-latest-products-service
    LATEST_PRODUCT_IDS_KEY = "latest_arrivals_product_ids"
    LATEST_ENABLED_KEY = "latest_arrivals_enabled"
    MAX_LATEST_PRODUCTS = 12
    LATEST_TEXT_KEYS = {
        "latest_arrivals_eyebrow": 80,
        "latest_arrivals_title": 120,
        "latest_arrivals_description": 320,
    }
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

    @classmethod
    def normalize_instagram_url(cls, value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        if len(raw) > 2500 or any(ch in raw for ch in ("\x00", "\r", "\n")):
            raise StorefrontMediaValidationError("Link Instagram không hợp lệ.", code="invalid_instagram_url")
        parsed = urlparse(raw)
        hostname = str(parsed.hostname or "").lower()
        is_instagram = hostname == "instagram.com" or hostname.endswith(".instagram.com")
        try:
            port = parsed.port
        except ValueError as exc:
            raise StorefrontMediaValidationError("Link Instagram không hợp lệ.", code="invalid_instagram_url") from exc
        if parsed.scheme != "https" or not is_instagram or parsed.username or parsed.password or port not in (None, 443):
            raise StorefrontMediaValidationError(
                "Chỉ chấp nhận link HTTPS thuộc instagram.com.",
                code="invalid_instagram_url",
            )
        return raw

    @classmethod
    def normalize_instagram_items(cls, value: object) -> list[dict[str, object]]:
        source = value
        if isinstance(source, str):
            try:
                source = json.loads(source)
            except (TypeError, ValueError) as exc:
                raise StorefrontMediaValidationError("Danh sách Instagram không hợp lệ.", code="invalid_instagram_items") from exc
        if not isinstance(source, list):
            raise StorefrontMediaValidationError("Danh sách Instagram phải là một mảng.", code="invalid_instagram_items")
        if len(source) > cls.MAX_INSTAGRAM_ITEMS:
            raise StorefrontMediaValidationError(
                f"Thư viện Instagram tối đa {cls.MAX_INSTAGRAM_ITEMS} mục.",
                code="too_many_instagram_items",
            )
        clean: list[dict[str, object]] = []
        used_ids: set[str] = set()
        for position, item in enumerate(source):
            if not isinstance(item, dict):
                raise StorefrontMediaValidationError("Mục Instagram không hợp lệ.", code="invalid_instagram_item")
            item_id = str(item.get("id") or "").strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", item_id) or item_id in used_ids:
                raise StorefrontMediaValidationError("ID mục Instagram không hợp lệ hoặc bị trùng.", code="invalid_instagram_item_id")
            used_ids.add(item_id)
            media_url = cls.normalize_media_url(item.get("media_url", ""), allow_video=True)
            click_url = cls.normalize_instagram_url(item.get("click_url", ""))
            clean.append({"id": item_id, "media_url": media_url, "click_url": click_url, "position": position})
        return clean

    @classmethod
    def normalize_latest_product_ids(cls, value: object) -> list[str]:
        source = value
        if isinstance(source, str):
            try:
                source = json.loads(source)
            except (TypeError, ValueError) as exc:
                raise StorefrontMediaValidationError("Danh sách sản phẩm không hợp lệ.", code="invalid_latest_products") from exc
        if not isinstance(source, list):
            raise StorefrontMediaValidationError("Danh sách sản phẩm phải là một mảng.", code="invalid_latest_products")
        if len(source) > cls.MAX_LATEST_PRODUCTS:
            raise StorefrontMediaValidationError(f"Chỉ được chọn tối đa {cls.MAX_LATEST_PRODUCTS} sản phẩm.", code="too_many_latest_products")
        clean: list[str] = []
        for raw in source:
            product_id = str(raw or "").strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", product_id):
                raise StorefrontMediaValidationError("ID sản phẩm không hợp lệ.", code="invalid_latest_product_id")
            if product_id not in clean:
                clean.append(product_id)
        return clean

    @classmethod
    def normalize_latest_text(cls, key: str, value: object) -> str:
        clean = re.sub(r"[\t\r\n]+", " ", str(value or "")).strip()
        limit = cls.LATEST_TEXT_KEYS[key]
        if not clean or len(clean) > limit or "\x00" in clean:
            raise StorefrontMediaValidationError("Nội dung giới thiệu sản phẩm mới không hợp lệ.", code="invalid_latest_copy")
        return clean

    @staticmethod
    def normalize_latest_enabled(value: object) -> str:
        normalized = str(value).strip().lower()
        if normalized not in {"true", "false"}:
            raise StorefrontMediaValidationError("Trạng thái hiển thị không hợp lệ.", code="invalid_latest_enabled")
        return normalized

    def upload(
        self,
        *,
        slot_key: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> MediaUpload:
        normalized_slot_key = str(slot_key or "")
        slot = self._slot(normalized_slot_key)
        is_dynamic_instagram = bool(self.DYNAMIC_UPLOAD_RE.fullmatch(normalized_slot_key))
        if slot is None and normalized_slot_key not in self.EXTRA_UPLOAD_SLOTS and not is_dynamic_instagram:
            raise StorefrontMediaValidationError(
                "Vị trí media không hợp lệ. Hãy tải lại trang rồi thử lại.",
                code="invalid_slot",
            )
        ext = self._extension(filename)
        allowed = self.IMAGE_EXTENSIONS | (self.VIDEO_EXTENSIONS if is_dynamic_instagram or slot is None or slot.allow_video else set())
        if ext not in allowed:
            allowed_labels = sorted(allowed)
            raise StorefrontMediaValidationError(
                "Định dạng tệp không phù hợp với vị trí này.",
                code="unsupported_type",
                details={"allowed_extensions": allowed_labels},
            )
        media_type = "video" if ext in self.VIDEO_EXTENSIONS else "image"
        size = len(content or b"")
        limit = self.MAX_VIDEO_BYTES if media_type == "video" else (self.MAX_GIF_BYTES if ext == "gif" else self.MAX_IMAGE_BYTES)
        if size <= 0:
            raise StorefrontMediaValidationError(
                "Tệp rỗng hoặc không đọc được.",
                code="empty_file",
            )
        if size > limit:
            label = "20MB" if media_type == "video" else ("10MB" if ext == "gif" else "4MB")
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
        if len(changes) > len(self.SLOTS) + len(self.CLICK_URL_KEYS) + 6:
            raise StorefrontMediaValidationError(
                "Payload media không hợp lệ.",
                code="invalid_payload",
            )
        clean: dict[str, object] = {}
        for key, value in changes.items():
            normalized_key = str(key)
            if normalized_key == self.LATEST_PRODUCT_IDS_KEY:
                clean[normalized_key] = self.normalize_latest_product_ids(value)
                continue
            if normalized_key == self.LATEST_ENABLED_KEY:
                clean[normalized_key] = self.normalize_latest_enabled(value)
                continue
            if normalized_key in self.LATEST_TEXT_KEYS:
                clean[normalized_key] = self.normalize_latest_text(normalized_key, value)
                continue
            if normalized_key == self.INSTAGRAM_ITEMS_KEY:
                clean[normalized_key] = self.normalize_instagram_items(value)
                continue
            if normalized_key in self.CLICK_URL_KEYS:
                clean[normalized_key] = self.normalize_instagram_url(value)
                continue
            slot = self._slot(normalized_key)
            if slot is None:
                raise StorefrontMediaValidationError(
                    f"Vị trí '{key}' không hợp lệ.",
                    code="invalid_slot",
                )
            clean[slot.key] = self.normalize_media_url(value, allow_video=slot.allow_video)
        saved, updated_at = self.repository.save_settings(clean)
        result = {slot.key: str(saved.get(slot.key) or "") for slot in self.SLOTS}
        result.update({key: str(saved.get(key) or "") for key in self.CLICK_URL_KEYS})
        stored_items = saved.get(self.INSTAGRAM_ITEMS_KEY)
        result[self.INSTAGRAM_ITEMS_KEY] = stored_items if isinstance(stored_items, list) else []
        stored_product_ids = saved.get(self.LATEST_PRODUCT_IDS_KEY)
        result[self.LATEST_PRODUCT_IDS_KEY] = stored_product_ids if isinstance(stored_product_ids, list) else []
        result[self.LATEST_ENABLED_KEY] = str(saved.get(self.LATEST_ENABLED_KEY) or "true")
        result.update({key: str(saved.get(key) or "") for key in self.LATEST_TEXT_KEYS})
        return MediaSaveResult(
            settings=result,
            changed_keys=tuple(clean.keys()),
            updated_at=updated_at,
        )
