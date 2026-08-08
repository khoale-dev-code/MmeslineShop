"""The only layer that talks to Supabase for editable content pages."""

from __future__ import annotations

import mimetypes
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from werkzeug.utils import secure_filename

from app.models.content_page import ContentPage, ContentPageDraft
from app.utils.supabase_client import get_supabase, get_supabase_admin


class ContentPageRepositoryError(RuntimeError):
    pass


class ContentPageSchemaMissingError(ContentPageRepositoryError):
    pass


class ContentPageConflictError(ContentPageRepositoryError):
    pass


class ContentPageRepository:
    PUBLISHED_TABLE = "content_pages"
    DRAFT_TABLE = "content_page_drafts"
    STORAGE_BUCKET = "store-assets"
    STORAGE_PREFIX = "content/about"

    @staticmethod
    def _is_schema_missing(exc: Exception) -> bool:
        message = str(exc).lower()
        return any(token in message for token in (
            "42p01", "pgrst205", "content_pages", "content_page_drafts",
            "could not find the table", "relation",
        )) and any(token in message for token in (
            "does not exist", "schema cache", "could not find", "42p01", "pgrst205",
        ))

    @classmethod
    def _raise_repository_error(cls, exc: Exception) -> None:
        if cls._is_schema_missing(exc):
            raise ContentPageSchemaMissingError(
                "Chưa có schema content_pages trên Supabase. Hãy chạy migration About v6 trước."
            ) from exc
        raise ContentPageRepositoryError(str(exc)) from exc

    @classmethod
    def get_published(cls, slug: str) -> ContentPage | None:
        try:
            response = (
                get_supabase()
                .table(cls.PUBLISHED_TABLE)
                .select("slug,content,version,published_at,published_by")
                .eq("slug", slug)
                .limit(1)
                .execute()
            )
            return ContentPage.from_record((response.data or [None])[0])
        except Exception as exc:
            cls._raise_repository_error(exc)

    @classmethod
    def get_draft(cls, slug: str) -> ContentPageDraft | None:
        try:
            response = (
                get_supabase_admin()
                .table(cls.DRAFT_TABLE)
                .select("slug,content,version,base_published_version,updated_at,updated_by")
                .eq("slug", slug)
                .limit(1)
                .execute()
            )
            return ContentPageDraft.from_record((response.data or [None])[0])
        except Exception as exc:
            cls._raise_repository_error(exc)

    @classmethod
    def create_draft(
        cls,
        slug: str,
        content: dict[str, Any],
        user_id: str | None,
        base_published_version: int = 0,
    ) -> ContentPageDraft:
        payload = {
            "slug": slug,
            "content": content,
            "version": 1,
            "base_published_version": max(0, int(base_published_version or 0)),
            "updated_by": user_id,
        }
        try:
            response = get_supabase_admin().table(cls.DRAFT_TABLE).insert(payload).execute()
            draft = ContentPageDraft.from_record((response.data or [None])[0])
            if not draft:
                raise ContentPageRepositoryError("Supabase không trả về bản nháp vừa tạo.")
            return draft
        except ContentPageRepositoryError:
            raise
        except Exception as exc:
            # A concurrent request may have created the row first.
            existing = cls.get_draft(slug)
            if existing:
                return existing
            cls._raise_repository_error(exc)

    @classmethod
    def save_draft(
        cls,
        slug: str,
        content: dict[str, Any],
        expected_version: int,
        user_id: str | None,
    ) -> ContentPageDraft:
        expected_version = int(expected_version or 0)
        if expected_version < 1:
            raise ContentPageConflictError("Phiên bản bản nháp không hợp lệ.")

        payload = {
            "content": content,
            "version": expected_version + 1,
            "updated_by": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            response = (
                get_supabase_admin()
                .table(cls.DRAFT_TABLE)
                .update(payload)
                .eq("slug", slug)
                .eq("version", expected_version)
                .execute()
            )
            draft = ContentPageDraft.from_record((response.data or [None])[0])
            if not draft:
                raise ContentPageConflictError(
                    "Bản nháp đã được cập nhật ở phiên khác. Hãy tải lại trước khi lưu."
                )
            return draft
        except ContentPageConflictError:
            raise
        except Exception as exc:
            cls._raise_repository_error(exc)

    @classmethod
    def publish(
        cls,
        slug: str,
        expected_draft_version: int,
        user_id: str | None,
    ) -> ContentPage:
        try:
            response = get_supabase_admin().rpc(
                "publish_content_page",
                {
                    "p_slug": slug,
                    "p_expected_draft_version": int(expected_draft_version or 0),
                    "p_user_id": user_id,
                },
            ).execute()
            record = (response.data or [None])[0]
            page = ContentPage.from_record(record)
            if not page:
                raise ContentPageRepositoryError("Supabase không trả về nội dung vừa xuất bản.")
            return page
        except ContentPageRepositoryError:
            raise
        except Exception as exc:
            message = str(exc).lower()
            if "content_page_version_conflict" in message or "40901" in message:
                raise ContentPageConflictError(
                    "Bản nháp đã thay đổi. Hãy tải lại trước khi xuất bản."
                ) from exc
            cls._raise_repository_error(exc)

    @classmethod
    def upload_image(cls, file_bytes: bytes, filename: str, content_type: str) -> str:
        safe_name = secure_filename(Path(filename or "about-image").name)
        mime = (content_type or mimetypes.guess_type(safe_name)[0] or "").lower()
        if mime == "image/jpg":
            mime = "image/jpeg"
        extension_by_mime = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/avif": ".avif",
        }
        ext = extension_by_mime.get(mime) or mimetypes.guess_extension(mime) or ".jpg"
        stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(safe_name).stem).strip("-") or "about"
        day = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        path = f"{cls.STORAGE_PREFIX}/{day}/{stem}-{uuid.uuid4().hex[:12]}{ext}"

        try:
            storage = get_supabase_admin().storage.from_(cls.STORAGE_BUCKET)
            try:
                storage.upload(
                    path,
                    file_bytes,
                    file_options={"content-type": mime, "upsert": "false"},
                )
            except TypeError:
                storage.upload(path, file_bytes, {"content-type": mime, "upsert": "false"})
            public_url = storage.get_public_url(path)
            if isinstance(public_url, dict):
                public_url = public_url.get("publicUrl") or public_url.get("public_url") or ""
            parsed = urlparse(str(public_url or ""))
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ContentPageRepositoryError("Storage không trả về public URL hợp lệ.")
            return str(public_url)
        except ContentPageRepositoryError:
            raise
        except Exception as exc:
            raise ContentPageRepositoryError(f"Không tải được ảnh About: {exc}") from exc
