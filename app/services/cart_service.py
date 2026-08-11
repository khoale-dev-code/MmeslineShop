"""Business rules for GUAMAISON carts.

The service is intentionally Flask-free.  Controllers pass plain values in and
receive data objects/dictionaries back.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, Iterable

from app.models.cart_model import CartMutation, CartPage, CartSelection, CartSummary
from app.repositories.cart_repository import CartRepository


logger = logging.getLogger(__name__)
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _unit_price(item: dict[str, Any]) -> float:
    variant = item.get("product_variants") or {}
    product = item.get("products") or {}
    value = variant.get("price_override")
    return _float(product.get("price")) if value is None else _float(value)


class CartService:
    def __init__(self, repository: CartRepository):
        self.repository = repository

    @staticmethod
    def _ids(values: Any) -> tuple[str, ...]:
        if isinstance(values, str):
            values = [part.strip() for part in values.split(",")]
        if not isinstance(values, (list, tuple, set)):
            values = []

        clean: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = str(raw or "").strip()
            if value and UUID_RE.fullmatch(value) and value not in seen:
                clean.append(value)
                seen.add(value)
        return tuple(clean)

    def selection_from_payload(self, payload: dict[str, Any] | None) -> CartSelection:
        payload = payload or {}
        mode = "all" if payload.get("mode") == "all" else "explicit"
        return CartSelection(
            mode=mode,
            item_ids=self._ids(payload.get("item_ids") or payload.get("selected_ids")),
            excluded_ids=self._ids(payload.get("excluded_ids")),
        )

    def get_page(self, user_id: str, page: int = 1, per_page: int = 24, query: str = "") -> CartPage:
        page = max(1, _int(page, 1))
        per_page = min(48, max(12, _int(per_page, 24)))
        query = str(query or "").strip()[:80]

        items, total = self.repository.get_page(user_id, page, per_page, query)
        max_page = max(1, (total + per_page - 1) // per_page)
        if page > max_page:
            page = max_page
            items, total = self.repository.get_page(user_id, page, per_page, query)

        return CartPage(tuple(items), page, per_page, total, query)

    def get_user_cart(self, user_id: str) -> list[dict[str, Any]]:
        return self.repository.list_all_items(user_id)

    def get_count(self, user_id: str) -> int:
        return self.repository.get_line_count(user_id)

    def calculate_total(self, items: Iterable[dict[str, Any]]) -> float:
        return sum(max(0, _int(item.get("quantity"))) * _unit_price(item) for item in items)

    def items_for_selection(self, user_id: str, selection: CartSelection) -> list[dict[str, Any]]:
        if selection.mode == "all":
            return self.repository.list_all_items(user_id, selection.excluded_ids)
        if not selection.item_ids:
            return []
        return self.repository.get_items_by_ids(user_id, selection.item_ids)

    def get_summary(self, user_id: str, selection: CartSelection) -> CartSummary:
        rpc = self.repository.selection_summary_rpc(user_id, selection)
        if rpc is not None:
            return CartSummary(
                line_count=max(0, _int(rpc.get("line_count"))),
                quantity=max(0, _int(rpc.get("quantity"))),
                total=max(0.0, _float(rpc.get("total"))),
            )

        items = self.items_for_selection(user_id, selection)
        return CartSummary(
            line_count=len(items),
            quantity=sum(max(0, _int(item.get("quantity"))) for item in items),
            total=self.calculate_total(items),
        )

    def prepare_checkout(self, user_id: str, selection: CartSelection) -> tuple[str | None, dict[str, Any] | None, CartSummary]:
        summary = self.get_summary(user_id, selection)
        if summary.line_count <= 0:
            return None, None, summary

        selection_id = self.repository.create_checkout_selection(user_id, selection)
        fallback = None if selection_id else selection.to_record()
        return selection_id, fallback, summary

    def resolve_checkout_selection(
        self,
        user_id: str,
        selection_id: str | None,
        fallback: dict[str, Any] | None = None,
    ) -> CartSelection:
        if selection_id and UUID_RE.fullmatch(str(selection_id)):
            selected = self.repository.get_checkout_selection(user_id, str(selection_id))
            if selected:
                return selected
        if fallback:
            return self.selection_from_payload(fallback)
        return CartSelection(mode="all")

    def delete_checkout_selection(self, user_id: str, selection_id: str | None) -> None:
        self.repository.delete_checkout_selection(user_id, selection_id)

    def add_item(self, user_id: str, product_id: str, variant_id: str, quantity: int = 1) -> CartMutation:
        quantity = max(1, _int(quantity, 1))
        variant = self.repository.get_variant(variant_id)
        if not variant or str(variant.get("product_id")) != str(product_id):
            return CartMutation(False, "Biến thể sản phẩm không hợp lệ.")

        stock = max(0, _int(variant.get("stock")))
        if stock <= 0:
            return CartMutation(False, "Phân loại này đã hết hàng.")

        existing = self.repository.get_item_by_variant(user_id, variant_id)
        if existing:
            new_quantity = min(stock, max(0, _int(existing.get("quantity"))) + quantity)
            item = self.repository.update_item(user_id, str(existing["id"]), {"quantity": new_quantity})
        else:
            item = self.repository.insert_item({
                "user_id": user_id,
                "product_id": product_id,
                "variant_id": variant_id,
                "quantity": min(quantity, stock),
                "size": variant.get("size"),
                "color": variant.get("color_name"),
            })

        if not item:
            return CartMutation(False, "Không thể thêm sản phẩm vào giỏ.")
        return CartMutation(True, "Đã thêm sản phẩm vào giỏ.", affected=1, item=item)

    def update_quantity(self, user_id: str, item_id: str, quantity: int) -> CartMutation:
        item = self.repository.get_item(user_id, item_id)
        if not item:
            return CartMutation(False, "Sản phẩm không còn trong giỏ.")

        quantity = _int(quantity, 1)
        if quantity <= 0:
            removed = self.repository.delete_item(user_id, item_id)
            return CartMutation(removed, "Đã xóa sản phẩm." if removed else "Không thể xóa sản phẩm.", int(removed))

        variant = item.get("product_variants") or {}
        stock = max(0, _int(variant.get("stock")))
        if stock <= 0:
            return CartMutation(False, "Phân loại này đã hết hàng.")

        safe_quantity = min(quantity, stock)
        updated = self.repository.update_item(user_id, item_id, {"quantity": safe_quantity})
        if not updated:
            return CartMutation(False, "Không thể cập nhật số lượng.")

        message = "Đã cập nhật số lượng."
        if safe_quantity < quantity:
            message = f"Kho chỉ còn {stock} sản phẩm; số lượng đã được điều chỉnh."
        return CartMutation(True, message, affected=1, item=updated)

    def remove_item(self, user_id: str, item_id: str) -> CartMutation:
        removed = self.repository.delete_item(user_id, item_id)
        return CartMutation(
            removed,
            "Đã xóa sản phẩm khỏi giỏ." if removed else "Không tìm thấy sản phẩm trong giỏ.",
            affected=int(removed),
        )

    def get_variant_editor(self, user_id: str, item_id: str) -> dict[str, Any] | None:
        item = self.repository.get_item(user_id, item_id)
        if not item:
            return None
        product = item.get("products") or {}
        current_variant = item.get("product_variants") or {}
        if isinstance(product, list):
            product = product[0] if product else {}
        if isinstance(current_variant, list):
            current_variant = current_variant[0] if current_variant else {}

        variants = [
            variant
            for variant in self.repository.get_product_variants(str(item.get("product_id") or ""))
            if isinstance(variant, dict) and variant.get("id")
        ]
        current_variant_id = str(item.get("variant_id") or current_variant.get("id") or "")
        return {
            "item": item,
            "product": product,
            "current_variant": current_variant,
            "current_variant_id": current_variant_id,
            "variants": variants,
        }

    def change_variant(self, user_id: str, item_id: str, variant_id: str) -> CartMutation:
        rpc = self.repository.change_variant_rpc(user_id, item_id, variant_id)
        if rpc is not None:
            return CartMutation(
                bool(rpc.get("success")),
                str(rpc.get("message") or "Đã cập nhật phân loại."),
                affected=max(0, _int(rpc.get("affected"), 1)),
                item=rpc.get("item") if isinstance(rpc.get("item"), dict) else None,
            )

        current = self.repository.get_item(user_id, item_id, with_relations=False)
        target = self.repository.get_variant(variant_id)
        if not current or not target or str(target.get("product_id")) != str(current.get("product_id")):
            return CartMutation(False, "Phân loại không hợp lệ cho sản phẩm này.")

        stock = max(0, _int(target.get("stock")))
        if stock <= 0:
            return CartMutation(False, "Phân loại bạn chọn đã hết hàng.")
        if str(current.get("variant_id")) == str(variant_id):
            return CartMutation(True, "Sản phẩm đã dùng phân loại này.", affected=0, item=current)

        other = self.repository.get_item_by_variant(user_id, variant_id)
        if other and str(other.get("id")) != str(item_id):
            old_quantity = max(1, _int(other.get("quantity"), 1))
            merged_quantity = min(stock, old_quantity + max(1, _int(current.get("quantity"), 1)))
            updated = self.repository.update_item(user_id, str(other["id"]), {"quantity": merged_quantity})
            if not updated:
                return CartMutation(False, "Không thể gộp phân loại trong giỏ.")
            if not self.repository.delete_item(user_id, item_id):
                self.repository.update_item(user_id, str(other["id"]), {"quantity": old_quantity})
                return CartMutation(False, "Không thể hoàn tất đổi phân loại; giỏ đã được giữ nguyên.")
            return CartMutation(True, "Đã đổi phân loại và gộp với sản phẩm có sẵn.", affected=2, item=updated)

        updated = self.repository.update_item(user_id, item_id, {
            "variant_id": variant_id,
            "size": target.get("size"),
            "color": target.get("color_name"),
            "quantity": min(stock, max(1, _int(current.get("quantity"), 1))),
        })
        if not updated:
            return CartMutation(False, "Không thể đổi phân loại.")
        return CartMutation(True, "Đã cập nhật size và màu.", affected=1, item=updated)

    def remove_selection(self, user_id: str, selection: CartSelection) -> CartMutation:
        summary = self.get_summary(user_id, selection)
        if summary.line_count <= 0:
            return CartMutation(False, "Bạn chưa chọn sản phẩm cần xóa.")

        affected = self.repository.delete_selection_rpc(user_id, selection)
        if affected is None:
            if selection.mode == "all":
                excluded = set(selection.excluded_ids)
                ids = [item_id for item_id in self.repository.list_all_ids(user_id) if item_id not in excluded]
            else:
                ids = list(selection.item_ids)
            affected = self.repository.delete_ids(user_id, ids)

        if affected <= 0:
            return CartMutation(False, "Không có sản phẩm nào được xóa.")
        return CartMutation(True, f"Đã xóa {affected} sản phẩm khỏi giỏ.", affected=affected)

    def remove_purchased_items(self, user_id: str, order_items: Iterable[dict[str, Any]]) -> int:
        """Subtract only purchased quantities, preserving later cart additions."""
        purchased: dict[str, int] = defaultdict(int)
        for item in order_items or []:
            variant_id = str(item.get("variant_id") or "")
            if UUID_RE.fullmatch(variant_id):
                purchased[variant_id] += max(1, _int(item.get("quantity"), 1))

        affected = 0
        for variant_id, quantity in purchased.items():
            current = self.repository.get_item_by_variant(user_id, variant_id)
            if not current:
                continue
            remaining = max(0, _int(current.get("quantity")) - quantity)
            if remaining:
                affected += int(bool(self.repository.update_item(user_id, str(current["id"]), {"quantity": remaining})))
            else:
                affected += int(self.repository.delete_item(user_id, str(current["id"])))
        return affected

    def clear_cart(self, user_id: str) -> int:
        return self.repository.clear_cart(user_id)


cart_service = CartService(CartRepository())
