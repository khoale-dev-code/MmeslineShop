"""Business rules for broadcasts sent from Admin to customers."""

from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.broadcast_notification_repository import BroadcastNotificationRepository


class BroadcastValidationError(ValueError):
    pass


class BroadcastNotificationService:
    def __init__(self, repository: BroadcastNotificationRepository | None = None) -> None:
        self.repository = repository or BroadcastNotificationRepository()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def normalize(data: dict) -> dict:
        title = " ".join(str(data.get("title") or "").split())[:180]
        content = str(data.get("content") or "").strip()[:4000]
        if not title or not content:
            raise BroadcastValidationError("Vui lòng nhập đầy đủ tiêu đề và nội dung.")
        try:
            sort_order = int(data.get("sort_order") or 0)
        except (TypeError, ValueError) as exc:
            raise BroadcastValidationError("Thứ tự hiển thị không hợp lệ.") from exc
        start_at = str(data.get("start_at") or "").strip() or None
        end_at = str(data.get("end_at") or "").strip() or None
        if start_at and end_at and end_at <= start_at:
            raise BroadcastValidationError("Thời gian kết thúc phải sau thời gian bắt đầu.")
        link = str(data.get("link") or "").strip()[:500] or None
        if link and not (link.startswith("/") or link.startswith("https://")):
            raise BroadcastValidationError("Liên kết phải là đường dẫn nội bộ hoặc HTTPS.")
        return {
            "title": title,
            "content": content,
            "is_active": bool(data.get("is_active")),
            "is_permanent": bool(data.get("is_permanent")),
            "start_at": start_at,
            "end_at": end_at,
            "link": link,
            "link_text": " ".join(str(data.get("link_text") or "").split())[:100] or None,
            "sort_order": sort_order,
        }

    def list_all(self) -> list[dict]:
        return self.repository.list_all()

    def get(self, notification_id: str) -> dict | None:
        return self.repository.get(notification_id)

    def create(self, data: dict) -> dict | None:
        item = self.repository.create(self.normalize(data))
        if item:
            self.fan_out(item["id"])
        return item

    def update(self, notification_id: str, data: dict) -> bool:
        payload = self.normalize(data)
        payload["updated_at"] = self._now()
        return self.repository.update(notification_id, payload)

    def toggle(self, notification_id: str) -> bool:
        item = self.repository.get(notification_id)
        if not item:
            return False
        return self.repository.update(notification_id, {"is_active": not bool(item.get("is_active")), "updated_at": self._now()})

    def delete(self, notification_id: str) -> bool:
        return self.repository.delete(notification_id)

    def fan_out(self, notification_id: str) -> int:
        existing = self.repository.existing_user_ids(notification_id)
        rows = [
            {"user_id": user_id, "notification_id": notification_id, "is_read": False, "is_deleted": False}
            for user_id in self.repository.customer_ids()
            if user_id not in existing
        ]
        return self.repository.insert_user_notifications(rows) if rows else 0

