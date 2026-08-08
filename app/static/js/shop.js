(function () {
  "use strict";

  if (window.GUAMaisonShopV9) {
    window.GUAMaisonShopV9.init();
    return;
  }

  const SELECTOR = Object.freeze({
    page: "[data-shop-page]",
    card: "[data-shop-card]",
    grid: "[data-shop-grid]",
    empty: "[data-shop-empty]",
    filter: "[data-shop-filter]",
    filterCount: "[data-shop-filter-count]",
    visibleCount: "[data-shop-visible-count]",
    drawer: "[data-shop-filter-drawer]",
    quick: "[data-shop-quick-view]",
    notice: "[data-shop-notice]"
  });

  const state = {
    activeLayer: null,
    activeTrigger: null,
    quickCard: null,
    previousOverflow: "",
    noticeTimer: 0,
    initFrame: 0
  };

  const one = (selector, root = document) => root.querySelector(selector);
  const all = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function mountLayerAtViewport(selector, page) {
    const main = page?.closest("#main-content");
    const currentLayer = main?.querySelector(selector) || one(selector);
    if (!currentLayer || currentLayer.parentElement === document.body) return currentLayer;

    all(selector).forEach((layer) => {
      if (layer === currentLayer || layer.dataset.shopPortal !== "viewport") return;
      if (state.activeLayer === layer) closeLayer(layer, false);
      layer.remove();
    });

    currentLayer.dataset.shopPortal = "viewport";
    document.body.appendChild(currentLayer);
    return currentLayer;
  }

  function mountShopLayers(page) {
    mountLayerAtViewport(SELECTOR.drawer, page);
    mountLayerAtViewport(SELECTOR.quick, page);
    mountLayerAtViewport(SELECTOR.notice, page);
  }

  function normalizeDisplayText(value) {
    const text = String(value ?? "");
    return typeof text.normalize === "function" ? text.normalize("NFC") : text;
  }

  function parseList(value) {
    try {
      const result = JSON.parse(value || "[]");
      return Array.isArray(result) ? result.map(String) : [];
    } catch (_error) {
      return [];
    }
  }

  function setText(element, value) {
    const next = normalizeDisplayText(value);
    if (element && element.textContent !== next) element.textContent = next;
  }

  function csrfToken() {
    return one('meta[name="csrf-token"]')?.content || "";
  }

  function notify(message, type = "info") {
    const normalizedType = type === "danger" ? "error" : type;

    try {
      if (window.GUA && typeof window.GUA.snackbar === "function") {
        window.GUA.snackbar(normalizeDisplayText(message), normalizedType);
        return;
      }
    } catch (error) {
      console.warn("[GUAMAISON Shop] Global snackbar unavailable; using page notice.", error);
    }

    const notice = one(SELECTOR.notice);
    if (!notice) return;

    notice.textContent = normalizeDisplayText(message);
    notice.dataset.type = normalizedType;
    notice.setAttribute("role", normalizedType === "error" ? "alert" : "status");
    notice.classList.add("is-visible");
    window.clearTimeout(state.noticeTimer);
    state.noticeTimer = window.setTimeout(() => {
      notice.classList.remove("is-visible");
    }, 2400);
  }

  function setButtonState(button, status, label) {
    if (!button) return;

    const icon = one("i", button);
    const text = one("span", button);

    if (!button.dataset.defaultLabel) {
      button.dataset.defaultLabel = normalizeDisplayText(text?.textContent || "Thêm vào giỏ").trim();
    }
    if (icon && !button.dataset.defaultIcon) {
      button.dataset.defaultIcon = icon.className;
    }

    button.classList.remove("is-loading", "is-success", "is-error");

    const config = {
      loading: { className: "is-loading", icon: "fa-solid fa-spinner", label: "Đang thêm…" },
      success: { className: "is-success", icon: "fa-solid fa-check", label: "Đã thêm vào giỏ" },
      error: { className: "is-error", icon: "fa-solid fa-circle-exclamation", label: "Thử lại" }
    }[status];

    if (!config) {
      if (icon && button.dataset.defaultIcon) icon.className = button.dataset.defaultIcon;
      if (text) setText(text, button.dataset.defaultLabel);
      return;
    }

    button.classList.add(config.className);
    if (icon) icon.className = config.icon;
    if (text) setText(text, label || config.label);
  }

  function resetButtonAfter(button, initialDisabled, delay = 1800) {
    if (!button) return;

    window.clearTimeout(button._guaShopResetTimer);
    button._guaShopResetTimer = window.setTimeout(() => {
      setButtonState(button, "idle");
      button.disabled = Boolean(initialDisabled);
      delete button._guaShopResetTimer;
    }, delay);
  }

  function setQuickFeedback(message = "", type = "success") {
    const quick = one(SELECTOR.quick);
    if (!quick) return;

    const feedback = one("[data-shop-quick-feedback]", quick);
    if (!feedback) return;

    const visible = Boolean(message);
    feedback.hidden = !visible;
    feedback.dataset.type = type;
    setText(feedback, message);
  }

  function loginUrl() {
    const next = `${window.location.pathname}${window.location.search}`;
    return `/auth/login?next=${encodeURIComponent(next)}`;
  }

  function isLoginResponse(response) {
    if (response.status === 401 || response.status === 403) return true;
    if (!response.redirected) return false;

    try {
      return new URL(response.url).pathname.startsWith("/auth/login");
    } catch (_error) {
      return false;
    }
  }

  async function requestJson(url, options) {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 10000);

    try {
      const response = await fetch(url, { ...options, signal: controller.signal });

      if (isLoginResponse(response)) {
        return { response, data: {}, requiresLogin: true };
      }

      const contentType = response.headers.get("content-type") || "";
      const data = contentType.includes("application/json")
        ? await response.json().catch(() => ({}))
        : {};

      return { response, data, requiresLogin: false };
    } finally {
      window.clearTimeout(timer);
    }
  }

  function setLocked(locked) {
    if (locked) {
      state.previousOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      document.body.classList.add("gua-shop-overlay-open");
      window.MMScroll?.stop?.();
      return;
    }

    document.body.style.overflow = state.previousOverflow;
    document.body.classList.remove("gua-shop-overlay-open");
    window.MMScroll?.start?.();
  }

  function focusable(layer) {
    return all(
      'a[href], button:not([disabled]), select:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
      layer
    ).filter((element) => !element.hidden && element.getClientRects().length > 0);
  }

  function openLayer(layer, trigger) {
    if (!layer) return;
    if (layer.parentElement !== document.body) {
      layer.dataset.shopPortal = "viewport";
      document.body.appendChild(layer);
    }
    if (state.activeLayer && state.activeLayer !== layer) closeLayer(state.activeLayer, false);

    state.activeLayer = layer;
    state.activeTrigger = trigger || document.activeElement;
    layer.classList.add("is-open");
    layer.setAttribute("aria-hidden", "false");
    trigger?.setAttribute("aria-expanded", "true");
    setLocked(true);

    window.requestAnimationFrame(() => {
      focusable(layer)[0]?.focus({ preventScroll: true });
    });
  }

  function closeLayer(layer = state.activeLayer, restoreFocus = true) {
    if (!layer) return;

    layer.classList.remove("is-open");
    layer.setAttribute("aria-hidden", "true");
    state.activeTrigger?.setAttribute("aria-expanded", "false");

    const trigger = state.activeTrigger;
    state.activeLayer = null;
    state.activeTrigger = null;
    state.quickCard = null;
    setLocked(false);

    if (restoreFocus && trigger?.isConnected) {
      trigger.focus({ preventScroll: true });
    }
  }

  function trapFocus(event) {
    if (event.key !== "Tab" || !state.activeLayer) return;

    const items = focusable(state.activeLayer);
    if (!items.length) return;

    const first = items[0];
    const last = items[items.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function selectedValues(kind) {
    return all(`${SELECTOR.filter}[data-shop-filter="${kind}"]:checked`).map((input) => input.value);
  }

  function matchesCard(card, filters) {
    const cardValues = {
      category: parseList(card.dataset.categorySlugs),
      size: parseList(card.dataset.sizes),
      color: parseList(card.dataset.colors)
    };

    return Object.entries(filters).every(([kind, chosen]) => {
      if (!chosen.length) return true;
      return chosen.some((value) => cardValues[kind].includes(value));
    });
  }

  function applyFilters() {
    const page = one(SELECTOR.page);
    if (!page) return;

    const cards = all(SELECTOR.card, page);
    const filters = {
      category: selectedValues("category"),
      size: selectedValues("size"),
      color: selectedValues("color")
    };
    const activeCount = Object.values(filters).reduce((sum, values) => sum + values.length, 0);
    let visible = 0;

    cards.forEach((card) => {
      const matched = matchesCard(card, filters);
      card.hidden = !matched;
      if (matched) visible += 1;
    });

    all(SELECTOR.visibleCount).forEach((element) => {
      setText(element, visible);
    });

    all(SELECTOR.filterCount).forEach((element) => {
      setText(element, activeCount);
      element.hidden = activeCount === 0;
    });

    const grid = one(SELECTOR.grid, page);
    const empty = one(SELECTOR.empty, page);
    if (grid) grid.hidden = visible === 0;
    if (empty) empty.hidden = visible !== 0;
  }

  function clearFilters() {
    all(`${SELECTOR.filter}:checked`).forEach((input) => {
      input.checked = false;
    });
    applyFilters();
  }

  function loadHoverImage(card) {
    const image = one(".gua-shop-card__image--hover[data-src]", card);
    if (!image || image.dataset.loaded === "true") return;

    const source = image.dataset.src;
    if (!source) return;

    image.dataset.loaded = "true";
    image.addEventListener("load", () => image.classList.add("is-loaded"), { once: true });
    image.src = source;
  }

  function favoriteIds() {
    try {
      const value = JSON.parse(localStorage.getItem("mm_favs") || "[]");
      return Array.isArray(value) ? value.map(String) : [];
    } catch (_error) {
      return [];
    }
  }

  function paintFavorite(button, active) {
    button.setAttribute("aria-pressed", String(active));
    const icon = one("i", button);
    if (icon) icon.className = active ? "fa-solid fa-heart" : "fa-regular fa-heart";
  }

  function initFavorites(page) {
    const favorites = favoriteIds();
    all(SELECTOR.card, page).forEach((card) => {
      const button = one("[data-shop-favorite]", card);
      if (!button) return;
      paintFavorite(button, favorites.includes(String(card.dataset.id || "")));
    });
  }

  async function toggleFavorite(button, card) {
    const productId = String(card?.dataset.id || "");
    if (!productId || button.dataset.busy === "true") return;

    const wasActive = button.getAttribute("aria-pressed") === "true";
    button.dataset.busy = "true";
    paintFavorite(button, !wasActive);

    try {
      const { response, data, requiresLogin } = await requestJson("/api/favorites/toggle", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({ product_id: productId })
      });

      if (requiresLogin) {
        paintFavorite(button, wasActive);
        notify("Vui lòng đăng nhập để lưu sản phẩm", "warning");
        window.setTimeout(() => window.location.assign(loginUrl()), 650);
        return;
      }

      if (!response.ok || data.success === false) {
        throw new Error(data.message || "Không thể cập nhật yêu thích");
      }

      const favorites = favoriteIds().filter((id) => id !== productId);
      if (!wasActive) favorites.push(productId);
      localStorage.setItem("mm_favs", JSON.stringify(favorites));
      notify(!wasActive ? "Đã thêm vào yêu thích" : "Đã bỏ khỏi yêu thích", "success");
    } catch (error) {
      paintFavorite(button, wasActive);
      notify(error.name === "AbortError" ? "Kết nối quá chậm, vui lòng thử lại" : error.message || "Không thể cập nhật yêu thích", "error");
    } finally {
      delete button.dataset.busy;
    }
  }

  function cloneVariantOptions(card, target) {
    const source = one("[data-shop-variant-source]", card);
    target.replaceChildren();

    if (!source) return;
    Array.from(source.options).forEach((option) => target.appendChild(option.cloneNode(true)));

    const firstAvailable = Array.from(target.options).find((option) => !option.disabled);
    if (firstAvailable) target.value = firstAvailable.value;
  }

  function openQuickView(card, trigger) {
    const quick = one(SELECTOR.quick);
    if (!quick || !card) return;

    const image = one("[data-shop-quick-image]", quick);
    const title = one("[data-shop-quick-title]", quick);
    const category = one("[data-shop-quick-category]", quick);
    const price = one("[data-shop-quick-price]", quick);
    const link = one("[data-shop-quick-link]", quick);
    const select = one("[data-shop-quick-variant]", quick);
    const addButton = one("[data-shop-quick-add]", quick);

    if (image) {
      image.src = card.dataset.img || "";
      image.alt = card.dataset.title || "";
    }
    if (title) setText(title, card.dataset.title || "");
    if (category) setText(category, card.dataset.category || "GUAMAISON");
    if (price) setText(price, card.dataset.priceText || "");
    if (link) link.href = card.dataset.url || "/shop";
    if (select) cloneVariantOptions(card, select);
    if (addButton) {
      window.clearTimeout(addButton._guaShopResetTimer);
      setButtonState(addButton, "idle");
      addButton.disabled = !select?.value;
    }

    trigger?.removeAttribute("title");
    setQuickFeedback();

    state.quickCard = card;
    openLayer(quick, trigger);
  }

  async function addToCart(card, variantId, button) {
    if (!card || button?.dataset.busy === "true") return;

    const productId = card.dataset.id;
    const selectedVariant = variantId || card.dataset.firstVariant;

    if (!productId || !selectedVariant) {
      openQuickView(card, button);
      setQuickFeedback("Vui lòng chọn phân loại trước khi thêm.", "warning");
      notify("Vui lòng chọn phân loại", "warning");
      return;
    }

    const initialDisabled = Boolean(button?.disabled);
    let outcome = "idle";

    if (button) {
      window.clearTimeout(button._guaShopResetTimer);
      button.dataset.busy = "true";
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      setButtonState(button, "loading");
    }
    setQuickFeedback();

    try {
      const { response, data, requiresLogin } = await requestJson("/cart/add", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({ product_id: productId, variant_id: selectedVariant, quantity: 1 })
      });

      if (requiresLogin) {
        outcome = "login";
        setButtonState(button, "error", "Cần đăng nhập");
        setQuickFeedback("Vui lòng đăng nhập để thêm sản phẩm vào giỏ.", "warning");
        notify("Vui lòng đăng nhập để thêm vào giỏ", "warning");
        window.setTimeout(() => window.location.assign(loginUrl()), 650);
        return;
      }

      if (!response.ok || data.success === false) {
        throw new Error(data.message || "Không thể thêm vào giỏ hàng");
      }

      outcome = "success";
      const successMessage = data.message || "Đã thêm sản phẩm vào giỏ hàng";
      setButtonState(button, "success");
      setQuickFeedback("Đã thêm sản phẩm vào giỏ hàng.", "success");
      notify(successMessage, "success");
      window.dispatchEvent(new CustomEvent("cart:updated", { detail: data }));
    } catch (error) {
      outcome = "error";
      const errorMessage = error.name === "AbortError"
        ? "Kết nối quá chậm, vui lòng thử lại"
        : error.message || "Không thể thêm vào giỏ hàng";
      setButtonState(button, "error");
      setQuickFeedback(errorMessage, "error");
      notify(errorMessage, "error");
    } finally {
      if (button) {
        delete button.dataset.busy;
        button.removeAttribute("aria-busy");

        if (outcome === "success") {
          resetButtonAfter(button, initialDisabled, 1800);
        } else if (outcome === "error") {
          button.disabled = initialDisabled;
          resetButtonAfter(button, initialDisabled, 1800);
        } else if (outcome !== "login") {
          setButtonState(button, "idle");
          button.disabled = initialDisabled;
        }
      }
    }
  }

  function updateSort(select) {
    const form = one("[data-shop-search-form]");
    if (form) {
      let field = one('input[name="sort"]', form);
      if (!field) {
        field = document.createElement("input");
        field.type = "hidden";
        field.name = "sort";
        form.appendChild(field);
      }
      field.value = select.value;
      form.requestSubmit();
      return;
    }

    const url = new URL(window.location.href);
    url.searchParams.set("sort", select.value);
    url.searchParams.delete("page");
    window.location.assign(url.toString());
  }

  function initHeroVideo(page) {
    const video = one("[data-shop-hero-video]", page);
    if (!video || video.dataset.ready === "true") return;

    video.dataset.ready = "true";
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const saveData = Boolean(navigator.connection?.saveData);
    if (reducedMotion || saveData || !video.dataset.src) return;

    video.src = video.dataset.src;
    video.load();
    video.play().catch(() => {});
  }

  function init() {
    const page = one(SELECTOR.page);

    if (!page) {
      if (state.activeLayer && !state.activeLayer.isConnected) closeLayer(state.activeLayer, false);
      return;
    }

    mountShopLayers(page);
    initHeroVideo(page);
    initFavorites(page);
    all("[data-shop-quick][title]", page).forEach((button) => button.removeAttribute("title"));
    applyFilters();
  }

  function scheduleInit() {
    if (state.initFrame) return;
    state.initFrame = window.requestAnimationFrame(() => {
      state.initFrame = 0;
      init();
    });
  }

  document.addEventListener("pointerover", (event) => {
    if (!window.matchMedia("(hover: hover)").matches) return;
    const card = event.target.closest(SELECTOR.card);
    if (card) loadHoverImage(card);
  }, { passive: true });

  document.addEventListener("focusin", (event) => {
    const card = event.target.closest(SELECTOR.card);
    if (card) loadHoverImage(card);
  });

  document.addEventListener("click", (event) => {
    const action = event.target.closest(
      "[data-shop-open-filter], [data-shop-close-filter], [data-shop-clear-filter], " +
      "[data-shop-favorite], [data-shop-quick], [data-shop-add], " +
      "[data-shop-close-quick], [data-shop-quick-add]"
    );

    if (!action) return;

    if (action.matches("[data-shop-open-filter]")) {
      event.preventDefault();
      openLayer(one(SELECTOR.drawer), action);
      return;
    }

    if (action.matches("[data-shop-close-filter], [data-shop-close-quick]")) {
      event.preventDefault();
      closeLayer();
      return;
    }

    if (action.matches("[data-shop-clear-filter]")) {
      event.preventDefault();
      clearFilters();
      return;
    }

    const card = action.closest(SELECTOR.card);

    if (action.matches("[data-shop-favorite]")) {
      event.preventDefault();
      toggleFavorite(action, card);
      return;
    }

    if (action.matches("[data-shop-quick]")) {
      event.preventDefault();
      openQuickView(card, action);
      return;
    }

    if (action.matches("[data-shop-add]")) {
      event.preventDefault();
      addToCart(card, card?.dataset.firstVariant, action);
      return;
    }

    if (action.matches("[data-shop-quick-add]")) {
      event.preventDefault();
      const select = one("[data-shop-quick-variant]", one(SELECTOR.quick));
      addToCart(state.quickCard, select?.value, action);
    }
  });

  document.addEventListener("change", (event) => {
    if (event.target.matches(SELECTOR.filter)) {
      applyFilters();
      return;
    }

    if (event.target.matches("[data-shop-sort]")) {
      updateSort(event.target);
      return;
    }

    if (event.target.matches("[data-shop-quick-variant]")) {
      const addButton = one("[data-shop-quick-add]", one(SELECTOR.quick));
      if (addButton) {
        window.clearTimeout(addButton._guaShopResetTimer);
        setButtonState(addButton, "idle");
        addButton.disabled = !event.target.value;
      }
      setQuickFeedback();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.activeLayer) {
      event.preventDefault();
      closeLayer();
      return;
    }
    trapFocus(event);
  });

  ["gua:route:complete", "mm:route:complete", "router:complete"].forEach((eventName) => {
    document.addEventListener(eventName, scheduleInit);
  });

  window.addEventListener("pageshow", scheduleInit);

  const observer = new MutationObserver((mutations) => {
    const touchesShop = mutations.some((mutation) => {
      return [...mutation.addedNodes, ...mutation.removedNodes].some((node) => {
        if (node.nodeType !== Node.ELEMENT_NODE) return false;
        return node.matches?.(`${SELECTOR.page}, ${SELECTOR.drawer}, ${SELECTOR.quick}`) ||
          Boolean(node.querySelector?.(`${SELECTOR.page}, ${SELECTOR.drawer}, ${SELECTOR.quick}`));
      });
    });

    if (touchesShop) {
      scheduleInit();
    }
  });

  function start() {
    init();
    observer.observe(document.body, { childList: true, subtree: true });
  }

  window.GUAMaisonShopV9 = Object.freeze({ version: "9.1.2", init: scheduleInit });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
