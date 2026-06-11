"""
app/services/audit_service.py
Service ghi nhận và truy xuất lịch sử thao tác của Admin/Staff.
"""

import logging
from datetime import datetime, timedelta, timezone
from flask import request, session
from app.utils.supabase_client import get_supabase, get_supabase_admin
logger = logging.getLogger(__name__)

class AuditService:

   @staticmethod
   def log_action(action: str, table_name: str, record_id: str = None, old_values: dict = None, new_values: dict = None):
    try:
        db = get_supabase_admin()

        user_id = session.get("user_id")
        ip_address = request.headers.get("X-Forwarded-For", request.remote_addr) if request else None

        log_data = {
            "action": action,
            "table_name": table_name,
            "old_values": old_values if old_values else {},
            "new_values": new_values if new_values else {},
            "ip_address": ip_address,
        }

        if user_id:
            log_data["user_id"] = user_id

        if record_id:
            log_data["record_id"] = str(record_id)

        db.table("audit_logs").insert(log_data).execute()

    except Exception as e:
        logger.error(f"[AuditService] Lỗi ghi log thao tác: {e}")

    @staticmethod
    def get_recent_logs(days: int = 7, role_slug: str = None, page: int = 1, per_page: int = 50) -> dict:
        """
        Lấy danh sách log trong X ngày qua. Có thể lọc theo nhóm quyền (role_slug).
        """
        db = get_supabase()
        try:
            # Mốc thời gian 7 ngày trước
            time_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            # Nếu lọc theo Role, bắt buộc dùng !inner join để filter trên bảng users
            if role_slug:
                query = db.table("audit_logs").select("*, users!inner(full_name, email, admin_role_slug)", count="exact")
                query = query.eq("users.admin_role_slug", role_slug)
            else:
                query = db.table("audit_logs").select("*, users(full_name, email, admin_role_slug)", count="exact")

            query = query.gte("created_at", time_threshold).order("created_at", desc=True)
            
            offset = (page - 1) * per_page
            res = query.range(offset, offset + per_page - 1).execute()
            
            return {
                "items": res.data or [],
                "total": res.count or 0,
                "total_pages": max(1, -(- (res.count or 0) // per_page))
            }
        except Exception as e:
            logger.error(f"[AuditService] Lỗi get_recent_logs: {e}")
            return {"items": [], "total": 0, "total_pages": 1}