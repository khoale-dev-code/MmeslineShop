"""
app/models/address_model.py
============================
Quản lý sổ địa chỉ khách hàng.

Fix:
- Dùng Supabase Admin client để tránh RLS.
- Insert đúng schema tối thiểu của bảng user_addresses.
- Không gửi các cột *_name / *_code nếu DB không có.
- Không clear default trước khi insert thất bại.
- Có create() alias cho controller mới.
"""

import logging
from typing import Any, Dict, List, Optional

from app.utils.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)


class AddressModel:
    TABLE = "user_addresses"
    USER_TABLE = "users"

    # Đây là schema an toàn nhất theo DB hiện tại của bạn.
    SAFE_COLUMNS = {
        "user_id",
        "full_name",
        "phone",
        "province",
        "district",
        "ward",
        "address_line",
        "note",
        "is_default",
    }

    EXTRA_COLUMNS = {
        "province_name",
        "district_name",
        "ward_name",
        "province_code",
        "district_code",
        "ward_code",
    }

    @staticmethod
    def _db():
        return get_supabase_admin()

    @staticmethod
    def _safe_rows(result: Any) -> List[Dict[str, Any]]:
        data = getattr(result, "data", None)
        return data if isinstance(data, list) else []

    @staticmethod
    def _clean_value(value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            if value.lower() in ("none", "null", "undefined", "nan"):
                return ""
        return value

    @staticmethod
    def _normalize_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Nhận form/controller có thể gửi cả province_name hoặc province.
        Nhưng output cuối cùng chỉ dùng cột thật trong DB: province/district/ward.
        """
        data = data or {}

        province = (
            data.get("province")
            or data.get("province_name")
            or data.get("hid-prov")
            or ""
        )

        district = (
            data.get("district")
            or data.get("district_name")
            or data.get("hid-dist")
            or ""
        )

        ward = (
            data.get("ward")
            or data.get("ward_name")
            or data.get("hid-ward")
            or ""
        )

        payload = {
            "user_id": AddressModel._clean_value(data.get("user_id")),
            "full_name": AddressModel._clean_value(data.get("full_name")),
            "phone": AddressModel._clean_value(data.get("phone")),
            "province": AddressModel._clean_value(province),
            "district": AddressModel._clean_value(district),
            "ward": AddressModel._clean_value(ward),
            "address_line": AddressModel._clean_value(data.get("address_line")),
            "note": AddressModel._clean_value(data.get("note")) or "",
            "is_default": bool(data.get("is_default")),
        }

        return {
            key: value
            for key, value in payload.items()
            if key in AddressModel.SAFE_COLUMNS
        }

    @staticmethod
    def _sync_user_phone(user_id: str, phone: Optional[str]) -> None:
        phone = (phone or "").strip()
        if not user_id or not phone:
            return

        try:
            (
                AddressModel._db()
                .table(AddressModel.USER_TABLE)
                .update({"phone": phone})
                .eq("id", user_id)
                .execute()
            )
        except Exception as e:
            logger.warning("[AddressModel._sync_user_phone] Không đồng bộ được phone: %s", e)

    # ═══════════════════════════════════════════════════════════════
    # READ
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_user_addresses(user_id: str) -> List[Dict[str, Any]]:
        if not user_id:
            return []

        try:
            result = (
                AddressModel._db()
                .table(AddressModel.TABLE)
                .select("*")
                .eq("user_id", user_id)
                .order("is_default", desc=True)
                .order("created_at", desc=True)
                .execute()
            )
            return AddressModel._safe_rows(result)

        except Exception as e:
            logger.error("[AddressModel.get_user_addresses] Lỗi: %s", e)
            return []

    @staticmethod
    def get_default_address(user_id: str) -> Optional[Dict[str, Any]]:
        if not user_id:
            return None

        try:
            result = (
                AddressModel._db()
                .table(AddressModel.TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("is_default", True)
                .limit(1)
                .execute()
            )
            rows = AddressModel._safe_rows(result)
            return rows[0] if rows else None

        except Exception as e:
            logger.error("[AddressModel.get_default_address] Lỗi: %s", e)
            return None

    @staticmethod
    def get_by_id(user_id: str, address_id: str) -> Optional[Dict[str, Any]]:
        if not user_id or not address_id:
            return None

        try:
            result = (
                AddressModel._db()
                .table(AddressModel.TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("id", address_id)
                .limit(1)
                .execute()
            )
            rows = AddressModel._safe_rows(result)
            return rows[0] if rows else None

        except Exception as e:
            logger.error("[AddressModel.get_by_id] Lỗi: %s", e)
            return None

    # ═══════════════════════════════════════════════════════════════
    # CREATE
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict[str, Any]:
        user_id = (data or {}).get("user_id")
        return AddressModel.add_address(user_id, data)

    @staticmethod
    def add_address(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not user_id:
            logger.error("[AddressModel.add_address] Thiếu user_id.")
            return {}

        try:
            current = AddressModel.get_user_addresses(user_id)
            is_first = len(current) == 0

            payload = AddressModel._normalize_input(data)
            payload["user_id"] = user_id
            payload["is_default"] = bool(payload.get("is_default") or is_first)

            logger.info("[AddressModel.add_address] Insert payload keys: %s", list(payload.keys()))

            result = (
                AddressModel._db()
                .table(AddressModel.TABLE)
                .insert(payload)
                .execute()
            )

            rows = AddressModel._safe_rows(result)
            if not rows:
                logger.error("[AddressModel.add_address] Insert không trả data.")
                return {}

            new_address = rows[0]

            # Chỉ sau khi insert thành công mới clear default cũ.
            if new_address.get("is_default"):
                AddressModel._clear_other_defaults(user_id, new_address.get("id"))
                AddressModel._sync_user_phone(user_id, new_address.get("phone"))

            return new_address

        except Exception as e:
            logger.error("[AddressModel.add_address] Lỗi: %s", e)
            return {}

    # ═══════════════════════════════════════════════════════════════
    # UPDATE / DEFAULT
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _clear_other_defaults(user_id: str, keep_address_id: Optional[str] = None) -> bool:
        if not user_id:
            return False

        try:
            query = (
                AddressModel._db()
                .table(AddressModel.TABLE)
                .update({"is_default": False})
                .eq("user_id", user_id)
            )

            if keep_address_id:
                query = query.neq("id", keep_address_id)

            query.execute()
            return True

        except Exception as e:
            logger.error("[AddressModel._clear_other_defaults] Lỗi: %s", e)
            return False

    @staticmethod
    def set_default(user_id: str, address_id: str) -> bool:
        if not user_id or not address_id:
            return False

        try:
            address = AddressModel.get_by_id(user_id, address_id)
            if not address:
                return False

            AddressModel._clear_other_defaults(user_id, address_id)

            result = (
                AddressModel._db()
                .table(AddressModel.TABLE)
                .update({"is_default": True})
                .eq("user_id", user_id)
                .eq("id", address_id)
                .execute()
            )

            rows = AddressModel._safe_rows(result)
            if not rows:
                return False

            AddressModel._sync_user_phone(user_id, rows[0].get("phone") or address.get("phone"))
            return True

        except Exception as e:
            logger.error("[AddressModel.set_default] Lỗi: %s", e)
            return False

    @staticmethod
    def update_address(user_id: str, address_id: str, data: Dict[str, Any]) -> bool:
        if not user_id or not address_id:
            return False

        try:
            old_address = AddressModel.get_by_id(user_id, address_id)
            if not old_address:
                return False

            payload = AddressModel._normalize_input(data)
            payload.pop("user_id", None)

            wants_default = bool(payload.pop("is_default", False))
            if wants_default:
                payload["is_default"] = True

            result = (
                AddressModel._db()
                .table(AddressModel.TABLE)
                .update(payload)
                .eq("user_id", user_id)
                .eq("id", address_id)
                .execute()
            )

            rows = AddressModel._safe_rows(result)
            if not rows:
                return False

            updated = rows[0]

            if wants_default or updated.get("is_default"):
                AddressModel._clear_other_defaults(user_id, address_id)
                AddressModel._sync_user_phone(user_id, updated.get("phone"))

            return True

        except Exception as e:
            logger.error("[AddressModel.update_address] Lỗi: %s", e)
            return False

    @staticmethod
    def update(address_id: str, data: Dict[str, Any], user_id: Optional[str] = None) -> bool:
        user_id = user_id or (data or {}).get("user_id")
        return AddressModel.update_address(user_id, address_id, data)

    # ═══════════════════════════════════════════════════════════════
    # DELETE
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def delete_address(user_id: str, address_id: str) -> bool:
        if not user_id or not address_id:
            return False

        try:
            address = AddressModel.get_by_id(user_id, address_id)
            if not address:
                return False

            was_default = bool(address.get("is_default"))

            result = (
                AddressModel._db()
                .table(AddressModel.TABLE)
                .delete()
                .eq("user_id", user_id)
                .eq("id", address_id)
                .execute()
            )

            rows = AddressModel._safe_rows(result)
            deleted = bool(rows)

            if deleted and was_default:
                remaining = AddressModel.get_user_addresses(user_id)
                if remaining:
                    next_id = remaining[0].get("id")
                    if next_id:
                        AddressModel.set_default(user_id, next_id)

            return deleted

        except Exception as e:
            logger.error("[AddressModel.delete_address] Lỗi: %s", e)
            return False