import logging
from typing import Any, Dict

from app.repositories.favorite_repository import FavoriteRepository

logger = logging.getLogger(__name__)


class FavoriteService:
    @staticmethod
    def toggle_favorite(user_id: str, product_id: str) -> Dict[str, Any]:
        if not user_id:
            raise ValueError("Vui lòng đăng nhập.")

        if not product_id:
            raise ValueError("Thiếu mã sản phẩm.")

        action = FavoriteRepository.toggle(user_id, product_id)

        return {
            "status": "success",
            "action": action,
            "message": "Đã thêm vào yêu thích" if action == "added" else "Đã xóa khỏi yêu thích",
            "product_id": product_id,
        }

    @staticmethod
    def get_user_wishlist(user_id: str, page: int = 1, per_page: int = 24) -> Dict[str, Any]:
        page = max(1, int(page or 1))
        per_page = max(1, min(int(per_page or 24), 100))
        offset = (page - 1) * per_page

        items = FavoriteRepository.get_user_favorites(
            user_id=user_id,
            limit=per_page,
            offset=offset,
        )

        total = FavoriteRepository.count_user_favorites(user_id)
        pages = max(1, (total + per_page - 1) // per_page)

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "has_prev": page > 1,
            "has_next": page < pages,
        }