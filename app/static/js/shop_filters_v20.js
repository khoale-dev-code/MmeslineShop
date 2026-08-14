(() => {
  "use strict";

  const form = document.getElementById("shopConfiguredFilterForm");
  if (!form) return;

  const inputs = Array.from(form.querySelectorAll('input[name="f"]'));
  const submit = document.querySelector("[data-configured-filter-submit]");
  const counters = Array.from(document.querySelectorAll("[data-shop-filter-count]"));

  function selectedCount() {
    return inputs.filter((input) => input.checked).length;
  }

  function update() {
    const count = selectedCount();
    if (submit) {
      submit.innerHTML = `Xem kết quả${count ? ` (${count} bộ lọc)` : ""}`;
    }
    counters.forEach((counter) => {
      counter.textContent = String(count);
      counter.hidden = count === 0;
      if (count) counter.dataset.configuredActive = "1";
      else delete counter.dataset.configuredActive;
    });
  }

  form.addEventListener("submit", () => {
    if (!submit) return;
    submit.disabled = true;
    submit.textContent = "Đang lọc…";
  });

  inputs.forEach((input) => input.addEventListener("change", update));

  document.addEventListener("click", (event) => {
    const clear = event.target.closest("[data-shop-clear-filter]");
    if (!clear || !inputs.some((input) => input.checked)) return;

    const url = new URL(window.location.href);
    url.searchParams.delete("f");
    url.searchParams.delete("page");
    window.location.assign(url.toString());
  });

  update();
})();
