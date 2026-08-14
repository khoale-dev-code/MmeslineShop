"""Pure data contracts for GUAMAISON Analytics Intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any


ANALYTICS_VERSION = "19.0.0"


@dataclass(frozen=True, slots=True)
class ReportFilters:
    """Validated reporting filters. This model has no HTTP or database knowledge."""

    start_date: date
    end_date: date
    channels: tuple[str, ...] = ()
    compare_previous: bool = True

    @property
    def day_count(self) -> int:
        return (self.end_date - self.start_date).days + 1

    @property
    def previous_start_date(self) -> date:
        return self.start_date - timedelta(days=self.day_count)

    @property
    def previous_end_date(self) -> date:
        return self.start_date - timedelta(days=1)

    @property
    def history_start_date(self) -> date:
        forecast_floor = self.end_date - timedelta(days=119)
        comparison_floor = self.previous_start_date if self.compare_previous else self.start_date
        return min(forecast_floor, comparison_floor)

    @property
    def history_start_iso(self) -> str:
        return datetime.combine(
            self.history_start_date,
            time.min,
            tzinfo=timezone.utc,
        ).isoformat()

    @property
    def end_iso(self) -> str:
        return datetime.combine(
            self.end_date,
            time.max,
            tzinfo=timezone.utc,
        ).isoformat()

    def as_dict(self) -> dict[str, Any]:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "channels": list(self.channels),
            "compare_previous": self.compare_previous,
            "day_count": self.day_count,
        }


@dataclass(slots=True)
class ReportSnapshot:
    """Raw rows returned by repositories before business calculations."""

    orders: list[dict[str, Any]] = field(default_factory=list)
    order_items: list[dict[str, Any]] = field(default_factory=list)
    products: list[dict[str, Any]] = field(default_factory=list)
    analytics: list[dict[str, Any]] = field(default_factory=list)
    marketplace_connections: list[dict[str, Any]] = field(default_factory=list)
    external_orders: list[dict[str, Any]] = field(default_factory=list)
    external_order_items: list[dict[str, Any]] = field(default_factory=list)
    product_channel_mappings: list[dict[str, Any]] = field(default_factory=list)
    repository_issues: list[str] = field(default_factory=list)
    truncated_sources: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ExportSelection:
    """Allow-listed Excel export options."""

    sheets: tuple[str, ...]
    product_columns: tuple[str, ...]
    include_charts: bool = True
    title: str = "GUAMAISON Analytics Intelligence"
    note: str = ""
