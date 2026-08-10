(function () {
  "use strict";

  const money = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });

  function boot() {
    const root = document.querySelector("[data-cart-v10]");
    if (!root || root.dataset.ready === "true") return;
    root.dataset.ready = "true";
    document.documentElement.classList.add("gua-cart-page");
    document.body.classList.add("gua-cart-page");
    document.querySelectorAll('[data-cart-portal="v10.1"]').forEach((layer) => {
      if (!root.contains(layer)) layer.remove();
    });

    const csrf = root.dataset.csrfToken || "";
    const totalLines = Number(root.dataset.totalLines || 0);
    const storageKey = `gua-cart-selection-v10:${root.dataset.userId || "guest"}`;
    const cards = () => Array.from(root.querySelectorAll("[data-cart-item]"));
    const toast = root.querySelector("[data-cart-toast]");
    const pageToggle = root.querySelector("[data-select-page]");
    const allToggle = root.querySelector("[data-select-all-cart]");
    const deleteButton = root.querySelector("[data-open-delete]");
    const selectedLabel = root.querySelector("[data-selected-label]");
    const checkoutButtons = Array.from(root.querySelectorAll("[data-checkout]"));

    let state = loadState();
    let summaryAbort = null;
    let summaryTimer = 0;
    let toastTimer = 0;
    let lastFocus = null;
    let pendingDelete = null;
    let activeCard = null;
    let selectedVariantId = "";
    let variantState = null;

    if (toast) {
      toast.classList.add("gua-cart-layer");
      toast.dataset.cartPortal = "v10.1";
    }
    if (toast && toast.parentElement !== document.body) document.body.appendChild(toast);

    function loadState() {
      try {
        const value = JSON.parse(sessionStorage.getItem(storageKey) || "null");
        if (!value || (value.mode !== "all" && value.mode !== "explicit")) throw new Error("invalid");
        return {
          mode: value.mode,
          itemIds: new Set(Array.isArray(value.itemIds) ? value.itemIds : []),
          excludedIds: new Set(Array.isArray(value.excludedIds) ? value.excludedIds : []),
        };
      } catch (_) {
        return { mode: "explicit", itemIds: new Set(), excludedIds: new Set() };
      }
    }

    function saveState() {
      try {
        sessionStorage.setItem(storageKey, JSON.stringify({
          mode: state.mode,
          itemIds: Array.from(state.itemIds),
          excludedIds: Array.from(state.excludedIds),
        }));
      } catch (_) {}
    }

    function resetState() {
      state = { mode: "explicit", itemIds: new Set(), excludedIds: new Set() };
      saveState();
    }

    function payload(source) {
      const value = source || state;
      return {
        mode: value.mode,
        item_ids: Array.from(value.itemIds || []),
        excluded_ids: Array.from(value.excludedIds || []),
      };
    }

    function isSelected(itemId) {
      return state.mode === "all" ? !state.excludedIds.has(itemId) : state.itemIds.has(itemId);
    }

    function selectedCount() {
      return state.mode === "all"
        ? Math.max(0, totalLines - state.excludedIds.size)
        : state.itemIds.size;
    }

    function showToast(message, type) {
      if (!toast) return;
      window.clearTimeout(toastTimer);
      toast.textContent = message;
      toast.classList.toggle("is-error", type === "error");
      toast.hidden = false;
      toastTimer = window.setTimeout(() => { toast.hidden = true; }, 3200);

      if (typeof window.showToast === "function") {
        try { window.showToast(message, type === "error" ? "error" : "success"); } catch (_) {}
      }
    }

    function setBusy(card, busy) {
      if (!card) return;
      const overlay = card.querySelector("[data-item-busy]");
      if (overlay) overlay.hidden = !busy;
      card.setAttribute("aria-busy", busy ? "true" : "false");
    }

    async function requestJson(url, options) {
      const response = await fetch(url, Object.assign({
        credentials: "same-origin",
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrf,
        },
      }, options || {}));

      const type = response.headers.get("content-type") || "";
      if (response.redirected && !type.includes("application/json")) {
        window.location.href = response.url;
        throw new Error("redirected");
      }
      const data = type.includes("application/json") ? await response.json() : {};
      if (!response.ok || data.success === false) {
        throw new Error(data.message || data.error || "Thao tác chưa thành công.");
      }
      return data;
    }

    function updateSelectionUI(fetchSummary) {
      const visible = cards();
      let checkedOnPage = 0;
      visible.forEach((card) => {
        const itemId = card.dataset.itemId;
        const checkbox = card.querySelector("[data-item-select]");
        const checked = isSelected(itemId);
        if (checkbox) checkbox.checked = checked;
        card.classList.toggle("is-selected", checked);
        if (checked) checkedOnPage += 1;
      });

      if (pageToggle) {
        pageToggle.checked = visible.length > 0 && checkedOnPage === visible.length;
        pageToggle.indeterminate = checkedOnPage > 0 && checkedOnPage < visible.length;
      }
      if (allToggle) {
        allToggle.classList.toggle("is-active", state.mode === "all");
        allToggle.textContent = state.mode === "all"
          ? "Bỏ chọn toàn bộ giỏ"
          : `Chọn toàn bộ ${money.format(totalLines)} sản phẩm`;
      }

      const count = selectedCount();
      if (selectedLabel) selectedLabel.textContent = count ? `Đã chọn ${money.format(count)}` : "Chưa chọn sản phẩm";
      if (deleteButton) deleteButton.disabled = count === 0;
      checkoutButtons.forEach((button) => { button.disabled = count === 0; });
      saveState();

      if (fetchSummary !== false) scheduleSummary();
    }

    function writeSummary(summary) {
      const lines = Number(summary.line_count || 0);
      const quantity = Number(summary.quantity || 0);
      const total = Number(summary.total || 0);
      root.querySelectorAll("[data-summary-lines]").forEach((el) => { el.textContent = money.format(lines); });
      root.querySelectorAll("[data-summary-quantity]").forEach((el) => { el.textContent = money.format(quantity); });
      root.querySelectorAll("[data-summary-total], [data-mobile-total]").forEach((el) => { el.textContent = `${money.format(total)} ₫`; });
      root.querySelectorAll("[data-mobile-count]").forEach((el) => { el.textContent = `${money.format(lines)} sản phẩm`; });
      const hint = root.querySelector("[data-summary-hint]");
      if (hint) hint.textContent = lines ? "Phí vận chuyển được tính ở bước thanh toán." : "Chọn ít nhất một sản phẩm để tiếp tục.";
      checkoutButtons.forEach((button) => { button.disabled = lines === 0; });
      if (lines === 0 && selectedCount() > 0) {
        resetState();
        updateSelectionUI(false);
      }
    }

    function scheduleSummary() {
      window.clearTimeout(summaryTimer);
      const count = selectedCount();
      if (!count) {
        if (summaryAbort) summaryAbort.abort();
        writeSummary({ line_count: 0, quantity: 0, total: 0 });
        return;
      }
      summaryTimer = window.setTimeout(refreshSummary, 120);
    }

    async function refreshSummary() {
      if (summaryAbort) summaryAbort.abort();
      summaryAbort = new AbortController();
      try {
        const data = await requestJson(root.dataset.summaryUrl, {
          method: "POST",
          body: JSON.stringify(payload()),
          signal: summaryAbort.signal,
        });
        writeSummary(data);
      } catch (error) {
        if (error.name !== "AbortError" && error.message !== "redirected") showToast(error.message, "error");
      }
    }

    function changeOne(itemId, checked) {
      if (state.mode === "all") {
        if (checked) state.excludedIds.delete(itemId);
        else state.excludedIds.add(itemId);
      } else if (checked) state.itemIds.add(itemId);
      else state.itemIds.delete(itemId);
      updateSelectionUI();
    }

    root.addEventListener("change", (event) => {
      const checkbox = event.target.closest("[data-item-select]");
      if (checkbox) {
        const card = checkbox.closest("[data-cart-item]");
        if (card) changeOne(card.dataset.itemId, checkbox.checked);
        return;
      }
      if (event.target.matches("[data-select-page]")) {
        cards().forEach((card) => {
          const itemId = card.dataset.itemId;
          if (state.mode === "all") {
            if (event.target.checked) state.excludedIds.delete(itemId);
            else state.excludedIds.add(itemId);
          } else if (event.target.checked) state.itemIds.add(itemId);
          else state.itemIds.delete(itemId);
        });
        updateSelectionUI();
      }
    });

    if (allToggle) allToggle.addEventListener("click", () => {
      if (state.mode === "all") resetState();
      else state = { mode: "all", itemIds: new Set(), excludedIds: new Set() };
      updateSelectionUI();
    });

    root.addEventListener("click", (event) => {
      const deltaButton = event.target.closest("[data-qty-delta]");
      if (deltaButton) {
        const card = deltaButton.closest("[data-cart-item]");
        const input = card && card.querySelector("[data-quantity]");
        if (!card || !input) return;
        const next = Number(input.value || 1) + Number(deltaButton.dataset.qtyDelta || 0);
        changeQuantity(card, Math.max(1, Math.min(Number(input.max || 999), next)));
        return;
      }

      const edit = event.target.closest("[data-edit-variant]");
      if (edit) {
        const card = edit.closest("[data-cart-item]");
        if (card) openVariantSheet(card, edit);
        return;
      }

      const remove = event.target.closest("[data-remove-one]");
      if (remove) {
        const card = remove.closest("[data-cart-item]");
        if (card) openDeleteDialog({ mode: "explicit", itemIds: new Set([card.dataset.itemId]), excludedIds: new Set() }, remove, true);
      }
    });

    root.querySelectorAll("[data-quantity]").forEach((input) => {
      let timer = 0;
      input.addEventListener("change", () => {
        window.clearTimeout(timer);
        const card = input.closest("[data-cart-item]");
        timer = window.setTimeout(() => changeQuantity(card, Number(input.value || 1)), 180);
      });
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          input.blur();
        }
      });
    });

    async function changeQuantity(card, requested) {
      if (!card) return;
      const input = card.querySelector("[data-quantity]");
      const max = Math.max(1, Number(input.max || 1));
      const quantity = Math.max(1, Math.min(max, Math.round(Number(requested || 1))));
      input.value = String(quantity);
      setBusy(card, true);
      try {
        const data = await requestJson(card.dataset.updateUrl, {
          method: "POST",
          body: JSON.stringify({ quantity }),
        });
        const actual = Number((data.item && data.item.quantity) || quantity);
        input.value = String(actual);
        card.dataset.currentQuantity = String(actual);
        const lineTotal = card.querySelector("[data-line-total]");
        if (lineTotal) lineTotal.textContent = `${money.format(Number(card.dataset.unitPrice || 0) * actual)} ₫`;
        showToast(data.message || "Đã cập nhật số lượng.");
        if (isSelected(card.dataset.itemId)) refreshSummary();
      } catch (error) {
        input.value = card.dataset.currentQuantity || "1";
        if (error.message !== "redirected") showToast(error.message, "error");
      } finally {
        setBusy(card, false);
      }
    }

    const deleteDialog = root.querySelector("[data-delete-dialog]");
    const deleteCopy = root.querySelector("[data-delete-copy]");
    if (deleteDialog) {
      deleteDialog.classList.add("gua-cart-layer");
      deleteDialog.dataset.cartPortal = "v10.1";
    }
    if (deleteDialog && deleteDialog.parentElement !== document.body) document.body.appendChild(deleteDialog);

    function openDeleteDialog(deleteState, trigger, single) {
      if (!deleteDialog) return;
      pendingDelete = deleteState || state;
      lastFocus = trigger || document.activeElement;
      const count = pendingDelete.mode === "all"
        ? Math.max(0, totalLines - pendingDelete.excludedIds.size)
        : pendingDelete.itemIds.size;
      if (deleteCopy) deleteCopy.textContent = single
        ? "Sản phẩm này sẽ được xóa khỏi giỏ hàng của bạn."
        : `${money.format(count)} sản phẩm đã chọn sẽ được xóa khỏi giỏ hàng.`;
      deleteDialog.hidden = false;
      document.body.classList.add("gua-cart-modal-open");
      deleteDialog.querySelector("section").focus();
    }

    function closeDeleteDialog() {
      if (!deleteDialog) return;
      deleteDialog.hidden = true;
      pendingDelete = null;
      document.body.classList.remove("gua-cart-modal-open");
      if (lastFocus && lastFocus.isConnected) lastFocus.focus();
    }

    if (deleteButton) deleteButton.addEventListener("click", () => openDeleteDialog(state, deleteButton, false));
    if (deleteDialog) {
      deleteDialog.querySelectorAll("[data-cancel-delete]").forEach((button) => button.addEventListener("click", closeDeleteDialog));
      deleteDialog.querySelector("[data-confirm-delete]").addEventListener("click", async (event) => {
        if (!pendingDelete) return;
        const button = event.currentTarget;
        button.disabled = true;
        try {
          const data = await requestJson(root.dataset.bulkRemoveUrl, {
            method: "POST",
            body: JSON.stringify(payload(pendingDelete)),
          });
          resetState();
          showToast(data.message || "Đã xóa sản phẩm.");
          window.setTimeout(() => window.location.reload(), 420);
        } catch (error) {
          if (error.message !== "redirected") showToast(error.message, "error");
          button.disabled = false;
          closeDeleteDialog();
        }
      });
    }

    const sheet = root.querySelector("[data-variant-sheet]");
    const sheetPanel = sheet && sheet.querySelector(".gua-sheet__panel");
    const sheetStatus = sheet && sheet.querySelector("[data-sheet-status]");
    const sheetPicker = sheet && sheet.querySelector("[data-variant-picker]");
    const colorOptions = sheet && sheet.querySelector("[data-color-options]");
    const sizeOptions = sheet && sheet.querySelector("[data-size-options]");
    const saveVariant = sheet && sheet.querySelector("[data-save-variant]");
    if (sheet) {
      sheet.classList.add("gua-cart-layer");
      sheet.dataset.cartPortal = "v10.1";
    }
    if (sheet && sheet.parentElement !== document.body) document.body.appendChild(sheet);

    function cleanVariantText(value, fallback) {
      const text = String(value == null ? "" : value).trim();
      return text && !["none", "null", "undefined", "nan"].includes(text.toLowerCase())
        ? text
        : fallback;
    }

    function colorKey(variant) {
      return cleanVariantText(variant && variant.color_name, "Mặc định").toLocaleLowerCase("vi-VN");
    }

    function sizeKey(variant) {
      return cleanVariantText(variant && variant.size, "Free").toLocaleLowerCase("vi-VN");
    }

    function findVariant(color, size) {
      if (!variantState) return null;
      return variantState.variants.find((variant) => colorKey(variant) === color && sizeKey(variant) === size) || null;
    }

    function updateVariantSelection() {
      if (!variantState) return;
      const chosen = findVariant(variantState.color, variantState.size);
      selectedVariantId = chosen ? String(chosen.id || "") : "";

      colorOptions.querySelectorAll("[data-color-key]").forEach((button) => {
        const selected = button.dataset.colorKey === variantState.color;
        button.classList.toggle("is-selected", selected);
        button.setAttribute("aria-pressed", selected ? "true" : "false");
      });
      sizeOptions.querySelectorAll("[data-size-key]").forEach((button) => {
        const selected = button.dataset.sizeKey === variantState.size;
        button.classList.toggle("is-selected", selected);
        button.setAttribute("aria-pressed", selected ? "true" : "false");
      });

      const selectedLabel = sheet.querySelector("[data-selected-variant]");
      const selectedStock = sheet.querySelector("[data-selected-stock]");
      if (chosen) {
        const colorName = cleanVariantText(chosen.color_name, "Màu tiêu chuẩn");
        const sizeName = cleanVariantText(chosen.size, "Free");
        selectedLabel.textContent = `${colorName} · Size ${sizeName}`;
        selectedStock.textContent = Number(chosen.stock || 0) > 0
          ? `Còn ${money.format(Number(chosen.stock || 0))} sản phẩm`
          : "Phân loại này đã hết hàng";
      } else {
        selectedLabel.textContent = "Vui lòng chọn màu và size";
        selectedStock.textContent = "";
      }

      saveVariant.disabled = !chosen
        || Number(chosen.stock || 0) <= 0
        || selectedVariantId === variantState.currentId;
    }

    function renderSizes(preferredSize) {
      sizeOptions.replaceChildren();
      const variantsForColor = variantState.variants.filter((variant) => colorKey(variant) === variantState.color);
      const sizes = new Map();
      variantsForColor.forEach((variant) => {
        const key = sizeKey(variant);
        if (!sizes.has(key) || Number(variant.stock || 0) > Number(sizes.get(key).stock || 0)) sizes.set(key, variant);
      });

      const preferred = cleanVariantText(preferredSize, "").toLocaleLowerCase("vi-VN");
      const currentChoice = sizes.get(preferred);
      const firstAvailable = Array.from(sizes.values()).find((variant) => Number(variant.stock || 0) > 0);
      variantState.size = currentChoice && (
        Number(currentChoice.stock || 0) > 0
        || String(currentChoice.id || "") === variantState.currentId
      )
        ? preferred
        : (firstAvailable ? sizeKey(firstAvailable) : "");

      sizes.forEach((variant, key) => {
        const button = document.createElement("button");
        const available = Number(variant.stock || 0) > 0;
        button.type = "button";
        button.className = "gua-size-option";
        button.dataset.sizeKey = key;
        button.disabled = !available;
        button.setAttribute("aria-pressed", "false");

        const label = document.createElement("strong");
        label.textContent = cleanVariantText(variant.size, "Free");
        const stock = document.createElement("small");
        stock.textContent = available ? `Còn ${money.format(Number(variant.stock || 0))}` : "Hết hàng";
        button.append(label, stock);
        button.addEventListener("click", () => {
          variantState.size = key;
          updateVariantSelection();
        });
        sizeOptions.appendChild(button);
      });
      updateVariantSelection();
    }

    async function openVariantSheet(card, trigger) {
      if (!sheet) return;
      activeCard = card;
      selectedVariantId = "";
      variantState = null;
      lastFocus = trigger || document.activeElement;
      sheet.hidden = false;
      document.body.classList.add("gua-cart-modal-open");
      sheetStatus.hidden = false;
      sheetStatus.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang tải các phân loại còn hàng…';
      sheetPicker.hidden = true;
      colorOptions.replaceChildren();
      sizeOptions.replaceChildren();
      saveVariant.disabled = true;
      sheetPanel.focus();

      try {
        const data = await requestJson(card.dataset.variantsUrl);
        renderVariantEditor(data);
      } catch (error) {
        sheetStatus.textContent = error.message === "redirected" ? "Đang chuyển trang…" : error.message;
      }
    }

    function renderVariantEditor(data) {
      const item = data.item || {};
      const product = data.product || item.products || {};
      const current = data.current_variant || item.product_variants || {};
      const variants = Array.isArray(data.variants)
        ? data.variants.filter((variant) => variant && variant.id)
        : [];
      const currentId = String(data.current_variant_id || item.variant_id || current.id || "");
      const currentFromList = variants.find((variant) => String(variant.id) === currentId) || current;
      const productBox = sheet.querySelector("[data-sheet-product]");
      productBox.hidden = false;
      const image = sheet.querySelector("[data-sheet-image]");
      image.src = product.thumbnail_url || "";
      image.alt = product.name || "";
      sheet.querySelector("[data-sheet-name]").textContent = product.name || "Sản phẩm";
      sheet.querySelector("[data-sheet-current]").textContent = `Đang chọn: ${cleanVariantText(currentFromList.color_name, "Màu tiêu chuẩn")} · Size ${cleanVariantText(currentFromList.size, "Free")}`;

      if (!variants.length) {
        sheetStatus.textContent = "Sản phẩm này chưa có phân loại để thay đổi.";
        sheetPicker.hidden = true;
        return;
      }

      variantState = {
        variants,
        currentId,
        color: colorKey(currentFromList),
        size: sizeKey(currentFromList),
      };

      const colors = new Map();
      variants.forEach((variant) => {
        const key = colorKey(variant);
        if (!colors.has(key)) colors.set(key, variant);
      });
      const onlyDefaultColor = colors.size === 1
        && Array.from(colors.keys())[0] === "mặc định";
      const colorHelp = sheet.querySelector("[data-color-help]");
      colorHelp.textContent = onlyDefaultColor
        ? "Sản phẩm này có một màu tiêu chuẩn."
        : "Chọn màu bạn muốn.";

      colors.forEach((variant, key) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "gua-color-option";
        button.dataset.colorKey = key;
        button.setAttribute("aria-pressed", "false");
        button.style.setProperty("--variant-color", variant.color_hex || "#ded7ce");

        const swatch = document.createElement("i");
        swatch.setAttribute("aria-hidden", "true");
        const title = document.createElement("span");
        title.textContent = onlyDefaultColor ? "Màu tiêu chuẩn" : cleanVariantText(variant.color_name, "Màu tiêu chuẩn");
        button.append(swatch, title);
        button.addEventListener("click", () => {
          const previousSize = variantState.size;
          variantState.color = key;
          renderSizes(previousSize);
        });
        colorOptions.appendChild(button);
      });

      sheetStatus.hidden = true;
      sheetPicker.hidden = false;
      renderSizes(variantState.size);
    }

    function closeSheet() {
      if (!sheet) return;
      sheet.hidden = true;
      activeCard = null;
      selectedVariantId = "";
      variantState = null;
      document.body.classList.remove("gua-cart-modal-open");
      if (lastFocus && lastFocus.isConnected) lastFocus.focus();
    }

    if (sheet) {
      sheet.querySelectorAll("[data-close-sheet]").forEach((button) => button.addEventListener("click", closeSheet));
      saveVariant.addEventListener("click", async () => {
        if (!activeCard || !selectedVariantId) return;
        saveVariant.disabled = true;
        const label = saveVariant.querySelector("span");
        const previous = label.textContent;
        label.textContent = "Đang lưu…";
        try {
          const data = await requestJson(activeCard.dataset.changeVariantUrl, {
            method: "POST",
            body: JSON.stringify({
              target_variant_id: selectedVariantId,
              variant_id: selectedVariantId,
            }),
          });
          showToast(data.message || "Đã cập nhật phân loại.");
          closeSheet();
          window.setTimeout(() => window.location.reload(), 420);
        } catch (error) {
          if (error.message !== "redirected") showToast(error.message, "error");
          saveVariant.disabled = false;
          label.textContent = previous;
        }
      });
    }

    checkoutButtons.forEach((button) => button.addEventListener("click", async () => {
      if (!selectedCount()) return;
      checkoutButtons.forEach((item) => { item.disabled = true; item.setAttribute("aria-busy", "true"); });
      try {
        const data = await requestJson(root.dataset.prepareCheckoutUrl, {
          method: "POST",
          body: JSON.stringify(payload()),
        });
        if (!data.redirect) throw new Error("Không tìm thấy trang thanh toán.");
        window.location.href = data.redirect;
      } catch (error) {
        checkoutButtons.forEach((item) => { item.disabled = false; item.removeAttribute("aria-busy"); });
        if (error.message !== "redirected") showToast(error.message, "error");
      }
    }));

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (sheet && !sheet.hidden) closeSheet();
      else if (deleteDialog && !deleteDialog.hidden) closeDeleteDialog();
    });

    updateSelectionUI();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
  window.addEventListener("pageshow", boot);
})();
