"""
app/models/collection_model.py
==============================
Quản lý các chiến dịch bộ sưu tập thời trang xu hướng (Lookbook/Campaigns).

Fix chính:
- Admin CRUD dùng service_role để không bị RLS chặn.
- Upload media lên Supabase Storage bucket `store-assets`.
- Validate file ảnh/video rõ ràng.
- Tạo path an toàn, tránh lỗi tên file tiếng Việt/ký tự đặc biệt.
"""

import logging
import mimetypes
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

from werkzeug.utils import secure_filename

from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)


class CollectionModel:
    STORAGE_BUCKET = "store-assets"
    STORAGE_PREFIX = "collections"

    ALLOWED_IMAGE_MIMES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }

    ALLOWED_VIDEO_MIMES = {
        "video/mp4",
        "video/webm",
        "video/quicktime",
    }

    MAX_IMAGE_BYTES = 8 * 1024 * 1024       # 8MB
    MAX_VIDEO_BYTES = 80 * 1024 * 1024      # 80MB

    @staticmethod
    def _db():
        return get_supabase()

    @staticmethod
    def _db_admin():
        return get_supabase_admin()

    @staticmethod
    def get_all(active_only: bool = False, admin_mode: bool = False) -> List[Dict]:
        """
        Lấy danh sách bộ sưu tập.
        - admin_mode=True: dùng service_role, lấy cả collection ẩn.
        - active_only=True: chỉ lấy collection active.
        """
        db = CollectionModel._db_admin() if admin_mode else CollectionModel._db()

        try:
            query = db.table("collections").select("*")

            if active_only:
                query = query.eq("is_active", True)

            r = query.order("sort_order").order("created_at", desc=True).execute()
            return r.data or []

        except Exception as e:
            logger.error(f"[CollectionModel] get_all error: {e}")
            return []

    @staticmethod
    def get_by_id(cid: str) -> Optional[Dict]:
        db = CollectionModel._db_admin()

        try:
            r = (
                db.table("collections")
                .select("*")
                .eq("id", cid)
                .limit(1)
                .execute()
            )
            return r.data[0] if r.data else None

        except Exception as e:
            logger.error(f"[CollectionModel] get_by_id error cid={cid}: {e}")
            return None

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict:
        db = CollectionModel._db_admin()

        try:
            clean_data = {k: v for k, v in data.items() if v is not None}
            clean_data.setdefault("sort_order", 0)

            r = db.table("collections").insert(clean_data).execute()
            return r.data[0] if r.data else {}

        except Exception as e:
            logger.error(f"[CollectionModel] create error: {e}")
            return {}

    @staticmethod
    def update(cid: str, data: Dict[str, Any]) -> Dict:
        db = CollectionModel._db_admin()

        try:
            clean_data = {k: v for k, v in data.items() if v is not None}
            if not clean_data:
                return {}

            r = (
                db.table("collections")
                .update(clean_data)
                .eq("id", cid)
                .execute()
            )
            return r.data[0] if r.data else {}

        except Exception as e:
            logger.error(f"[CollectionModel] update error cid={cid}: {e}")
            return {}

    @staticmethod
    def delete(cid: str) -> bool:
        db = CollectionModel._db_admin()

        try:
            coll = CollectionModel.get_by_id(cid)

            if coll:
                CollectionModel.delete_media_from_url(coll.get("image_url"))
                CollectionModel.delete_media_from_url(coll.get("video_url"))

            db.table("collections").delete().eq("id", cid).execute()
            return True

        except Exception as e:
            logger.error(f"[CollectionModel] delete error cid={cid}: {e}")
            return False

    @staticmethod
    def _guess_content_type(filename: str, content_type: str | None) -> str:
        if content_type and content_type != "application/octet-stream":
            return content_type

        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"

    @staticmethod
    def _safe_ext(filename: str, content_type: str) -> str:
        ext = Path(filename or "").suffix.lower().strip()

        if ext:
            return ext

        fallback = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "video/mp4": ".mp4",
            "video/webm": ".webm",
            "video/quicktime": ".mov",
        }
        return fallback.get(content_type, "")

    @staticmethod
    def _build_storage_path(filename: str, content_type: str) -> str:
        today = datetime.utcnow().strftime("%Y/%m/%d")
        base = secure_filename(Path(filename or "collection-media").stem)
        base = re.sub(r"[^a-zA-Z0-9_-]+", "-", base).strip("-").lower()
        if not base:
            base = "collection-media"

        ext = CollectionModel._safe_ext(filename, content_type)
        unique = uuid.uuid4().hex[:12]

        return f"{CollectionModel.STORAGE_PREFIX}/{today}/{base}-{unique}{ext}"

    @staticmethod
    def upload_media(file_bytes: bytes, filename: str, content_type: str | None = None) -> str:
        """
        Upload ảnh/video collection lên Supabase Storage.

        Trả về public URL nếu thành công.
        Trả về "" nếu thất bại.
        """
        if not file_bytes:
            logger.warning("[CollectionModel] upload_media called with empty file.")
            return ""

        content_type = CollectionModel._guess_content_type(filename, content_type)
        file_size = len(file_bytes)

        is_image = content_type in CollectionModel.ALLOWED_IMAGE_MIMES
        is_video = content_type in CollectionModel.ALLOWED_VIDEO_MIMES

        if not is_image and not is_video:
            logger.warning(
                "[CollectionModel] Unsupported media type: filename=%s content_type=%s",
                filename,
                content_type,
            )
            return ""

        if is_image and file_size > CollectionModel.MAX_IMAGE_BYTES:
            logger.warning("[CollectionModel] Image too large: %s bytes", file_size)
            return ""

        if is_video and file_size > CollectionModel.MAX_VIDEO_BYTES:
            logger.warning("[CollectionModel] Video too large: %s bytes", file_size)
            return ""

        path = CollectionModel._build_storage_path(filename, content_type)

        try:
            db = CollectionModel._db_admin()

            # supabase-py 2.x hỗ trợ file_options.
            # upsert=true để tránh lỗi nếu trùng path, dù path đã random.
            db.storage.from_(CollectionModel.STORAGE_BUCKET).upload(
                path,
                file_bytes,
                file_options={
                    "content-type": content_type,
                    "upsert": "true",
                },
            )

            public_url = db.storage.from_(CollectionModel.STORAGE_BUCKET).get_public_url(path)

            logger.info(
                "[CollectionModel] Uploaded collection media: path=%s content_type=%s size=%s",
                path,
                content_type,
                file_size,
            )

            return public_url

        except Exception as e:
            logger.error(f"[CollectionModel] upload_media error path={path}: {e}", exc_info=True)
            return ""

    @staticmethod
    def delete_media_from_url(public_url: str | None) -> bool:
        """
        Xóa file trong Supabase Storage từ public URL.
        Chỉ xóa nếu URL thuộc bucket store-assets.
        """
        if not public_url:
            return False

        try:
            marker = f"/{CollectionModel.STORAGE_BUCKET}/"
            if marker not in public_url:
                return False

            path = public_url.split(marker, 1)[1]
            if not path:
                return False

            db = CollectionModel._db_admin()
            db.storage.from_(CollectionModel.STORAGE_BUCKET).remove([path])
            return True

        except Exception as e:
            logger.error(f"[CollectionModel] delete_media_from_url error: {e}")
            return False