(function () {
  "use strict";

  const root = document.getElementById("aboutEditor");
  const stateNode = document.getElementById("aboutEditorState");
  if (!root || !stateNode) return;

  const initial = JSON.parse(stateNode.textContent || "{}");
  const state = {
    content: structuredCloneSafe(initial.content || {}),
    version: Number(initial.draft_version || 0),
    publishedVersion: Number(initial.published_version || 0),
    schemaReady: initial.schema_ready !== false,
    dirty: false,
    busy: false
  };

  const sectionMeta = {
    hero: ["Hero", "Ấn tượng đầu tiên", "fa-star"],
    marquee: ["Marquee", "Dòng chữ chuyển động", "fa-text-width"],
    story: ["Câu chuyện", "Nguồn gốc thương hiệu", "fa-book-open"],
    gallery: ["Thư viện ảnh", "Lookbook hình ảnh", "fa-images"],
    beliefs: ["Giá trị", "Điều thương hiệu tin tưởng", "fa-gem"],
    manifesto: ["Manifesto", "Thông điệp kết trang", "fa-flag"]
  };

  const listConfig = {
    marquee: { path: "marquee", max: 12, create: () => "Thông điệp mới" },
    stats: { path: "story.stats", max: 6, create: (i) => ({ number: pad(i + 1), label: "Điểm nhấn mới" }) },
    gallery: { path: "gallery", max: 8, create: (i) => ({ url: "", alt: `GUAMAISON look ${i + 1}` }) },
    values: { path: "beliefs.values", max: 8, create: (i) => ({ number: pad(i + 1), title: "Giá trị mới", text: "Mô tả giá trị thương hiệu." }) }
  };

  function structuredCloneSafe(value) {
    if (typeof window.structuredClone === "function") return window.structuredClone(value);
    return JSON.parse(JSON.stringify(value));
  }

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function getPath(path, fallback) {
    const value = String(path || "").split(".").reduce((cursor, key) => {
      return cursor && Object.prototype.hasOwnProperty.call(cursor, key) ? cursor[key] : undefined;
    }, state.content);
    return value === undefined ? fallback : value;
  }

  function setPath(path, value) {
    const keys = String(path || "").split(".").filter(Boolean);
    if (!keys.length) return;
    let cursor = state.content;
    keys.slice(0, -1).forEach((key) => {
      if (!cursor[key] || typeof cursor[key] !== "object" || Array.isArray(cursor[key])) cursor[key] = {};
      cursor = cursor[key];
    });
    cursor[keys[keys.length - 1]] = value;
    markDirty();
  }

  function markDirty() {
    state.dirty = true;
    root.classList.add("is-dirty");
  }

  function markClean() {
    state.dirty = false;
    root.classList.remove("is-dirty");
  }

  function notify(message, type = "success") {
    if (window.GUA && typeof window.GUA.snackbar === "function") {
      window.GUA.snackbar(message, type);
    } else if (window.GUA && typeof window.GUA.toast === "function") {
      window.GUA.toast(message, type);
    } else if (typeof window.showToast === "function") {
      window.showToast(message, type);
    } else {
      window.alert(message);
    }
  }

  function csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || "";
  }

  async function jsonRequest(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
        "X-Requested-With": "XMLHttpRequest"
      },
      body: JSON.stringify(payload)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || result.success === false) {
      const error = new Error(result.message || `Yêu cầu thất bại (HTTP ${response.status}).`);
      error.status = response.status;
      error.payload = result;
      throw error;
    }
    return result;
  }

  function setBusy(isBusy, activeButton) {
    state.busy = isBusy;
    root.classList.toggle("is-busy", isBusy);
    root.querySelectorAll("[data-action]").forEach((button) => {
      button.disabled = isBusy || !state.schemaReady;
    });
    if (activeButton) {
      if (isBusy) {
        activeButton.dataset.oldHtml = activeButton.innerHTML;
        activeButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xử lý';
      } else if (activeButton.dataset.oldHtml) {
        activeButton.innerHTML = activeButton.dataset.oldHtml;
        delete activeButton.dataset.oldHtml;
      }
    }
  }

  function handleError(error) {
    if (error.status === 409 || error.payload?.conflict) {
      root.querySelector("[data-conflict-banner]")?.classList.remove("hidden");
      notify(error.message, "warning");
      return;
    }
    notify(error.message || "Không thể hoàn thành thao tác.", "error");
  }

  function updateVersionUI() {
    root.querySelector("[data-draft-version]").textContent = String(state.version);
    root.querySelector("[data-published-version]").textContent = String(state.publishedVersion);
  }

  function hydrateStaticFields() {
    root.querySelectorAll("[data-about-path]").forEach((input) => {
      input.value = getPath(input.dataset.aboutPath, "") ?? "";
    });
    root.querySelectorAll("[data-image-preview]").forEach((image) => {
      image.src = getPath(image.dataset.imagePreview, "") || "";
    });
  }

  function renderSectionOrder() {
    const host = root.querySelector("[data-section-order]");
    if (!host) return;
    const order = Array.isArray(state.content.section_order) ? state.content.section_order : Object.keys(sectionMeta);
    const enabled = state.content.sections_enabled || {};
    host.innerHTML = order.map((key, index) => {
      const meta = sectionMeta[key] || [key, "Khối nội dung", "fa-layer-group"];
      return `<div class="ab-section-row" data-section-key="${escapeHtml(key)}">
        <i class="fa-solid ${escapeHtml(meta[2])}"></i>
        <div><strong>${escapeHtml(meta[0])}</strong><small>${escapeHtml(meta[1])}</small></div>
        <label class="ab-switch" title="Bật hoặc tắt khối">
          <input type="checkbox" data-section-enabled="${escapeHtml(key)}" ${enabled[key] !== false ? "checked" : ""}>
          <span></span>
        </label>
        <div class="ab-row-move">
          <button class="ab-icon-btn" type="button" data-section-move="up" data-section-index="${index}" ${index === 0 ? "disabled" : ""} aria-label="Đưa lên"><i class="fa-solid fa-arrow-up"></i></button>
          <button class="ab-icon-btn" type="button" data-section-move="down" data-section-index="${index}" ${index === order.length - 1 ? "disabled" : ""} aria-label="Đưa xuống"><i class="fa-solid fa-arrow-down"></i></button>
        </div>
      </div>`;
    }).join("");
  }

  function listValue(name) {
    const config = listConfig[name];
    const value = getPath(config.path, []);
    return Array.isArray(value) ? value : [];
  }

  function listActions(name, index, length) {
    return `<div class="ab-list-actions">
      <button type="button" class="ab-icon-btn" data-list-move="up" data-list-name="${name}" data-list-index="${index}" ${index === 0 ? "disabled" : ""} aria-label="Đưa lên"><i class="fa-solid fa-arrow-up"></i></button>
      <button type="button" class="ab-icon-btn" data-list-move="down" data-list-name="${name}" data-list-index="${index}" ${index === length - 1 ? "disabled" : ""} aria-label="Đưa xuống"><i class="fa-solid fa-arrow-down"></i></button>
      <button type="button" class="ab-icon-btn is-delete" data-list-delete="${name}" data-list-index="${index}" aria-label="Xóa"><i class="fa-regular fa-trash-can"></i></button>
    </div>`;
  }

  function renderList(name) {
    const host = root.querySelector(`[data-list="${name}"]`);
    if (!host) return;
    const items = listValue(name);

    host.innerHTML = items.map((item, index) => {
      if (name === "marquee") {
        return `<div class="ab-list-item"><div class="ab-list-fields is-single"><label class="ab-field"><span class="ab-label">Cụm từ ${index + 1}</span><input class="ab-input" value="${escapeHtml(item)}" data-list-name="marquee" data-list-index="${index}" data-list-key="value"></label></div>${listActions(name, index, items.length)}</div>`;
      }
      if (name === "stats") {
        return `<div class="ab-list-item"><div class="ab-list-fields"><label class="ab-field"><span class="ab-label">Số</span><input class="ab-input" value="${escapeHtml(item.number)}" data-list-name="stats" data-list-index="${index}" data-list-key="number"></label><label class="ab-field"><span class="ab-label">Nhãn</span><input class="ab-input" value="${escapeHtml(item.label)}" data-list-name="stats" data-list-index="${index}" data-list-key="label"></label></div>${listActions(name, index, items.length)}</div>`;
      }
      if (name === "values") {
        return `<div class="ab-list-item"><div class="ab-list-fields is-values"><label class="ab-field"><span class="ab-label">Số</span><input class="ab-input" value="${escapeHtml(item.number)}" data-list-name="values" data-list-index="${index}" data-list-key="number"></label><label class="ab-field"><span class="ab-label">Tên giá trị</span><input class="ab-input" value="${escapeHtml(item.title)}" data-list-name="values" data-list-index="${index}" data-list-key="title"></label><label class="ab-field"><span class="ab-label">Mô tả</span><textarea class="ab-textarea" data-list-name="values" data-list-index="${index}" data-list-key="text">${escapeHtml(item.text)}</textarea></label></div>${listActions(name, index, items.length)}</div>`;
      }
      return `<div class="ab-list-item"><div class="ab-gallery-thumb"><img src="${escapeHtml(item.url)}" alt=""></div><div class="ab-list-fields is-single"><label class="ab-field"><span class="ab-label">URL ảnh</span><input class="ab-input" type="url" value="${escapeHtml(item.url)}" data-list-name="gallery" data-list-index="${index}" data-list-key="url"></label><label class="ab-field"><span class="ab-label">Mô tả ảnh</span><input class="ab-input" value="${escapeHtml(item.alt)}" data-list-name="gallery" data-list-index="${index}" data-list-key="alt"></label><label class="ab-upload-button"><i class="fa-solid fa-cloud-arrow-up"></i><span>Tải lên</span><input class="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/gif,image/avif" data-gallery-upload="${index}"></label></div>${listActions(name, index, items.length)}</div>`;
    }).join("");
  }

  function renderAll() {
    hydrateStaticFields();
    renderSectionOrder();
    Object.keys(listConfig).forEach(renderList);
    updateVersionUI();
  }

  function addListItem(name) {
    const config = listConfig[name];
    const items = listValue(name);
    if (!config || items.length >= config.max) {
      notify(`Danh sách chỉ hỗ trợ tối đa ${config?.max || 0} mục.`, "warning");
      return;
    }
    items.push(config.create(items.length));
    setPath(config.path, items);
    renderList(name);
  }

  function moveListItem(name, index, direction) {
    const config = listConfig[name];
    const items = listValue(name);
    const next = direction === "up" ? index - 1 : index + 1;
    if (!config || next < 0 || next >= items.length) return;
    [items[index], items[next]] = [items[next], items[index]];
    setPath(config.path, items);
    renderList(name);
  }

  function deleteListItem(name, index) {
    const config = listConfig[name];
    const items = listValue(name);
    if (!config || index < 0 || index >= items.length) return;
    items.splice(index, 1);
    setPath(config.path, items);
    renderList(name);
  }

  async function uploadFile(file, onSuccess, input) {
    if (!file) return;
    const data = new FormData();
    data.append("image", file);
    input.disabled = true;
    notify("Đang tải ảnh lên...", "info");
    try {
      const response = await fetch(root.dataset.uploadUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": csrfToken(), "X-Requested-With": "XMLHttpRequest" },
        body: data
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok || result.success === false) throw new Error(result.message || "Tải ảnh thất bại.");
      onSuccess(result.url);
      notify(result.message || "Đã tải ảnh lên.", "success");
    } catch (error) {
      notify(error.message, "error");
    } finally {
      input.disabled = false;
      input.value = "";
    }
  }

  async function saveDraft(button) {
    if (!state.schemaReady) throw new Error("Supabase chưa có schema About.");
    setBusy(true, button);
    try {
      const result = await jsonRequest(root.dataset.saveUrl, { version: state.version, content: state.content });
      state.version = Number(result.draft_version);
      state.content = structuredCloneSafe(result.content || state.content);
      markClean();
      renderAll();
      notify(result.message || "Đã lưu bản nháp.", "success");
      return result;
    } catch (error) {
      handleError(error);
      throw error;
    } finally {
      setBusy(false, button);
    }
  }

  async function publish(button) {
    if (state.dirty) {
      try { await saveDraft(button); } catch (_) { return; }
    }
    setBusy(true, button);
    try {
      const result = await jsonRequest(root.dataset.publishUrl, { version: state.version });
      state.publishedVersion = Number(result.published_version || state.publishedVersion);
      updateVersionUI();
      notify(result.message || "Đã xuất bản trang About.", "success");
    } catch (error) {
      handleError(error);
    } finally {
      setBusy(false, button);
    }
  }

  async function preview(button) {
    const previewWindow = window.open("about:blank", "about-draft-preview");
    if (previewWindow) previewWindow.opener = null;
    if (state.dirty) {
      try {
        await saveDraft(button);
      } catch (_) {
        if (previewWindow) previewWindow.close();
        return;
      }
    }
    if (previewWindow) {
      previewWindow.location.replace(root.dataset.previewUrl);
    } else {
      window.location.assign(root.dataset.previewUrl);
    }
  }

  async function resetDraft(button) {
    if (!window.confirm("Khôi phục toàn bộ bản nháp About về nội dung mặc định? Trang đang xuất bản sẽ chưa thay đổi.")) return;
    setBusy(true, button);
    try {
      const result = await jsonRequest(root.dataset.resetUrl, { version: state.version });
      state.version = Number(result.draft_version);
      state.content = structuredCloneSafe(result.content || {});
      markClean();
      renderAll();
      notify(result.message || "Đã khôi phục bản nháp.", "success");
    } catch (error) {
      handleError(error);
    } finally {
      setBusy(false, button);
    }
  }

  root.addEventListener("click", (event) => {
    const panelButton = event.target.closest("[data-panel-target]");
    if (panelButton) {
      root.querySelectorAll("[data-panel-target]").forEach((item) => item.classList.toggle("is-active", item === panelButton));
      root.querySelectorAll("[data-panel]").forEach((panel) => panel.classList.toggle("is-active", panel.dataset.panel === panelButton.dataset.panelTarget));
      return;
    }

    const action = event.target.closest("[data-action]");
    if (action) {
      if (action.dataset.action === "save") saveDraft(action).catch(() => {});
      if (action.dataset.action === "publish") publish(action);
      if (action.dataset.action === "preview") preview(action);
      if (action.dataset.action === "reset") resetDraft(action);
      return;
    }

    const add = event.target.closest("[data-list-add]");
    if (add) return addListItem(add.dataset.listAdd);

    const del = event.target.closest("[data-list-delete]");
    if (del) return deleteListItem(del.dataset.listDelete, Number(del.dataset.listIndex));

    const move = event.target.closest("[data-list-move]");
    if (move) return moveListItem(move.dataset.listName, Number(move.dataset.listIndex), move.dataset.listMove);

    const sectionMove = event.target.closest("[data-section-move]");
    if (sectionMove) {
      const order = state.content.section_order;
      const index = Number(sectionMove.dataset.sectionIndex);
      const next = sectionMove.dataset.sectionMove === "up" ? index - 1 : index + 1;
      if (Array.isArray(order) && next >= 0 && next < order.length) {
        [order[index], order[next]] = [order[next], order[index]];
        markDirty();
        renderSectionOrder();
      }
    }
  });

  root.addEventListener("input", (event) => {
    const field = event.target.closest("[data-about-path]");
    if (field) {
      setPath(field.dataset.aboutPath, field.value);
      const preview = root.querySelector(`[data-image-preview="${CSS.escape(field.dataset.aboutPath)}"]`);
      if (preview) preview.src = field.value;
      return;
    }

    const listInput = event.target.closest("[data-list-name][data-list-index][data-list-key]");
    if (listInput) {
      const name = listInput.dataset.listName;
      const items = listValue(name);
      const index = Number(listInput.dataset.listIndex);
      if (name === "marquee") items[index] = listInput.value;
      else if (items[index]) items[index][listInput.dataset.listKey] = listInput.value;
      setPath(listConfig[name].path, items);
      if (name === "gallery" && listInput.dataset.listKey === "url") {
        listInput.closest(".ab-list-item")?.querySelector(".ab-gallery-thumb img")?.setAttribute("src", listInput.value);
      }
    }
  });

  root.addEventListener("change", (event) => {
    const enabled = event.target.closest("[data-section-enabled]");
    if (enabled) {
      state.content.sections_enabled = state.content.sections_enabled || {};
      state.content.sections_enabled[enabled.dataset.sectionEnabled] = enabled.checked;
      markDirty();
      return;
    }

    const upload = event.target.closest("[data-about-upload]");
    if (upload && upload.files?.[0]) {
      const path = upload.dataset.aboutUpload;
      uploadFile(upload.files[0], (url) => {
        setPath(path, url);
        const input = root.querySelector(`[data-about-path="${CSS.escape(path)}"]`);
        const preview = root.querySelector(`[data-image-preview="${CSS.escape(path)}"]`);
        if (input) input.value = url;
        if (preview) preview.src = url;
      }, upload);
      return;
    }

    const galleryUpload = event.target.closest("[data-gallery-upload]");
    if (galleryUpload && galleryUpload.files?.[0]) {
      const index = Number(galleryUpload.dataset.galleryUpload);
      uploadFile(galleryUpload.files[0], (url) => {
        const items = listValue("gallery");
        if (items[index]) items[index].url = url;
        setPath("gallery", items);
        renderList("gallery");
      }, galleryUpload);
    }
  });

  window.addEventListener("beforeunload", (event) => {
    if (!state.dirty) return;
    event.preventDefault();
    event.returnValue = "";
  });

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      const button = root.querySelector('[data-action="save"]');
      if (!state.busy) saveDraft(button).catch(() => {});
    }
  });

  renderAll();
  if (!state.schemaReady) {
    root.querySelectorAll("[data-action], [data-about-upload], [data-gallery-upload]").forEach((item) => { item.disabled = true; });
  }
})();
