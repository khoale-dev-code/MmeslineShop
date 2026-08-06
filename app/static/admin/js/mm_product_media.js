(function () {
  "use strict";

  const SELECTOR = {
    root: "#mmProductMedia",
    dropzone: "[data-media-dropzone]",
    input: "#mmMediaFiles",
    pick: "[data-media-pick]",
    grid: "#mmMediaGrid",
    template: "#mmMediaCardTemplate",
    empty: "[data-media-empty]",
    synced: "#imagesSynced",
    order: "#mmMediaOrder",
    thumbnailUrl: "#mmThumbnailUrl",
    urlInput: "#mmMediaUrlInput",
    urlAdd: "[data-media-url-add]",
    clearNew: "[data-media-clear-new]"
  };

  const ACCEPTED_TYPES = new Set([
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/mp4",
    "video/webm"
  ]);

  const IMAGE_EXT = [".jpg", ".jpeg", ".png", ".webp", ".gif"];
  const VIDEO_EXT = [".mp4", ".webm", ".mov"];

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  let dragCard = null;
  let selectedFiles = [];
  let objectUrls = [];

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function normalizeUrl(value) {
    const url = String(value || "").trim();

    if (!url) return "";

    try {
      const parsed = new URL(url);
      if (!["http:", "https:"].includes(parsed.protocol)) return "";
      return parsed.toString();
    } catch {
      return "";
    }
  }

  function getPath(url) {
    try {
      return new URL(url).pathname.toLowerCase();
    } catch {
      return String(url || "").toLowerCase();
    }
  }

  function urlKind(url) {
    const path = getPath(url);

    if (VIDEO_EXT.some((ext) => path.endsWith(ext))) return "video";
    if (path.endsWith(".gif")) return "gif";
    if (path.endsWith(".webp")) return "webp";

    return "image";
  }

  function isMediaUrl(url) {
    const path = getPath(url);
    return IMAGE_EXT.concat(VIDEO_EXT).some((ext) => path.endsWith(ext));
  }

  function isAccepted(file) {
    return ACCEPTED_TYPES.has(file.type);
  }

  function fileKind(file) {
    if (file.type.startsWith("video/")) return "video";
    if (file.type === "image/gif") return "gif";
    if (file.type === "image/webp") return "webp";
    return "image";
  }

  function kindLabel(kind) {
    if (kind === "video") return "Video";
    if (kind === "gif") return "GIF";
    if (kind === "webp") return "WEBP";
    return "Image";
  }

  function getGrid() {
    return $(SELECTOR.grid);
  }

  function setSynced() {
    const synced = $(SELECTOR.synced);
    if (synced) synced.value = "1";
  }

  function createObjectUrl(file) {
    const url = URL.createObjectURL(file);
    objectUrls.push(url);
    return url;
  }

  function clearObjectUrls() {
    objectUrls.forEach((url) => URL.revokeObjectURL(url));
    objectUrls = [];
  }

  function addFiles(files) {
    const validFiles = Array.from(files || []).filter(isAccepted);
    if (!validFiles.length) return;

    selectedFiles = selectedFiles.concat(validFiles);

    syncFileInput();
    renderNewFiles(validFiles);
    refreshOrder();
  }

  function syncFileInput() {
    const input = $(SELECTOR.input);
    if (!input || !window.DataTransfer) return;

    const dt = new DataTransfer();
    selectedFiles.forEach((file) => dt.items.add(file));
    input.files = dt.files;
  }

  function getTemplateCard() {
    const template = $(SELECTOR.template);
    if (!template) return null;

    return template.content.firstElementChild.cloneNode(true);
  }

  function renderPreview(preview, src, kind, altText) {
    if (!preview) return;

    if (kind === "video") {
      preview.innerHTML = `
        <video src="${escapeHtml(src)}" muted playsinline preload="metadata"></video>
        <span class="mm-media-type-badge">${kindLabel(kind)}</span>
      `;
      return;
    }

    preview.innerHTML = `
      <img src="${escapeHtml(src)}" alt="${escapeHtml(altText || "Product media")}" loading="eager" decoding="async">
      <span class="mm-media-type-badge">${kindLabel(kind)}</span>
    `;
  }

  function appendUrlHidden(card, url) {
    let input = $("[data-media-url]", card);

    if (!input) {
      input = document.createElement("input");
      input.type = "hidden";
      input.name = "image_urls";
      input.setAttribute("data-media-url", "1");
      card.appendChild(input);
    }

    input.value = url;
  }

  function renderNewFiles(files) {
    const grid = getGrid();
    if (!grid) return;

    files.forEach((file) => {
      const card = getTemplateCard();
      if (!card) return;

      const preview = $("[data-media-preview]", card);
      const kind = fileKind(file);
      const url = createObjectUrl(file);

      card.dataset.mediaKind = kind;
      card.dataset.fileName = file.name;
      card.dataset.existing = "0";
      card.dataset.source = "file";

      renderPreview(preview, url, kind, file.name);

      grid.appendChild(card);
    });
  }

  function addUrlMedia(rawUrl) {
    const url = normalizeUrl(rawUrl);

    if (!url) {
      showUrlInputError("Vui lòng dán URL hợp lệ bắt đầu bằng http:// hoặc https://");
      return false;
    }

    if (!isMediaUrl(url)) {
      showUrlInputError("URL nên kết thúc bằng .jpg, .png, .webp, .gif, .mp4 hoặc .webm");
      return false;
    }

    const exists = $$("[data-media-url]", getGrid()).some((input) => input.value === url);

    if (exists) {
      showUrlInputError("Link này đã có trong danh sách media.");
      return false;
    }

    const grid = getGrid();
    const card = getTemplateCard();

    if (!grid || !card) return false;

    const kind = urlKind(url);
    const preview = $("[data-media-preview]", card);

    card.dataset.mediaKind = kind;
    card.dataset.existing = "1";
    card.dataset.source = "url";

    renderPreview(preview, url, kind, url);
    appendUrlHidden(card, url);

    grid.appendChild(card);

    setSynced();
    refreshOrder();
    clearUrlInputError();

    return true;
  }

  function showUrlInputError(message) {
    const input = $(SELECTOR.urlInput);
    if (!input) return;

    input.classList.add("is-invalid");
    input.title = message || "";
    input.focus();

    let msg = document.getElementById("mmMediaUrlMessage");

    if (!msg) {
      msg = document.createElement("p");
      msg.id = "mmMediaUrlMessage";
      msg.className = "mm-help";
      msg.style.color = "#b91c1c";
      input.closest(".mm-field-block")?.appendChild(msg);
    }

    msg.textContent = message || "";
  }

  function clearUrlInputError() {
    const input = $(SELECTOR.urlInput);
    const msg = document.getElementById("mmMediaUrlMessage");

    if (input) {
      input.classList.remove("is-invalid");
      input.title = "";
    }

    if (msg) msg.textContent = "";
  }

  function handleAddUrl() {
    const input = $(SELECTOR.urlInput);
    if (!input) return;

    const ok = addUrlMedia(input.value);

    if (ok) {
      input.value = "";
      input.focus();
    }
  }

  function askRemoval(options) {
    if (window.GuaAdminDelete && typeof window.GuaAdminDelete.confirm === "function") {
      return window.GuaAdminDelete.confirm(options);
    }
    return Promise.resolve(window.confirm(options.message || "Bạn có chắc muốn xóa ảnh?"));
  }

  async function removeCard(card) {
    if (!card) return;

    const source = card.dataset.source === "file" ? "ảnh mới chọn" : "ảnh sản phẩm";
    const ok = await askRemoval({
      title: "Xóa hình ảnh",
      message: `Bạn có muốn xóa ${source} này?`,
      detail: card.dataset.source === "file"
        ? "Ảnh chưa tải lên sẽ được loại khỏi biểu mẫu."
        : "Ảnh đã lưu sẽ bị gỡ khỏi sản phẩm sau khi bạn bấm Cập nhật.",
      confirmText: "Xóa ảnh",
      tone: "danger"
    });
    if (!ok) return;

    const fileName = card.dataset.fileName;

    if (card.dataset.source === "file" && fileName) {
      const removeIndex = selectedFiles.findIndex((file) => file.name === fileName);

      if (removeIndex >= 0) {
        selectedFiles.splice(removeIndex, 1);
        syncFileInput();
      }
    }

    card.remove();
    setSynced();
    refreshOrder();
  }

  async function clearNewFiles() {
    const count = $$('[data-media-card][data-source="file"]', getGrid()).length;
    if (!count) return;
    const ok = await askRemoval({
      title: "Xóa ảnh mới",
      message: `Bạn có muốn loại bỏ cả ${count} ảnh mới đã chọn?`,
      detail: "Các ảnh đã lưu trước đó không bị ảnh hưởng.",
      confirmText: "Xóa ảnh mới",
      tone: "danger"
    });
    if (!ok) return;
    selectedFiles = [];
    syncFileInput();

    $$('[data-media-card][data-source="file"]', getGrid()).forEach((card) => card.remove());

    clearObjectUrls();
    refreshOrder();
  }

  function refreshOrder() {
    const grid = getGrid();
    if (!grid) return;

    const cards = $$("[data-media-card]", grid);
    const order = [];

    cards.forEach((card, index) => {
      const orderEl = $("[data-media-order]", card);
      if (orderEl) orderEl.textContent = String(index + 1);

      const urlInput = $("[data-media-url]", card);
      if (urlInput && urlInput.value) {
        order.push(urlInput.value);
      }
    });

    const empty = $(SELECTOR.empty);
    if (empty) empty.classList.toggle("is-visible", cards.length === 0);

    const orderInput = $(SELECTOR.order);
    if (orderInput) orderInput.value = order.join("\n");

    syncThumbnailFromFirst();
  }

  function syncThumbnailFromFirst() {
    const thumbnail = $(SELECTOR.thumbnailUrl);
    if (!thumbnail) return;

    const firstUrl = $('[data-media-card] [data-media-url]', getGrid());

    if (firstUrl && firstUrl.value) {
      thumbnail.value = firstUrl.value;
      return;
    }

    if (!$$("[data-media-card]", getGrid()).length) {
      thumbnail.value = "";
    }
  }

  function getInsertAfterElement(container, y) {
    const elements = $$("[data-media-card]:not(.is-dragging)", container);

    return elements.reduce((closest, child) => {
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;

      if (offset < 0 && offset > closest.offset) {
        return {
          offset,
          element: child
        };
      }

      return closest;
    }, {
      offset: Number.NEGATIVE_INFINITY,
      element: null
    }).element;
  }

  function bindDragSorting() {
    const grid = getGrid();
    if (!grid) return;

    grid.addEventListener("dragstart", (event) => {
      const card = event.target.closest("[data-media-card]");
      if (!card) return;

      dragCard = card;
      card.classList.add("is-dragging");

      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
      }
    });

    grid.addEventListener("dragend", () => {
      if (dragCard) {
        dragCard.classList.remove("is-dragging");
      }

      dragCard = null;
      refreshOrder();
      setSynced();
    });

    grid.addEventListener("dragover", (event) => {
      event.preventDefault();

      if (!dragCard) return;

      const afterElement = getInsertAfterElement(grid, event.clientY);

      if (afterElement == null) {
        grid.appendChild(dragCard);
      } else {
        grid.insertBefore(dragCard, afterElement);
      }
    });
  }

  function bindDropzone() {
    const root = $(SELECTOR.root);
    const dropzone = $(SELECTOR.dropzone);
    const input = $(SELECTOR.input);

    if (!root || !dropzone || !input) return;

    dropzone.addEventListener("click", (event) => {
      if (event.target.closest(SELECTOR.pick)) return;
      input.click();
    });

    dropzone.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        input.click();
      }
    });

    root.addEventListener("click", async (event) => {
      if (event.target.closest(SELECTOR.pick)) {
        event.preventDefault();
        input.click();
        return;
      }

      if (event.target.closest(SELECTOR.urlAdd)) {
        event.preventDefault();
        handleAddUrl();
        return;
      }

      const removeBtn = event.target.closest("[data-media-remove]");
      if (removeBtn) {
        event.preventDefault();
        await removeCard(removeBtn.closest("[data-media-card]"));
        return;
      }

      if (event.target.closest(SELECTOR.clearNew)) {
        event.preventDefault();
        await clearNewFiles();
      }
    });

    const urlInput = $(SELECTOR.urlInput);

    if (urlInput) {
      urlInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          handleAddUrl();
        }
      });

      urlInput.addEventListener("paste", () => {
        window.setTimeout(() => {
          const value = urlInput.value.trim();
          if (isMediaUrl(value)) {
            handleAddUrl();
          }
        }, 60);
      });

      urlInput.addEventListener("input", clearUrlInputError);
    }

    input.addEventListener("change", () => {
      addFiles(input.files);
    });

    ["dragenter", "dragover"].forEach((name) => {
      dropzone.addEventListener(name, (event) => {
        event.preventDefault();
        dropzone.classList.add("is-dragging");
      });
    });

    ["dragleave", "drop"].forEach((name) => {
      dropzone.addEventListener(name, (event) => {
        event.preventDefault();
        dropzone.classList.remove("is-dragging");
      });
    });

    dropzone.addEventListener("drop", (event) => {
      addFiles(event.dataTransfer ? event.dataTransfer.files : []);
    });
  }

  function bindFormSubmit() {
    const form = document.getElementById("productForm");
    if (!form || form.dataset.mmMediaBound === "1") return;

    form.dataset.mmMediaBound = "1";
    form.addEventListener("submit", () => {
      refreshOrder();
      syncFileInput();
    });
  }

  function init() {
    if (!$(SELECTOR.root)) return;

    bindDropzone();
    bindDragSorting();
    bindFormSubmit();
    refreshOrder();
  }

  document.addEventListener("DOMContentLoaded", init);

  window.MM = window.MM || {};
  window.MM.ProductMedia = {
    refreshOrder,
    clearNewFiles,
    addUrlMedia
  };
})();