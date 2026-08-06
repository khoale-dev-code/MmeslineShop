(function () {
  "use strict";

  const VND = new Intl.NumberFormat("vi-VN");

  const SELECTOR = {
    root: "#mmVariantsLite",
    list: "#variantList",
    template: "#mvlRowTemplate",
    initial: "#mvlInitialVariants",
    empty: "#mvlEmpty",
    count: "#mvlCount",
    stock: "#mvlStock",
    colors: "#mvlColors",
    sizePanel: "#mvlSizePanel",
    bulkColor: "#mvlBulkColor",
    bulkHex: "#mvlBulkHex",
    bulkPicker: "#mvlBulkPicker",
    bulkSizes: "#mvlBulkSizes",
    bulkStock: "#mvlBulkStock",
    form: "#productForm"
  };

  const FIELD_DEFAULTS = {
    color_name: "Mặc định",
    color_hex: "#3b2414",
    size: "Freesize",
    stock: 0,
    price_override: "",
    cost_price: "",
    sku: "",
    barcode: "",
    compare_at_price: ""
  };

  const COLOR_MAP = {
    "mặc định": "#3b2414",
    "nâu espresso": "#3b2414",
    "nâu mocha": "#8b5e3c",
    "be kem": "#e8d8c3",
    "trắng": "#ffffff",
    "đen": "#111111",
    "xám": "#8a8a8a",
    "xanh navy": "#1f2a44",
    "đỏ rượu": "#6f1d1b"
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const digits = (value) => String(value || "").replace(/[^\d]/g, "");
  const formatMoney = (value) => digits(value) ? VND.format(Number(digits(value))) : "";

  let state = [];

  function uid() {
    return "v_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 8);
  }

  function normalizeHex(value) {
    let hex = String(value || "").trim();

    if (!hex) return "#3b2414";
    if (!hex.startsWith("#")) hex = "#" + hex;

    if (/^#[0-9a-fA-F]{3}$/.test(hex)) {
      hex = "#" + hex.slice(1).split("").map((x) => x + x).join("");
    }

    if (!/^#[0-9a-fA-F]{6}$/.test(hex)) return "#3b2414";

    return hex.toLowerCase();
  }

  function colorHexByName(name) {
    return COLOR_MAP[String(name || "").trim().toLowerCase()] || null;
  }

  function randomDigits(length) {
    let output = "";

    if (window.crypto && window.crypto.getRandomValues) {
      const arr = new Uint8Array(length);
      window.crypto.getRandomValues(arr);
      arr.forEach((n) => output += String(n % 10));
      return output;
    }

    for (let i = 0; i < length; i += 1) {
      output += Math.floor(Math.random() * 10);
    }

    return output;
  }

  function makeBarcode() {
    return "290" + randomDigits(10);
  }

  function parseSizes(value) {
    return String(value || "")
      .split(/[,;\n|]+/)
      .map((item) => item.trim())
      .filter(Boolean)
      .filter((item, index, arr) => arr.findIndex((x) => x.toLowerCase() === item.toLowerCase()) === index);
  }

  function normalizeVariant(raw) {
    const colorName = raw.color_name || raw.color || FIELD_DEFAULTS.color_name;
    const presetHex = colorHexByName(colorName);

    return {
      id: raw.id || uid(),
      color_name: colorName,
      color_hex: normalizeHex(raw.color_hex || presetHex || FIELD_DEFAULTS.color_hex),
      size: raw.size || FIELD_DEFAULTS.size,
      stock: Number(raw.stock || 0),
      price_override: raw.price_override || "",
      cost_price: raw.cost_price || "",
      sku: raw.sku || "",
      barcode: raw.barcode || "",
      compare_at_price: raw.compare_at_price || "",
      open: Boolean(raw.open)
    };
  }

  function readInitialVariants() {
    const el = $(SELECTOR.initial);

    if (!el) return [];

    try {
      const rows = JSON.parse(el.textContent || "[]");
      return Array.isArray(rows) ? rows : [];
    } catch {
      return [];
    }
  }

  function getVariantById(id) {
    return state.find((item) => item.id === id);
  }

  function render() {
    const list = $(SELECTOR.list);
    const template = $(SELECTOR.template);

    if (!list || !template) return;

    list.innerHTML = "";

    state.forEach((variant) => {
      const node = template.content.firstElementChild.cloneNode(true);
      node.dataset.variantId = variant.id;

      if (variant.open) node.classList.add("is-open");

      bindRowValues(node, variant);
      list.appendChild(node);
    });

    updateSummary();
  }

  function bindRowValues(row, variant) {
    setInput(row, "color_name", variant.color_name);
    setInput(row, "color_hex", variant.color_hex);
    setInput(row, "color_picker", variant.color_hex);
    setInput(row, "size", variant.size);
    setInput(row, "stock", variant.stock);
    setInput(row, "price_override", formatMoney(variant.price_override));
    setInput(row, "cost_price", formatMoney(variant.cost_price));
    setInput(row, "sku", variant.sku);
    setInput(row, "barcode", variant.barcode);
    setInput(row, "compare_at_price", variant.compare_at_price);

    updateRowHeader(row, variant);
  }

  function setInput(row, field, value) {
    const input = row.querySelector(`[data-field="${field}"]`);
    if (input) input.value = value == null ? "" : String(value);
  }

  function updateRowHeader(row, variant) {
    const dot = $(".mvl-dot", row);
    const title = $(".mvl-title-text", row);
    const subtitle = $(".mvl-subtitle", row);
    const detailBtn = $('[data-mvl-action="toggle-detail"]', row);
    const detailIcon = detailBtn ? $("i", detailBtn) : null;

    const hasAdvanced = Boolean(
      String(variant.cost_price || "").trim() ||
      String(variant.sku || "").trim() ||
      String(variant.barcode || "").trim()
    );

    if (dot) dot.style.background = variant.color_hex;
    if (title) title.textContent = `${variant.color_name || "Mặc định"} / ${variant.size || "Freesize"}`;
    if (subtitle) subtitle.textContent = `Tồn: ${Number(variant.stock || 0)} · ${hasAdvanced ? "Có chi tiết nâng cao" : "Gọn"}`;

    if (detailBtn) detailBtn.setAttribute("aria-expanded", variant.open ? "true" : "false");
    if (detailIcon) detailIcon.className = variant.open ? "fa-solid fa-chevron-up" : "fa-solid fa-sliders";
  }

  function updateSummary() {
    const colors = new Set();
    const totalStock = state.reduce((sum, item) => {
      if (item.color_name) colors.add(item.color_name.trim().toLowerCase());
      return sum + Number(item.stock || 0);
    }, 0);

    setText(SELECTOR.count, state.length);
    setText(SELECTOR.stock, totalStock);
    setText(SELECTOR.colors, colors.size);

    const empty = $(SELECTOR.empty);
    if (empty) empty.classList.toggle("hidden", state.length > 0);
  }

  function setText(selector, value) {
    const el = $(selector);
    if (el) el.textContent = String(value);
  }

  function addVariant(data = {}) {
    state.push(normalizeVariant({ ...FIELD_DEFAULTS, ...data }));
    render();
  }

  function duplicateVariant(id) {
    const item = getVariantById(id);
    if (!item) return;

    const clone = {
      ...item,
      id: uid(),
      sku: "",
      barcode: "",
      open: false
    };

    state.push(clone);
    render();
  }

  function removeVariant(id) {
    state = state.filter((item) => item.id !== id);
    render();
  }

  function toggleDetail(id) {
    const item = getVariantById(id);
    if (!item) return;

    item.open = !item.open;

    const row = getRow(id);
    if (row) {
      row.classList.toggle("is-open", item.open);
      updateRowHeader(row, item);
    }
  }

  function getRow(id) {
    return $(`[data-variant-id="${id}"]`);
  }

  function updateVariantField(row, input) {
    const id = row.dataset.variantId;
    const item = getVariantById(id);
    if (!item) return;

    const field = input.dataset.field;
    if (!field) return;

    if (field === "color_picker") {
      item.color_hex = normalizeHex(input.value);
      setInput(row, "color_hex", item.color_hex);
      input.value = item.color_hex;
    } else if (field === "color_hex") {
      item.color_hex = normalizeHex(input.value);
      setInput(row, "color_hex", item.color_hex);
      setInput(row, "color_picker", item.color_hex);
    } else if (field === "color_name") {
      item.color_name = input.value;

      const presetHex = colorHexByName(input.value);
      if (presetHex) {
        item.color_hex = presetHex;
        setInput(row, "color_hex", presetHex);
        setInput(row, "color_picker", presetHex);
      }
    } else if (field === "stock") {
      item.stock = Number(input.value || 0);
    } else if (field === "price_override" || field === "cost_price") {
      item[field] = digits(input.value);
      input.value = formatMoney(input.value);
    } else {
      item[field] = input.value;
    }

    updateRowHeader(row, item);
    updateSummary();
  }

  function saveCustomColor(row) {
    const item = getVariantById(row.dataset.variantId);
    if (!item) return;

    const name = String(item.color_name || "").trim();
    if (!name) return;

    COLOR_MAP[name.toLowerCase()] = normalizeHex(item.color_hex);
  }

  function addBulkSizes() {
    const colorName = $(SELECTOR.bulkColor)?.value || "Mặc định";
    const hex = normalizeHex($(SELECTOR.bulkHex)?.value || colorHexByName(colorName) || "#3b2414");
    const sizes = parseSizes($(SELECTOR.bulkSizes)?.value || "");
    const stock = Number($(SELECTOR.bulkStock)?.value || 0);

    const finalSizes = sizes.length ? sizes : ["Freesize"];

    finalSizes.forEach((size) => {
      state.push(normalizeVariant({
        color_name: colorName,
        color_hex: hex,
        size: size,
        stock: stock
      }));
    });

    render();
  }

  function toggleSizePanel() {
    const panel = $(SELECTOR.sizePanel);
    if (!panel) return;

    panel.classList.toggle("is-open");
  }

  function syncBulkColor(source) {
    const colorInput = $(SELECTOR.bulkColor);
    const hexInput = $(SELECTOR.bulkHex);
    const picker = $(SELECTOR.bulkPicker);

    if (!colorInput || !hexInput || !picker) return;

    if (source === "name") {
      const presetHex = colorHexByName(colorInput.value);
      if (presetHex) {
        hexInput.value = presetHex;
        picker.value = presetHex;
      }
    }

    if (source === "hex") {
      const hex = normalizeHex(hexInput.value);
      hexInput.value = hex;
      picker.value = hex;
    }

    if (source === "picker") {
      const hex = normalizeHex(picker.value);
      hexInput.value = hex;
      picker.value = hex;
    }
  }

  function normalizeBeforeSubmit() {
    const rows = $$(".mvl-row", $(SELECTOR.list));

    rows.forEach((row) => {
      const id = row.dataset.variantId;
      const item = getVariantById(id);
      if (!item) return;

      if (!item.barcode) {
        item.barcode = makeBarcode();
      }

      bindRowValues(row, item);

      const price = $('[data-field="price_override"]', row);
      const cost = $('[data-field="cost_price"]', row);
      const hex = $('[data-field="color_hex"]', row);
      const barcode = $('[data-field="barcode"]', row);

      if (price) price.value = digits(price.value);
      if (cost) cost.value = digits(cost.value);
      if (hex) hex.value = normalizeHex(hex.value);
      if (barcode && !barcode.value.trim()) barcode.value = item.barcode;
    });
  }

  function bindEvents() {
    const root = $(SELECTOR.root);
    if (!root) return;

    root.addEventListener("click", (event) => {
      const actionButton = event.target.closest("[data-mvl-action]");
      if (!actionButton) return;

      const action = actionButton.dataset.mvlAction;
      const row = actionButton.closest(".mvl-row");
      const id = row ? row.dataset.variantId : null;

      if (action === "add-row") addVariant();
      if (action === "add-bulk-sizes") addBulkSizes();
      if (action === "toggle-size-panel") toggleSizePanel();
      if (action === "toggle-detail" && id) toggleDetail(id);
      if (action === "duplicate-row" && id) duplicateVariant(id);
      if (action === "remove-row" && id) removeVariant(id);
    });

    root.addEventListener("click", (event) => {
      const preset = event.target.closest("[data-mvl-size-preset]");
      if (!preset) return;

      const input = $(SELECTOR.bulkSizes);
      if (input) input.value = preset.dataset.mvlSizePreset || "";
    });

    root.addEventListener("input", (event) => {
      const input = event.target;

      if (input.id === "mvlBulkColor") syncBulkColor("name");
      if (input.id === "mvlBulkPicker") syncBulkColor("picker");

      const row = input.closest(".mvl-row");
      if (row && input.dataset.field) updateVariantField(row, input);
    });

    root.addEventListener("change", (event) => {
      const input = event.target;

      if (input.id === "mvlBulkHex") syncBulkColor("hex");

      const row = input.closest(".mvl-row");
      if (row && input.dataset.field) updateVariantField(row, input);
    });

    root.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;

      const row = event.target.closest(".mvl-row");

      if (row && event.target.dataset.field === "color_name") {
        event.preventDefault();
        updateVariantField(row, event.target);
        saveCustomColor(row);
      }

      if (event.target.id === "mvlBulkColor") {
        event.preventDefault();

        const name = event.target.value.trim();
        const hex = normalizeHex($(SELECTOR.bulkHex)?.value || "#3b2414");

        if (name) COLOR_MAP[name.toLowerCase()] = hex;
      }
    });

    const form = $(SELECTOR.form);
    if (form && !form.dataset.mvlBound) {
      form.dataset.mvlBound = "1";
      form.addEventListener("submit", normalizeBeforeSubmit);
    }
  }

  function init() {
    const initial = readInitialVariants();

    state = initial.length
      ? initial.map(normalizeVariant)
      : [normalizeVariant(FIELD_DEFAULTS)];

    const bulkPicker = $(SELECTOR.bulkPicker);
    const bulkHex = $(SELECTOR.bulkHex);

    if (bulkPicker && bulkHex) {
      bulkPicker.value = normalizeHex(bulkHex.value);
    }

    bindEvents();
    render();
  }

  document.addEventListener("DOMContentLoaded", init);

  window.MM = window.MM || {};
  window.MM.VariantsLite = {
    add: addVariant,
    addBulkSizes,
    normalizeBeforeSubmit,
    getState: () => state.slice()
  };
})();