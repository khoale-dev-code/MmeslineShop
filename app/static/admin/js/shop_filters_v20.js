(() => {
  "use strict";

  const root = document.querySelector("[data-shop-filter-admin]");
  if (!root) return;

  const list = root.querySelector("[data-group-list]");
  const empty = root.querySelector("[data-empty]");
  const groupDialog = root.querySelector("[data-group-dialog]");
  const optionDialog = root.querySelector("[data-option-dialog]");
  const groupForm = root.querySelector("[data-group-form]");
  const optionForm = root.querySelector("[data-option-form]");
  const csrf = root.dataset.csrf || "";
  let config = readJson(root.querySelector("[data-initial-config]"), { ready: false, groups: [] });

  function readJson(node, fallback) {
    try { return JSON.parse(node?.textContent || ""); } catch (_) { return fallback; }
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
    })[char]);
  }

  function endpoint(template, id) {
    return template.replace("__ID__", encodeURIComponent(id));
  }

  async function api(url, { method = "POST", body } = {}) {
    const response = await fetch(url, {
      method,
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.success === false) {
      throw new Error(payload.message || "Không thể hoàn thành thao tác.");
    }
    return payload;
  }

  function toast(message, type = "success") {
    const stack = root.querySelector("[data-toasts]");
    const node = document.createElement("div");
    node.className = `gm-sf-toast${type === "error" ? " is-error" : ""}`;
    node.textContent = message;
    stack.appendChild(node);
    window.setTimeout(() => node.remove(), 3200);
  }

  function iconFor(group) {
    if (group.key === "color") return "fa-palette";
    if (group.key === "chatlieu") return "fa-layer-group";
    if (group.key === "loai") return "fa-shirt";
    return "fa-filter";
  }

  function renderOption(group, option) {
    const swatch = group.display_type === "color"
      ? `<i class="gm-sf-swatch" style="--swatch:${escapeHtml(option.color_hex || "#d6b88d")}"></i>`
      : "";
    return `
      <div class="gm-sf-option${option.is_active ? "" : " is-off"}" data-option-id="${escapeHtml(option.id)}">
        <div class="gm-sf-option-name">${swatch}<span>${escapeHtml(option.label)}</span></div>
        <code>${escapeHtml(group.key)}:${escapeHtml(option.value)}</code>
        <div class="gm-sf-option-actions">
          <button type="button" data-edit-option="${escapeHtml(option.id)}" title="Sửa"><i class="fa-solid fa-pen"></i></button>
          <button type="button" data-toggle-option="${escapeHtml(option.id)}" title="${option.is_active ? "Ẩn" : "Bật"}"><i class="fa-solid ${option.is_active ? "fa-eye-slash" : "fa-eye"}"></i></button>
        </div>
      </div>`;
  }

  function render() {
    const groups = Array.isArray(config.groups) ? config.groups : [];
    root.querySelector("[data-group-count]").textContent = groups.filter((g) => g.is_active).length;
    root.querySelector("[data-option-count]").textContent = groups.reduce(
      (sum, group) => sum + (group.options || []).filter((item) => item.is_active).length, 0
    );
    empty.hidden = groups.length > 0;
    list.innerHTML = groups.map((group) => `
      <article class="gm-sf-card${group.is_active ? "" : " is-off"}" data-group-id="${escapeHtml(group.id)}">
        <header class="gm-sf-card-head">
          <div class="gm-sf-card-title">
            <span class="gm-sf-card-icon"><i class="fa-solid ${iconFor(group)}"></i></span>
            <div><h2>${escapeHtml(group.label)}</h2><p>Token <code>${escapeHtml(group.key)}:&lt;giá-trị&gt;</code> · ${escapeHtml(group.display_type)}</p></div>
          </div>
          <div class="gm-sf-actions">
            <button type="button" data-add-option="${escapeHtml(group.id)}" title="Thêm lựa chọn"><i class="fa-solid fa-plus"></i></button>
            <button type="button" data-edit-group="${escapeHtml(group.id)}" title="Sửa"><i class="fa-solid fa-pen"></i></button>
            <button type="button" data-toggle-group="${escapeHtml(group.id)}" title="${group.is_active ? "Ẩn khỏi Shop" : "Bật lại"}"><i class="fa-solid ${group.is_active ? "fa-eye-slash" : "fa-eye"}"></i></button>
          </div>
        </header>
        <div class="gm-sf-options">
          ${(group.options || []).map((option) => renderOption(group, option)).join("")}
          <button class="gm-sf-add-option" type="button" data-add-option="${escapeHtml(group.id)}"><i class="fa-solid fa-plus"></i> Thêm lựa chọn</button>
        </div>
      </article>`).join("");
  }

  function findGroup(id) {
    return (config.groups || []).find((group) => String(group.id) === String(id));
  }

  function findOption(id) {
    for (const group of config.groups || []) {
      const option = (group.options || []).find((item) => String(item.id) === String(id));
      if (option) return { group, option };
    }
    return null;
  }

  function openGroup(group = null) {
    groupForm.reset();
    groupForm.elements.id.value = group?.id || "";
    groupForm.elements.label.value = group?.label || "";
    groupForm.elements.key.value = group?.key || "";
    groupForm.elements.key.disabled = Boolean(group?.id);
    groupForm.elements.display_type.value = group?.display_type || "chips";
    groupForm.elements.is_active.checked = group ? Boolean(group.is_active) : true;
    root.querySelector("[data-group-dialog-title]").textContent = group ? "Sửa bộ lọc" : "Tạo bộ lọc";
    groupDialog.showModal();
  }

  function openOption(group, option = null) {
    optionForm.reset();
    optionForm.elements.id.value = option?.id || "";
    optionForm.elements.group_id.value = group.id;
    optionForm.elements.group_key.value = group.key;
    optionForm.elements.label.value = option?.label || "";
    optionForm.elements.value.value = option?.value || "";
    optionForm.elements.color_hex.value = option?.color_hex || "#d6b88d";
    optionForm.elements.is_active.checked = option ? Boolean(option.is_active) : true;
    root.querySelector("[data-token-prefix]").textContent = `${group.key}:`;
    root.querySelector("[data-color-field]").hidden = group.key !== "color";
    root.querySelector("[data-option-dialog-title]").textContent = option ? "Sửa lựa chọn" : `Thêm vào ${group.label}`;
    optionDialog.showModal();
  }

  root.addEventListener("click", async (event) => {
    const newGroup = event.target.closest("[data-new-group]");
    if (newGroup) return openGroup();
    const editGroup = event.target.closest("[data-edit-group]");
    if (editGroup) return openGroup(findGroup(editGroup.dataset.editGroup));
    const addOption = event.target.closest("[data-add-option]");
    if (addOption) return openOption(findGroup(addOption.dataset.addOption));
    const editOption = event.target.closest("[data-edit-option]");
    if (editOption) {
      const found = findOption(editOption.dataset.editOption);
      if (found) openOption(found.group, found.option);
      return;
    }
    const toggleGroup = event.target.closest("[data-toggle-group]");
    if (toggleGroup) {
      const group = findGroup(toggleGroup.dataset.toggleGroup);
      try {
        await api(endpoint(root.dataset.groupActiveTemplate, group.id), { method: "PATCH", body: { is_active: !group.is_active } });
        group.is_active = !group.is_active; render(); toast("Đã cập nhật trạng thái bộ lọc.");
      } catch (error) { toast(error.message, "error"); }
      return;
    }
    const toggleOption = event.target.closest("[data-toggle-option]");
    if (toggleOption) {
      const found = findOption(toggleOption.dataset.toggleOption);
      try {
        await api(endpoint(root.dataset.optionActiveTemplate, found.option.id), { method: "PATCH", body: { is_active: !found.option.is_active } });
        found.option.is_active = !found.option.is_active; render(); toast("Đã cập nhật lựa chọn.");
      } catch (error) { toast(error.message, "error"); }
    }
  });

  groupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(groupForm));
    data.key = groupForm.elements.key.value;
    data.is_active = groupForm.elements.is_active.checked;
    try {
      await api(root.dataset.groupsUrl, { body: data });
      groupDialog.close(); toast("Đã lưu bộ lọc. Đang tải lại cấu hình…");
      window.setTimeout(() => window.location.reload(), 450);
    } catch (error) { toast(error.message, "error"); }
  });

  optionForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(optionForm));
    data.is_active = optionForm.elements.is_active.checked;
    try {
      await api(root.dataset.optionsUrl, { body: data });
      optionDialog.close(); toast("Đã lưu lựa chọn. Đang tải lại cấu hình…");
      window.setTimeout(() => window.location.reload(), 450);
    } catch (error) { toast(error.message, "error"); }
  });

  render();
})();
