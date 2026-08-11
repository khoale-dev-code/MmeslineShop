(() => {
  "use strict";

  const root = document.querySelector("[data-coupon-form-page]");
  const form = root?.querySelector("[data-coupon-form]");
  if (!root || !form) return;

  const field = (selector) => form.querySelector(selector);
  const preview = (selector) => root.querySelector(selector);
  const ui = {
    code: field("[data-code]"),
    description: field("[data-description]"),
    image: field("[data-image]"),
    type: field("[data-type]"),
    value: field("[data-value]"),
    min: field("[data-min]"),
    max: field("[data-max]"),
    start: field("[data-start]"),
    expiry: field("[data-expiry]"),
    points: field("[data-points]"),
    channel: field("[data-channel]"),
    valueField: field("[data-value-field]"),
    maxField: field("[data-max-field]"),
    unit: field("[data-value-unit]"),
    scopePanels: [...form.querySelectorAll("[data-scope-panel]")],
    submitButtons: [...root.querySelectorAll('[type="submit"][form="couponForm"], [data-submit]')],
    pCode: preview("[data-preview-code]"),
    pDescription: preview("[data-preview-description]"),
    pImage: preview("[data-preview-image]"),
    pType: preview("[data-preview-type]"),
    pValue: preview("[data-preview-value]"),
    pMin: preview("[data-preview-min]"),
    pPoints: preview("[data-preview-points]"),
    pChannel: preview("[data-preview-channel]"),
    previewWrap: preview(".gpa-preview"),
    previewToggle: preview("[data-preview-toggle]"),
  };

  const money = (value) => Number(value || 0).toLocaleString("vi-VN") + "₫";
  const normalizeCode = (value) => String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/gi, "d")
    .toUpperCase()
    .replace(/[^A-Z0-9_-]/g, "")
    .slice(0, 50);

  function syncType() {
    const type = ui.type?.value || "percent";
    const isShipping = type === "free_shipping";
    const isFixed = type === "fixed";

    if (ui.value) {
      ui.value.disabled = isShipping;
      ui.value.required = !isShipping;
      ui.value.max = type === "percent" ? "100" : "";
    }
    if (ui.max) ui.max.disabled = isShipping || isFixed;
    if (ui.valueField) ui.valueField.hidden = isShipping;
    if (ui.maxField) ui.maxField.hidden = isShipping || isFixed;
    if (ui.unit) ui.unit.textContent = type === "percent" ? "(%)" : "(₫)";
  }

  function syncScope() {
    const selected = field('input[name="scope"]:checked')?.value || "all";
    ui.scopePanels.forEach((panel) => {
      const isActive = panel.dataset.scopePanel === selected;
      panel.hidden = !isActive;
      panel.querySelectorAll("select").forEach((select) => { select.disabled = !isActive; });
    });
  }

  function syncDates() {
    if (!ui.start || !ui.expiry) return;
    ui.expiry.min = ui.start.value || "";
    const invalid = Boolean(ui.start.value && ui.expiry.value && ui.expiry.value <= ui.start.value);
    ui.expiry.setCustomValidity(invalid ? "Thời gian kết thúc phải sau thời gian bắt đầu." : "");
  }

  function syncPreview() {
    const type = ui.type?.value || "percent";
    const value = Number(ui.value?.value || 0);
    const code = normalizeCode(ui.code?.value) || "------";
    if (ui.pCode) ui.pCode.textContent = code;
    if (ui.pDescription) ui.pDescription.textContent = ui.description?.value.trim() || "Quyền lợi dành riêng cho khách hàng GUAMAISON.";
    if (ui.pType) ui.pType.textContent = type === "percent" ? "Ưu đãi theo phần trăm" : type === "fixed" ? "Ưu đãi trực tiếp" : "Đặc quyền giao hàng";
    if (ui.pValue) ui.pValue.textContent = type === "percent" ? `${value}%` : type === "fixed" ? money(value) : "Freeship";
    if (ui.pMin) ui.pMin.textContent = money(ui.min?.value || 0);
    if (ui.pPoints) ui.pPoints.textContent = Number(ui.points?.value || 0).toLocaleString("vi-VN");
    if (ui.pChannel) ui.pChannel.textContent = ui.channel?.selectedOptions[0]?.textContent || "Website & POS";

    const url = ui.image?.value.trim() || "";
    if (ui.pImage) {
      ui.pImage.hidden = !url;
      if (url && ui.pImage.getAttribute("src") !== url) ui.pImage.src = url;
    }
  }

  function sync() {
    syncType();
    syncScope();
    syncDates();
    syncPreview();
  }

  function togglePreview() {
    if (!ui.previewWrap || !ui.previewToggle) return;
    const open = ui.previewWrap.dataset.open !== "true";
    ui.previewWrap.dataset.open = String(open);
    ui.previewToggle.setAttribute("aria-expanded", String(open));
  }

  form.addEventListener("input", sync);
  form.addEventListener("change", sync);
  ui.previewToggle?.addEventListener("click", togglePreview);
  ui.code?.addEventListener("blur", () => {
    ui.code.value = normalizeCode(ui.code.value);
    syncPreview();
  });
  ui.pImage?.addEventListener("error", () => { ui.pImage.hidden = true; });

  form.addEventListener("submit", (event) => {
    syncDates();
    if (!form.checkValidity()) {
      event.preventDefault();
      form.reportValidity();
      const invalid = form.querySelector(":invalid");
      const section = invalid?.closest("[data-form-section]");
      section?.classList.add("is-invalid");
      window.setTimeout(() => section?.classList.remove("is-invalid"), 450);
      invalid?.focus({ preventScroll: true });
      section?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    ui.submitButtons.forEach((button) => {
      button.disabled = true;
      const label = button.querySelector("span");
      if (label) label.textContent = "Đang lưu...";
    });
  });

  sync();
})();
