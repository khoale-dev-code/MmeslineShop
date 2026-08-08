"""Business logic liên kết sản phẩm với bảng size."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlparse

from app.models.size_chart import SizeChart
from app.repositories.size_chart_repository import SizeChartRepository


class SizeChartService:
    _TAG_SPLITTER = re.compile(r"[,|;\n]+")

    def __init__(self, repository: SizeChartRepository) -> None:
        self._repository = repository

    @staticmethod
    def _clean_text(value: Any, max_length: int = 1500) -> str:
        text = unicodedata.normalize("NFKC", str(value or ""))
        return " ".join(text.strip().split())[:max_length]

    @classmethod
    def _name_key(cls, value: Any) -> str:
        text = cls._clean_text(value, 80)
        if text.startswith("#"):
            text = text[1:].strip()
        return text.casefold()

    @classmethod
    def _parse_tags(cls, raw: Any) -> set[str]:
        values: Iterable[Any]

        if isinstance(raw, Mapping):
            values = raw.values()
        elif isinstance(raw, (list, tuple, set)):
            values = raw
        elif isinstance(raw, str):
            text = raw.strip()
            if not text:
                return set()
            if text.startswith("["):
                try:
                    decoded = json.loads(text)
                    values = decoded if isinstance(decoded, list) else [text]
                except (TypeError, ValueError, json.JSONDecodeError):
                    values = cls._TAG_SPLITTER.split(text)
            else:
                values = cls._TAG_SPLITTER.split(text)
        else:
            return set()

        return {key for value in values if (key := cls._name_key(value))}

    @staticmethod
    def _safe_http_url(value: Any) -> str:
        url = str(value or "").strip()[:1500]
        parsed = urlparse(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return ""
        return url

    def get_active(self) -> list[SizeChart]:
        config = self._repository.get_config()
        raw_items = config.get("items") if isinstance(config, dict) else []
        if not isinstance(raw_items, list):
            return []

        charts: list[SizeChart] = []
        seen_names: set[str] = set()

        for raw in raw_items[:500]:
            if not isinstance(raw, Mapping):
                continue

            name = self._clean_text(raw.get("name"), 80)
            image_url = self._safe_http_url(raw.get("image_url"))
            name_key = self._name_key(name)
            is_active = raw.get("is_active", True)
            if isinstance(is_active, str):
                is_active = is_active.strip().lower() in {"1", "true", "yes", "on"}

            if not name_key or not image_url or not is_active or name_key in seen_names:
                continue

            try:
                chart = SizeChart.from_mapping(
                    {
                        **raw,
                        "name": name,
                        "image_url": image_url,
                        "is_active": True,
                    }
                )
            except (TypeError, ValueError):
                continue

            charts.append(chart)
            seen_names.add(name_key)

        return sorted(charts, key=lambda item: (item.sort_order, self._name_key(item.name)))

    def get_for_product(self, product: Mapping[str, Any] | None) -> SizeChart | None:
        if not product:
            return None

        charts = self.get_active()
        if not charts:
            return None

        direct_id = self._clean_text(product.get("size_chart_id"), 80)
        if direct_id:
            direct_match = next((chart for chart in charts if chart.id == direct_id), None)
            if direct_match:
                return direct_match

        tag_keys = self._parse_tags(product.get("tags"))
        if not tag_keys:
            return None

        return next((chart for chart in charts if self._name_key(chart.name) in tag_keys), None)


size_chart_service = SizeChartService(SizeChartRepository())