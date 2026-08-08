"""Đọc cấu hình bảng size từ Supabase."""

from __future__ import annotations

from typing import Any

from app.utils.supabase_client import get_supabase


class SizeChartRepository:
    TABLE = "store_settings"
    SETTING_KEY = "size_charts"

    def get_config(self) -> dict[str, Any]:
        response = (
            get_supabase()
            .table(self.TABLE)
            .select("setting_value")
            .eq("setting_key", self.SETTING_KEY)
            .limit(1)
            .execute()
        )

        rows = response.data or []
        if isinstance(rows, dict):
            rows = [rows]
        if not rows:
            return {}

        value = rows[0].get("setting_value")
        return value if isinstance(value, dict) else {}