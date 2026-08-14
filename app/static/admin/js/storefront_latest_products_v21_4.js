(function () {
  "use strict";

  var root = document.querySelector("[data-media-studio]");
  var manager = root && root.querySelector("[data-latest-products-manager]");
  if (!root || !manager || manager.dataset.ready === "1") return;
  manager.dataset.ready = "1";

  var MAX_ITEMS = 12;
  var catalogUrl = manager.dataset.catalogUrl || "";
  var catalogNode = manager.querySelector("[data-latest-catalog]");
  var catalogState = manager.querySelector("[data-latest-catalog-state]");
  var selectedNode = manager.querySelector("[data-latest-selected]");
  var selectedEmpty = manager.querySelector("[data-latest-selected-empty]");
  var selectedCount = manager.querySelector("[data-latest-selected-count]");
  var catalogCount = manager.querySelector("[data-latest-catalog-count]");
  var searchInput = manager.querySelector("[data-latest-search]");
  var saveButton = manager.querySelector("[data-latest-save]");
  var statusNode = manager.querySelector("[data-latest-status]");
  var enabledInput = manager.querySelector("[data-latest-enabled]");
  var eyebrowInput = manager.querySelector("[data-latest-eyebrow]");
  var titleInput = manager.querySelector("[data-latest-title]");
  var descriptionInput = manager.querySelector("[data-latest-description]");
  var products = new Map();
  var catalogItems = [];
  var selectedIds = [];
  var draggedId = "";
  var loadingSerial = 0;
  var searchTimer = 0;

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return root.dataset.csrf || (meta ? meta.content : "") || "";
  }

  function readInitial() {
    var node = manager.querySelector("[data-latest-products-data]");
    var data = {};
    try { data = JSON.parse(node ? node.textContent : "{}"); } catch (_) {}
    selectedIds = Array.isArray(data.selected_ids)
      ? data.selected_ids.map(String).filter(Boolean).slice(0, MAX_ITEMS)
      : [];
    selectedIds = selectedIds.filter(function (id, index, all) { return all.indexOf(id) === index; });
    enabledInput.checked = String(data.enabled || "true").toLowerCase() !== "false";
    eyebrowInput.value = String(data.eyebrow || "Bộ sưu tập mới · 2026");
    var initialTitle = String(data.title || "");
    titleInput.value = !initialTitle || ["latest arrivals", "sản phẩm vừa cập bến"].indexOf(initialTitle.toLowerCase()) >= 0
      ? "WHATS' HOT"
      : initialTitle;
    descriptionInput.value = String(data.description || "Những thiết kế mới được GUAMAISON tuyển chọn, sẵn sàng đồng hành cùng nhịp sống mỗi ngày.");
  }

  function setStatus(message, state) {
    statusNode.textContent = message || "";
    statusNode.className = state ? "is-" + state : "";
  }

  function notify(message, type) {
    var stack = root.querySelector("[data-media-snackbar-stack]");
    if (!stack) return;
    var snack = document.createElement("div");
    snack.className = "gm-media-snack is-" + (type || "info");
    snack.setAttribute("role", type === "error" ? "alert" : "status");
    var icon = document.createElement("i");
    icon.className = "fa-solid " + (type === "success" ? "fa-circle-check" : "fa-circle-exclamation");
    var label = document.createElement("span");
    label.textContent = message;
    snack.append(icon, label);
    stack.prepend(snack);
    window.setTimeout(function () { if (snack.isConnected) snack.remove(); }, 4500);
  }

  function remember(item) {
    if (!item || !item.id) return;
    item.id = String(item.id);
    products.set(item.id, item);
  }

  function productCard(item, selected) {
    var card = document.createElement("article");
    card.className = "gm-lp-product";
    card.dataset.productId = item.id;

    if (selected) {
      var drag = document.createElement("button");
      drag.type = "button";
      drag.className = "gm-lp-drag";
      drag.title = "Kéo để đổi vị trí";
      drag.setAttribute("aria-label", "Kéo để đổi vị trí " + item.name);
      drag.innerHTML = '<i class="fa-solid fa-grip-vertical" aria-hidden="true"></i>';
      card.appendChild(drag);
      drag.addEventListener("mousedown", function () { card.draggable = true; });
      drag.addEventListener("touchstart", function () { card.draggable = true; }, { passive: true });
    }

    var image = document.createElement("img");
    image.src = item.thumbnail_url || "/static/images/placeholder-product.png";
    image.alt = "";
    image.loading = "lazy";
    var copy = document.createElement("div");
    copy.className = "gm-lp-product__copy";
    var name = document.createElement("strong");
    name.textContent = item.name || "Sản phẩm";
    var meta = document.createElement("span");
    meta.textContent = [item.sku, item.price_label].filter(Boolean).join(" · ") || "GUAMAISON";
    copy.append(name, meta);
    card.append(image, copy);

    var action = document.createElement("button");
    action.type = "button";
    if (selected) {
      action.className = "gm-lp-remove";
      action.title = "Bỏ sản phẩm";
      action.setAttribute("aria-label", "Bỏ " + item.name);
      action.innerHTML = '<i class="fa-regular fa-trash-can" aria-hidden="true"></i>';
      action.addEventListener("click", function () {
        selectedIds = selectedIds.filter(function (id) { return id !== item.id; });
        renderAll();
      });
    } else {
      var isSelected = selectedIds.indexOf(item.id) >= 0;
      action.disabled = isSelected || selectedIds.length >= MAX_ITEMS;
      action.innerHTML = isSelected
        ? '<i class="fa-solid fa-check" aria-hidden="true"></i> Đã chọn'
        : '<i class="fa-solid fa-plus" aria-hidden="true"></i> Thêm';
      action.addEventListener("click", function () {
        if (selectedIds.length >= MAX_ITEMS || selectedIds.indexOf(item.id) >= 0) return;
        selectedIds.push(item.id);
        renderAll();
      });
    }
    card.appendChild(action);

    if (selected) bindDrag(card, item.id);
    return card;
  }

  function bindDrag(card, id) {
    card.addEventListener("dragstart", function (event) {
      draggedId = id;
      card.classList.add("is-dragging");
      if (event.dataTransfer) event.dataTransfer.setData("text/plain", id);
    });
    card.addEventListener("dragend", function () {
      draggedId = "";
      card.draggable = false;
      selectedNode.querySelectorAll(".gm-lp-product").forEach(function (node) {
        node.classList.remove("is-dragging", "is-drop-target");
      });
    });
    card.addEventListener("dragover", function (event) {
      if (!draggedId || draggedId === id) return;
      event.preventDefault();
      card.classList.add("is-drop-target");
    });
    card.addEventListener("dragleave", function () { card.classList.remove("is-drop-target"); });
    card.addEventListener("drop", function (event) {
      event.preventDefault();
      var sourceId = draggedId || (event.dataTransfer ? event.dataTransfer.getData("text/plain") : "");
      var from = selectedIds.indexOf(sourceId);
      var to = selectedIds.indexOf(id);
      if (from < 0 || to < 0 || from === to) return;
      var moved = selectedIds.splice(from, 1)[0];
      selectedIds.splice(to, 0, moved);
      draggedId = "";
      renderAll();
    });
  }

  function renderCatalog() {
    catalogNode.replaceChildren();
    catalogItems.forEach(function (item) { catalogNode.appendChild(productCard(item, false)); });
    catalogCount.textContent = String(catalogItems.length);
    catalogState.hidden = catalogItems.length > 0;
    if (!catalogItems.length) catalogState.textContent = "Không tìm thấy sản phẩm phù hợp.";
  }

  function renderSelected() {
    selectedNode.replaceChildren();
    selectedIds.forEach(function (id) {
      var item = products.get(id) || { id: id, name: "Sản phẩm " + id, thumbnail_url: "", sku: "", price_label: "" };
      selectedNode.appendChild(productCard(item, true));
    });
    selectedCount.textContent = String(selectedIds.length);
    selectedEmpty.hidden = selectedIds.length !== 0;
    selectedNode.hidden = selectedIds.length === 0;
    var tabCount = root.querySelector('[data-media-filter="latest-products"] b');
    if (tabCount) tabCount.textContent = String(selectedIds.length);
  }

  function renderAll() {
    renderCatalog();
    renderSelected();
  }

  async function loadCatalog(query, idsOnly) {
    var serial = ++loadingSerial;
    catalogState.hidden = false;
    catalogState.textContent = "Đang tải sản phẩm…";
    var url = new URL(catalogUrl, window.location.origin);
    if (idsOnly && selectedIds.length) url.searchParams.set("ids", selectedIds.join(","));
    else if (query) url.searchParams.set("q", query);
    try {
      var response = await fetch(url.toString(), { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } });
      var data = await response.json().catch(function () { return {}; });
      if (!response.ok || !data.ok || !Array.isArray(data.items)) throw new Error(data.message || "Không thể tải sản phẩm.");
      data.items.forEach(remember);
      if (!idsOnly && serial === loadingSerial) {
        catalogItems = data.items;
        renderAll();
      } else if (idsOnly) {
        renderSelected();
      }
    } catch (error) {
      if (!idsOnly && serial === loadingSerial) {
        catalogItems = [];
        renderAll();
        catalogState.hidden = false;
        catalogState.textContent = error.message || "Không thể tải sản phẩm.";
      }
    }
  }

  async function save() {
    var eyebrow = eyebrowInput.value.trim();
    var title = titleInput.value.trim();
    var description = descriptionInput.value.trim();
    if (!eyebrow || !title) {
      setStatus("Dòng giới thiệu và tiêu đề không được để trống.", "error");
      (!eyebrow ? eyebrowInput : titleInput).focus();
      return;
    }
    saveButton.disabled = true;
    setStatus("Đang lưu cấu hình sản phẩm mới…", "saving");
    try {
      var response = await fetch(root.dataset.saveUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken(), "X-Requested-With": "XMLHttpRequest" },
        body: JSON.stringify({ changes: {
          latest_arrivals_enabled: enabledInput.checked ? "true" : "false",
          latest_arrivals_eyebrow: eyebrow,
          latest_arrivals_title: title,
          latest_arrivals_description: description,
          latest_arrivals_product_ids: selectedIds
        } })
      });
      var data = await response.json().catch(function () { return {}; });
      if (!response.ok || !data.ok) throw new Error(data.message || "Không thể lưu cấu hình.");
      setStatus("Đã lưu. Trang chủ sẽ dùng đúng sản phẩm và thứ tự đã chọn.", "success");
      notify("Đã cập nhật khu vực WHATS' HOT.", "success");
    } catch (error) {
      setStatus(error.message || "Không thể lưu cấu hình.", "error");
      notify(error.message || "Không thể lưu cấu hình.", "error");
    } finally {
      saveButton.disabled = false;
    }
  }

  function syncFilter() {
    var active = root.querySelector("[data-media-filter].is-active");
    var group = active ? active.dataset.mediaFilter : "home";
    manager.hidden = group !== "latest-products" && group !== "all";
  }

  searchInput.addEventListener("input", function () {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(function () { loadCatalog(searchInput.value.trim(), false); }, 260);
  });
  saveButton.addEventListener("click", save);
  root.querySelectorAll("[data-media-filter]").forEach(function (button) {
    button.addEventListener("click", function () { window.setTimeout(syncFilter, 0); });
  });

  readInitial();
  renderAll();
  syncFilter();
  if (selectedIds.length) loadCatalog("", true);
  loadCatalog("", false);
})();
