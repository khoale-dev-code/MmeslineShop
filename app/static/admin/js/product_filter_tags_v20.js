(() => {
  "use strict";
  const root = document.querySelector("[data-product-filter-tags]");
  if (!root) return;

  const groupsNode = root.querySelector("[data-filter-groups]");
  const loading = root.querySelector("[data-filter-loading]");
  const errorNode = root.querySelector("[data-filter-error]");
  const hidden = root.querySelector("#filterTagsHidden");
  const csrf = root.dataset.csrf || "";
  let groups = [];
  let selected = new Set();

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
    })[char]);
  }

  function existingTags() {
    try {
      return JSON.parse(document.getElementById("currentTagsJson")?.textContent || "[]");
    } catch (_) {
      return String(document.querySelector("#tagsHidden")?.value || "").split(",");
    }
  }

  function token(group, option) { return `${group.key}:${option.value}`.toLowerCase(); }

  function sync() {
    hidden.value = Array.from(selected).join(", ");
  }

  function render() {
    groupsNode.innerHTML = groups.filter((group) => group.is_active).map((group) => `
      <section class="gm-pft-group" data-pft-group="${escapeHtml(group.id)}">
        <div class="gm-pft-group-head"><strong>${escapeHtml(group.label)}</strong><code>${escapeHtml(group.key)}:&lt;giá-trị&gt;</code></div>
        <div class="gm-pft-options">
          ${(group.options || []).filter((option) => option.is_active).map((option) => {
            const value = token(group, option);
            const swatch = group.key === "color" ? `<i style="--filter-color:${escapeHtml(option.color_hex || "#d6b88d")}"></i>` : "";
            return `<label class="gm-pft-option"><input type="checkbox" value="${escapeHtml(value)}" ${selected.has(value) ? "checked" : ""}><span>${swatch}${escapeHtml(option.label)}</span></label>`;
          }).join("")}
        </div>
        <div class="gm-pft-quick">
          <input type="text" data-quick-label maxlength="80" placeholder="Thêm ${escapeHtml(group.label.toLowerCase())} mới…">
          ${group.key === "color" ? '<input class="gm-pft-quick-color" type="color" data-quick-color value="#d6b88d" aria-label="Chọn màu">' : ""}
          <button type="button" data-quick-add="${escapeHtml(group.id)}"><i class="fa-solid fa-plus"></i> Tạo & chọn</button>
        </div>
      </section>`).join("");
    groupsNode.hidden = false;
    sync();
  }

  async function createOption(group, section) {
    const input = section.querySelector("[data-quick-label]");
    const label = input.value.trim();
    if (!label) { input.focus(); return; }
    const response = await fetch(root.dataset.optionUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      body: JSON.stringify({
        group_id: group.id,
        label,
        color_hex: section.querySelector("[data-quick-color]")?.value || null,
        is_active: true
      })
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.success === false) throw new Error(payload.message || "Không thể tạo lựa chọn.");
    const option = payload.option;
    const currentIndex = (group.options || []).findIndex((item) => item.value === option.value);
    if (currentIndex >= 0) group.options[currentIndex] = option; else group.options.push(option);
    selected.add(`${group.key}:${option.value}`.toLowerCase());
    render();
  }

  groupsNode.addEventListener("change", (event) => {
    const input = event.target.closest(".gm-pft-option input");
    if (!input) return;
    if (input.checked) selected.add(input.value); else selected.delete(input.value);
    sync();
  });

  groupsNode.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-quick-add]");
    if (!button) return;
    const group = groups.find((item) => String(item.id) === String(button.dataset.quickAdd));
    const section = button.closest("[data-pft-group]");
    button.disabled = true;
    try { await createOption(group, section); }
    catch (error) { errorNode.textContent = error.message; errorNode.hidden = false; }
    finally { button.disabled = false; }
  });

  fetch(root.dataset.configUrl, { credentials: "same-origin", headers: { "Accept": "application/json" } })
    .then((response) => response.json().then((payload) => ({ response, payload })))
    .then(({ response, payload }) => {
      if (!response.ok || !payload.ready) throw new Error("Chưa chạy migration Shop Filters v20 trong Supabase.");
      groups = payload.groups || [];
      const knownKeys = new Set(groups.map((group) => String(group.key).toLowerCase()));
      for (const raw of existingTags()) {
        const value = String(raw || "").trim().toLowerCase();
        if (knownKeys.has(value.split(":", 1)[0])) selected.add(value);
      }
      loading.hidden = true;
      render();
    })
    .catch((error) => {
      loading.hidden = true;
      errorNode.textContent = `${error.message} Tag cũ của sản phẩm vẫn được giữ nguyên.`;
      errorNode.hidden = false;
    });
})();
