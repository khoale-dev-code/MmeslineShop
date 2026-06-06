"""
app/models/notification_model.py
================================
Notification model cho GUA Maison.

Schema chính:
  notifications:
    id, title, content, is_active, is_permanent,
    start_at, end_at, link, link_text, sort_order,
    created_at, updated_at

  user_notifications:
    id, user_id, notification_id,
    is_read, is_deleted, read_at,
    created_at, updated_at

Nguyên tắc:
  - Admin CRUD dùng service_role.
  - User notification actions chạy server-side nên cũng dùng service_role,
    sau đó filter theo user_id để đảm bảo user chỉ thao tác dữ liệu của chính họ.
  - Không dùng anon client để query trực tiếp user_notifications trong Flask,
    vì app đang dùng session custom, không truyền Supabase Auth JWT.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)

_BATCH_SIZE = 500


class NotificationModel:
    # ═══════════════════════════════════════════════════════════════
    # DB CLIENTS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _db():
        """
        Public/anon client.

        Chỉ nên dùng cho dữ liệu public thật sự như bảng notifications
        đã có policy public SELECT.
        """
        return get_supabase()

    @staticmethod
    def _admin_db():
        """
        Service role client.

        Dùng cho admin CRUD và user_notifications vì các bảng này có RLS.
        Chỉ chạy ở server-side.
        """
        return get_supabase_admin()

    # ═══════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_datetime_fields(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert chuỗi rỗng của input datetime-local thành None.
        Không mutate object gốc.
        """
        cleaned = dict(data or {})

        for key in ("start_at", "end_at"):
            if cleaned.get(key) == "":
                cleaned[key] = None

        return cleaned

    @staticmethod
    def _is_visible_notification(notif: Dict[str, Any], now_iso: Optional[str] = None) -> bool:
        """
        Kiểm tra notification có đang hiển thị không.

        is_permanent=True thì bỏ qua start/end.
        """
        if not notif:
            return False

        if not notif.get("is_active", False):
            return False

        if notif.get("is_permanent"):
            return True

        now_iso = now_iso or NotificationModel._now_iso()

        start = notif.get("start_at")
        end = notif.get("end_at")

        if start and start > now_iso:
            return False

        if end and end < now_iso:
            return False

        return True

    @staticmethod
    def _extract_rpc_int(data: Any) -> int:
        """
        Supabase RPC có thể trả:
          - int trực tiếp
          - list[int]
          - list[dict]
          - None
        """
        try:
            if data is None:
                return 0

            if isinstance(data, int):
                return max(0, data)

            if isinstance(data, list):
                if not data:
                    return 0

                first = data[0]

                if isinstance(first, int):
                    return max(0, first)

                if isinstance(first, dict):
                    for value in first.values():
                        if isinstance(value, int):
                            return max(0, value)
                        if isinstance(value, str) and value.isdigit():
                            return max(0, int(value))

            if isinstance(data, dict):
                for value in data.values():
                    if isinstance(value, int):
                        return max(0, value)
                    if isinstance(value, str) and value.isdigit():
                        return max(0, int(value))

            return 0

        except Exception:
            return 0

    # ═══════════════════════════════════════════════════════════════
    # ADMIN METHODS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_all_admin() -> List[Dict]:
        """Lấy toàn bộ notifications cho admin."""
        try:
            res = (
                NotificationModel._admin_db()
                .table("notifications")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            return res.data or []

        except Exception as e:
            logger.error(f"[NotificationModel] get_all_admin error: {e}")
            return []

    @staticmethod
    def get_by_id(notif_id: str) -> Optional[Dict]:
        """Lấy notification theo id."""
        if not notif_id:
            return None

        try:
            res = (
                NotificationModel._admin_db()
                .table("notifications")
                .select("*")
                .eq("id", notif_id)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None

        except Exception as e:
            logger.error(f"[NotificationModel] get_by_id {notif_id} error: {e}")
            return None

    @staticmethod
    def create(data: Dict) -> Optional[Dict]:
        """
        Tạo notification mới.

        Sau khi tạo:
          - Nếu notification active thì fan-out cho customer.
          - Nếu chưa active vẫn có thể không fan-out ngay;
            nhưng để đơn giản, vẫn fan-out để user có record sẵn.
        """
        try:
            cleaned = NotificationModel._normalize_datetime_fields(data)
            cleaned.setdefault("is_active", True)
            cleaned.setdefault("is_permanent", False)
            cleaned.setdefault("sort_order", 0)

            res = (
                NotificationModel._admin_db()
                .table("notifications")
                .insert(cleaned)
                .execute()
            )

            if not res.data:
                logger.error("[NotificationModel] create: insert không trả data")
                return None

            new_notif = res.data[0]

            count = NotificationModel.fan_out_to_all_users(new_notif["id"])
            logger.info(
                "[NotificationModel] Created notification %s, fan-out %s users.",
                new_notif["id"],
                count,
            )

            return new_notif

        except Exception as e:
            logger.error(f"[NotificationModel] create error: {e}", exc_info=True)
            return None

    @staticmethod
    def update(notif_id: str, data: Dict) -> bool:
        """Cập nhật notification."""
        if not notif_id:
            return False

        try:
            cleaned = NotificationModel._normalize_datetime_fields(data)
            cleaned["updated_at"] = NotificationModel._now_iso()

            res = (
                NotificationModel._admin_db()
                .table("notifications")
                .update(cleaned)
                .eq("id", notif_id)
                .execute()
            )

            return bool(res.data)

        except Exception as e:
            logger.error(f"[NotificationModel] update {notif_id} error: {e}")
            return False

    @staticmethod
    def delete(notif_id: str) -> bool:
        """
        Xóa notification.

        Xóa user_notifications trước để tránh FK constraint.
        """
        if not notif_id:
            return False

        try:
            db = NotificationModel._admin_db()

            db.table("user_notifications").delete().eq("notification_id", notif_id).execute()
            db.table("notifications").delete().eq("id", notif_id).execute()

            return True

        except Exception as e:
            logger.error(f"[NotificationModel] delete {notif_id} error: {e}")
            return False

    @staticmethod
    def toggle_active(notif_id: str) -> bool:
        """Bật/tắt notification."""
        notif = NotificationModel.get_by_id(notif_id)
        if not notif:
            return False

        return NotificationModel.update(
            notif_id,
            {"is_active": not bool(notif.get("is_active"))},
        )

    # ═══════════════════════════════════════════════════════════════
    # FAN OUT / SYNC
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def fan_out_to_all_users(notification_id: str) -> int:
        """
        Tạo user_notifications cho toàn bộ customer.

        Vì schema hiện tại chưa chắc có UNIQUE(user_id, notification_id),
        nên phải check existing trước để tránh duplicate.
        """
        if not notification_id:
            return 0

        db = NotificationModel._admin_db()

        try:
            user_ids: List[str] = []
            page_size = 1000
            offset = 0

            while True:
                res = (
                    db.table("users")
                    .select("id")
                    .eq("role", "customer")
                    .range(offset, offset + page_size - 1)
                    .execute()
                )

                batch = res.data or []
                user_ids.extend(row["id"] for row in batch if row.get("id"))

                if len(batch) < page_size:
                    break

                offset += page_size

        except Exception as e:
            logger.error(f"[NotificationModel] fan_out get users error: {e}")
            return 0

        if not user_ids:
            logger.info("[NotificationModel] fan_out: no customer users.")
            return 0

        try:
            existing_user_ids: set[str] = set()
            offset = 0
            page_size = 1000

            while True:
                res = (
                    db.table("user_notifications")
                    .select("user_id")
                    .eq("notification_id", notification_id)
                    .range(offset, offset + page_size - 1)
                    .execute()
                )

                batch = res.data or []
                existing_user_ids.update(
                    row["user_id"] for row in batch if row.get("user_id")
                )

                if len(batch) < page_size:
                    break

                offset += page_size

        except Exception as e:
            logger.warning(f"[NotificationModel] fan_out existing check error: {e}")
            existing_user_ids = set()

        missing_ids = [uid for uid in user_ids if uid not in existing_user_ids]

        if not missing_ids:
            logger.info(
                "[NotificationModel] fan_out: all %s users already have notification %s.",
                len(user_ids),
                notification_id,
            )
            return 0

        rows = [
            {
                "user_id": uid,
                "notification_id": notification_id,
                "is_read": False,
                "is_deleted": False,
            }
            for uid in missing_ids
        ]

        total = 0

        try:
            for i in range(0, len(rows), _BATCH_SIZE):
                chunk = rows[i:i + _BATCH_SIZE]
                db.table("user_notifications").insert(chunk).execute()
                total += len(chunk)

            logger.info(
                "[NotificationModel] fan_out_to_all_users: %s/%s rows inserted for notification %s.",
                total,
                len(missing_ids),
                notification_id,
            )

            return total

        except Exception as e:
            logger.error(f"[NotificationModel] fan_out insert error: {e}")
            return total

    @staticmethod
    def sync_user_notification(user_id: str, notification_id: str) -> None:
        """Sync một notification cụ thể cho một user."""
        if not user_id or not notification_id:
            return

        try:
            db = NotificationModel._admin_db()

            existing = (
                db.table("user_notifications")
                .select("id")
                .eq("user_id", user_id)
                .eq("notification_id", notification_id)
                .limit(1)
                .execute()
            )

            if existing.data:
                return

            db.table("user_notifications").insert({
                "user_id": user_id,
                "notification_id": notification_id,
                "is_read": False,
                "is_deleted": False,
            }).execute()

        except Exception as e:
            logger.error(
                f"[NotificationModel] sync_user_notification {user_id}/{notification_id} error: {e}"
            )

    @staticmethod
    def _lazy_sync_missing(user_id: str, active_notif_ids: List[str]) -> None:
        """Tạo bản ghi user_notifications còn thiếu cho user."""
        if not user_id or not active_notif_ids:
            return

        try:
            db = NotificationModel._admin_db()

            existing = (
                db.table("user_notifications")
                .select("notification_id")
                .eq("user_id", user_id)
                .in_("notification_id", active_notif_ids)
                .execute()
            )

            existing_ids = {
                row["notification_id"]
                for row in (existing.data or [])
                if row.get("notification_id")
            }

            missing = [nid for nid in active_notif_ids if nid not in existing_ids]

            if not missing:
                return

            rows = [
                {
                    "user_id": user_id,
                    "notification_id": nid,
                    "is_read": False,
                    "is_deleted": False,
                }
                for nid in missing
            ]

            for i in range(0, len(rows), _BATCH_SIZE):
                db.table("user_notifications").insert(rows[i:i + _BATCH_SIZE]).execute()

            logger.info(
                "[NotificationModel] lazy_sync: created %s rows for user %s.",
                len(rows),
                user_id,
            )

        except Exception as e:
            logger.warning(f"[NotificationModel] lazy_sync failed for user {user_id}: {e}")

    # ═══════════════════════════════════════════════════════════════
    # USER-FACING READS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_all_active(limit: int = 10) -> List[Dict]:
        """
        Lấy notification public active cho navbar/topbar.

        Dùng public client được, vì bảng notifications có thể public SELECT.
        Nếu RLS lỗi thì fallback service_role.
        """
        now = NotificationModel._now_iso()

        def _query(db):
            return (
                db.table("notifications")
                .select("*")
                .eq("is_active", True)
                .order("sort_order", desc=False)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

        try:
            res = _query(NotificationModel._db())
            rows = res.data or []

        except Exception as e:
            logger.warning(f"[NotificationModel] get_all_active public query failed: {e}")
            try:
                res = _query(NotificationModel._admin_db())
                rows = res.data or []
            except Exception as e2:
                logger.error(f"[NotificationModel] get_all_active admin fallback failed: {e2}")
                return []

        return [
            row for row in rows
            if NotificationModel._is_visible_notification(row, now)
        ][:limit]

    @staticmethod
    def get_user_notifications(
        user_id: str,
        page: int = 1,
        per_page: int = 15,
        filter_type: str = "all",
    ) -> Dict:
        """
        Danh sách thông báo của user.

        Có lazy-sync:
          - Lấy notifications active.
          - Tạo user_notifications còn thiếu.
          - Query user_notifications của riêng user.
        """
        if not user_id:
            return {
                "items": [],
                "total": 0,
                "page": 1,
                "per_page": per_page,
                "total_pages": 1,
            }

        page = max(1, int(page or 1))
        per_page = max(1, min(int(per_page or 15), 50))
        filter_type = filter_type if filter_type in {"all", "unread", "read"} else "all"

        offset = (page - 1) * per_page
        now = NotificationModel._now_iso()
        db = NotificationModel._admin_db()

        try:
            active_res = (
                db.table("notifications")
                .select("id")
                .eq("is_active", True)
                .execute()
            )

            active_notif_ids = [
                row["id"] for row in (active_res.data or [])
                if row.get("id")
            ]

            NotificationModel._lazy_sync_missing(user_id, active_notif_ids)

            query = (
                db.table("user_notifications")
                .select(
                    "id, notification_id, is_read, is_deleted, read_at, created_at, "
                    "notifications(id, title, content, link, link_text, is_active, "
                    "is_permanent, start_at, end_at, created_at)"
                )
                .eq("user_id", user_id)
                .eq("is_deleted", False)
            )

            if filter_type == "unread":
                query = query.eq("is_read", False)
            elif filter_type == "read":
                query = query.eq("is_read", True)

            res = query.order("created_at", desc=True).execute()
            rows = res.data or []

            valid_rows = [
                row for row in rows
                if NotificationModel._is_visible_notification(
                    row.get("notifications") or {},
                    now,
                )
            ]

            total = len(valid_rows)
            paged = valid_rows[offset: offset + per_page]

            items = []

            for row in paged:
                notif = row.get("notifications") or {}

                items.append({
                    "id": row.get("notification_id"),
                    "user_notification_id": row.get("id"),
                    "title": notif.get("title"),
                    "content": notif.get("content"),
                    "link": notif.get("link"),
                    "link_text": notif.get("link_text"),
                    "created_at": notif.get("created_at") or row.get("created_at"),
                    "is_read": bool(row.get("is_read")),
                    "read_at": row.get("read_at"),
                })

            return {
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": max(1, (total + per_page - 1) // per_page),
            }

        except Exception as e:
            logger.error(f"[NotificationModel] get_user_notifications {user_id} error: {e}")
            return {
                "items": [],
                "total": 0,
                "page": 1,
                "per_page": per_page,
                "total_pages": 1,
            }

    # ═══════════════════════════════════════════════════════════════
    # USER ACTIONS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def mark_as_read(user_id: str, notification_id: str) -> bool:
        """Đánh dấu một notification là đã đọc cho đúng user."""
        if not user_id or not notification_id:
            return False

        try:
            res = (
                NotificationModel._admin_db()
                .table("user_notifications")
                .update({
                    "is_read": True,
                    "read_at": NotificationModel._now_iso(),
                    "updated_at": NotificationModel._now_iso(),
                })
                .eq("user_id", user_id)
                .eq("notification_id", notification_id)
                .eq("is_deleted", False)
                .execute()
            )

            return bool(res.data)

        except Exception as e:
            logger.error(f"[NotificationModel] mark_as_read {user_id}/{notification_id} error: {e}")
            return False

    @staticmethod
    def mark_all_as_read(user_id: str) -> bool:
        """Đánh dấu tất cả thông báo chưa đọc của user là đã đọc."""
        if not user_id:
            return False

        try:
            (
                NotificationModel._admin_db()
                .table("user_notifications")
                .update({
                    "is_read": True,
                    "read_at": NotificationModel._now_iso(),
                    "updated_at": NotificationModel._now_iso(),
                })
                .eq("user_id", user_id)
                .eq("is_read", False)
                .eq("is_deleted", False)
                .execute()
            )

            return True

        except Exception as e:
            logger.error(f"[NotificationModel] mark_all_as_read {user_id} error: {e}")
            return False

    @staticmethod
    def delete_notification(user_id: str, notification_id: str) -> bool:
        """Xóa mềm notification của user."""
        if not user_id or not notification_id:
            return False

        try:
            res = (
                NotificationModel._admin_db()
                .table("user_notifications")
                .update({
                    "is_deleted": True,
                    "updated_at": NotificationModel._now_iso(),
                })
                .eq("user_id", user_id)
                .eq("notification_id", notification_id)
                .execute()
            )

            return bool(res.data)

        except Exception as e:
            logger.error(
                f"[NotificationModel] delete_notification {user_id}/{notification_id} error: {e}"
            )
            return False

    # ═══════════════════════════════════════════════════════════════
    # BADGE COUNT
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_unread_count(user_id: str) -> int:
        """
        Badge navbar: đếm thông báo chưa đọc.

        Ưu tiên RPC để DB đếm chính xác và nhanh.
        Nếu RPC chưa có, fallback bằng service_role count.
        """
        if not user_id:
            return 0

        try:
            res = (
                NotificationModel._admin_db()
                .rpc(
                    "get_unread_notification_count",
                    {"p_user_id": user_id},
                )
                .execute()
            )

            return NotificationModel._extract_rpc_int(res.data)

        except Exception as e:
            logger.warning(
                "[NotificationModel] get_unread_count RPC failed for user %s: %s. "
                "Fallback to service_role count.",
                user_id,
                e,
            )

            return NotificationModel._get_unread_count_fallback(user_id)

    @staticmethod
    def _get_unread_count_fallback(user_id: str) -> int:
        """
        Fallback khi RPC chưa tồn tại.

        Dùng service_role để không bị RLS chặn.
        Fallback này chỉ đếm user_notifications, không join notifications,
        nên có thể cao hơn nếu notification đã bị tắt.
        """
        if not user_id:
            return 0

        try:
            res = (
                NotificationModel._admin_db()
                .table("user_notifications")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("is_read", False)
                .eq("is_deleted", False)
                .execute()
            )

            return res.count or 0

        except Exception as e:
            logger.error(f"[NotificationModel] get_unread_count fallback {user_id} error: {e}")
            return 0