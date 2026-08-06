"""Quản lý bảng size bằng store_settings, không yêu cầu migration database."""

from __future__ import annotations

import json
import logging
import mimetypes
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from werkzeug.utils import secure_filename

from app.models.setting_model import SettingModel
from app.utils.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)


class SizeChartModel:
    STORAGE_BUCKET = "store-assets"
    STORAGE_PREFIX = "size-charts"
    MAX_IMAGE_BYTES = 10 * 1024 * 1024
    ALLOWED_IMAGE_MIMES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/avif",
    }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _clean_name(value: Any) -> str:
        return " ".join(str(value or "").strip().split())[:80]

    @staticmethod
    def _name_key(value: Any) -> str:
        text = unicodedata.normalize("NFKC", SizeChartModel._clean_name(value))
        return text.casefold()

    @staticmethod
    def _safe_url(value: Any) -> str:
        text = str(value or "").strip()[:1500]
        if not text:
            return ""
        parsed = urlparse(text)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return ""
        return text

    @staticmethod
    def _safe_bool(value: Any, default: bool = True) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def normalize_config(cls, value: Any) -> dict:
        raw_items = value.get("items") if isinstance(value, dict) else value
        if not isinstance(raw_items, list):
            raw_items = []

        items = []
        seen_ids: set[str] = set()
        seen_names: set[str] = set()

        for index, raw in enumerate(raw_items[:500]):
            if not isinstance(raw, dict):
                continue

            name = cls._clean_name(raw.get("name"))
            image_url = cls._safe_url(raw.get("image_url"))
            name_key = cls._name_key(name)
            if not name or not image_url or name_key in seen_names:
                continue

            chart_id = re.sub(r"[^a-zA-Z0-9_-]", "", str(raw.get("id") or ""))[:80]
            if not chart_id or chart_id in seen_ids:
                chart_id = uuid.uuid4().hex

            created_at = str(raw.get("created_at") or "").strip() or cls._now()
            updated_at = str(raw.get("updated_at") or "").strip() or created_at

            items.append({
                "id": chart_id,
                "name": name,
                "image_url": image_url,
                "is_active": cls._safe_bool(raw.get("is_active"), True),
                "sort_order": max(0, cls._safe_int(raw.get("sort_order"), index)),
                "created_at": created_at,
                "updated_at": updated_at,
            })
            seen_ids.add(chart_id)
            seen_names.add(name_key)

        items.sort(key=lambda row: (row.get("sort_order", 0), cls._name_key(row.get("name"))))
        for index, item in enumerate(items):
            item["sort_order"] = index
        return {"items": items}

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(float(str(value or "").strip()))
        except (TypeError, ValueError):
            return default

    @classmethod
    def get_config(cls, force_reload: bool = False) -> dict:
        settings = SettingModel.get_settings(force_reload=force_reload)
        return cls.normalize_config(settings.get("size_charts") or {})

    @classmethod
    def get_all(cls, active_only: bool = False, force_reload: bool = False) -> list[dict]:
        items = cls.get_config(force_reload=force_reload).get("items") or []
        if active_only:
            items = [item for item in items if item.get("is_active")]
        return [dict(item) for item in items]

    @classmethod
    def get_by_id(cls, chart_id: Any, force_reload: bool = False) -> dict | None:
        target = str(chart_id or "").strip()
        return next(
            (item for item in cls.get_all(force_reload=force_reload) if item.get("id") == target),
            None,
        )

    @classmethod
    def _save_items(cls, items: list[dict]) -> bool:
        config = cls.normalize_config({"items": items})
        return SettingModel.update_section("size_charts", config)

    @classmethod
    def create(cls, name: Any, image_url: Any, is_active: Any = True) -> tuple[bool, dict | None, str]:
        name = cls._clean_name(name)
        image_url = cls._safe_url(image_url)
        if not name:
            return False, None, "Vui lòng nhập tên bảng size."
        if not image_url:
            return False, None, "Vui lòng tải ảnh bảng size hợp lệ."

        items = cls.get_all(force_reload=True)
        if any(cls._name_key(item.get("name")) == cls._name_key(name) for item in items):
            return False, None, "Tên bảng size đã tồn tại."

        now = cls._now()
        chart = {
            "id": uuid.uuid4().hex,
            "name": name,
            "image_url": image_url,
            "is_active": cls._safe_bool(is_active, True),
            "sort_order": len(items),
            "created_at": now,
            "updated_at": now,
        }
        if not cls._save_items([*items, chart]):
            return False, None, "Không thể lưu bảng size vào cơ sở dữ liệu."
        return True, chart, "Đã tạo bảng size."

    @classmethod
    def update(
        cls,
        chart_id: Any,
        *,
        name: Any,
        image_url: Any,
        is_active: Any,
    ) -> tuple[bool, dict | None, dict | None, str]:
        target = str(chart_id or "").strip()
        name = cls._clean_name(name)
        image_url = cls._safe_url(image_url)
        if not name:
            return False, None, None, "Vui lòng nhập tên bảng size."
        if not image_url:
            return False, None, None, "Bảng size phải có ảnh hợp lệ."

        items = cls.get_all(force_reload=True)
        old_chart = next((dict(item) for item in items if item.get("id") == target), None)
        if not old_chart:
            return False, None, None, "Bảng size không tồn tại."

        duplicate = any(
            item.get("id") != target
            and cls._name_key(item.get("name")) == cls._name_key(name)
            for item in items
        )
        if duplicate:
            return False, old_chart, None, "Tên bảng size đã tồn tại."

        updated_chart = {
            **old_chart,
            "name": name,
            "image_url": image_url,
            "is_active": cls._safe_bool(is_active, False),
            "updated_at": cls._now(),
        }
        next_items = [updated_chart if item.get("id") == target else item for item in items]
        if not cls._save_items(next_items):
            return False, old_chart, None, "Không thể cập nhật bảng size."
        return True, old_chart, updated_chart, "Đã cập nhật bảng size."

    @classmethod
    def delete(cls, chart_id: Any) -> tuple[bool, dict | None, str]:
        target = str(chart_id or "").strip()
        items = cls.get_all(force_reload=True)
        old_chart = next((dict(item) for item in items if item.get("id") == target), None)
        if not old_chart:
            return False, None, "Bảng size không tồn tại."
        if not cls._save_items([item for item in items if item.get("id") != target]):
            return False, old_chart, "Không thể xóa bảng size."
        return True, old_chart, "Đã xóa bảng size."

    @classmethod
    def _parse_tags(cls, raw: Any) -> list[str]:
        if isinstance(raw, list):
            values = raw
        elif isinstance(raw, str):
            text = raw.strip()
            if text.startswith("["):
                try:
                    decoded = json.loads(text)
                    values = decoded if isinstance(decoded, list) else [text]
                except (TypeError, ValueError, json.JSONDecodeError):
                    values = re.split(r"[,|;]+", text)
            else:
                values = re.split(r"[,|;]+", text)
        else:
            values = []

        output = []
        seen = set()
        for value in values:
            tag = cls._clean_name(value)
            key = cls._name_key(tag)
            if tag and key not in seen:
                seen.add(key)
                output.append(tag)
        return output

    @classmethod
    def find_for_tags(cls, tags: Any) -> dict | None:
        tag_keys = {cls._name_key(tag) for tag in cls._parse_tags(tags)}
        if not tag_keys:
            return None
        return next(
            (
                chart
                for chart in cls.get_all(active_only=True)
                if cls._name_key(chart.get("name")) in tag_keys
            ),
            None,
        )

    @classmethod
    def _iter_product_tag_rows(cls):
        db = get_supabase_admin()
        page_size = 1000
        offset = 0
        while offset < 50000:
            rows = (
                db.table("products")
                .select("id,tags,deleted_at")
                .range(offset, offset + page_size - 1)
                .execute()
                .data
                or []
            )
            for row in rows:
                yield row
            if len(rows) < page_size:
                break
            offset += page_size

    @classmethod
    def usage_counts(cls, names: list[Any]) -> dict[str, int]:
        keys = {cls._name_key(name): 0 for name in names if cls._clean_name(name)}
        if not keys:
            return {}
        try:
            for row in cls._iter_product_tag_rows():
                if row.get("deleted_at"):
                    continue
                row_keys = {cls._name_key(tag) for tag in cls._parse_tags(row.get("tags"))}
                for key in keys.keys() & row_keys:
                    keys[key] += 1
        except Exception as exc:
            logger.warning("[SizeChartModel] Không đếm được sản phẩm theo bảng size: %s", exc)
        return keys

    @classmethod
    def rename_product_tag(cls, old_name: Any, new_name: Any) -> dict:
        old_key = cls._name_key(old_name)
        new_name = cls._clean_name(new_name)
        if not old_key or not new_name or old_key == cls._name_key(new_name):
            return {"matched": 0, "updated": 0, "failed": 0}

        matched = updated = failed = 0
        db = get_supabase_admin()
        try:
            for row in cls._iter_product_tag_rows():
                tags = cls._parse_tags(row.get("tags"))
                if old_key not in {cls._name_key(tag) for tag in tags}:
                    continue
                matched += 1
                next_tags = []
                seen = set()
                for tag in tags:
                    value = new_name if cls._name_key(tag) == old_key else tag
                    key = cls._name_key(value)
                    if key and key not in seen:
                        seen.add(key)
                        next_tags.append(value)
                try:
                    db.table("products").update({"tags": next_tags}).eq("id", row["id"]).execute()
                    updated += 1
                except Exception as exc:
                    failed += 1
                    logger.warning("[SizeChartModel] Không đổi tag product=%s: %s", row.get("id"), exc)
        except Exception as exc:
            logger.error("[SizeChartModel] Luồng đổi tag bị lỗi: %s", exc, exc_info=True)
            failed += max(1, matched - updated)
        return {"matched": matched, "updated": updated, "failed": failed}

    @classmethod
    def upload_image(cls, file_bytes: bytes, filename: str, content_type: str | None) -> str:
        if not file_bytes or len(file_bytes) > cls.MAX_IMAGE_BYTES:
            return ""

        safe_name = secure_filename(Path(filename or "size-chart").name)
        guessed_type = mimetypes.guess_type(safe_name)[0]
        mime = (content_type or guessed_type or "application/octet-stream").lower()
        if mime == "application/octet-stream" and guessed_type:
            mime = guessed_type
        if mime == "image/jpg":
            mime = "image/jpeg"
        if mime not in cls.ALLOWED_IMAGE_MIMES:
            return ""

        ext = Path(safe_name).suffix.lower()
        if not ext:
            ext = mimetypes.guess_extension(mime) or ".jpg"
        stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(safe_name).stem).strip("-") or "size-chart"
        today = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        path = f"{cls.STORAGE_PREFIX}/{today}/{stem}-{uuid.uuid4().hex[:12]}{ext}"

        try:
            db = get_supabase_admin()
            storage = db.storage.from_(cls.STORAGE_BUCKET)
            try:
                storage.upload(
                    path,
                    file_bytes,
                    file_options={"content-type": mime, "upsert": "false"},
                )
            except TypeError:
                storage.upload(path, file_bytes, {"content-type": mime, "upsert": "false"})
            return cls._safe_url(storage.get_public_url(path))
        except Exception as exc:
            logger.error("[SizeChartModel] Upload ảnh thất bại: %s", exc, exc_info=True)
            return ""

    @classmethod
    def delete_image_from_url(cls, image_url: Any) -> bool:
        url = cls._safe_url(image_url)
        marker = f"/{cls.STORAGE_BUCKET}/"
        if not url or marker not in url:
            return False
        try:
            path = unquote(url.split(marker, 1)[1].split("?", 1)[0]).lstrip("/")
            if not path.startswith(f"{cls.STORAGE_PREFIX}/"):
                return False
            get_supabase_admin().storage.from_(cls.STORAGE_BUCKET).remove([path])
            return True
        except Exception as exc:
            logger.warning("[SizeChartModel] Không xóa được ảnh cũ: %s", exc)
            return False
