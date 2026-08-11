(() => {
  "use strict";

  const root = document.querySelector("[data-voucher-page]");
  if (!root) return;

  const cards = [...root.querySelectorAll("[data-voucher-card]")];
  const tabs = [...root.querySelectorAll("[data-filter]")];
  const ui = {
    search: root.querySelector("[data-voucher-search]"), grid: root.querySelector("[data-voucher-grid]"),
    empty: root.querySelector("[data-empty-state]"), count: root.querySelector("[data-visible-count]"),
    moreWrap: root.querySelector("[data-load-more-wrap]"), snackbar: root.querySelector("[data-snackbar]"),
    snackbarText: root.querySelector("[data-snackbar-text]"),
  };
  const state = { filter: "all", query: "", limit: 9 };
  let toastTimer;

  const normalize = (value) => String(value || "").normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").toLowerCase().trim();
  const matches = () => cards.filter((card) => {
    const sameType = state.filter === "all" || card.dataset.type === state.filter;
    return sameType && normalize(card.dataset.search).includes(state.query);
  });

  function render() {
    if (!cards.length) return;
    const filtered = matches();
    cards.forEach((card) => { card.hidden = true; });
    filtered.slice(0, state.limit).forEach((card) => { card.hidden = false; });
    if (ui.grid) ui.grid.hidden = filtered.length === 0;
    if (ui.empty) ui.empty.hidden = filtered.length !== 0;
    if (ui.count) ui.count.textContent = String(filtered.length);
    if (ui.moreWrap) ui.moreWrap.hidden = state.limit >= filtered.length;
  }

  function reset() {
    state.filter = "all"; state.query = ""; state.limit = 9;
    if (ui.search) ui.search.value = "";
    tabs.forEach((tab, index) => {
      tab.classList.toggle("is-active", index === 0);
      tab.setAttribute("aria-selected", index === 0 ? "true" : "false");
    });
    render();
  }

  function toast(message) {
    if (!ui.snackbar || !ui.snackbarText) return;
    window.clearTimeout(toastTimer);
    ui.snackbarText.textContent = message;
    ui.snackbar.hidden = false;
    requestAnimationFrame(() => ui.snackbar.classList.add("is-visible"));
    toastTimer = window.setTimeout(() => {
      ui.snackbar.classList.remove("is-visible");
      window.setTimeout(() => { ui.snackbar.hidden = true; }, 230);
    }, 2200);
  }

  async function copyCode(button) {
    const code = button.dataset.copyCode || "";
    try {
      await navigator.clipboard.writeText(code);
    } catch (_) {
      const input = document.createElement("textarea");
      input.value = code; input.readOnly = true; input.style.position = "fixed"; input.style.opacity = "0";
      document.body.appendChild(input); input.select(); document.execCommand("copy"); input.remove();
    }
    button.classList.add("is-copied");
    const label = button.querySelector("span");
    const oldLabel = label?.textContent;
    if (label) label.textContent = "Đã lưu mã";
    toast(`Đã lưu mã ${code}`);
    window.setTimeout(() => { button.classList.remove("is-copied"); if (label) label.textContent = oldLabel || "Sao chép"; }, 1700);
  }

  root.addEventListener("click", (event) => {
    const tab = event.target.closest("[data-filter]");
    const copy = event.target.closest("[data-copy-code]");
    if (copy) return void copyCode(copy);
    if (tab) {
      state.filter = tab.dataset.filter || "all"; state.limit = 9;
      tabs.forEach((item) => { const active = item === tab; item.classList.toggle("is-active", active); item.setAttribute("aria-selected", active ? "true" : "false"); });
      render();
    } else if (event.target.closest("[data-reset-filter]")) reset();
    else if (event.target.closest("[data-load-more]")) { state.limit += 9; render(); }
  });

  let debounce;
  ui.search?.addEventListener("input", (event) => {
    window.clearTimeout(debounce);
    debounce = window.setTimeout(() => { state.query = normalize(event.target.value); state.limit = 9; render(); }, 120);
  });
  ui.search?.addEventListener("keydown", (event) => { if (event.key === "Escape") reset(); });
  render();
})();

