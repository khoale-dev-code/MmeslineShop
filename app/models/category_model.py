"""
app/models/category_model.py
============================
CRUD Danh mục hàng hóa thuần túy.

Cải thiện:
- Dùng get_supabase_admin() mặc định cho các thao tác admin để tránh lỗi RLS.
- Có retry nhẹ cho lỗi kết nối Supabase/httpx: Server disconnected, timeout.
- Fail-safe: lỗi đọc danh mục sẽ trả [] hoặc None thay vì làm sập trang.
- Slug tiếng Việt chuẩn hơn.
- Clean payload trước khi insert/update.
- Hỗ trợ tạo nhanh danh mục theo tên, tránh trùng slug cơ bản.
"""

import logging
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional, Callable, TypeVar

from postgrest.exceptions import APIError

from app.utils.supabase_client import get_supabase, get_supabase_admin

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CategoryModel:
    TABLE = "categories"

    DEFAULT_SELECT = (
        "id, name, slug, description, parent_id, "
        "is_active, sort_order, created_at"
    )

    # ═══════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _admin_db():
        """
        Service role client cho admin.
        Dùng client này cho admin dashboard/report/form để tránh RLS 401.
        """
        return get_supabase_admin()

    @staticmethod
    def _public_db():
        """
        Public/anon client cho storefront nếu cần.
        """
        return get_supabase()

    @staticmethod
    def _execute_with_retry(
        fn: Callable[[], T],
        *,
        fallback: T,
        label: str = "category_query",
        retries: int = 2,
        delay: float = 0.35,
    ) -> T:
        """
        Retry nhẹ cho lỗi mạng Supabase/PostgREST.

        Lỗi thường gặp:
        - httpx.RemoteProtocolError: Server disconnected
        - timeout
        - connection reset

        Không retry quá nhiều để tránh chậm trang admin.
        """
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                message = str(exc).lower()

                retryable = (
                    "server disconnected" in message
                    or "remoteprotocolerror" in message
                    or "timeout" in message
                    or "connection" in message
                    or "temporarily unavailable" in message
                )

                if not retryable or attempt >= retries:
                    break

                sleep_time = delay * (attempt + 1)
                logger.warning(
                    "[CategoryModel] %s lỗi kết nối, retry %s/%s sau %.2fs: %s",
                    label,
                    attempt + 1,
                    retries,
                    sleep_time,
                    exc,
                )
                time.sleep(sleep_time)

        logger.error("[CategoryModel] %s thất bại: %s", label, last_error, exc_info=True)
        return fallback

    @staticmethod
    def _clean_text(value: Any, max_len: int | None = None) -> str:
        text = str(value or "").strip()

        if max_len is not None:
            text = text[:max_len]

        return text

    @staticmethod
    def _clean_bool(value: Any, default: bool = True) -> bool:
        if value is None:
            return default

        if isinstance(value, bool):
            return value

        text = str(value).strip().lower()

        if text in {"1", "true", "yes", "on", "active"}:
            return True

        if text in {"0", "false", "no", "off", "inactive"}:
            return False

        return default

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _clean_payload(data: Dict[str, Any], *, for_update: bool = False) -> Dict[str, Any]:
        """
        Chỉ giữ các field category thật sự cần.
        Tránh gửi field lạ lên Supabase gây PGRST204 schema cache.
        """
        allowed_fields = {
            "name",
            "slug",
            "description",
            "parent_id",
            "is_active",
            "sort_order",
        }

        payload: Dict[str, Any] = {}

        for key, value in (data or {}).items():
            if key not in allowed_fields:
                continue

            if for_update and value is None:
                continue

            payload[key] = value

        if "name" in payload:
            payload["name"] = CategoryModel._clean_text(payload.get("name"), max_len=160)

        if "slug" in payload:
            payload["slug"] = CategoryModel.generate_slug(payload.get("slug"))

        if "description" in payload:
            desc = CategoryModel._clean_text(payload.get("description"), max_len=500)
            payload["description"] = desc or None

        if "parent_id" in payload:
            parent_id = CategoryModel._clean_text(payload.get("parent_id"), max_len=80)
            payload["parent_id"] = parent_id or None

        if "is_active" in payload:
            payload["is_active"] = CategoryModel._clean_bool(payload.get("is_active"))

        if "sort_order" in payload:
            payload["sort_order"] = CategoryModel._safe_int(payload.get("sort_order"), default=0)

        return payload

    # ═══════════════════════════════════════════════════════════════
    # SLUG
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def generate_slug(name: str) -> str:
        """
        Chuyển tiếng Việt sang slug an toàn.
        """
        text = str(name or "").strip().lower()

        if not text:
            return ""

        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = text.replace("đ", "d")

        text = re.sub(r"[^a-z0-9\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text)
        text = text.strip("-")

        return text[:180]

    @staticmethod
    def _ensure_unique_slug(base_slug: str, exclude_id: str | None = None) -> str:
        """
        Tạo slug không trùng.

        Nếu slug đã có:
        - ao-thun
        - ao-thun-2
        - ao-thun-3
        """
        db = CategoryModel._admin_db()

        base = CategoryModel.generate_slug(base_slug) or "danh-muc"
        slug = base

        for index in range(1, 50):
            def query_slug():
                q = (
                    db.table(CategoryModel.TABLE)
                    .select("id, slug")
                    .eq("slug", slug)
                    .limit(1)
                )

                if exclude_id:
                    q = q.neq("id", exclude_id)

                return q.execute().data or []

            rows = CategoryModel._execute_with_retry(
                query_slug,
                fallback=[],
                label="ensure_unique_slug",
                retries=1,
            )

            if not rows:
                return slug

            slug = f"{base}-{index + 1}"

        return f"{base}-{int(time.time())}"

    # ═══════════════════════════════════════════════════════════════
    # READ
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_all(
        active_only: bool = False,
        *,
        admin_mode: bool = True,
        parent_id: str | None = None,
    ) -> List[Dict]:
        """
        Lấy danh sách danh mục.

        admin_mode=True:
        - Dùng service role để trang admin không bị RLS/401.

        active_only=True:
        - Dùng cho storefront nếu chỉ muốn danh mục đang bật.
        """
        db = CategoryModel._admin_db() if admin_mode else CategoryModel._public_db()

        def run_query():
            query = db.table(CategoryModel.TABLE).select(CategoryModel.DEFAULT_SELECT)

            if active_only:
                query = query.eq("is_active", True)

            if parent_id is not None:
                query = query.eq("parent_id", parent_id)

            return (
                query
                .order("sort_order", desc=False)
                .order("name", desc=False)
                .execute()
                .data
                or []
            )

        return CategoryModel._execute_with_retry(
            run_query,
            fallback=[],
            label="get_all_categories",
            retries=2,
        )

    @staticmethod
    def get_active() -> List[Dict]:
        """
        Shortcut cho storefront.
        """
        return CategoryModel.get_all(active_only=True, admin_mode=False)

    @staticmethod
    def get_by_id(cid: str, *, admin_mode: bool = True) -> Optional[Dict]:
        if not cid:
            return None

        db = CategoryModel._admin_db() if admin_mode else CategoryModel._public_db()

        def run_query():
            res = (
                db.table(CategoryModel.TABLE)
                .select("*")
                .eq("id", cid)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None

        return CategoryModel._execute_with_retry(
            run_query,
            fallback=None,
            label=f"get_category_by_id:{cid}",
            retries=2,
        )

    @staticmethod
    def get_by_slug(slug: str, *, active_only: bool = False, admin_mode: bool = False) -> Optional[Dict]:
        clean_slug = CategoryModel.generate_slug(slug)

        if not clean_slug:
            return None

        db = CategoryModel._admin_db() if admin_mode else CategoryModel._public_db()

        def run_query():
            query = (
                db.table(CategoryModel.TABLE)
                .select("*")
                .eq("slug", clean_slug)
                .limit(1)
            )

            if active_only:
                query = query.eq("is_active", True)

            res = query.execute()
            return res.data[0] if res.data else None

        return CategoryModel._execute_with_retry(
            run_query,
            fallback=None,
            label=f"get_category_by_slug:{clean_slug}",
            retries=2,
        )

    # ═══════════════════════════════════════════════════════════════
    # CREATE / UPDATE / DELETE
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict:
        db = CategoryModel._admin_db()

        payload = CategoryModel._clean_payload(data or {})

        if not payload.get("name"):
            logger.warning("[CategoryModel.create] Thiếu tên danh mục.")
            return {}

        if not payload.get("slug"):
            payload["slug"] = CategoryModel.generate_slug(payload["name"])

        payload["slug"] = CategoryModel._ensure_unique_slug(payload["slug"])

        if "is_active" not in payload:
            payload["is_active"] = True

        if "sort_order" not in payload:
            payload["sort_order"] = 0

        def run_query():
            res = db.table(CategoryModel.TABLE).insert(payload).execute()
            return res.data[0] if res.data else {}

        return CategoryModel._execute_with_retry(
            run_query,
            fallback={},
            label="create_category",
            retries=1,
        )

    @staticmethod
    def update(cid: str, data: Dict[str, Any]) -> Dict:
        if not cid:
            return {}

        db = CategoryModel._admin_db()

        payload = CategoryModel._clean_payload(data or {}, for_update=True)

        if not payload:
            return CategoryModel.get_by_id(cid) or {}

        if payload.get("slug"):
            payload["slug"] = CategoryModel._ensure_unique_slug(payload["slug"], exclude_id=cid)
        elif payload.get("name"):
            payload["slug"] = CategoryModel._ensure_unique_slug(
                CategoryModel.generate_slug(payload["name"]),
                exclude_id=cid,
            )

        def run_query():
            res = (
                db.table(CategoryModel.TABLE)
                .update(payload)
                .eq("id", cid)
                .execute()
            )
            return res.data[0] if res.data else {}

        return CategoryModel._execute_with_retry(
            run_query,
            fallback={},
            label=f"update_category:{cid}",
            retries=1,
        )

    @staticmethod
    def delete(cid: str) -> bool:
        """
        Xóa cứng danh mục.

        Nếu DB có khóa ngoại product_categories đang tham chiếu category_id,
        Supabase có thể chặn xóa. Khi đó nên dùng deactivate() thay vì delete().
        """
        if not cid:
            return False

        db = CategoryModel._admin_db()

        def run_query():
            res = (
                db.table(CategoryModel.TABLE)
                .delete()
                .eq("id", cid)
                .execute()
            )
            return bool(res.data)

        return CategoryModel._execute_with_retry(
            run_query,
            fallback=False,
            label=f"delete_category:{cid}",
            retries=1,
        )

    @staticmethod
    def deactivate(cid: str) -> bool:
        """
        Ẩn danh mục thay vì xóa cứng.
        An toàn hơn nếu category đang được gắn với sản phẩm.
        """
        if not cid:
            return False

        result = CategoryModel.update(cid, {"is_active": False})
        return bool(result)

    # ═══════════════════════════════════════════════════════════════
    # QUICK CREATE FOR PRODUCT FORM
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def get_or_create_by_name(name: str) -> Dict:
        """
        Dùng cho product_form: nhập danh mục mới nhanh.

        Nếu đã có slug tương ứng thì trả danh mục cũ.
        Nếu chưa có thì tạo mới.
        """
        clean_name = CategoryModel._clean_text(name, max_len=160)

        if not clean_name:
            return {}

        slug = CategoryModel.generate_slug(clean_name)

        existing = CategoryModel.get_by_slug(slug, admin_mode=True)

        if existing:
            return existing

        return CategoryModel.create({
            "name": clean_name,
            "slug": slug,
            "is_active": True,
            "sort_order": 0,
        })

    @staticmethod
    def bulk_get_or_create(names: List[str]) -> List[Dict]:
        """
        Tạo nhanh nhiều danh mục.
        Hỗ trợ dữ liệu từ textarea:
        - mỗi dòng một danh mục
        - hoặc đã được controller split bằng dấu phẩy
        """
        output: List[Dict] = []
        seen: set[str] = set()

        for raw_name in names or []:
            name = CategoryModel._clean_text(raw_name, max_len=160)

            if not name:
                continue

            key = CategoryModel.generate_slug(name)

            if not key or key in seen:
                continue

            seen.add(key)

            category = CategoryModel.get_or_create_by_name(name)

            if category:
                output.append(category)

        return output