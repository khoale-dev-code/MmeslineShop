(function () {
  "use strict";

  const root = document.getElementById("menuAdmin");
  if (!root) return;

  let dirty = false;
  let saving = false;

  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));
  const value = (selector, scope = document) => ($(selector, scope)?.value || "").trim();
  const checked = (selector, scope = document) => Boolean($(selector, scope)?.checked);
  const makeId = (prefix) => `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;

  function notify(message, type = "success") {
    document.querySelector(".menu-toast")?.remove();
    const toast = document.createElement("div");
    toast.className = `menu-toast${type === "error" ? " is-error" : ""}`;
    toast.setAttribute("role", "status");
    toast.textContent = message;
    document.body.appendChild(toast);
    window.setTimeout(() => toast.remove(), 4200);
  }

  function markDirty() {
    if (saving) return;
    dirty = true;
    const status = $("#menuSaveStatus");
    if (status) status.innerHTML = '<i class="fa-solid fa-circle mr-2 text-amber-500"></i>Có thay đổi chưa lưu.';
  }

  function switchTab(name) {
    $$("[data-menu-tab]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.menuTab === name);
    });
    $$("[data-menu-panel]").forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.menuPanel === name);
    });
    history.replaceState(null, "", `#${name}`);
  }

  function cloneTemplate(templateId, rowType) {
    const template = document.getElementById(templateId);
    const row = template?.content.firstElementChild?.cloneNode(true);
    if (!row) return null;
    row.dataset.id = makeId(rowType);
    return row;
  }

  function moveRow(button, direction) {
    const row = button.closest("[data-row]");
    if (!row) return;
    if (direction === "up" && row.previousElementSibling) {
      row.parentElement.insertBefore(row, row.previousElementSibling);
      markDirty();
    }
    if (direction === "down" && row.nextElementSibling) {
      row.parentElement.insertBefore(row.nextElementSibling, row);
      markDirty();
    }
  }

  function addRow(button) {
    const type = button.dataset.add;
    if (type === "navbar") {
      const list = $("#navbarItems");
      if ($$("[data-row='navbar']", list).length >= 12) {
        notify("Navbar chỉ hỗ trợ tối đa 12 mục.", "error");
        return;
      }
      const row = cloneTemplate("navbarRowTemplate", "nav");
      if (row) list.appendChild(row);
    } else if (type === "footer-link") {
      const card = button.closest(".footer-column");
      const list = $(".js-footer-links", card);
      if ($$("[data-row='footer-link']", list).length >= 12) {
        notify("Mỗi cột footer hỗ trợ tối đa 12 liên kết.", "error");
        return;
      }
      const row = cloneTemplate("linkRowTemplate", "footer");
      if (row) list.appendChild(row);
    } else if (type === "bottom-link") {
      const list = $("#bottomLinks");
      if ($$("[data-row='bottom-link']", list).length >= 6) {
        notify("Thanh cuối footer hỗ trợ tối đa 6 liên kết.", "error");
        return;
      }
      const row = cloneTemplate("linkRowTemplate", "bottom");
      if (row) {
        row.dataset.row = "bottom-link";
        list.appendChild(row);
      }
    }
    markDirty();
  }

  function syncCategoryPicker() {
    const fieldset = $("#categoryPicker");
    if (!fieldset) return;
    const manual = value("#categoryMode") === "selected";
    const visible = checked("#showCategories");
    fieldset.disabled = !manual || !visible;
    fieldset.style.opacity = manual && visible ? "1" : ".52";
  }

  function collectLink(row) {
    return {
      id: row.dataset.id || makeId("link"),
      label: value(".js-label", row),
      url: value(".js-url", row) || "#",
      new_tab: checked(".js-new-tab", row),
    };
  }

  function collectPayload() {
    const navbarItems = $$("#navbarItems [data-row='navbar']").map((row) => ({
      id: row.dataset.id || makeId("nav"),
      label: value(".js-label", row),
      url: value(".js-url", row) || "#",
      kind: value(".js-kind", row) || "link",
      enabled: checked(".js-enabled", row),
      new_tab: checked(".js-new-tab", row),
    }));

    const columns = $$(".footer-column").map((column, index) => ({
      id: `column-${index + 1}`,
      title: value(".js-column-title", column),
      links: $$(".js-footer-links [data-row]", column).map(collectLink),
    }));

    const socials = {};
    $$(".js-social").forEach((input) => {
      socials[input.dataset.platform] = input.value.trim() || "#";
    });

    return {
      navbar: {
        brand_label: value("#navBrandLabel") || "GUAMAISON",
        transparent_home: checked("#navTransparentHome"),
        items: navbarItems,
      },
      product_menu: {
        heading: value("#productHeading") || "Shop",
        show_new_arrivals: checked("#showNewArrivals"),
        new_arrivals_label: value("#newArrivalsLabel") || "New Arrival",
        new_arrivals_url: value("#newArrivalsUrl") || "/shop?sort=new",
        show_all_products: checked("#showAllProducts"),
        all_products_label: value("#allProductsLabel") || "All Products",
        all_products_url: value("#allProductsUrl") || "/shop",
        show_categories: checked("#showCategories"),
        category_mode: value("#categoryMode") || "automatic",
        category_limit: Number.parseInt(value("#productCategoryLimit"), 10) || 12,
        selected_category_ids: $$("#categoryPicker input:checked").map((input) => input.value),
      },
      footer: {
        kicker: value("#footerKicker"),
        seal: value("#footerSeal"),
        brand_name: value("#footerBrandName") || "GUAMAISON",
        description: value("#footerDescription"),
        newsletter_enabled: checked("#newsletterEnabled"),
        newsletter_placeholder: value("#newsletterPlaceholder"),
        newsletter_button_label: value("#newsletterButtonLabel"),
        columns,
        contact_title: value("#contactTitle"),
        contact_text: value("#contactText"),
        contact_email: value("#contactEmail"),
        socials,
        copyright: value("#footerCopyright"),
        bottom_links: $$("#bottomLinks [data-row]").map(collectLink),
      },
    };
  }

  function validate(payload) {
    const visibleItems = payload.navbar.items.filter((item) => item.enabled && item.label);
    if (!visibleItems.length) return "Navbar cần ít nhất một mục đang hiển thị.";
    if (payload.navbar.items.some((item) => !item.label)) return "Mỗi mục navbar phải có nhãn.";

    for (const column of payload.footer.columns) {
      if (!column.title) return "Mỗi cột footer phải có tiêu đề.";
      if (column.links.some((link) => !link.label)) return "Mỗi liên kết footer phải có nhãn.";
    }
    return "";
  }

  async function save() {
    if (saving) return;
    const payload = collectPayload();
    const error = validate(payload);
    if (error) {
      notify(error, "error");
      return;
    }

    const button = $("#saveMenusBtn");
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content || "";
    const original = button.innerHTML;
    saving = true;
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>Đang lưu';

    try {
      const response = await fetch(root.dataset.saveUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(payload),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok || !result.success) {
        throw new Error(result.message || `Không thể lưu (HTTP ${response.status}).`);
      }

      dirty = false;
      const status = $("#menuSaveStatus");
      if (status) status.innerHTML = '<i class="fa-solid fa-circle-check mr-2 text-emerald-600"></i>Đã đồng bộ với storefront.';
      notify(result.message || "Đã lưu cấu hình menu.");
    } catch (err) {
      notify(err.message || "Mất kết nối tới máy chủ.", "error");
    } finally {
      saving = false;
      button.disabled = false;
      button.innerHTML = original;
    }
  }

  root.addEventListener("click", (event) => {
    const tab = event.target.closest("[data-menu-tab]");
    if (tab) return switchTab(tab.dataset.menuTab);

    const add = event.target.closest("[data-add]");
    if (add) return addRow(add);

    const action = event.target.closest("[data-action]");
    if (action?.dataset.action === "remove") {
      action.closest("[data-row]")?.remove();
      markDirty();
    } else if (action?.dataset.action === "up" || action?.dataset.action === "down") {
      moveRow(action, action.dataset.action);
    }

    if (event.target.closest("[data-reset]")) {
      if (!dirty || window.confirm("Bỏ toàn bộ thay đổi chưa lưu?")) window.location.reload();
    }

    if (event.target.closest("#saveMenusBtn")) save();
  });

  root.addEventListener("input", markDirty);
  root.addEventListener("change", (event) => {
    markDirty();
    if (event.target.matches("#categoryMode, #showCategories")) syncCategoryPicker();
  });

  window.addEventListener("beforeunload", (event) => {
    if (!dirty || saving) return;
    event.preventDefault();
    event.returnValue = "";
  });

  const initialTab = ["navbar", "products", "footer"].includes(location.hash.slice(1))
    ? location.hash.slice(1)
    : "navbar";
  switchTab(initialTab);
  syncCategoryPicker();
})();
