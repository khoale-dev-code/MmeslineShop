"""Pure data objects for GUAMAISON Media Studio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MediaSlot:
    """A configurable decorative media position on the public storefront."""

    key: str
    group: str
    label: str
    description: str
    route: str
    ratio_label: str
    allow_video: bool = True


@dataclass(frozen=True)
class MediaUpload:
    url: str
    storage_path: str
    media_type: str
    content_type: str
    size: int


@dataclass(frozen=True)
class MediaSaveResult:
    settings: dict[str, str]
    changed_keys: tuple[str, ...]
    updated_at: Optional[str] = None

