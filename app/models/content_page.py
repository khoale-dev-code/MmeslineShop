"""Data objects for editable content pages. No database or Flask side effects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ContentPage:
    slug: str
    content: dict[str, Any] = field(default_factory=dict)
    version: int = 0
    published_at: str | None = None
    published_by: str | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any] | None) -> "ContentPage | None":
        if not record:
            return None
        return cls(
            slug=str(record.get("slug") or ""),
            content=dict(record.get("content") or {}),
            version=int(record.get("version") or 0),
            published_at=record.get("published_at"),
            published_by=record.get("published_by"),
        )


@dataclass(frozen=True, slots=True)
class ContentPageDraft:
    slug: str
    content: dict[str, Any] = field(default_factory=dict)
    version: int = 0
    base_published_version: int = 0
    updated_at: str | None = None
    updated_by: str | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any] | None) -> "ContentPageDraft | None":
        if not record:
            return None
        return cls(
            slug=str(record.get("slug") or ""),
            content=dict(record.get("content") or {}),
            version=int(record.get("version") or 0),
            base_published_version=int(record.get("base_published_version") or 0),
            updated_at=record.get("updated_at"),
            updated_by=record.get("updated_by"),
        )
