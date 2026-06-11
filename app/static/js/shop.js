(function () {
  "use strict";

  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const grid = document.getElementById("shopGrid");
  const empty = document.getElementById("shopEmpty");
  const toast = document.getElementById("shopToast");
  const drawer = document.getElementById("filterDrawer");
  const quick = document.getElementById("quickModal");
  const search = document.getElementById("shopLiveSearch");
  const mobileSearch = document.getElementById("shopMobileSearch");

  const countEls = [
    document.getElementById("shopCount"),
    document.getElementById("shopHeroCount")
  ].filter(Boolean);

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function parseJson(value, fallback = []) {
    try {
      return JSON.parse(value || "");
    } catch (_) {
      return fallback;
    }
  }

  function cards() {
    return grid ? $$(".mm-card", grid) : [];
  }

  function checked(selector) {
    return $$(selector + ":checked").map((input) => input.value);
  }

  function money(value) {
    return (Number(value) || 0).toLocaleString("vi-VN") + "₫";
  }

  function notify(message) {
    if (!toast) return;

    toast.textContent = message || "";
    toast.classList.add("show");

    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.classList.remove("show");
    }, 2200);
  }

  function setPageLocked(locked) {
    document.body.style.overflow = locked ? "hidden" : "";
    window.MMScroll?.[locked ? "stop" : "start"]?.();
  }

  function openDrawer() {
    drawer?.classList.add("open");
    setPageLocked(true);
  }

  function closeDrawer() {
    drawer?.classList.remove("open");
    setPageLocked(false);
  }

  function openQuick() {
    quick?.classList.add("open");
    setPageLocked(true);
  }

  function closeQuick() {
    quick?.classList.remove("open");
    setPageLocked(false);
  }

  function normalizeUrl(url) {
    return String(url || "").trim();
  }

  function prefetchUrl(url) {
    const cleanUrl = normalizeUrl(url);

    if (!cleanUrl || document.querySelector(`link[rel="prefetch"][href="${cleanUrl}"]`)) {
      return;
    }

    const link = document.createElement("link");
    link.rel = "prefetch";
    link.as = "document";
    link.href = cleanUrl;

    document.head.appendChild(link);
  }

  /**
   * Fix chính:
   * - Không dùng goToProduct qua card nữa.
   * - Bắt trực tiếp từng <a data-product-link>.
   * - Dùng capture phase để tránh JS khác trong base/data-nav chặn link.
   * - Lấy href từ chính link đang bấm, không lấy nhầm card bên cạnh.
   */
  function initProductLinks() {
    const links = $$("[data-product-link]");

    links.forEach((link) => {
      if (link.dataset.shopLinkReady === "1") return;
      link.dataset.shopLinkReady = "1";

      const card = link.closest(".mm-card");

      if (card?.dataset.url && link.getAttribute("href") !== card.dataset.url) {
        link.setAttribute("href", card.dataset.url);
      }

      let startX = 0;
      let startY = 0;
      let moved = false;

      const href = () => normalizeUrl(link.getAttribute("href"));

      link.addEventListener("pointerdown", (event) => {
        startX = event.clientX;
        startY = event.clientY;
        moved = false;

        prefetchUrl(href());
      }, { passive: true, capture: true });

      link.addEventListener("touchstart", (event) => {
        const touch = event.touches && event.touches[0];

        if (!touch) return;

        startX = touch.clientX;
        startY = touch.clientY;
        moved = false;

        prefetchUrl(href());
      }, { passive: true, capture: true });

      link.addEventListener("pointermove", (event) => {
        const dx = Math.abs(event.clientX - startX);
        const dy = Math.abs(event.clientY - startY);

        if (dx > 8 || dy > 8) {
          moved = true;
        }
      }, { passive: true, capture: true });

      link.addEventListener("touchmove", (event) => {
        const touch = event.touches && event.touches[0];

        if (!touch) return;

        const dx = Math.abs(touch.clientX - startX);
        const dy = Math.abs(touch.clientY - startY);

        if (dx > 8 || dy > 8) {
          moved = true;
        }
      }, { passive: true, capture: true });

      link.addEventListener("click", (event) => {
        const url = href();

        if (!url) return;

        if (moved) {
          event.preventDefault();
          event.stopPropagation();
          moved = false;
          return;
        }

        event.preventDefault();
        event.stopImmediatePropagation();

        window.location.assign(url);
      }, { capture: true });
    });
  }

  function applyFilters() {
    if (!grid) return;

    const term = (search?.value || mobileSearch?.value || "").trim().toLowerCase();
    const cats = checked(".filter-category");
    const sizes = checked(".filter-size");
    const colors = checked(".filter-color");
    const sort = $('input[name="shopSort"]:checked')?.value || "newest";
    const visible = [];

    cards().forEach((card) => {
      const name = card.dataset.name || "";
      const catSlugs = parseJson(card.dataset.categorySlugs);
      const catNames = parseJson(card.dataset.categoryNames);
      const cardSizes = parseJson(card.dataset.sizes);
      const cardColors = parseJson(card.dataset.colors);

      let ok = true;

      if (term && !name.includes(term) && !catNames.some((c) => String(c).includes(term))) {
        ok = false;
      }

      if (ok && cats.length && !cats.some((c) => catSlugs.includes(c))) {
        ok = false;
      }

      if (ok && sizes.length && !sizes.some((s) => cardSizes.includes(s))) {
        ok = false;
      }

      if (ok && colors.length && !colors.some((c) => cardColors.includes(c))) {
        ok = false;
      }

      card.hidden = !ok;

      if (ok) {
        visible.push(card);
      }
    });

    visible.sort((a, b) => {
      if (sort === "price_asc") {
        return Number(a.dataset.price) - Number(b.dataset.price);
      }

      if (sort === "price_desc") {
        return Number(b.dataset.price) - Number(a.dataset.price);
      }

      if (sort === "best") {
        return Number(b.dataset.sold) - Number(a.dataset.sold);
      }

      return new Date(b.dataset.created || 0) - new Date(a.dataset.created || 0);
    });

    visible.forEach((card) => grid.appendChild(card));

    countEls.forEach((el) => {
      el.textContent = visible.length;
    });

    grid.style.display = visible.length ? "grid" : "none";
    empty?.classList.toggle("show", visible.length === 0);

    initProductLinks();
  }

  function clearFilters() {
    $$(".filter-category,.filter-size,.filter-color").forEach((input) => {
      input.checked = false;
    });

    const newest = $('input[name="shopSort"][value="newest"]');

    if (newest) {
      newest.checked = true;
    }

    if (search) {
      search.value = "";
    }

    if (mobileSearch) {
      mobileSearch.value = "";
    }

    applyFilters();
  }

  function escapeAttr(value) {
    return String(value).replace(/"/g, "&quot;");
  }

  function initChips() {
    const meta = document.getElementById("shopFilterMeta");

    if (!meta) return;

    const data = parseJson(meta.textContent, { sizes: [], colors: [] });

    function render(list, boxId, groupId, cls) {
      const box = document.getElementById(boxId);
      const group = document.getElementById(groupId);

      if (!list?.length || !box || !group) return;

      group.classList.remove("hidden");

      box.innerHTML = list.map((value) => {
        const safe = escapeAttr(value);

        return `
          <label class="mm-chip">
            <input type="checkbox" class="${cls}" value="${safe}">
            <span>${safe}</span>
          </label>
        `;
      }).join("");
    }

    render(data.sizes, "sizeChips", "sizeGroup", "filter-size");
    render(data.colors, "colorChips", "colorGroup", "filter-color");
  }

  async function addToCart(card, variantId) {
    const productId = card?.dataset.id;
    const selectedVariant = variantId || card?.dataset.firstVariant;

    if (!productId || !selectedVariant) {
      notify("Vui lòng chọn phân loại");
      openQuickFromCard(card);
      return;
    }

    try {
      const res = await fetch("/cart/add", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({
          product_id: productId,
          variant_id: selectedVariant,
          quantity: 1
        })
      });

      if (res.status === 401) {
        notify("Vui lòng đăng nhập");

        setTimeout(() => {
          window.location.href = "/auth/login";
        }, 700);

        return;
      }

      const data = await res.json().catch(() => ({}));

      if (!res.ok || data.success === false) {
        notify(data.message || "Không thể thêm giỏ hàng");
        return;
      }

      notify("Đã thêm vào giỏ hàng");
    } catch (_) {
      notify("Lỗi kết nối");
    }
  }

  function openQuickFromCard(card) {
    if (!card) return;

    const img = $("#qvImg");
    const title = $("#qvTitle");
    const cat = $("#qvCat");
    const price = $("#qvPrice");
    const link = $("#qvLink");
    const select = $("#qvVariant");
    const addBtn = $("#qvAdd");
    const source = $("[data-variant-select-source]", card);

    if (img) {
      img.src = card.dataset.img || "";
      img.alt = card.dataset.title || "";
    }

    if (title) {
      title.textContent = card.dataset.title || "";
    }

    if (cat) {
      cat.textContent = card.dataset.category || "GUAMAISON";
    }

    if (price) {
      price.textContent = card.dataset.priceText || money(card.dataset.price);
    }

    if (link) {
      link.href = card.dataset.url || "#";
    }

    if (select) {
      select.innerHTML = source ? source.innerHTML : "";
    }

    if (addBtn) {
      addBtn.onclick = () => addToCart(card, select?.value);
    }

    openQuick();
  }

  function initFavorites() {
    let favs = parseJson(localStorage.getItem("mm_favs"), []);

    cards().forEach((card) => {
      const btn = $("[data-fav]", card);
      const productId = String(card.dataset.id || "");

      if (!btn || !productId || btn.dataset.favReady === "1") return;

      btn.dataset.favReady = "1";

      if (favs.includes(productId)) {
        btn.classList.add("is-on");
        $("i", btn).className = "fa-solid fa-heart";
      }

      btn.addEventListener("click", async (event) => {
        event.preventDefault();
        event.stopPropagation();

        const wasOn = btn.classList.contains("is-on");

        btn.classList.toggle("is-on", !wasOn);
        $("i", btn).className = wasOn ? "fa-regular fa-heart" : "fa-solid fa-heart";

        try {
          const res = await fetch("/api/favorites/toggle", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrf
            },
            body: JSON.stringify({ product_id: productId })
          });

          if (res.status === 401) {
            btn.classList.toggle("is-on", wasOn);
            $("i", btn).className = wasOn ? "fa-solid fa-heart" : "fa-regular fa-heart";
            notify("Vui lòng đăng nhập");
            return;
          }

          favs = favs.filter((id) => id !== productId);

          if (!wasOn) {
            favs.push(productId);
          }

          localStorage.setItem("mm_favs", JSON.stringify(favs));
          notify(!wasOn ? "Đã thêm yêu thích" : "Đã bỏ yêu thích");
        } catch (_) {
          btn.classList.toggle("is-on", wasOn);
          $("i", btn).className = wasOn ? "fa-solid fa-heart" : "fa-regular fa-heart";
          notify("Lỗi kết nối");
        }
      });
    });
  }

  function initEvents() {
    document.addEventListener("click", (event) => {
      const actionEl = event.target.closest(
        "[data-open-filter], [data-close-filter], [data-clear-filter], [data-close-quick], [data-quick], [data-add]"
      );

      if (!actionEl) return;

      const card = actionEl.closest(".mm-card");

      event.preventDefault();
      event.stopPropagation();

      if (actionEl.matches("[data-open-filter]")) {
        openDrawer();
        return;
      }

      if (actionEl.matches("[data-close-filter]")) {
        closeDrawer();
        return;
      }

      if (actionEl.matches("[data-clear-filter]")) {
        clearFilters();
        return;
      }

      if (actionEl.matches("[data-close-quick]")) {
        closeQuick();
        return;
      }

      if (actionEl.matches("[data-quick]") && card) {
        openQuickFromCard(card);
        return;
      }

      if (actionEl.matches("[data-add]") && card) {
        addToCart(card);
      }
    });

    document.addEventListener("change", (event) => {
      if (event.target.matches(".filter-category,.filter-size,.filter-color,input[name='shopSort']")) {
        applyFilters();
      }
    });

    let searchTimer;

    [search, mobileSearch].forEach((input) => {
      input?.addEventListener("input", () => {
        if (input === mobileSearch && search) {
          search.value = mobileSearch.value;
        }

        clearTimeout(searchTimer);
        searchTimer = setTimeout(applyFilters, 160);
      });
    });

    $$("[data-grid]").forEach((btn) => {
      btn.addEventListener("click", () => {
        grid?.classList.remove("large", "compact");

        if (btn.dataset.grid === "large") {
          grid?.classList.add("large");
        }

        if (btn.dataset.grid === "compact") {
          grid?.classList.add("compact");
        }
      });
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeDrawer();
        closeQuick();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initChips();
    initFavorites();
    initProductLinks();
    initEvents();
    applyFilters();
  });
})();