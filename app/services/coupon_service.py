"""Promotion business rules shared by Admin, storefront and checkout."""

from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from app.models.coupon_model import CouponApplication, CouponDraft, CouponFormOptions, CouponScope
from app.repositories.coupon_repository import CouponRepository, CouponRepositoryError, CouponRepositoryUnavailable


class CouponValidationError(ValueError):
    pass


class CouponConflictError(CouponValidationError):
    pass


class CouponNotFoundError(CouponValidationError):
    pass


class CouponService:
    WRITE_FIELDS = {
        "code", "description", "discount_type", "discount_value", "max_discount",
        "min_order_value", "usage_limit", "usage_per_user", "starts_at", "expires_at",
        "is_stackable", "is_active", "is_first_order_only", "max_usage_per_day",
        "image_url", "applicable_channel", "min_loyalty_points",
    }

    def __init__(
        self,
        repository: CouponRepository,
        *,
        now: Callable[[], datetime] | None = None,
        local_timezone: str | None = None,
    ) -> None:
        self.repository = repository
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._local_tz = ZoneInfo(local_timezone or os.getenv("COUPON_TIMEZONE", "Asia/Ho_Chi_Minh"))

    @staticmethod
    def normalize_code(value: Any) -> str:
        normalized = unicodedata.normalize("NFD", str(value or "").strip())
        normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        return re.sub(r"[^A-Z0-9_-]", "", normalized.upper().replace("Đ", "D"))[:50]

    @staticmethod
    def _bool(form: dict, key: str, default: bool = False) -> bool:
        if key not in form:
            return default
        return str(form.get(key) or "").strip().lower() in {"1", "true", "on", "yes", "checked"}

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value) if value is not None and str(value).strip() else default
        except (TypeError, ValueError):
            raise CouponValidationError("Giá trị tiền hoặc phần trăm không hợp lệ.")

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None or not str(value).strip():
            return None
        return CouponService._float(value)

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None or not str(value).strip():
            return None
        try:
            number = int(float(value))
        except (TypeError, ValueError):
            raise CouponValidationError("Giới hạn lượt dùng phải là số nguyên.")
        return number if number > 0 else None

    def _form_datetime_to_utc(self, value: Any) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CouponValidationError("Thời gian khuyến mãi không hợp lệ.") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=self._local_tz)
        return parsed.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _as_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None

    def _local_input_value(self, value: Any) -> str:
        parsed = self._as_datetime(value)
        return parsed.astimezone(self._local_tz).strftime("%Y-%m-%dT%H:%M") if parsed else ""

    def parse_draft(self, form: dict, category_ids: list[str], product_ids: list[str]) -> CouponDraft:
        code = self.normalize_code(form.get("code"))
        if not code:
            raise CouponValidationError("Mã khuyến mãi không hợp lệ.")

        discount_type = str(form.get("discount_type") or "percent")
        if discount_type not in {"percent", "fixed", "free_shipping"}:
            raise CouponValidationError("Loại khuyến mãi không hợp lệ.")

        discount_value = self._float(form.get("discount_value"), 0)
        max_discount = self._optional_float(form.get("max_discount"))
        if discount_type == "percent" and not 0 < discount_value <= 100:
            raise CouponValidationError("Mức giảm phần trăm phải lớn hơn 0 và không vượt quá 100%.")
        if discount_type == "fixed" and discount_value <= 0:
            raise CouponValidationError("Mức giảm tiền phải lớn hơn 0.")
        if discount_type == "free_shipping":
            discount_value, max_discount = 0.0, None
        elif discount_type == "fixed":
            max_discount = None
        if max_discount is not None and max_discount <= 0:
            raise CouponValidationError("Mức giảm tối đa phải lớn hơn 0.")

        min_order = self._float(form.get("min_order_value"), 0)
        if min_order < 0:
            raise CouponValidationError("Giá trị đơn tối thiểu không được âm.")

        starts_at = self._form_datetime_to_utc(form.get("starts_at"))
        expires_at = self._form_datetime_to_utc(form.get("expires_at"))
        if starts_at and expires_at and self._as_datetime(expires_at) <= self._as_datetime(starts_at):
            raise CouponValidationError("Thời gian kết thúc phải sau thời gian bắt đầu.")

        channel = str(form.get("applicable_channel") or "all")
        if channel not in {"all", "web", "pos"}:
            raise CouponValidationError("Kênh áp dụng không hợp lệ.")

        scope_kind = str(form.get("scope") or "all")
        if scope_kind not in {"all", "category", "product"}:
            scope_kind = "all"
        raw_scope_ids = category_ids if scope_kind == "category" else product_ids if scope_kind == "product" else []
        scope_ids = tuple(dict.fromkeys(str(item_id) for item_id in raw_scope_ids if item_id))
        if scope_kind != "all" and not scope_ids:
            raise CouponValidationError("Hãy chọn ít nhất một danh mục hoặc sản phẩm cho phạm vi áp dụng.")

        image_url = str(form.get("image_url") or "").strip()[:2000] or None
        if image_url and urlparse(image_url).scheme.lower() not in {"http", "https"}:
            raise CouponValidationError("Ảnh editorial phải dùng đường dẫn http hoặc https.")

        return CouponDraft(
            code=code,
            description=str(form.get("description") or "").strip()[:500],
            discount_type=discount_type,
            discount_value=discount_value,
            max_discount=max_discount,
            min_order_value=min_order,
            usage_limit=self._optional_int(form.get("usage_limit")),
            usage_per_user=self._optional_int(form.get("usage_per_user")),
            starts_at=starts_at,
            expires_at=expires_at,
            is_stackable=self._bool(form, "is_stackable"),
            is_active=self._bool(form, "is_active", False),
            is_first_order_only=self._bool(form, "is_first_order_only"),
            max_usage_per_day=self._optional_int(form.get("max_usage_per_day")),
            image_url=image_url,
            applicable_channel=channel,
            min_loyalty_points=max(0, int(self._float(form.get("min_loyalty_points"), 0))),
            scope=CouponScope(scope_kind, scope_ids),
        )

    @staticmethod
    def _payload(draft: CouponDraft) -> dict:
        return {field: getattr(draft, field) for field in CouponService.WRITE_FIELDS}

    def form_options(self) -> CouponFormOptions:
        categories: list[dict] = []
        products: list[dict] = []
        unavailable: list[str] = []
        try:
            categories = self.repository.list_categories()
        except CouponRepositoryUnavailable:
            unavailable.append("danh mục")
        try:
            products = self.repository.list_products()
        except CouponRepositoryUnavailable:
            unavailable.append("sản phẩm")
        warning = "Không tải được " + " và ".join(unavailable) + ". Bạn vẫn có thể lưu voucher áp dụng cho toàn bộ cửa hàng." if unavailable else ""
        return CouponFormOptions(tuple(categories), tuple(products), warning)

    def create(self, form: dict, category_ids: list[str], product_ids: list[str]) -> dict:
        draft = self.parse_draft(form, category_ids, product_ids)
        if self.repository.get_by_code(draft.code):
            raise CouponConflictError(f"Mã '{draft.code}' đã tồn tại.")
        created = self.repository.create(self._payload(draft))
        try:
            self.repository.replace_scope(str(created["id"]), draft.scope)
        except CouponRepositoryError:
            try:
                self.repository.delete(str(created["id"]))
            except CouponRepositoryError:
                pass
            raise
        return created

    def update(self, coupon_id: str, form: dict, category_ids: list[str], product_ids: list[str]) -> dict:
        previous = self.repository.get_by_id(coupon_id)
        if not previous:
            raise CouponNotFoundError("Voucher không tồn tại.")
        previous_scope = self.repository.scope_for(coupon_id)
        draft = self.parse_draft(form, category_ids, product_ids)
        same_code = self.repository.get_by_code(draft.code)
        if same_code and str(same_code.get("id")) != str(coupon_id):
            raise CouponConflictError(f"Mã '{draft.code}' đã được dùng cho voucher khác.")
        try:
            updated = self.repository.update(coupon_id, self._payload(draft))
            self.repository.replace_scope(coupon_id, draft.scope)
            return updated
        except CouponRepositoryError:
            rollback_payload = {key: previous.get(key) for key in self.WRITE_FIELDS}
            try:
                self.repository.update(coupon_id, rollback_payload)
                self.repository.replace_scope(coupon_id, previous_scope)
            except CouponRepositoryError:
                pass
            raise

    def delete(self, coupon_id: str) -> None:
        if not self.repository.get_by_id(coupon_id):
            raise CouponNotFoundError("Voucher không tồn tại.")
        self.repository.delete(coupon_id)

    def toggle(self, coupon_id: str) -> tuple[str, bool]:
        coupon = self.repository.get_by_id(coupon_id)
        if not coupon:
            raise CouponNotFoundError("Voucher không tồn tại.")
        active = not bool(coupon.get("is_active"))
        self.repository.set_active(coupon_id, active)
        return str(coupon.get("code") or ""), active

    def admin_page(self, page: int, per_page: int, filter_mode: str) -> tuple[list[dict], int]:
        rows, total = self.repository.list_admin(page, per_page, filter_mode, self._now().isoformat())
        try:
            counts = self.repository.usage_counts([str(row.get("id")) for row in rows if row.get("id")])
        except CouponRepositoryUnavailable:
            counts = {}
        for row in rows:
            row["used_count"] = counts.get(str(row.get("id")), 0)
        return rows, total

    def now_iso(self) -> str:
        return self._now().astimezone(timezone.utc).isoformat()

    def admin_form_coupon(self, coupon_id: str) -> dict:
        coupon = self.repository.get_by_id(coupon_id)
        if not coupon:
            raise CouponNotFoundError("Voucher không tồn tại.")
        scope = self.repository.scope_for(coupon_id)
        view = dict(coupon)
        view["scope"] = scope.kind
        view["scope_ids"] = list(scope.ids)
        view["starts_at"] = self._local_input_value(coupon.get("starts_at"))
        view["expires_at"] = self._local_input_value(coupon.get("expires_at"))
        view["used_count"] = self.repository.usage_counts([coupon_id]).get(coupon_id, 0)
        return view

    def usage_history(self, coupon_id: str) -> tuple[dict, list[dict]]:
        coupon = self.repository.get_by_id(coupon_id)
        if not coupon:
            raise CouponNotFoundError("Voucher không tồn tại.")
        return coupon, self.repository.usages(coupon_id)

    def _is_live(self, coupon: dict, channel: str = "web") -> bool:
        now = self._now().astimezone(timezone.utc)
        starts_at = self._as_datetime(coupon.get("starts_at"))
        expires_at = self._as_datetime(coupon.get("expires_at"))
        coupon_channel = coupon.get("applicable_channel") or "all"
        return bool(
            coupon.get("is_active")
            and (not starts_at or starts_at <= now)
            and (not expires_at or expires_at > now)
            and coupon_channel in {"all", channel}
        )

    def _decorate_public(self, rows: list[dict]) -> list[dict]:
        ids = [str(row.get("id")) for row in rows if row.get("id")]
        try:
            scopes = self.repository.scopes_for_many(ids)
        except CouponRepositoryUnavailable:
            scopes = {coupon_id: CouponScope() for coupon_id in ids}
        labels = {"all": "Toàn bộ sản phẩm", "category": "Danh mục chọn lọc", "product": "Sản phẩm chọn lọc"}
        decorated: list[dict] = []
        for source in rows:
            row = dict(source)
            scope = scopes.get(str(row.get("id")), CouponScope())
            row["scope_kind"] = scope.kind
            row["scope_label"] = labels[scope.kind]
            expires = self._as_datetime(row.get("expires_at"))
            row["expires_label"] = expires.astimezone(self._local_tz).strftime("%d.%m.%Y") if expires else "Không giới hạn"
            decorated.append(row)
        return decorated

    def public_list(self) -> list[dict]:
        rows = [row for row in self.repository.list_public_candidates(self._now().isoformat()) if self._is_live(row, "web")]
        return self._decorate_public(rows)

    def public_detail(self, code: str) -> dict | None:
        coupon = self.repository.get_by_code(self.normalize_code(code))
        if not coupon or not self._is_live(coupon, "web"):
            return None
        return self._decorate_public([coupon])[0]

    @staticmethod
    def _item_subtotal(item: dict) -> float:
        quantity = max(0, int(float(item.get("quantity") or 0)))
        product = item.get("products") or {}
        variant = item.get("product_variants") or {}
        raw_price = variant.get("price_override")
        if raw_price is None:
            raw_price = product.get("price", 0)
        try:
            return max(0.0, float(raw_price or 0)) * quantity
        except (TypeError, ValueError):
            return 0.0

    def validate_for_checkout(
        self,
        code: str,
        *,
        user_id: str,
        items: list[dict],
        subtotal: float,
        channel: str = "web",
    ) -> CouponApplication:
        normalized = self.normalize_code(code)
        if not normalized:
            return CouponApplication(message="")
        coupon = self.repository.get_by_code(normalized)
        if not coupon or not coupon.get("is_active"):
            return CouponApplication(message="Mã ưu đãi không tồn tại hoặc đã tắt.")
        if not self._is_live(coupon, channel):
            starts = self._as_datetime(coupon.get("starts_at"))
            if starts and starts > self._now().astimezone(timezone.utc):
                return CouponApplication(message="Mã ưu đãi chưa đến thời gian áp dụng.")
            expires = self._as_datetime(coupon.get("expires_at"))
            if expires and expires <= self._now().astimezone(timezone.utc):
                return CouponApplication(message="Mã ưu đãi đã hết hạn.")
            return CouponApplication(message="Mã ưu đãi không áp dụng trên kênh mua sắm này.")

        coupon_id = str(coupon.get("id") or "")
        usage_limit = int(coupon.get("usage_limit") or 0)
        if usage_limit and self.repository.count_usages(coupon_id) >= usage_limit:
            return CouponApplication(message="Mã ưu đãi đã hết lượt sử dụng.")
        per_user = int(coupon.get("usage_per_user") or 0)
        if per_user and self.repository.count_usages(coupon_id, user_id=user_id) >= per_user:
            return CouponApplication(message="Bạn đã dùng hết số lượt cho mã này.")
        daily_limit = int(coupon.get("max_usage_per_day") or 0)
        if daily_limit:
            local_now = self._now().astimezone(self._local_tz)
            day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()
            if self.repository.count_usages(coupon_id, used_after=day_start) >= daily_limit:
                return CouponApplication(message="Mã ưu đãi đã hết lượt dùng trong hôm nay.")
        if coupon.get("is_first_order_only") and self.repository.order_count(user_id) > 0:
            return CouponApplication(message="Mã này chỉ dành cho đơn hàng đầu tiên.")
        points_required = int(coupon.get("min_loyalty_points") or 0)
        if points_required and self.repository.user_points(user_id) < points_required:
            return CouponApplication(message=f"Bạn cần tối thiểu {points_required:,} điểm để dùng mã này.".replace(",", "."))

        scope = self.repository.scope_for(coupon_id)
        product_ids = [str(item.get("product_id") or (item.get("products") or {}).get("id") or "") for item in items]
        eligible_items = list(items)
        if scope.kind == "product":
            allowed = set(scope.ids)
            eligible_items = [item for item, product_id in zip(items, product_ids) if product_id in allowed]
        elif scope.kind == "category":
            category_map = self.repository.product_category_map(product_ids)
            allowed = set(scope.ids)
            eligible_items = [item for item, product_id in zip(items, product_ids) if category_map.get(product_id, set()) & allowed]
        applicable_subtotal = sum(self._item_subtotal(item) for item in eligible_items)
        if applicable_subtotal <= 0:
            return CouponApplication(message="Giỏ hàng chưa có sản phẩm phù hợp với mã này.")
        min_order = float(coupon.get("min_order_value") or 0)
        if applicable_subtotal < min_order:
            formatted = f"{min_order:,.0f}".replace(",", ".")
            return CouponApplication(message=f"Giá trị sản phẩm áp dụng cần đạt tối thiểu {formatted}₫.")

        discount_type = coupon.get("discount_type")
        value = float(coupon.get("discount_value") or 0)
        free_shipping = discount_type == "free_shipping"
        if discount_type == "percent":
            discount = applicable_subtotal * value / 100
        elif discount_type == "fixed":
            discount = value
        else:
            discount = 0.0
        max_discount = float(coupon.get("max_discount") or 0)
        if max_discount > 0:
            discount = min(discount, max_discount)
        discount = min(max(0.0, discount), applicable_subtotal, max(0.0, float(subtotal)))
        message = "Đã áp dụng miễn phí vận chuyển." if free_shipping else "Đã áp dụng mã ưu đãi."
        return CouponApplication(True, coupon_id, normalized, discount, free_shipping, applicable_subtotal, message)
