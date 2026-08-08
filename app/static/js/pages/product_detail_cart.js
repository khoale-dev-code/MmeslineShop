(() => {
  "use strict";

  const GUA = window.GUA = window.GUA || {};
  const DEFAULT_DURATION = 4200;
  const MIN_LOADING_TIME = 360;
  const REQUEST_TIMEOUT = 12000;
  const ICONS = {
    success: "fa-solid fa-check",
    error: "fa-solid fa-xmark",
    warning: "fa-solid fa-exclamation"
  };

  const wait = (milliseconds) => new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });

  const feedback = (() => {
    const element = document.querySelector("[data-cart-feedback]");
    if (!element) return null;

    const title = element.querySelector("[data-cart-feedback-title]");
    const message = element.querySelector("[data-cart-feedback-message]");
    const icon = element.querySelector("[data-cart-feedback-icon]");
    const action = element.querySelector("[data-cart-feedback-action]");
    const close = element.querySelector("[data-cart-feedback-close]");
    let hideTimer = 0;
    let finishTimer = 0;

    const dismiss = () => {
      window.clearTimeout(hideTimer);
      window.clearTimeout(finishTimer);
      if (element.hidden || element.classList.contains("is-hiding")) return;

      element.classList.remove("is-visible");
      element.classList.add("is-hiding");
      finishTimer = window.setTimeout(() => {
        element.hidden = true;
        element.classList.remove("is-hiding");
      }, 240);
    };

    const show = (options = {}) => {
      const type = ["success", "error", "warning"].includes(options.type)
        ? options.type
        : "success";
      const duration = Math.max(1800, Number(options.duration || DEFAULT_DURATION));

      window.clearTimeout(hideTimer);
      window.clearTimeout(finishTimer);

      element.dataset.type = type;
      element.style.setProperty("--pd-cart-feedback-duration", `${duration}ms`);
      element.setAttribute("role", type === "error" ? "alert" : "status");

      if (title) title.textContent = options.title || "Thông báo";
      if (message) message.textContent = options.message || "";
      if (icon) icon.className = ICONS[type] || ICONS.success;

      if (action) {
        action.hidden = options.action === false;
        if (options.actionLabel) action.textContent = options.actionLabel;
      }

      element.classList.remove("is-visible", "is-hiding");
      element.hidden = false;

      // Restart the progress animation for consecutive notifications.
      void element.offsetWidth;
      window.requestAnimationFrame(() => element.classList.add("is-visible"));
      hideTimer = window.setTimeout(dismiss, duration);
    };

    close?.addEventListener("click", dismiss);
    return { show, dismiss };
  })();

  function showFeedback(type, title, message, options = {}) {
    if (feedback) {
      feedback.show({ type, title, message, ...options });
      return;
    }

    if (typeof GUA.snackbar === "function") {
      GUA.snackbar(message || title, type);
    }
  }

  function updateCartCounters(data) {
    const count =
      data?.cart_count ??
      data?.count ??
      data?.cart?.count ??
      data?.cart_total_items ??
      null;

    if (count === null || count === undefined) return;

    document
      .querySelectorAll("[data-cart-count], .cart-count, #cart-count, .js-cart-count")
      .forEach((element) => {
        element.textContent = String(count);
        element.classList.remove("hidden");
      });
  }

  function animateCartNavigation() {
    const links = document.querySelectorAll(
      'a[href="/cart/"], a[href="/cart"], [data-cart-link]'
    );

    links.forEach((link) => {
      link.classList.remove("pd-cart-nav-pop");
      void link.offsetWidth;
      link.classList.add("pd-cart-nav-pop");
      window.setTimeout(() => link.classList.remove("pd-cart-nav-pop"), 700);
    });
  }

  function focusVariantChoice(form) {
    const target = form.querySelector(".size-radio:not([disabled])");
    const wrapper = form.querySelector("#size-wrapper") || target?.closest(".pd-field");
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    wrapper?.scrollIntoView({
      behavior: reducedMotion ? "auto" : "smooth",
      block: "center"
    });

    window.setTimeout(() => target?.focus({ preventScroll: true }), 180);
  }

  function init({ form, onAdded } = {}) {
    if (!form || form.dataset.cartAjaxReady === "1") return;
    form.dataset.cartAjaxReady = "1";

    let pending = false;
    let activeController = null;

    const desktopButton = document.getElementById("btn-submit");
    const mobileButton = document.getElementById("mobile-btn-submit");
    const submitButtons = [desktopButton, mobileButton].filter(Boolean);

    const snapshotControls = () => Array.from(
      document.querySelectorAll(".color-radio, .size-radio, .btn-qty")
    ).map((element) => ({ element, disabled: Boolean(element.disabled) }));

    const setButtonVisual = (state, label) => {
      submitButtons.forEach((button) => {
        button.classList.remove(
          "is-cart-loading",
          "is-cart-added",
          "is-cart-error"
        );

        if (state) button.classList.add(`is-cart-${state}`);
        button.textContent = label;
        button.setAttribute("aria-busy", state === "loading" ? "true" : "false");
      });
    };

    const restoreUi = (buttonSnapshot, controlSnapshot) => {
      submitButtons.forEach((button) => {
        const previous = buttonSnapshot.find((item) => item.element === button);
        button.classList.remove(
          "is-cart-loading",
          "is-cart-added",
          "is-cart-error"
        );
        button.removeAttribute("aria-busy");

        if (previous) {
          button.textContent = previous.label;
          button.disabled = previous.disabled;
        }
      });

      controlSnapshot.forEach(({ element, disabled }) => {
        element.disabled = disabled;
      });

      form.classList.remove("is-cart-pending");
      form.removeAttribute("aria-busy");
    };

    const setPendingUi = (controlSnapshot) => {
      form.classList.add("is-cart-pending");
      form.setAttribute("aria-busy", "true");
      controlSnapshot.forEach(({ element }) => {
        element.disabled = true;
      });
      submitButtons.forEach((button) => {
        button.disabled = true;
      });
      setButtonVisual("loading", "ĐANG THÊM...");
    };

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (pending) return;

      const productId = String(
        form.querySelector('[name="product_id"]')?.value || ""
      ).trim();
      const variantId = String(
        form.querySelector('[name="variant_id"]')?.value || ""
      ).trim();
      const quantity = Math.max(
        1,
        Number(form.querySelector('[name="quantity"]')?.value || 1)
      );
      const hasVariants = Boolean(form.querySelector(".size-radio"));
      const selectedSize = form.querySelector(".size-radio:checked");

      if (hasVariants && !variantId) {
        showFeedback(
          "warning",
          "Chọn phân loại",
          "Vui lòng chọn màu sắc và kích cỡ trước khi thêm vào giỏ.",
          { action: false }
        );
        focusVariantChoice(form);
        return;
      }

      if (!productId) {
        showFeedback(
          "error",
          "Thiếu thông tin sản phẩm",
          "Không thể xác định sản phẩm. Vui lòng tải lại trang.",
          { action: false }
        );
        return;
      }

      if (selectedSize && selectedSize.dataset.available !== "1") {
        showFeedback(
          "warning",
          "Sản phẩm đã hết hàng",
          "Phân loại này hiện không còn hàng. Vui lòng chọn phân loại khác.",
          { action: false }
        );
        return;
      }

      const csrf =
        form.querySelector('[name="csrf_token"]')?.value ||
        document.querySelector('meta[name="csrf-token"]')?.content ||
        "";
      const buttonSnapshot = submitButtons.map((element) => ({
        element,
        label: element.textContent.trim(),
        disabled: Boolean(element.disabled)
      }));
      const controlSnapshot = snapshotControls();
      const startedAt = performance.now();

      pending = true;
      activeController = new AbortController();
      const timeoutId = window.setTimeout(
        () => activeController?.abort("timeout"),
        REQUEST_TIMEOUT
      );

      setPendingUi(controlSnapshot);

      let succeeded = false;

      try {
        const response = await fetch(form.action || "/cart/add", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-CSRFToken": csrf,
            "X-Requested-With": "XMLHttpRequest"
          },
          body: JSON.stringify({
            product_id: productId,
            variant_id: variantId,
            quantity
          }),
          signal: activeController.signal
        });

        const elapsed = performance.now() - startedAt;
        if (elapsed < MIN_LOADING_TIME) {
          await wait(MIN_LOADING_TIME - elapsed);
        }

        const redirectedToLogin =
          response.redirected && /\/auth\/login(?:[/?#]|$)/.test(response.url);

        if (response.status === 401 || redirectedToLogin) {
          showFeedback(
            "warning",
            "Cần đăng nhập",
            "Đăng nhập để thêm sản phẩm vào giỏ hàng.",
            { action: false, duration: 2600 }
          );
          window.setTimeout(() => {
            window.location.href = "/auth/login";
          }, 750);
          return;
        }

        if (response.status === 403) {
          setButtonVisual("error", "PHIÊN ĐÃ HẾT HẠN");
          showFeedback(
            "error",
            "Phiên đã hết hạn",
            "Vui lòng tải lại trang rồi thử thêm sản phẩm một lần nữa.",
            { action: false }
          );
          await wait(720);
          return;
        }

        const contentType = response.headers.get("content-type") || "";
        const data = contentType.includes("application/json")
          ? await response.json().catch(() => ({}))
          : {};

        if (!response.ok || data.success === false || data.status === "error") {
          setButtonVisual("error", "CHƯA THỂ THÊM");
          showFeedback(
            "error",
            "Chưa thêm được sản phẩm",
            data.message || "Hệ thống đang bận. Vui lòng thử lại sau ít phút.",
            { action: false }
          );
          await wait(720);
          return;
        }

        succeeded = true;
        setButtonVisual("added", "ĐÃ THÊM ✓");
        updateCartCounters(data);
        animateCartNavigation();

        showFeedback(
          "success",
          "Đã thêm vào giỏ",
          data.message || "Sản phẩm đã sẵn sàng trong giỏ hàng."
        );

        if (typeof onAdded === "function") {
          onAdded(quantity, data);
        }

        window.dispatchEvent(new CustomEvent("cart:updated", {
          detail: {
            product_id: productId,
            variant_id: variantId,
            quantity,
            response: data
          }
        }));

        await wait(1050);
      } catch (error) {
        if (
          error?.name === "AbortError" &&
          activeController?.signal.reason === "pagehide"
        ) {
          return;
        }

        if (error?.name === "AbortError") {
          setButtonVisual("error", "KẾT NỐI CHẬM");
          showFeedback(
            "error",
            "Kết nối phản hồi chậm",
            "Yêu cầu đã dừng để tránh thêm trùng. Vui lòng kiểm tra giỏ trước khi thử lại.",
            { action: false }
          );
        } else {
          setButtonVisual("error", "MẤT KẾT NỐI");
          showFeedback(
            "error",
            "Không thể kết nối",
            "Vui lòng kiểm tra mạng và thử lại.",
            { action: false }
          );
        }
        await wait(720);
      } finally {
        window.clearTimeout(timeoutId);
        activeController = null;
        pending = false;
        restoreUi(buttonSnapshot, controlSnapshot);

        if (!succeeded) {
          const retryButton =
            submitButtons.find((button) => !button.disabled && button.offsetParent !== null) ||
            submitButtons.find((button) => !button.disabled);
          retryButton?.focus({ preventScroll: true });
        }
      }
    });

    window.addEventListener("pagehide", () => {
      activeController?.abort("pagehide");
    });
  }

  GUA.ProductDetailCart = { init };
  GUA.ProductCartFeedback = feedback;
})();
