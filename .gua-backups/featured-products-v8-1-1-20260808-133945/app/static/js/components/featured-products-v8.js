/* GUAMAISON Featured Products v8 — event-delegated, framework-free controller */
(function () {
  "use strict";

  const SELECTOR = {
    root: "[data-featured-products]",
    viewport: "[data-featured-viewport]",
    card: "[data-featured-card]",
    previous: "[data-featured-previous]",
    next: "[data-featured-next]",
    progress: "[data-featured-progress]",
    notice: "[data-featured-notice]",
    noticeIcon: "[data-featured-notice-icon]",
    noticeText: "[data-featured-notice-text]",
    action: "[data-featured-action]",
    cartForm: "[data-featured-cart-form]"
  };

  class FeaturedProductsController {
    constructor(root) {
      this.root = root;
      this.viewport = root.querySelector(SELECTOR.viewport);
      this.previousButton = root.querySelector(SELECTOR.previous);
      this.nextButton = root.querySelector(SELECTOR.next);
      this.progress = root.querySelector(SELECTOR.progress);
      this.notice = root.querySelector(SELECTOR.notice);
      this.noticeTimer = 0;
      this.scrollFrame = 0;
      this.resizeObserver = null;
    }

    mount() {
      if (!this.viewport || this.root.dataset.featuredReady === "1") return;

      this.root.dataset.featuredReady = "1";
      this.root.addEventListener("click", (event) => this.handleClick(event));
      this.root.addEventListener("submit", (event) => this.handleSubmit(event));
      this.root.addEventListener("error", (event) => this.handleImageError(event), true);
      this.viewport.addEventListener("scroll", () => this.scheduleScrollUpdate(), { passive: true });
      this.viewport.addEventListener("keydown", (event) => this.handleViewportKeydown(event));

      if ("ResizeObserver" in window) {
        this.resizeObserver = new ResizeObserver(() => this.updateScrollState());
        this.resizeObserver.observe(this.viewport);
      } else {
        window.addEventListener("resize", () => this.updateScrollState(), { passive: true });
      }

      this.updateScrollState();
    }

    handleClick(event) {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;

      if (target.closest(SELECTOR.previous)) {
        this.scrollByCard(-1);
        return;
      }

      if (target.closest(SELECTOR.next)) {
        this.scrollByCard(1);
        return;
      }

      const actionButton = target.closest(SELECTOR.action);
      if (!actionButton) return;

      const action = actionButton.dataset.featuredAction;
      if (action === "quick-view") {
        this.openQuickView(actionButton);
      } else if (action === "favorite") {
        this.toggleFavorite(actionButton);
      }
    }

    handleSubmit(event) {
      const form = event.target instanceof HTMLFormElement
        ? event.target.closest(SELECTOR.cartForm)
        : null;

      if (!form) return;

      event.preventDefault();
      this.addToCart(form);
    }

    handleViewportKeydown(event) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;

      event.preventDefault();
      this.scrollByCard(event.key === "ArrowRight" ? 1 : -1);
    }

    handleImageError(event) {
      const image = event.target;
      if (!(image instanceof HTMLImageElement)) return;

      const fallback = image.dataset.fallbackSrc;
      if (!fallback || image.dataset.fallbackApplied === "1") return;

      image.dataset.fallbackApplied = "1";
      image.src = fallback;
    }

    scrollByCard(direction) {
      const card = this.viewport.querySelector(SELECTOR.card);
      if (!card) return;

      const track = card.parentElement;
      const styles = track ? window.getComputedStyle(track) : null;
      const gap = styles ? parseFloat(styles.columnGap || styles.gap || "0") : 0;
      const distance = card.getBoundingClientRect().width + gap;

      this.viewport.scrollBy({
        left: distance * direction,
        behavior: this.prefersReducedMotion() ? "auto" : "smooth"
      });
    }

    scheduleScrollUpdate() {
      if (this.scrollFrame) return;

      this.scrollFrame = window.requestAnimationFrame(() => {
        this.scrollFrame = 0;
        this.updateScrollState();
      });
    }

    updateScrollState() {
      const maximum = Math.max(0, this.viewport.scrollWidth - this.viewport.clientWidth);
      const current = Math.max(0, Math.min(maximum, this.viewport.scrollLeft));
      const percentage = maximum > 0 ? Math.round((current / maximum) * 100) : 100;

      if (this.previousButton) {
        this.previousButton.disabled = current <= 2;
      }

      if (this.nextButton) {
        this.nextButton.disabled = maximum === 0 || current >= maximum - 2;
      }

      if (this.progress) {
        this.progress.style.setProperty("--featured-progress", percentage + "%");
        this.progress.setAttribute("aria-valuenow", String(percentage));
      }
    }

    openQuickView(button) {
      if (typeof window.triggerQuickView === "function") {
        window.triggerQuickView(button);
        return;
      }

      window.location.assign(button.dataset.url || "/shop");
    }

    async toggleFavorite(button) {
      if (button.getAttribute("aria-busy") === "true") return;

      const productId = button.dataset.productId || "";
      if (!productId) {
        this.showNotice("Không tìm thấy mã sản phẩm.", "error");
        return;
      }

      const icon = button.querySelector("i");
      const originalIcon = icon ? icon.className : "";
      this.setBusy(button, true, icon);

      try {
        const response = await this.fetchJSON(
          "/api/favorites/toggle",
          {
            method: "POST",
            headers: this.jsonHeaders(),
            body: JSON.stringify({ product_id: productId })
          },
          10000
        );

        if (response.status === 401 || this.isLoginRedirect(response)) {
          this.showNotice("Đăng nhập để lưu thiết kế yêu thích.", "error");
          window.setTimeout(() => window.location.assign(this.root.dataset.loginUrl || "/auth/login"), 850);
          return;
        }

        if (!response.ok || response.data.status === "error") {
          throw new Error(response.data.message || "Không thể cập nhật yêu thích.");
        }

        const liked = response.data.action === "added";
        button.setAttribute("aria-pressed", String(liked));
        button.setAttribute("aria-label", liked ? "Bỏ khỏi yêu thích" : "Thêm vào yêu thích");

        if (icon) {
          icon.className = liked ? "fa-solid fa-heart" : "fa-regular fa-heart";
        }

        this.showNotice(response.data.message || (liked ? "Đã thêm vào yêu thích." : "Đã bỏ khỏi yêu thích."), "success");
        window.dispatchEvent(new CustomEvent("favorite:updated", {
          detail: { product_id: productId, liked }
        }));
      } catch (error) {
        if (icon) icon.className = originalIcon;
        this.showNotice(this.errorMessage(error, "Không thể cập nhật yêu thích."), "error");
      } finally {
        this.setBusy(button, false);
      }
    }

    async addToCart(form) {
      const button = form.querySelector('button[type="submit"]');
      if (!button || button.getAttribute("aria-busy") === "true") return;

      const formData = new FormData(form);
      const productId = String(formData.get("product_id") || "");
      const variantId = String(formData.get("variant_id") || "");
      const icon = button.querySelector("i");
      const label = button.querySelector("span");
      const originalIcon = icon ? icon.className : "";
      const originalLabel = label ? label.textContent : "";

      if (!productId || !variantId) {
        this.showNotice("Vui lòng chọn phiên bản sản phẩm.", "error");
        return;
      }

      this.setBusy(button, true, icon);
      if (label) label.textContent = "Đang thêm";

      try {
        const response = await this.fetchJSON(
          form.action,
          {
            method: "POST",
            headers: this.jsonHeaders(),
            body: JSON.stringify({ product_id: productId, variant_id: variantId, quantity: 1 })
          },
          12000
        );

        if (response.status === 401 || this.isLoginRedirect(response)) {
          this.showNotice("Vui lòng đăng nhập để thêm vào giỏ.", "error");
          window.setTimeout(() => window.location.assign(this.root.dataset.loginUrl || "/auth/login"), 850);
          return;
        }

        if (response.status === 403) {
          throw new Error("Phiên đã hết hạn. Hãy tải lại trang và thử lại.");
        }

        if (!response.ok || response.data.success === false || response.data.status === "error") {
          throw new Error(response.data.message || "Không thể thêm sản phẩm vào giỏ.");
        }

        if (icon) icon.className = "fa-solid fa-check";
        if (label) label.textContent = "Đã thêm";
        button.classList.add("is-complete");

        this.updateCartCounters(response.data);
        this.showNotice(response.data.message || "Đã thêm sản phẩm vào giỏ hàng.", "success");
        window.dispatchEvent(new CustomEvent("cart:updated", {
          detail: { product_id: productId, variant_id: variantId, quantity: 1 }
        }));

        window.setTimeout(() => {
          button.classList.remove("is-complete");
          if (icon) icon.className = originalIcon;
          if (label) label.textContent = originalLabel;
        }, 1500);
      } catch (error) {
        if (icon) icon.className = "fa-solid fa-xmark";
        if (label) label.textContent = "Thử lại";
        this.showNotice(this.errorMessage(error, "Không thể kết nối giỏ hàng."), "error");

        window.setTimeout(() => {
          if (icon) icon.className = originalIcon;
          if (label) label.textContent = originalLabel;
        }, 1500);
      } finally {
        this.setBusy(button, false);
      }
    }

    updateCartCounters(data) {
      const explicitCount = data.cart_count ?? data.count ?? data.cart?.count ?? data.cart_total_items;

      document.querySelectorAll("[data-cart-count], .cart-count, #cart-count, .js-cart-count").forEach((element) => {
        const current = Number.parseInt(element.textContent || "0", 10) || 0;
        const next = explicitCount === undefined || explicitCount === null
          ? current + 1
          : Number.parseInt(explicitCount, 10) || 0;

        element.textContent = String(next);
        element.classList.remove("hidden", "is-zero");
      });
    }

    setBusy(button, busy, icon) {
      button.setAttribute("aria-busy", String(busy));
      button.disabled = busy;

      if (busy && icon) {
        icon.className = "fa-solid fa-spinner fa-spin";
      }
    }

    jsonHeaders() {
      const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
      return {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrf
      };
    }

    async fetchJSON(url, options, timeout) {
      const controller = new AbortController();
      const timer = window.setTimeout(() => controller.abort(), timeout);

      try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        const data = await response.json().catch(() => ({}));
        return {
          ok: response.ok,
          status: response.status,
          data,
          redirected: response.redirected,
          url: response.url || ""
        };
      } finally {
        window.clearTimeout(timer);
      }
    }

    errorMessage(error, fallback) {
      if (error && error.name === "AbortError") {
        return "Phản hồi quá chậm. Vui lòng thử lại.";
      }

      return error instanceof Error && error.message ? error.message : fallback;
    }

    isLoginRedirect(response) {
      if (!response.redirected || !response.url) return false;

      try {
        return new URL(response.url, window.location.origin).pathname.startsWith("/auth/login");
      } catch (_) {
        return response.url.includes("/auth/login");
      }
    }

    showNotice(message, type) {
      if (!this.notice) return;

      const text = this.notice.querySelector(SELECTOR.noticeText);
      const icon = this.notice.querySelector(SELECTOR.noticeIcon);

      if (text) text.textContent = message;
      if (icon) {
        icon.className = type === "error"
          ? "fa-solid fa-circle-exclamation"
          : "fa-solid fa-circle-check";
      }

      window.clearTimeout(this.noticeTimer);
      this.notice.hidden = false;
      this.notice.classList.toggle("is-error", type === "error");

      window.requestAnimationFrame(() => this.notice.classList.add("is-visible"));

      this.noticeTimer = window.setTimeout(() => {
        this.notice.classList.remove("is-visible");
        window.setTimeout(() => {
          this.notice.hidden = true;
        }, this.prefersReducedMotion() ? 0 : 230);
      }, 2600);
    }

    prefersReducedMotion() {
      return Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
    }
  }

  function initializeFeaturedProducts() {
    document.querySelectorAll(SELECTOR.root).forEach((root) => {
      new FeaturedProductsController(root).mount();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeFeaturedProducts, { once: true });
  } else {
    initializeFeaturedProducts();
  }
})();
