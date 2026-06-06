import logging
from typing import Any, Dict, List

try:
    from app.utils.supabase_client import get_supabase_admin
except Exception:
    get_supabase_admin = None

from config.settings import get_supabase_client

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom Exception cho các lỗi liên quan đến Database."""
    pass


def _db_admin():
    """
    Dùng service role/admin client cho server-side repository.
    Nếu project chưa có get_supabase_admin thì fallback về client cũ.
    """
    if get_supabase_admin:
        return get_supabase_admin()

    return get_supabase_client()


class FavoriteRepository:
    @staticmethod
    def toggle(user_id: str, product_id: str) -> str:
        db = _db_admin()

        if not user_id or not product_id:
            raise ValueError("Thiếu user_id hoặc product_id.")

        try:
            existing = (
                db.table("favorites")
                .select("id")
                .eq("user_id", user_id)
                .eq("product_id", product_id)
                .limit(1)
                .execute()
            )

            if existing.data:
                (
                    db.table("favorites")
                    .delete()
                    .eq("user_id", user_id)
                    .eq("product_id", product_id)
                    .execute()
                )
                return "removed"

            (
                db.table("favorites")
                .insert({
                    "user_id": user_id,
                    "product_id": product_id,
                })
                .execute()
            )

            return "added"

        except Exception as exc:
            logger.exception(
                "[FAVORITE_REPO] Toggle failed | user_id=%s | product_id=%s",
                user_id,
                product_id,
            )
            raise DatabaseError("Lỗi hệ thống khi thao tác dữ liệu yêu thích.") from exc

    @staticmethod
    def get_user_favorites(
        user_id: str,
        limit: int = 24,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        db = _db_admin()

        if not user_id:
            return []

        limit = max(1, min(int(limit or 24), 100))
        offset = max(0, int(offset or 0))

        try:
            response = (
                db.table("favorites")
                .select(
                    """
                    id,
                    user_id,
                    product_id,
                    created_at,
                    products(
                        id,
                        name,
                        slug,
                        price,
                        stock,
                        thumbnail_url,
                        is_active,
                        deleted_at
                    )
                    """
                )
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

            return FavoriteRepository._normalize_rows(response.data or [])

        except Exception as join_error:
            logger.warning(
                "[FAVORITE_REPO] Join products failed, fallback 2 queries | user_id=%s | error=%s",
                user_id,
                join_error,
            )

            try:
                return FavoriteRepository._get_user_favorites_fallback(
                    user_id=user_id,
                    limit=limit,
                    offset=offset,
                )
            except Exception as fallback_error:
                logger.exception(
                    "[FAVORITE_REPO] Fallback failed | user_id=%s",
                    user_id,
                )
                raise DatabaseError("Không thể tải danh sách yêu thích.") from fallback_error

    @staticmethod
    def count_user_favorites(user_id: str) -> int:
        db = _db_admin()

        if not user_id:
            return 0

        try:
            response = (
                db.table("favorites")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .execute()
            )

            return int(response.count or 0)

        except Exception:
            logger.warning(
                "[FAVORITE_REPO] Count failed | user_id=%s",
                user_id,
                exc_info=True,
            )
            return 0

    @staticmethod
    def _get_user_favorites_fallback(
        user_id: str,
        limit: int,
        offset: int,
    ) -> List[Dict[str, Any]]:
        db = _db_admin()

        fav_res = (
            db.table("favorites")
            .select("id, user_id, product_id, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        fav_rows = fav_res.data or []

        if not fav_rows:
            return []

        product_ids = [
            row.get("product_id")
            for row in fav_rows
            if row.get("product_id")
        ]

        if not product_ids:
            return []

        product_res = (
            db.table("products")
            .select(
                """
                id,
                name,
                slug,
                price,
                stock,
                thumbnail_url,
                is_active,
                deleted_at
                """
            )
            .in_("id", product_ids)
            .execute()
        )

        products = product_res.data or []

        product_map = {
            product.get("id"): product
            for product in products
            if product.get("id")
        }

        rows = []

        for fav in fav_rows:
            product = product_map.get(fav.get("product_id"))

            if not product:
                continue

            fav["products"] = product
            rows.append(fav)

        return FavoriteRepository._normalize_rows(rows)

    @staticmethod
    def _normalize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []

        for row in rows or []:
            if not isinstance(row, dict):
                continue

            product = row.get("products")

            if isinstance(product, list):
                product = product[0] if product else None

            if not product or not isinstance(product, dict):
                continue

            if product.get("deleted_at"):
                continue

            if product.get("is_active") is False:
                continue

            product["price"] = product.get("price") or 0
            product["stock"] = product.get("stock") or 0
            product["name"] = product.get("name") or "Sản phẩm MMESTLINE"
            product["slug"] = product.get("slug") or product.get("id")
            product["thumbnail_url"] = product.get("thumbnail_url") or ""

            row["products"] = product
            normalized.append(row)

        return normalized