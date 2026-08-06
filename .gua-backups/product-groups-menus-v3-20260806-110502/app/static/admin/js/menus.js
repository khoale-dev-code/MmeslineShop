(function () {
  "use strict";

  const root = document.getElementById("menuAdmin");
  const dataNode = document.getElementById("menuInitialData");
  if (!root || !dataNode) return;

  const initial = JSON.parse(dataNode.textContent || "{}");
  const config = initial.config || {};
  let menus = structuredClone(config.menus || []);
  let placements = { ...(config.placements || {}) };
  let selectedHandle = placements.navbar || menus[0]?.handle || "";
  let editingId = null;
  let dirty = false;
  let saving = false;

  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));
  const makeId = (prefix = "item") => `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  const slugify = (text) => String(text || "menu").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 90) || "menu";
  const escapeHtml = (text) => String(text ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));

  const catalogs = {
    product: (initial.products || []).map((item) => ({ id: String(item.id), label: item.name, url: `/product/${item.slug}` })),
    category: (initial.categories || []).map((item) => ({ id: String(item.id), label: item.name, url: `/shop?category=${encodeURIComponent(item.slug)}` })),
    collection: (initial.collections || []).map((item) => ({ id: String(item.id), label: item.name, url: `/shop?collection=${encodeURIComponent(item.slug)}` })),
    page: [
      { id: "shop", label: "Tất cả sản phẩm", url: "/shop" },
      { id: "collections", label: "Tất cả nhóm sản phẩm", url: "/collections" },
      { id: "about", label: "Giới thiệu", url: "/about" },
      { id: "contact", label: "Liên hệ", url: "/contact" },
      { id: "cart", label: "Giỏ hàng", url: "/cart/" },
      { id: "favorites", label: "Yêu thích", url: "/profile/favorites" },
    ],
  };

  function currentMenu() { return menus.find((menu) => menu.handle === selectedHandle) || menus[0]; }
  function notify(message, type = "success") {
    $(".hm-toast")?.remove();
    const toast = document.createElement("div");
    toast.className = `hm-toast${type === "error" ? " is-error" : ""}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4200);
  }
  function markDirty() {
    if (saving) return;
    dirty = true;
    $("#menuSaveStatus").innerHTML = '<i class="fa-solid fa-circle mr-2 text-amber-500"></i>Có thay đổi chưa lưu.';
  }

  function flatten(items, depth = 1, parent = null, output = []) {
    (items || []).forEach((item, index) => {
      const entry = { item, depth, parent, array: items, index };
      output.push(entry);
      flatten(item.children || [], depth + 1, entry, output);
    });
    return output;
  }
  function findEntry(id) { return flatten(currentMenu()?.items || []).find((entry) => entry.item.id === id); }
  function countItems(items) { return flatten(items || []).length; }

  function renderMenuList() {
    const list = $("#menuList");
    list.innerHTML = menus.map((menu) => `
      <button type="button" class="hm-menu-button ${menu.handle === selectedHandle ? "is-active" : ""}" data-menu-handle="${escapeHtml(menu.handle)}">
        <span class="min-w-0"><strong class="block truncate text-xs font-black">${escapeHtml(menu.title)}</strong><small class="mt-1 block truncate font-mono text-[10px] text-[#8a6a52]">${escapeHtml(menu.handle)}</small></span>
        <span class="shrink-0 rounded-full bg-[#f4ece5] px-2 py-1 text-[9px] font-black text-[#75543f]">${countItems(menu.items)}</span>
      </button>`).join("");
  }

  function renderTree() {
    const menu = currentMenu();
    const rows = flatten(menu?.items || []);
    $("#itemCount").textContent = `${rows.length}/120 liên kết`;
    $("#menuTree").innerHTML = rows.length ? rows.map(({ item, depth }) => `
      <div class="hm-item ${item.enabled === false ? "opacity-50" : ""}" data-item-id="${escapeHtml(item.id)}" data-depth="${depth}">
        <span class="hm-drag" title="Sắp xếp"><i class="fa-solid fa-grip-vertical"></i></span>
        <span class="min-w-0"><strong class="hm-item-title block truncate">${escapeHtml(item.label)}</strong><small class="hm-item-meta block truncate">Cấp ${depth} · ${escapeHtml(item.link_type || "url")} · ${escapeHtml(item.url || "#")}</small></span>
        <span class="hm-actions">
          <button type="button" class="hm-icon" data-item-action="up" title="Lên"><i class="fa-solid fa-arrow-up"></i></button>
          <button type="button" class="hm-icon" data-item-action="down" title="Xuống"><i class="fa-solid fa-arrow-down"></i></button>
          <button type="button" class="hm-icon" data-item-action="indent" title="Thành menu con"><i class="fa-solid fa-indent"></i></button>
          <button type="button" class="hm-icon" data-item-action="outdent" title="Giảm cấp"><i class="fa-solid fa-outdent"></i></button>
          <button type="button" class="hm-icon" data-item-action="edit" title="Sửa"><i class="fa-regular fa-pen-to-square"></i></button>
          <button type="button" class="hm-icon text-rose-600" data-item-action="remove" title="Xóa"><i class="fa-regular fa-trash-can"></i></button>
        </span>
      </div>`).join("") : '<div class="hm-empty"><i class="fa-solid fa-link mb-2 text-lg"></i><br>Menu chưa có liên kết. Hãy thêm liên kết đầu tiên bên dưới.</div>';
  }

  function loadSelectedMenu() {
    const menu = currentMenu();
    if (!menu) return;
    selectedHandle = menu.handle;
    $("#menuTitle").value = menu.title;
    $("#menuHandle").value = menu.handle;
    renderMenuList();
    renderTree();
    resetItemEditor();
  }

  function uniqueHandle(seed, exceptId = "") {
    const base = slugify(seed);
    let value = base;
    let index = 2;
    while (menus.some((menu) => menu.id !== exceptId && menu.handle === value)) value = `${base}-${index++}`;
    return value;
  }

  function createMenu() {
    const title = window.prompt("Tên menu mới:", "Menu mới");
    if (!title?.trim()) return;
    const handle = uniqueHandle(title);
    menus.push({ id: makeId("menu"), title: title.trim().slice(0, 100), handle, items: [] });
    selectedHandle = handle;
    renderPlacements();
    loadSelectedMenu();
    markDirty();
  }
  function deleteMenu() {
    const menu = currentMenu();
    if (!menu || menus.length <= 1) return notify("Cần giữ lại ít nhất một menu.", "error");
    if (!window.confirm(`Xóa menu “${menu.title}”? Các liên kết bên trong cũng sẽ bị xóa.`)) return;
    menus = menus.filter((item) => item.id !== menu.id);
    const fallback = menus[0].handle;
    Object.keys(placements).forEach((key) => { if (placements[key] === menu.handle) placements[key] = fallback; });
    selectedHandle = fallback;
    renderPlacements();
    loadSelectedMenu();
    markDirty();
  }

  function updateMenuIdentity(field) {
    const menu = currentMenu();
    if (!menu) return;
    if (field === "title") {
      menu.title = $("#menuTitle").value.trim().slice(0, 100) || "Menu chưa đặt tên";
    } else {
      const old = menu.handle;
      menu.handle = uniqueHandle($("#menuHandle").value, menu.id);
      selectedHandle = menu.handle;
      Object.keys(placements).forEach((key) => { if (placements[key] === old) placements[key] = menu.handle; });
      $("#menuHandle").value = menu.handle;
      renderPlacements();
    }
    renderMenuList();
    markDirty();
  }

  function targetOptions(type) {
    if (type === "home") return [{ id: "home", label: "Trang chủ", url: "/" }];
    if (type === "search") return [{ id: "search", label: "Tìm kiếm sản phẩm", url: "/shop?search=" }];
    return catalogs[type] || [];
  }
  function refreshTarget(selectedId = "") {
    const type = $("#itemLinkType").value;
    const options = targetOptions(type);
    const targetField = $("#targetField");
    const urlField = $("#urlField");
    const hasPicker = options.length > 0 && type !== "url";
    targetField.classList.toggle("hidden", !hasPicker);
    urlField.classList.toggle("hidden", type !== "url" && type !== "search");
    $("#itemTarget").innerHTML = options.map((item) => `<option value="${escapeHtml(item.id)}" data-url="${escapeHtml(item.url)}">${escapeHtml(item.label)}</option>`).join("");
    if (selectedId && options.some((item) => item.id === String(selectedId))) $("#itemTarget").value = String(selectedId);
    syncTarget();
  }
  function syncTarget() {
    const type = $("#itemLinkType").value;
    if (type === "url") return;
    if (type === "none") { $("#itemUrl").value = "#"; return; }
    const option = $("#itemTarget").selectedOptions[0];
    if (option) {
      $("#itemUrl").value = option.dataset.url || "#";
      if (!$("#itemLabel").value.trim()) $("#itemLabel").value = option.textContent.trim();
    }
  }

  function resetItemEditor() {
    editingId = null;
    $("#itemEditorTitle").textContent = "Thêm liên kết";
    $("#saveItemBtn").innerHTML = '<i class="fa-solid fa-plus"></i>Thêm liên kết';
    $("#cancelItemBtn").classList.add("hidden");
    $("#itemLabel").value = "";
    $("#itemLinkType").value = "url";
    $("#itemUrl").value = "";
    $("#itemKind").value = "link";
    $("#itemEnabled").checked = true;
    $("#itemNewTab").checked = false;
    refreshTarget();
  }
  function editItem(id) {
    const entry = findEntry(id);
    if (!entry) return;
    const item = entry.item;
    editingId = item.id;
    $("#itemEditorTitle").textContent = "Chỉnh sửa liên kết";
    $("#saveItemBtn").innerHTML = '<i class="fa-solid fa-check"></i>Cập nhật liên kết';
    $("#cancelItemBtn").classList.remove("hidden");
    $("#itemLabel").value = item.label || "";
    $("#itemLinkType").value = item.link_type || "url";
    $("#itemUrl").value = item.url || "#";
    $("#itemKind").value = item.kind || "link";
    $("#itemEnabled").checked = item.enabled !== false;
    $("#itemNewTab").checked = Boolean(item.new_tab);
    refreshTarget(item.target_id || "");
    $("#itemUrl").value = item.url || "#";
    $("#itemEditor").scrollIntoView({ behavior: "smooth", block: "center" });
  }
  function saveItem() {
    const label = $("#itemLabel").value.trim();
    if (!label) return notify("Vui lòng nhập tên liên kết.", "error");
    const type = $("#itemLinkType").value;
    const target = $("#itemTarget").value || "";
    const payload = {
      id: editingId || makeId("link"), label: label.slice(0, 100), link_type: type,
      target_id: target, url: $("#itemUrl").value.trim() || "#", kind: $("#itemKind").value,
      enabled: $("#itemEnabled").checked, new_tab: $("#itemNewTab").checked, children: [],
    };
    if (editingId) {
      const entry = findEntry(editingId);
      if (!entry) return;
      payload.children = entry.item.children || [];
      entry.array[entry.index] = payload;
    } else {
      if (countItems(currentMenu().items) >= 120) return notify("Mỗi menu tối đa 120 liên kết.", "error");
      currentMenu().items.push(payload);
    }
    renderTree(); renderMenuList(); resetItemEditor(); markDirty();
  }

  function actOnItem(id, action) {
    const entry = findEntry(id);
    if (!entry) return;
    if (action === "edit") return editItem(id);
    if (action === "remove") {
      if (!window.confirm(`Xóa liên kết “${entry.item.label}” và toàn bộ menu con?`)) return;
      entry.array.splice(entry.index, 1);
    } else if (action === "up" && entry.index > 0) {
      [entry.array[entry.index - 1], entry.array[entry.index]] = [entry.array[entry.index], entry.array[entry.index - 1]];
    } else if (action === "down" && entry.index < entry.array.length - 1) {
      [entry.array[entry.index + 1], entry.array[entry.index]] = [entry.array[entry.index], entry.array[entry.index + 1]];
    } else if (action === "indent") {
      if (entry.depth >= 3 || entry.index === 0) return notify("Không thể tăng cấp cho mục này.", "error");
      const previous = entry.array[entry.index - 1];
      entry.array.splice(entry.index, 1);
      previous.children = previous.children || [];
      previous.children.push(entry.item);
    } else if (action === "outdent") {
      if (!entry.parent) return notify("Mục này đã ở cấp ngoài cùng.", "error");
      const parentEntry = entry.parent;
      const parentContainer = parentEntry.array;
      entry.array.splice(entry.index, 1);
      const parentIndex = parentContainer.indexOf(parentEntry.item);
      parentContainer.splice(parentIndex + 1, 0, entry.item);
    } else return;
    renderTree(); renderMenuList(); markDirty();
  }

  function renderPlacements() {
    const options = menus.map((menu) => `<option value="${escapeHtml(menu.handle)}">${escapeHtml(menu.title)} (${escapeHtml(menu.handle)})</option>`).join("");
    [["#placementNavbar", "navbar"], ["#placementProduct", "product_mega"], ["#placementFooter1", "footer_1"], ["#placementFooter2", "footer_2"]].forEach(([selector, key]) => {
      const select = $(selector); select.innerHTML = options; select.value = placements[key] || menus[0]?.handle || "";
    });
  }

  function fillSettings() {
    const navbar = config.navbar || {};
    const footer = config.footer || {};
    $("#navBrandLabel").value = navbar.brand_label || "GUAMAISON";
    $("#navTransparentHome").checked = navbar.transparent_home !== false;
    $("#footerBrandName").value = footer.brand_name || "GUAMAISON";
    $("#footerKicker").value = footer.kicker || "";
    $("#footerDescription").value = footer.description || "";
    $("#contactTitle").value = footer.contact_title || "";
    $("#contactEmail").value = footer.contact_email || "";
    $("#contactText").value = footer.contact_text || "";
    $("#footerCopyright").value = footer.copyright || "";
    $("#newsletterEnabled").checked = footer.newsletter_enabled !== false;
    $("#socialFacebook").value = footer.socials?.facebook || "#";
    $("#socialInstagram").value = footer.socials?.instagram || "#";
    $("#socialTiktok").value = footer.socials?.tiktok || "#";
    $("#socialYoutube").value = footer.socials?.youtube || "#";
  }

  function collectPayload() {
    return {
      schema_version: 2,
      menus,
      placements,
      navbar: { brand_label: $("#navBrandLabel").value.trim() || "GUAMAISON", transparent_home: $("#navTransparentHome").checked },
      product_menu: config.product_menu || {},
      footer: {
        ...(config.footer || {}), brand_name: $("#footerBrandName").value.trim() || "GUAMAISON",
        kicker: $("#footerKicker").value.trim(), description: $("#footerDescription").value.trim(),
        contact_title: $("#contactTitle").value.trim(), contact_email: $("#contactEmail").value.trim(),
        contact_text: $("#contactText").value.trim(), copyright: $("#footerCopyright").value.trim(),
        newsletter_enabled: $("#newsletterEnabled").checked,
        socials: { ...(config.footer?.socials || {}), facebook: $("#socialFacebook").value.trim() || "#", instagram: $("#socialInstagram").value.trim() || "#", tiktok: $("#socialTiktok").value.trim() || "#", youtube: $("#socialYoutube").value.trim() || "#" },
      },
    };
  }

  async function saveAll() {
    if (saving) return;
    if (!menus.length || menus.some((menu) => !menu.title || !menu.handle)) return notify("Tên và handle menu không được để trống.", "error");
    const button = $("#saveMenusBtn");
    const original = button.innerHTML;
    saving = true; button.disabled = true; button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>Đang lưu';
    try {
      const response = await fetch(root.dataset.saveUrl, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')?.content || "", "X-Requested-With": "XMLHttpRequest" },
        body: JSON.stringify(collectPayload()),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok || !result.success) throw new Error(result.message || `Không thể lưu (HTTP ${response.status}).`);
      dirty = false;
      $("#menuSaveStatus").innerHTML = '<i class="fa-solid fa-circle-check mr-2 text-emerald-600"></i>Đã đồng bộ với storefront.';
      notify(result.message || "Đã lưu menu.");
    } catch (error) { notify(error.message || "Mất kết nối tới máy chủ.", "error"); }
    finally { saving = false; button.disabled = false; button.innerHTML = original; }
  }

  root.addEventListener("click", (event) => {
    const tab = event.target.closest("[data-tab]");
    if (tab) {
      $$('[data-tab]').forEach((item) => item.classList.toggle("is-active", item === tab));
      $$('[data-panel]').forEach((panel) => panel.classList.toggle("is-active", panel.dataset.panel === tab.dataset.tab));
      return;
    }
    const menuButton = event.target.closest("[data-menu-handle]");
    if (menuButton) { selectedHandle = menuButton.dataset.menuHandle; loadSelectedMenu(); return; }
    const action = event.target.closest("[data-item-action]");
    if (action) { actOnItem(action.closest("[data-item-id]").dataset.itemId, action.dataset.itemAction); return; }
    if (event.target.closest("#newMenuBtn")) return createMenu();
    if (event.target.closest("#deleteMenuBtn")) return deleteMenu();
    if (event.target.closest("#saveItemBtn")) return saveItem();
    if (event.target.closest("#cancelItemBtn")) return resetItemEditor();
    if (event.target.closest("#saveMenusBtn")) return saveAll();
  });
  root.addEventListener("change", (event) => {
    if (event.target.id === "itemLinkType") refreshTarget();
    else if (event.target.id === "itemTarget") syncTarget();
    else if (event.target.matches(".hm-placement")) {
      placements = { navbar: $("#placementNavbar").value, product_mega: $("#placementProduct").value, footer_1: $("#placementFooter1").value, footer_2: $("#placementFooter2").value };
      markDirty();
    } else if (!event.target.matches("#menuTitle,#menuHandle,#itemLabel,#itemUrl,#itemLinkType,#itemTarget,#itemKind,#itemEnabled,#itemNewTab")) markDirty();
  });
  $("#menuTitle").addEventListener("change", () => updateMenuIdentity("title"));
  $("#menuHandle").addEventListener("change", () => updateMenuIdentity("handle"));
  root.addEventListener("input", (event) => {
    if (!event.target.closest("#itemEditor") && !event.target.matches("#menuTitle,#menuHandle")) markDirty();
  });
  window.addEventListener("beforeunload", (event) => { if (dirty && !saving) { event.preventDefault(); event.returnValue = ""; } });

  renderMenuList(); renderPlacements(); fillSettings(); loadSelectedMenu();
})();
