// app/static/js/admin/storefront-builder.js

(function () {
  "use strict";

  const CONFIG = window.StorefrontBuilderConfig || {};
  const MODULES = Array.isArray(CONFIG.modules) ? CONFIG.modules : [];
  const DEFAULT_LAYOUT_CONFIG = Array.isArray(CONFIG.defaultLayout) ? CONFIG.defaultLayout : [];

  let layout = [];
  let selectedId = null;
  let draggingId = null;
  let dirty = false;
  let toastTimer = null;
  let uploadTarget = null;

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function uid(prefix) {
    const safePrefix = String(prefix || "block").replace(/[^a-zA-Z0-9_]/g, "_");
    return `${safePrefix}_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  }

  function getModule(type) {
    return MODULES.find((module) => module.type === type) || MODULES[0] || null;
  }

  function createSectionData(type, overrides = {}) {
    const module = getModule(type);

    if (!module) {
      return null;
    }

    return {
      id: uid(module.type),
      type: module.type,
      enabled: true,
      title: module.title || module.type,
      subtitle: module.subtitle || "",
      icon: module.icon || "fa-puzzle-piece",
      settings: {
        ...clone(module.defaults || {}),
        ...(overrides || {})
      }
    };
  }

  function makeDefaultLayout() {
    const sections = DEFAULT_LAYOUT_CONFIG
      .map((item) => createSectionData(item.type, item.overrides || {}))
      .filter(Boolean);

    if (sections.length) {
      return sections;
    }

    return MODULES.slice(0, 4)
      .map((module) => createSectionData(module.type))
      .filter(Boolean);
  }

  function normalizeSection(raw) {
    if (!raw || !raw.type) {
      return null;
    }

    const module = getModule(raw.type);

    if (!module) {
      return null;
    }

    return {
      id: raw.id || uid(raw.type),
      type: module.type,
      enabled: raw.enabled !== false,
      title: raw.title || module.title || module.type,
      subtitle: raw.subtitle || module.subtitle || "",
      icon: raw.icon || module.icon || "fa-puzzle-piece",
      sort_order: Number.isFinite(Number(raw.sort_order)) ? Number(raw.sort_order) : 0,
      settings: {
        ...clone(module.defaults || {}),
        ...(raw.settings || {})
      }
    };
  }

  function parseStoredLayout() {
    const root = $("#sfbRoot");
    const raw = root ? root.dataset.storedLayout : "";

    if (!raw) {
      return [];
    }

    try {
      const parsed = JSON.parse(raw);

      if (Array.isArray(parsed)) {
        return parsed;
      }

      if (typeof parsed === "string" && parsed.trim()) {
        const parsedAgain = JSON.parse(parsed);
        return Array.isArray(parsedAgain) ? parsedAgain : [];
      }

      return [];
    } catch (error) {
      console.warn("[StorefrontBuilder] Cannot parse homepage_layout:", error);
      return [];
    }
  }

  function loadLayout() {
    const stored = parseStoredLayout()
      .map(normalizeSection)
      .filter(Boolean)
      .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));

    layout = stored.length ? stored : makeDefaultLayout();
    selectedId = layout[0] ? layout[0].id : null;
    markDirty(false);
  }

  function getSection(id) {
    return layout.find((item) => item.id === id);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function escapeAttr(value) {
    return escapeHtml(value).replace(/`/g, "&#096;");
  }

  function iconClass(sectionOrModule) {
    return "fa-solid " + (sectionOrModule.icon || "fa-puzzle-piece");
  }

  function notify(message, isError = false) {
    const toast = $("#sfbToast");
    const text = $("#sfbToastText");
    const icon = $("#sfbToastIcon");

    if (!toast || !text || !icon) {
      alert(message);
      return;
    }

    text.textContent = message || "";
    toast.classList.toggle("is-error", Boolean(isError));
    icon.className = isError
      ? "fa-solid fa-triangle-exclamation"
      : "fa-solid fa-circle-check";

    toast.classList.add("is-show");

    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.classList.remove("is-show");
    }, 3200);
  }

  function markDirty(value = true) {
    dirty = value !== false;

    const status = $("#sfbDirtyStatus");

    if (status) {
      status.textContent = dirty ? "Chưa lưu" : "Sẵn sàng";
      status.classList.toggle("is-dirty", dirty);
    }
  }

  function visualBlockCount() {
    const visualTypes = new Set([
      "hero_slider",
      "image_banner",
      "split_banner",
      "video_showcase"
    ]);

    return layout.filter((item) => visualTypes.has(item.type)).length;
  }

  function renderStats() {
    const total = $("#sfbTotalBlocks");
    const enabled = $("#sfbEnabledBlocks");
    const visual = $("#sfbVisualBlocks");

    if (total) total.textContent = String(layout.length);
    if (enabled) enabled.textContent = String(layout.filter((item) => item.enabled).length);
    if (visual) visual.textContent = String(visualBlockCount());
  }

  function sectionLabel(section) {
    const heading = section.settings && (
      section.settings.heading ||
      section.settings.title ||
      section.settings.label
    );

    if (heading) {
      return `${section.title}: ${heading}`;
    }

    return section.title || section.type;
  }

  function renderModules() {
    const wrap = $("#sfbModuleList");

    if (!wrap) {
      return;
    }

    if (!MODULES.length) {
      wrap.innerHTML = `
        <div class="sfb-empty-canvas">
          Chưa có module. Kiểm tra file storefront-builder.config.js.
        </div>
      `;
      return;
    }

    wrap.innerHTML = "";

    MODULES.forEach((module) => {
      const count = layout.filter((item) => item.type === module.type).length;

      const node = document.createElement("article");
      node.className = "sfb-module";
      node.innerHTML = `
        <div class="sfb-module-icon">
          <i class="${iconClass(module)}"></i>
        </div>

        <div class="sfb-module-info">
          <strong>${escapeHtml(module.title)}</strong>
          <small>${escapeHtml(module.subtitle || "")}</small>
        </div>

        <div class="sfb-module-action">
          <span class="sfb-module-count" title="Số block đang dùng">${count}</span>
          <button type="button" class="sfb-icon-btn" title="Thêm block">
            <i class="fa-solid fa-plus"></i>
          </button>
        </div>
      `;

      node.querySelector("button").addEventListener("click", () => {
        const section = createSectionData(module.type);

        if (!section) {
          notify("Không thể tạo block này.", true);
          return;
        }

        layout.push(section);
        selectedId = section.id;
        markDirty(true);
        renderAll();
      });

      wrap.appendChild(node);
    });
  }

  function renderCanvas() {
    const canvas = $("#sfbCanvas");

    if (!canvas) {
      return;
    }

    canvas.innerHTML = "";

    if (!layout.length) {
      canvas.innerHTML = `
        <div class="sfb-empty-canvas">
          <div>
            <i class="fa-solid fa-cubes sfb-empty-icon"></i>
            <p>Chưa có block nào.</p>
            <small>Hãy bấm “Thêm” ở thư viện bên trái để tạo bố cục trang chủ.</small>
          </div>
        </div>
      `;
      return;
    }

    layout.forEach((section, index) => {
      const card = document.createElement("article");
      card.className = [
        "sfb-section",
        section.id === selectedId ? "is-selected" : "",
        section.enabled ? "" : "is-off"
      ].filter(Boolean).join(" ");

      card.dataset.sectionId = section.id;
      card.draggable = true;

      card.innerHTML = `
        <button type="button" class="sfb-handle" title="Kéo để đổi vị trí">
          <i class="fa-solid fa-grip-vertical"></i>
        </button>

        <div class="sfb-section-icon">
          <i class="${iconClass(section)}"></i>
        </div>

        <div class="sfb-section-main">
          <div class="sfb-section-name">${escapeHtml(sectionLabel(section))}</div>
          <div class="sfb-section-meta">
            #${index + 1} · ${escapeHtml(section.type)} · ${section.enabled ? "Đang hiển thị" : "Đang ẩn"}
          </div>
        </div>

        <div class="sfb-section-actions">
          <button type="button" class="sfb-icon-btn" data-move="up" title="Đưa lên">
            <i class="fa-solid fa-arrow-up"></i>
          </button>

          <button type="button" class="sfb-icon-btn" data-move="down" title="Đưa xuống">
            <i class="fa-solid fa-arrow-down"></i>
          </button>

          <button type="button" class="sfb-icon-btn" data-duplicate title="Nhân bản">
            <i class="fa-solid fa-copy"></i>
          </button>

          <button type="button" class="sfb-icon-btn is-danger" data-delete title="Xóa block">
            <i class="fa-solid fa-trash-can"></i>
          </button>

          <label class="sfb-switch" title="Bật/tắt block">
            <input type="checkbox" ${section.enabled ? "checked" : ""}>
            <span></span>
          </label>
        </div>
      `;

      card.addEventListener("click", (event) => {
        if (event.target.closest(".sfb-section-actions")) {
          return;
        }

        selectedId = section.id;
        renderAll();
      });

      card.querySelector("input[type='checkbox']").addEventListener("change", (event) => {
        section.enabled = event.target.checked;
        selectedId = section.id;
        markDirty(true);
        renderAll();
      });

      card.querySelector("[data-move='up']").addEventListener("click", () => moveSection(section.id, -1));
      card.querySelector("[data-move='down']").addEventListener("click", () => moveSection(section.id, 1));
      card.querySelector("[data-duplicate]").addEventListener("click", () => duplicateSection(section.id));
      card.querySelector("[data-delete]").addEventListener("click", () => deleteSection(section.id));

      card.addEventListener("dragstart", (event) => {
        draggingId = section.id;
        card.classList.add("is-dragging");

        if (event.dataTransfer) {
          event.dataTransfer.effectAllowed = "move";
          event.dataTransfer.setData("text/plain", section.id);
        }
      });

      card.addEventListener("dragend", () => {
        draggingId = null;
        card.classList.remove("is-dragging");
      });

      card.addEventListener("dragover", (event) => {
        event.preventDefault();

        if (!draggingId || draggingId === section.id) {
          return;
        }

        const from = layout.findIndex((item) => item.id === draggingId);
        const to = layout.findIndex((item) => item.id === section.id);

        if (from < 0 || to < 0 || from === to) {
          return;
        }

        const dragged = layout.splice(from, 1)[0];
        layout.splice(to, 0, dragged);
        selectedId = draggingId;
        markDirty(true);
        renderAll(false);
      });

      canvas.appendChild(card);
    });
  }

  function moveSection(id, direction) {
    const index = layout.findIndex((item) => item.id === id);
    const next = index + direction;

    if (index < 0 || next < 0 || next >= layout.length) {
      return;
    }

    const item = layout.splice(index, 1)[0];
    layout.splice(next, 0, item);
    selectedId = id;
    markDirty(true);
    renderAll();
  }

  function duplicateSection(id) {
    const index = layout.findIndex((item) => item.id === id);

    if (index < 0) {
      return;
    }

    const copy = clone(layout[index]);
    copy.id = uid(copy.type);

    if (copy.settings && copy.settings.heading) {
      copy.settings.heading = copy.settings.heading + " - Copy";
    }

    layout.splice(index + 1, 0, copy);
    selectedId = copy.id;
    markDirty(true);
    renderAll();
  }

  function deleteSection(id) {
    const section = getSection(id);

    if (!section) {
      return;
    }

    const ok = confirm(`Xóa block "${sectionLabel(section)}"?`);

    if (!ok) {
      return;
    }

    layout = layout.filter((item) => item.id !== id);

    if (selectedId === id) {
      selectedId = layout[0] ? layout[0].id : null;
    }

    markDirty(true);
    renderAll();
  }

  function renderProperties() {
    const panel = $("#sfbProperties");

    if (!panel) {
      return;
    }

    const section = getSection(selectedId);

    if (!section) {
      panel.innerHTML = `
        <div class="sfb-empty-canvas">
          Chọn một block trong canvas để chỉnh thông tin.
        </div>
      `;
      return;
    }

    panel.innerHTML = `
      <div class="sfb-selected-head">
        <div class="sfb-module-icon">
          <i class="${iconClass(section)}"></i>
        </div>

        <div class="sfb-selected-info">
          <p class="sfb-kicker">Selected block</p>
          <h4>${escapeHtml(section.title)}</h4>
          <p>${escapeHtml(section.id)}</p>
        </div>
      </div>

      <div class="sfb-field">
        <label class="sfb-label">Tên block trong admin</label>
        <input class="sfb-input" data-prop="title" value="${escapeAttr(section.title)}">
      </div>

      <div class="sfb-field">
        <label class="sfb-label">Mô tả nội bộ</label>
        <textarea class="sfb-textarea" data-prop="subtitle">${escapeHtml(section.subtitle || "")}</textarea>
      </div>

      <div class="sfb-field">
        <label class="sfb-label">Hiển thị block</label>
        <label class="sfb-switch">
          <input type="checkbox" data-prop-enabled ${section.enabled ? "checked" : ""}>
          <span></span>
        </label>
      </div>

      ${renderSettingFields(section)}

      <div class="sfb-prop-actions">
        <button type="button" class="sfb-btn sfb-btn-soft" data-prop-duplicate>
          <i class="fa-solid fa-copy"></i>
          Nhân bản
        </button>

        <button type="button" class="sfb-btn sfb-btn-danger" data-prop-delete>
          <i class="fa-solid fa-trash-can"></i>
          Xóa
        </button>
      </div>
    `;

    $$("[data-prop]", panel).forEach((input) => {
      input.addEventListener("input", () => {
        section[input.dataset.prop] = input.value;
        markDirty(true);
        syncLayoutInput();
        renderCanvas();
        renderPhone();
      });
    });

    const enabledInput = panel.querySelector("[data-prop-enabled]");

    if (enabledInput) {
      enabledInput.addEventListener("change", () => {
        section.enabled = enabledInput.checked;
        markDirty(true);
        renderAll();
      });
    }

    $$("[data-setting]", panel).forEach((input) => {
      input.addEventListener("input", () => updateSettingValue(section, input));
      input.addEventListener("change", () => updateSettingValue(section, input));
    });

    $$("[data-media-preview-source]", panel).forEach((input) => {
      renderInlinePreview(input.dataset.mediaPreviewSource, input.value);
    });

    $$("[data-upload-setting]", panel).forEach((button) => {
      button.addEventListener("click", () => {
        uploadTarget = {
          sectionId: section.id,
          settingKey: button.dataset.uploadSetting
        };

        const upload = $("#sfbPropertyUpload");

        if (upload) {
          upload.click();
        }
      });
    });

    const duplicateBtn = panel.querySelector("[data-prop-duplicate]");
    const deleteBtn = panel.querySelector("[data-prop-delete]");

    if (duplicateBtn) {
      duplicateBtn.addEventListener("click", () => duplicateSection(section.id));
    }

    if (deleteBtn) {
      deleteBtn.addEventListener("click", () => deleteSection(section.id));
    }
  }

  function textField(key, label, value, placeholder = "") {
    return `
      <div class="sfb-field">
        <label class="sfb-label">${escapeHtml(label)}</label>
        <input
          class="sfb-input"
          data-setting="${escapeAttr(key)}"
          value="${escapeAttr(value || "")}"
          placeholder="${escapeAttr(placeholder)}"
        >
      </div>
    `;
  }

  function textareaField(key, label, value, placeholder = "") {
    return `
      <div class="sfb-field">
        <label class="sfb-label">${escapeHtml(label)}</label>
        <textarea
          class="sfb-textarea"
          data-setting="${escapeAttr(key)}"
          placeholder="${escapeAttr(placeholder)}"
        >${escapeHtml(value || "")}</textarea>
      </div>
    `;
  }

  function numberField(key, label, value, min, max) {
    return `
      <div class="sfb-field">
        <label class="sfb-label">${escapeHtml(label)}</label>
        <input
          type="number"
          class="sfb-input"
          data-setting="${escapeAttr(key)}"
          value="${escapeAttr(value == null ? "" : value)}"
          min="${min}"
          max="${max}"
        >
      </div>
    `;
  }

  function selectField(key, label, value, options) {
    return `
      <div class="sfb-field">
        <label class="sfb-label">${escapeHtml(label)}</label>
        <select class="sfb-select" data-setting="${escapeAttr(key)}">
          ${options.map((option) => `
            <option value="${escapeAttr(option.value)}" ${String(value) === String(option.value) ? "selected" : ""}>
              ${escapeHtml(option.label)}
            </option>
          `).join("")}
        </select>
      </div>
    `;
  }

  function checkboxField(key, label, value) {
    return `
      <div class="sfb-field">
        <label class="sfb-label">${escapeHtml(label)}</label>
        <label class="sfb-switch">
          <input
            type="checkbox"
            data-setting="${escapeAttr(key)}"
            data-setting-type="boolean"
            ${value ? "checked" : ""}
          >
          <span></span>
        </label>
      </div>
    `;
  }

  function mediaField(key, label, value, placeholder = "Dán URL ảnh/video...") {
    return `
      <div class="sfb-field">
        <label class="sfb-label">${escapeHtml(label)}</label>

        <div class="sfb-media-row">
          <input
            class="sfb-input"
            data-setting="${escapeAttr(key)}"
            data-media-preview-source="${escapeAttr(key)}"
            value="${escapeAttr(value || "")}"
            placeholder="${escapeAttr(placeholder)}"
          >

          <button type="button" class="sfb-btn sfb-btn-soft" data-upload-setting="${escapeAttr(key)}">
            <i class="fa-solid fa-cloud-arrow-up"></i>
            Tải lên
          </button>
        </div>

        <div class="sfb-inline-preview" id="preview_${escapeAttr(key)}"></div>
      </div>
    `;
  }

  function renderSettingFields(section) {
    const s = section.settings || {};

    if (section.type === "hero_slider") {
      return [
        textField("heading", "Tiêu đề hero", s.heading, "New Collection"),
        textField("subheading", "Mô tả hero", s.subheading, "Khám phá phong cách mới"),
        mediaField("media_url", "Ảnh hoặc video hero", s.media_url, "URL ảnh/video hero..."),
        textField("button_text", "Chữ trên nút", s.button_text, "Mua ngay"),
        textField("link", "Link khi bấm nút", s.link, "/shop"),
        selectField("height", "Chiều cao", s.height, [
          { value: "small", label: "Nhỏ" },
          { value: "medium", label: "Vừa" },
          { value: "large", label: "Lớn" },
          { value: "full", label: "Toàn màn hình" }
        ]),
        selectField("align", "Căn nội dung", s.align, [
          { value: "left", label: "Trái" },
          { value: "center", label: "Giữa" },
          { value: "right", label: "Phải" }
        ]),
        selectField("overlay", "Lớp phủ ảnh", s.overlay, [
          { value: "none", label: "Không phủ" },
          { value: "light", label: "Nhẹ" },
          { value: "medium", label: "Vừa" },
          { value: "dark", label: "Đậm" }
        ])
      ].join("");
    }

    if (section.type === "product_grid") {
      return [
        textField("heading", "Tiêu đề section", s.heading, "Sản phẩm nổi bật"),
        selectField("source", "Nguồn sản phẩm", s.source, [
          { value: "featured", label: "Sản phẩm nổi bật" },
          { value: "latest", label: "Sản phẩm mới nhất" },
          { value: "best_seller", label: "Bán chạy" },
          { value: "discount", label: "Đang giảm giá" },
          { value: "manual", label: "Chọn thủ công bằng ID" }
        ]),
        textareaField("product_ids", "Product IDs thủ công", s.product_ids, "Mỗi ID cách nhau bằng dấu phẩy. Chỉ dùng khi source = manual."),
        numberField("limit", "Số sản phẩm", s.limit || 8, 1, 60),
        numberField("columns", "Số cột desktop", s.columns || 4, 1, 6),
        textField("link", "Link xem tất cả", s.link, "/shop"),
        checkboxField("show_price", "Hiển thị giá", s.show_price !== false),
        checkboxField("show_button", "Hiển thị nút mua", s.show_button !== false)
      ].join("");
    }

    if (section.type === "image_banner") {
      return [
        textField("heading", "Tên chiến dịch", s.heading, "Ưu đãi đặc biệt"),
        mediaField("media_url", "Ảnh banner", s.media_url, "URL ảnh banner..."),
        textField("link", "Link khi bấm banner", s.link, "/shop"),
        selectField("height", "Chiều cao", s.height, [
          { value: "small", label: "Nhỏ" },
          { value: "medium", label: "Vừa" },
          { value: "large", label: "Lớn" }
        ]),
        checkboxField("rounded", "Bo góc banner", s.rounded !== false)
      ].join("");
    }

    if (section.type === "split_banner") {
      return [
        textField("heading", "Tiêu đề nhóm", s.heading, "For Him & For Her"),
        textField("left_title", "Tiêu đề banner trái", s.left_title, "For Him"),
        mediaField("left_media_url", "Ảnh banner trái", s.left_media_url, "URL ảnh trái..."),
        textField("left_link", "Link banner trái", s.left_link, "/shop"),
        textField("right_title", "Tiêu đề banner phải", s.right_title, "For Her"),
        mediaField("right_media_url", "Ảnh banner phải", s.right_media_url, "URL ảnh phải..."),
        textField("right_link", "Link banner phải", s.right_link, "/shop")
      ].join("");
    }

    if (section.type === "category_grid") {
      return [
        textField("heading", "Tiêu đề section", s.heading, "Danh mục nổi bật"),
        numberField("limit", "Số danh mục", s.limit || 8, 1, 40),
        numberField("columns", "Số cột desktop", s.columns || 4, 1, 6),
        selectField("layout", "Kiểu hiển thị", s.layout, [
          { value: "grid", label: "Grid" },
          { value: "carousel", label: "Carousel" }
        ])
      ].join("");
    }

    if (section.type === "collection_grid") {
      return [
        textField("heading", "Tiêu đề section", s.heading, "Bộ sưu tập"),
        numberField("limit", "Số collection", s.limit || 6, 1, 30),
        numberField("columns", "Số cột desktop", s.columns || 3, 1, 6),
        selectField("layout", "Kiểu hiển thị", s.layout, [
          { value: "grid", label: "Grid" },
          { value: "carousel", label: "Carousel" },
          { value: "masonry", label: "Masonry" }
        ])
      ].join("");
    }

    if (section.type === "video_showcase") {
      return [
        textField("heading", "Tiêu đề video", s.heading, "Best Sellers"),
        textField("subheading", "Mô tả video", s.subheading, "Khám phá những thiết kế bán chạy"),
        mediaField("video_url", "URL video", s.video_url, "URL video .mp4/.webm..."),
        mediaField("poster_url", "Ảnh poster", s.poster_url, "URL ảnh poster..."),
        textField("link", "Link khi bấm", s.link, "/shop")
      ].join("");
    }

    if (section.type === "text_block") {
      return [
        textField("heading", "Tiêu đề", s.heading, "Câu chuyện thương hiệu"),
        textareaField("content", "Nội dung", s.content, "Nhập nội dung..."),
        selectField("align", "Căn nội dung", s.align, [
          { value: "left", label: "Trái" },
          { value: "center", label: "Giữa" },
          { value: "right", label: "Phải" }
        ]),
        selectField("max_width", "Độ rộng", s.max_width, [
          { value: "small", label: "Nhỏ" },
          { value: "medium", label: "Vừa" },
          { value: "large", label: "Rộng" },
          { value: "full", label: "Toàn chiều ngang" }
        ])
      ].join("");
    }

    if (section.type === "benefits") {
      return [
        textField("heading", "Tiêu đề", s.heading, "Vì sao chọn GUAMAISON"),
        selectField("style", "Kiểu hiển thị", s.style, [
          { value: "cards", label: "Cards" },
          { value: "icons", label: "Icons" },
          { value: "minimal", label: "Tối giản" }
        ])
      ].join("");
    }

    if (section.type === "cta") {
      return [
        textField("heading", "Tiêu đề CTA", s.heading, "Tham gia cộng đồng GUAMAISON"),
        textField("subheading", "Mô tả CTA", s.subheading, "Nhận ưu đãi mới nhất và bộ sưu tập độc quyền."),
        textField("button_text", "Chữ trên nút", s.button_text, "Đăng ký ngay"),
        textField("link", "Link CTA", s.link, "/auth/register")
      ].join("");
    }

    if (section.type === "spacer") {
      return numberField("height", "Chiều cao khoảng trắng px", s.height || 48, 8, 240);
    }

    return `
      <div class="sfb-alert">
        <i class="fa-solid fa-circle-info"></i>
        <div>Block này chưa có form cấu hình riêng.</div>
      </div>
    `;
  }

  function updateSettingValue(section, input) {
    section.settings = section.settings || {};

    let value;

    if (input.dataset.settingType === "boolean") {
      value = input.checked;
    } else if (input.type === "number") {
      value = Number(input.value || 0);
    } else {
      value = input.value;
    }

    section.settings[input.dataset.setting] = value;

    markDirty(true);
    syncLayoutInput();
    renderJsonPreview();
    renderPhone();

    if (input.dataset.mediaPreviewSource) {
      renderInlinePreview(input.dataset.mediaPreviewSource, input.value);
    }

    renderCanvas();
  }

  function renderInlinePreview(key, value) {
    const target = document.getElementById(`preview_${key}`);

    if (!target) {
      return;
    }

    const url = String(value || "").trim();

    if (!url) {
      target.innerHTML = `<div class="sfb-inline-preview-empty">Chưa có media</div>`;
      return;
    }

    const path = url.split("?")[0].toLowerCase();
    const isVideo = [".mp4", ".webm", ".mov"].some((ext) => path.endsWith(ext));

    target.innerHTML = isVideo
      ? `<video src="${escapeAttr(url)}" controls preload="metadata"></video>`
      : `<img src="${escapeAttr(url)}" alt="Media preview" loading="lazy">`;
  }

  function renderPhone() {
    const phone = $("#sfbPhonePreview");

    if (!phone) {
      return;
    }

    phone.innerHTML = "";

    if (!layout.length) {
      phone.innerHTML = `
        <div class="sfb-phone-block is-off">
          <i class="fa-solid fa-cubes"></i>
          <span>Chưa có block</span>
        </div>
      `;
      return;
    }

    layout.forEach((section, index) => {
      const node = document.createElement("div");
      node.className = "sfb-phone-block " + (section.enabled ? "" : "is-off");
      node.innerHTML = `
        <i class="${iconClass(section)}"></i>
        <span>${index + 1}. ${escapeHtml(sectionLabel(section))}</span>
      `;
      phone.appendChild(node);
    });
  }

  function layoutOutput() {
    return layout.map((section, index) => ({
      id: section.id,
      type: section.type,
      enabled: Boolean(section.enabled),
      title: section.title || "",
      subtitle: section.subtitle || "",
      icon: section.icon || "",
      sort_order: index,
      settings: section.settings || {}
    }));
  }

  function syncLayoutInput() {
    const input = $("#homepage_layout");
    const value = layoutOutput();

    if (input) {
      input.value = JSON.stringify(value);
    }

    renderStats();
    renderJsonPreview();

    return value;
  }

  function renderJsonPreview() {
    const preview = $("#sfbJsonPreview");

    if (preview) {
      preview.value = JSON.stringify(layoutOutput(), null, 2);
    }
  }

  function renderAll(withProperties = true) {
    renderModules();
    renderCanvas();
    renderPhone();
    syncLayoutInput();

    if (withProperties) {
      renderProperties();
    }
  }

  function switchPanel(name) {
    $$("[data-sfb-tab]").forEach((tab) => {
      tab.classList.toggle("is-active", tab.dataset.sfbTab === name);
    });

    $$("[data-sfb-panel]").forEach((panel) => {
      panel.hidden = panel.dataset.sfbPanel !== name;
    });
  }

  async function uploadFile(file) {
    if (!uploadTarget || !file) {
      return;
    }

    const section = getSection(uploadTarget.sectionId);

    if (!section) {
      return;
    }

    const key = uploadTarget.settingKey;
    section.settings = section.settings || {};

    const tempUrl = URL.createObjectURL(file);
    section.settings[key] = tempUrl;
    renderProperties();

    const fd = new FormData();
    fd.append("file", file);

    const csrf = document.querySelector('meta[name="csrf-token"]')?.content ||
      document.querySelector('input[name="csrf_token"]')?.value ||
      "";

    try {
      const res = await fetch("/admin/settings/upload", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrf,
          "X-CSRF-Token": csrf
        },
        body: fd
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.success) {
        throw new Error(data.message || data.error || "Upload thất bại.");
      }

      section.settings[key] = data.url || "";
      markDirty(true);
      renderAll();
      notify("Tải media thành công.");
    } catch (error) {
      section.settings[key] = "";
      renderAll();
      notify(error.message || "Không thể tải media.", true);
    } finally {
      URL.revokeObjectURL(tempUrl);
      uploadTarget = null;

      const input = $("#sfbPropertyUpload");

      if (input) {
        input.value = "";
      }
    }
  }

  function saveStorefront() {
    syncLayoutInput();

    if (window.Settings && typeof window.Settings.save === "function") {
      window.Settings.save("storefront");
      markDirty(false);
      return;
    }

    fallbackSaveStorefront();
  }

  async function fallbackSaveStorefront() {
    const form = $("#form-storefront");

    if (!form) {
      notify("Không tìm thấy form storefront.", true);
      return;
    }

    const fd = new FormData(form);
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content ||
      document.querySelector('input[name="csrf_token"]')?.value ||
      "";

    try {
      const res = await fetch("/admin/settings/update/storefront", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrf,
          "X-CSRF-Token": csrf
        },
        body: fd
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok || data.success === false) {
        throw new Error(data.message || data.error || "Không thể lưu cấu hình.");
      }

      markDirty(false);
      notify(data.message || "Đã lưu giao diện.");
    } catch (error) {
      notify(error.message || "Không thể lưu giao diện.", true);
    }
  }

  function bindEvents() {
    document.addEventListener("click", (event) => {
      const tab = event.target.closest("[data-sfb-tab]");

      if (tab) {
        switchPanel(tab.dataset.sfbTab);
        return;
      }

      const action = event.target.closest("[data-sfb-action]");

      if (!action) {
        return;
      }

      const name = action.dataset.sfbAction;

      if (name === "save") {
        saveStorefront();
      }

      if (name === "reset-layout") {
        const ok = confirm("Khôi phục bố cục mẫu? Media trong từng block sẽ trở về mặc định.");

        if (ok) {
          layout = makeDefaultLayout();
          selectedId = layout[0] ? layout[0].id : null;
          markDirty(true);
          renderAll();
          notify("Đã khôi phục bố cục mẫu. Bấm Lưu giao diện để ghi vào hệ thống.");
        }
      }

      if (name === "clear-layout") {
        const ok = confirm("Xóa toàn bộ block trong canvas?");

        if (ok) {
          layout = [];
          selectedId = null;
          markDirty(true);
          renderAll();
        }
      }

      if (name === "toggle-all") {
        const hasOff = layout.some((item) => !item.enabled);
        layout.forEach((item) => {
          item.enabled = hasOff;
        });
        markDirty(true);
        renderAll();
      }

      if (name === "jump-guide") {
        document.getElementById("sfbGuide")?.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
      }

      if (name === "toggle-guide") {
        const body = document.querySelector("[data-sfb-guide-body]");
        const hidden = body ? body.classList.toggle("sfb-hidden") : false;

        action.innerHTML = hidden
          ? '<i class="fa-solid fa-chevron-down"></i> Mở hướng dẫn'
          : '<i class="fa-solid fa-chevron-up"></i> Thu gọn';
      }
    });

    const uploadInput = $("#sfbPropertyUpload");

    if (uploadInput) {
      uploadInput.addEventListener("change", () => {
        const file = uploadInput.files && uploadInput.files[0];
        uploadFile(file);
      });
    }

    const topbarCheckbox = $("#topbar_active_checkbox");
    const topbarHidden = $("#topbar_active");

    if (topbarCheckbox && topbarHidden) {
      topbarCheckbox.addEventListener("change", () => {
        topbarHidden.value = topbarCheckbox.checked ? "true" : "false";
        markDirty(true);
      });
    }

    $("#topbar_text")?.addEventListener("input", () => markDirty(true));
    $("#login_image_url")?.addEventListener("input", () => markDirty(true));
    $("#register_image_url")?.addEventListener("input", () => markDirty(true));

    window.addEventListener("beforeunload", (event) => {
      if (!dirty) {
        return;
      }

      event.preventDefault();
      event.returnValue = "";
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!$("#sfbRoot")) {
      return;
    }

    if (!MODULES.length) {
      notify("Thiếu storefront-builder.config.js hoặc chưa khai báo modules.", true);
    }
function getJsonEditorValue() {
  const editor = $("#sfbJsonPreview");
  return editor ? editor.value.trim() : JSON.stringify(layoutOutput(), null, 2);
}

function setJsonState(status, text) {
  const wrap = $("#sfbJsonState");
  if (!wrap) return;

  const className = status === "valid"
    ? "is-valid"
    : status === "invalid"
      ? "is-invalid"
      : "";

  const icon = status === "valid"
    ? "fa-circle-check"
    : status === "invalid"
      ? "fa-triangle-exclamation"
      : "fa-circle-info";

  wrap.innerHTML = `
    <span class="${className}">
      <i class="fa-solid ${icon}"></i>
      ${escapeHtml(text)}
    </span>
  `;
}

function updateAdvancedStatsFromLayout() {
  const total = $("#sfbAdvancedTotal");
  const enabled = $("#sfbAdvancedEnabled");
  const disabled = $("#sfbAdvancedDisabled");
  const types = $("#sfbAdvancedTypes");

  const typeCount = new Set(layout.map((item) => item.type)).size;

  if (total) total.textContent = String(layout.length);
  if (enabled) enabled.textContent = String(layout.filter((item) => item.enabled).length);
  if (disabled) disabled.textContent = String(layout.filter((item) => !item.enabled).length);
  if (types) types.textContent = String(typeCount);
}

function validateAdvancedJson(showToast = true) {
  const health = $("#sfbJsonHealth");
  const raw = getJsonEditorValue();

  let parsed = null;
  const messages = [];

  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    setJsonState("invalid", "JSON lỗi");
    if (health) {
      health.innerHTML = `
        <div class="sfb-json-health-item is-error">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <div>
            <strong>JSON không hợp lệ</strong>
            <p>${escapeHtml(error.message)}</p>
          </div>
        </div>
      `;
    }
    if (showToast) notify("JSON không hợp lệ.", true);
    return false;
  }

  if (!Array.isArray(parsed)) {
    setJsonState("invalid", "Sai cấu trúc");
    if (health) {
      health.innerHTML = `
        <div class="sfb-json-health-item is-error">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <div>
            <strong>Dữ liệu phải là array</strong>
            <p>homepage_layout cần là một mảng các block.</p>
          </div>
        </div>
      `;
    }
    if (showToast) notify("homepage_layout phải là array.", true);
    return false;
  }

  parsed.forEach((block, index) => {
    if (!block.id) {
      messages.push({
        type: "error",
        title: `Block #${index + 1} thiếu id`,
        text: "Mỗi block nên có id riêng để builder nhận diện."
      });
    }

    if (!block.type) {
      messages.push({
        type: "error",
        title: `Block #${index + 1} thiếu type`,
        text: "Mỗi block cần có type để biết phải render bằng module nào."
      });
    } else if (!getModule(block.type)) {
      messages.push({
        type: "error",
        title: `Block #${index + 1} có type chưa hỗ trợ`,
        text: `Type "${block.type}" chưa được khai báo trong storefront-builder.config.js.`
      });
    }

    if (!block.settings || typeof block.settings !== "object" || Array.isArray(block.settings)) {
      messages.push({
        type: "error",
        title: `Block #${index + 1} settings không hợp lệ`,
        text: "settings cần là object."
      });
    }
  });

  if (!messages.length) {
    messages.push({
      type: "ok",
      title: "JSON hợp lệ",
      text: `Tìm thấy ${parsed.length} block. Có thể áp dụng hoặc lưu giao diện.`
    });
  }

  if (health) {
    health.innerHTML = messages.map((item) => `
      <div class="sfb-json-health-item ${item.type === "ok" ? "is-ok" : "is-error"}">
        <i class="fa-solid ${item.type === "ok" ? "fa-circle-check" : "fa-triangle-exclamation"}"></i>
        <div>
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.text)}</p>
        </div>
      </div>
    `).join("");
  }

  const hasError = messages.some((item) => item.type === "error");
  setJsonState(hasError ? "invalid" : "valid", hasError ? "Có lỗi" : "Hợp lệ");

  if (showToast) {
    notify(hasError ? "JSON có lỗi cần kiểm tra." : "JSON hợp lệ.", hasError);
  }

  return !hasError;
}

function formatAdvancedJson() {
  const editor = $("#sfbJsonPreview");
  if (!editor) return;

  try {
    const parsed = JSON.parse(editor.value || "[]");
    editor.value = JSON.stringify(parsed, null, 2);
    setJsonState("valid", "Đã format");
    notify("Đã format JSON.");
  } catch (error) {
    setJsonState("invalid", "JSON lỗi");
    notify(error.message || "Không thể format JSON.", true);
  }
}

async function copyAdvancedJson() {
  const value = getJsonEditorValue();

  try {
    await navigator.clipboard.writeText(value);
    notify("Đã copy JSON.");
  } catch (error) {
    notify("Trình duyệt không cho phép copy tự động. Hãy copy thủ công.", true);
  }
}

function downloadAdvancedJson() {
  const value = getJsonEditorValue();
  const blob = new Blob([value], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");

  const now = new Date();
  const stamp = now.toISOString().slice(0, 19).replace(/[:T]/g, "-");

  a.href = url;
  a.download = `storefront-homepage-layout-${stamp}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
  notify("Đã tải file JSON.");
}

function applyAdvancedJson() {
  const raw = getJsonEditorValue();

  let parsed = null;

  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    setJsonState("invalid", "JSON lỗi");
    notify(error.message || "JSON không hợp lệ.", true);
    return;
  }

  if (!Array.isArray(parsed)) {
    notify("JSON phải là array các block.", true);
    setJsonState("invalid", "Sai cấu trúc");
    return;
  }

  const normalized = parsed
    .map(normalizeSection)
    .filter(Boolean)
    .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));

  layout = normalized;
  selectedId = layout[0] ? layout[0].id : null;

  markDirty(true);
  renderAll();
  validateAdvancedJson(false);
  notify("Đã áp dụng JSON vào Builder. Bấm Lưu giao diện để ghi database.");
}

function importAdvancedJsonFile(file) {
  if (!file) return;

  const reader = new FileReader();

  reader.onload = () => {
    const editor = $("#sfbJsonPreview");
    if (editor) {
      editor.value = String(reader.result || "");
    }

    formatAdvancedJson();
    validateAdvancedJson(false);
    notify("Đã import file JSON. Kiểm tra rồi bấm Áp dụng JSON.");
  };

  reader.onerror = () => {
    notify("Không thể đọc file JSON.", true);
  };

  reader.readAsText(file);
}
    loadLayout();
    bindEvents();
    renderAll();
  });
})();