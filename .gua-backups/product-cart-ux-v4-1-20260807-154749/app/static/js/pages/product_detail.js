const ProductUI = (() => {
  const meta = document.getElementById("mm-product-meta");

  const state = {
    productId: meta ? meta.dataset.id : "",
    csrf: meta ? meta.dataset.csrf : "",
    basePrice: Number(meta ? meta.dataset.basePrice || 0 : 0),
    basePriceFormatted: meta ? meta.dataset.basePriceFormatted || "" : "",
    baseCompare: Number(meta ? meta.dataset.baseCompare || 0 : 0),
    baseCompareFormatted: meta ? meta.dataset.baseCompareFormatted || "" : "",
    baseDiscount: meta ? meta.dataset.baseDiscount || "" : "",
    productStock: Number(meta ? meta.dataset.productStock || 0 : 0),
    productCanBuy: meta ? meta.dataset.productCanBuy === "1" : false,
    selectedStock: Number(meta ? meta.dataset.productStock || 0 : 0),
    selectedAvailable: meta ? meta.dataset.productCanBuy === "1" : false
  };

  function formatVnd(value) {
    return new Intl.NumberFormat("vi-VN").format(Number(value || 0)) + "đ";
  }

  function toast(message) {
    const el = document.getElementById("pdToast");
    if (!el) return;

    el.textContent = message;
    el.classList.add("show");

    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove("show"), 2200);
  }

  function updatePrice(price, priceFormatted, compare, compareFormatted, discount) {
    const priceEl = document.getElementById("price-display");
    const original = document.getElementById("price-original");
    const badge = document.getElementById("price-discount");
    const mainBadge = document.getElementById("main-discount-badge");

    if (priceEl) {
      priceEl.textContent = priceFormatted || formatVnd(price);
    }

    if (original) {
      original.textContent = compareFormatted || "";
      original.classList.toggle("hidden", !compare);
    }

    if (badge) {
      badge.textContent = discount ? "-" + discount + "%" : "";
      badge.classList.toggle("hidden", !discount);
    }

    if (mainBadge) {
      mainBadge.textContent = discount ? "-" + discount + "%" : "";
      mainBadge.classList.toggle("hidden", !discount);
    }
  }

  function setSubmitState(canBuy, text) {
    const desktop = document.getElementById("btn-submit");
    const mobile = document.getElementById("mobile-btn-submit");

    [desktop, mobile].forEach((btn) => {
      if (!btn) return;

      btn.disabled = !canBuy;
      btn.textContent = text;
    });
  }

  function updateQtyMax(maxValue) {
    const max = Math.max(1, Number(maxValue || 1));
    const qty = document.getElementById("qty");
    const mobileQty = document.getElementById("mobile-qty");
    const hiddenQty = document.getElementById("hidden-qty");

    [qty, mobileQty].forEach((input) => {
      if (!input) return;

      input.max = String(max);
      input.value = String(Math.max(1, Math.min(Number(input.value || 1), max)));
    });

    if (hiddenQty && qty) {
      hiddenQty.value = qty.value;
    }
  }

  function setStockMessage(stock, available) {
    const status = document.getElementById("stock-status");
    const pill = document.getElementById("stock-pill");

    if (!status || !pill) return;

    pill.className = "pd-pill";

    if (available && stock > 5) {
      status.textContent = "CÓ SẴN HÀNG";
      pill.textContent = "Còn hàng";
      pill.classList.add("ok");
      return;
    }

    if (available && stock > 0) {
      status.textContent = "CHỈ CÒN " + stock + " SẢN PHẨM";
      pill.textContent = "Sắp hết hàng";
      pill.classList.add("low");
      return;
    }

    if (available && stock <= 0) {
      status.textContent = "SẢN PHẨM CHO PHÉP ĐẶT TRƯỚC";
      pill.textContent = "Đặt trước";
      pill.classList.add("low");
      return;
    }

    status.textContent = "SẢN PHẨM HIỆN ĐÃ HẾT HÀNG";
    pill.textContent = "Hết hàng";
    pill.classList.add("out");
  }

  return {
    state,
    formatVnd,
    toast,
    updatePrice,
    setSubmitState,
    updateQtyMax,
    setStockMessage
  };
})();

const Gallery = {
  main: document.getElementById("main-focus-image"),
  fallback: "https://placehold.co/900x1200/f6f6f6/111111?text=GUAMAISON",

  init() {
    const thumbs = document.getElementById("pdThumbs");

    if (!thumbs) return;

    thumbs.addEventListener("click", (event) => {
      const btn = event.target.closest(".pd-thumb");

      if (!btn) return;

      this.swap(btn.dataset.url, btn);
    });
  },

  swap(url, btn) {
    if (!this.main || !url) return;

    const nextUrl = url || this.fallback;
    const loader = new Image();

    this.main.style.opacity = "0";

    loader.onload = () => {
      this.main.src = nextUrl;
      this.main.style.opacity = "1";
    };

    loader.onerror = () => {
      this.main.src = this.fallback;
      this.main.style.opacity = "1";
    };

    loader.src = nextUrl;

    document.querySelectorAll(".pd-thumb").forEach((item) => {
      item.classList.remove("is-active");
    });

    if (btn) {
      btn.classList.add("is-active");
    }
  }
};

const MobileCTA = {
  submitForm() {
    const btn = document.getElementById("mobile-btn-submit");
    const form = document.getElementById("purchase-form");

    if (form && btn && !btn.disabled) {
      if (form.requestSubmit) {
        form.requestSubmit();
      } else {
        form.submit();
      }
    }
  }
};

function selectColor(color) {
  const label = document.getElementById("color-label");

  if (label) {
    label.textContent = color;
  }

  document.querySelectorAll(".size-group").forEach((group) => {
    group.classList.toggle("hidden", group.dataset.color !== color);
  });

  const activeGroup = Array.from(document.querySelectorAll(".size-group")).find((group) => {
    return group.dataset.color === color;
  });

  if (!activeGroup) return;

  const target =
    activeGroup.querySelector(".size-radio:not([disabled])") ||
    activeGroup.querySelector(".size-radio");

  if (target) {
    target.checked = true;
    selectSize(target);
  } else {
    disableSubmitState("HẾT HÀNG");
  }
}

function selectSize(input) {
  if (!input) return;

  const stock = Number(input.dataset.stock || 0);
  const available = input.dataset.available === "1";
  const vid = input.dataset.vid || "";
  const price = Number(input.dataset.price || ProductUI.state.basePrice || 0);
  const priceFormatted = input.dataset.priceFormatted || ProductUI.formatVnd(price);
  const compare = Number(input.dataset.compare || 0);
  const compareFormatted = input.dataset.compareFormatted || "";
  const discount = input.dataset.discount || "";

  const variantInput = document.getElementById("selected-variant-id");

  if (variantInput) {
    variantInput.value = vid;
  }

  ProductUI.state.selectedStock = stock;
  ProductUI.state.selectedAvailable = available;

  ProductUI.updatePrice(price, priceFormatted, compare, compareFormatted, discount);
  ProductUI.updateQtyMax(stock > 0 ? stock : 1);
  ProductUI.setStockMessage(stock, available);
  ProductUI.setSubmitState(available, available ? "THÊM VÀO GIỎ" : "HẾT HÀNG");
}

function disableSubmitState(message) {
  const variantInput = document.getElementById("selected-variant-id");

  if (variantInput) {
    variantInput.value = "";
  }

  ProductUI.setSubmitState(false, message || "HẾT HÀNG");
  ProductUI.setStockMessage(0, false);
}

function chQty(delta) {
  const qty = document.getElementById("qty");
  const mobileQty = document.getElementById("mobile-qty");
  const hiddenQty = document.getElementById("hidden-qty");
  const maxStock = Number(qty ? qty.max || 1 : 1) || 1;

  let value = Number(qty ? qty.value || 1 : 1) + Number(delta || 0);
  value = Math.max(1, Math.min(value, maxStock));

  if (qty) {
    qty.value = String(value);
  }

  if (mobileQty) {
    mobileQty.value = String(value);
  }

  if (hiddenQty) {
    hiddenQty.value = String(value);
  }
}

function toggleAccordion(id) {
  const content = document.getElementById(id);
  const icon = document.getElementById("icon-" + id);
  const trigger = document.querySelector('[aria-controls="' + id + '"]');

  if (!content) return;

  content.classList.toggle("open");

  if (trigger) {
    trigger.setAttribute("aria-expanded", content.classList.contains("open") ? "true" : "false");
  }

  if (icon) {
    icon.classList.toggle("open");
  }
}

function getTrafficSource() {
  const params = new URLSearchParams(window.location.search);

  return params.get("utm_source") || localStorage.getItem("utm_source") || "organic";
}

function trackEvent(eventType, qty = 1) {
  if (!ProductUI.state.productId) return;

  try {
    const payload = JSON.stringify({
      product_id: ProductUI.state.productId,
      event_type: eventType,
      channel: "web",
      source: getTrafficSource(),
      qty
    });

    if (navigator.sendBeacon) {
      navigator.sendBeacon("/api/analytics/track", new Blob([payload], { type: "application/json" }));
    } else {
      fetch("/api/analytics/track", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload
      }).catch(() => {});
    }
  } catch (_) {}
}

document.addEventListener("DOMContentLoaded", () => {
  Gallery.init();

  document.querySelectorAll(".color-swatch").forEach((el) => {
    el.style.backgroundColor = el.dataset.bg || "#ddd";
  });

  const firstColor =
    document.querySelector(".color-radio:checked") ||
    document.querySelector(".color-radio");

  if (firstColor) {
    firstColor.checked = true;
    selectColor(firstColor.value);
  } else {
    ProductUI.updateQtyMax(ProductUI.state.productStock > 0 ? ProductUI.state.productStock : 1);
    ProductUI.setStockMessage(ProductUI.state.productStock, ProductUI.state.productCanBuy);
    ProductUI.setSubmitState(
      ProductUI.state.productCanBuy,
      ProductUI.state.productCanBuy ? "THÊM VÀO GIỎ" : "HẾT HÀNG"
    );
  }

  document.querySelectorAll(".color-radio").forEach((radio) => {
    radio.addEventListener("change", function () {
      selectColor(this.value);
    });
  });

  document.querySelectorAll(".size-radio").forEach((radio) => {
    radio.addEventListener("change", function () {
      selectSize(this);
    });
  });

  document.querySelectorAll(".btn-qty").forEach((btn) => {
    btn.addEventListener("click", function () {
      chQty(Number(this.dataset.qty || 0));
    });
  });

  const form = document.getElementById("purchase-form");

  if (form) {
    form.addEventListener("submit", (event) => {
      const hasVariants = Boolean(document.querySelector(".size-radio"));
      const selectedVariant = document.getElementById("selected-variant-id");

      if (hasVariants && (!selectedVariant || !selectedVariant.value)) {
        event.preventDefault();
        ProductUI.toast("Vui lòng chọn phân loại");
        ProductUI.setSubmitState(false, "CHỌN PHÂN LOẠI");
        return;
      }

      if (!ProductUI.state.selectedAvailable) {
        event.preventDefault();
        ProductUI.toast("Sản phẩm đã hết hàng");
        ProductUI.setSubmitState(false, "HẾT HÀNG");
        return;
      }

      trackEvent("cart", Number(document.getElementById("hidden-qty")?.value || 1));
    });
  }

  const wishlistBtn = document.getElementById("btn-wishlist");

  if (wishlistBtn) {
    wishlistBtn.addEventListener("click", async function () {
      if (!ProductUI.state.productId) return;

      this.disabled = true;

      try {
        const response = await fetch("/api/favorites/toggle", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": ProductUI.state.csrf
          },
          body: JSON.stringify({ product_id: ProductUI.state.productId })
        });

        const data = await response.json();

        if (response.status === 401) {
          window.location.href = "/auth/login";
          return;
        }

        if (data.status === "success") {
          const svg = this.querySelector("svg");

          if (data.action === "added") {
            if (svg) {
              svg.setAttribute("fill", "currentColor");
            }

            this.classList.add("is-on");
            ProductUI.toast("Đã thêm yêu thích");
            trackEvent("wishlist", 1);
          } else {
            if (svg) {
              svg.setAttribute("fill", "none");
            }

            this.classList.remove("is-on");
            ProductUI.toast("Đã bỏ yêu thích");
          }
        }
      } catch (_) {
        ProductUI.toast("Lỗi kết nối");
      } finally {
        this.disabled = false;
      }
    });
  }
if (ProductUI.state.productId) {
    trackEvent("view", 1);
  }
});
