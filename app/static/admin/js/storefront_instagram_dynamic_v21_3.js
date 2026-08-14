(function () {
  "use strict";

  var root = document.querySelector("[data-media-studio]");
  var manager = root && root.querySelector("[data-instagram-manager]");
  if (!root || !manager || manager.dataset.ready === "1") return;
  manager.dataset.ready = "1";

  var MAX_ITEMS = 60;
  var IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".jfif", ".webp", ".gif", ".avif"];
  var VIDEO_EXTENSIONS = [".mp4", ".webm", ".mov"];
  var IMAGE_LIMIT = 4 * 1024 * 1024;
  var GIF_LIMIT = 10 * 1024 * 1024;
  var VIDEO_LIMIT = 20 * 1024 * 1024;
  var list = manager.querySelector("[data-instagram-manager-list]");
  var empty = manager.querySelector("[data-instagram-manager-empty]");
  var status = manager.querySelector("[data-instagram-manager-status]");
  var addButton = manager.querySelector("[data-instagram-add]");
  var items = [];
  var saving = false;
  var queuedSaveMessage = "";
  var draggedId = "";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return root.dataset.csrf || (meta ? meta.content : "") || "";
  }

  function cleanPath(value) {
    return String(value || "").trim().toLowerCase().split("?")[0].split("#")[0];
  }

  function hasExtension(path, extensions) {
    return extensions.some(function (extension) { return path.endsWith(extension); });
  }

  function mediaKind(value) {
    return hasExtension(cleanPath(value), VIDEO_EXTENSIONS) ? "video" : "image";
  }

  function uniqueId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return "ig-" + window.crypto.randomUUID();
    }
    return "ig-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
  }

  function isMediaUrl(value) {
    if (!value) return true;
    return value.startsWith("/static/") || /^https:\/\//i.test(value);
  }

  function isInstagramUrl(value) {
    if (!value) return true;
    try {
      var parsed = new URL(value);
      var host = parsed.hostname.toLowerCase();
      return parsed.protocol === "https:" &&
        !parsed.username && !parsed.password &&
        (!parsed.port || parsed.port === "443") &&
        (host === "instagram.com" || host.endsWith(".instagram.com"));
    } catch (_) {
      return false;
    }
  }

  function normalizeItem(raw, index, used) {
    raw = raw && typeof raw === "object" ? raw : {};
    var id = String(raw.id || "").trim();
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(id) || used.has(id)) id = uniqueId();
    used.add(id);
    return {
      id: id,
      media_url: String(raw.media_url || "").trim(),
      click_url: String(raw.click_url || "").trim(),
      position: index
    };
  }

  function initialItems() {
    var dataNode = manager.querySelector("[data-instagram-manager-data]");
    var payload = {};
    try { payload = JSON.parse(dataNode ? dataNode.textContent : "{}"); } catch (_) {}
    var source = Array.isArray(payload.items) && payload.items.length
      ? payload.items
      : (Array.isArray(payload.legacy_items) ? payload.legacy_items.filter(function (item) {
          return item && (item.media_url || item.click_url);
        }) : []);
    var used = new Set();
    return source.slice(0, MAX_ITEMS).map(function (item, index) {
      return normalizeItem(item, index, used);
    });
  }

  function setManagerStatus(message, state) {
    if (!status) return;
    status.textContent = message || "";
    status.className = "gm-ig-manager__status" + (state ? " is-" + state : "");
  }

  function notify(message, type) {
    var stack = root.querySelector("[data-media-snackbar-stack]");
    if (!stack) return;
    var snack = document.createElement("div");
    snack.className = "gm-media-snack is-" + (type || "info");
    snack.setAttribute("role", type === "error" ? "alert" : "status");
    var icon = document.createElement("i");
    icon.className = "fa-solid " + (type === "success" ? "fa-circle-check" : "fa-circle-exclamation");
    icon.setAttribute("aria-hidden", "true");
    var text = document.createElement("span");
    text.textContent = message;
    var close = document.createElement("button");
    close.type = "button";
    close.setAttribute("aria-label", "Đóng thông báo");
    close.innerHTML = '<i class="fa-solid fa-xmark" aria-hidden="true"></i>';
    close.addEventListener("click", function () { snack.remove(); });
    snack.append(icon, text, close);
    stack.prepend(snack);
    window.setTimeout(function () { if (snack.isConnected) snack.remove(); }, type === "error" ? 6500 : 4200);
  }

  function updateCounts() {
    var social = root.querySelector('[data-media-filter="social"] b');
    var all = root.querySelector('[data-media-filter="all"] b');
    if (social) social.textContent = String(items.length);
    if (all) all.textContent = String(7 + items.length);
    if (addButton) addButton.disabled = items.length >= MAX_ITEMS || saving;
  }

  function setPreview(stage, item) {
    stage.replaceChildren();
    if (!item.media_url) {
      var placeholder = document.createElement("div");
      placeholder.className = "gm-ig-card__empty";
      placeholder.innerHTML = '<i class="fa-regular fa-image" aria-hidden="true"></i><strong>Chưa có media</strong><span>Chọn tệp hoặc dán URL</span>';
      stage.appendChild(placeholder);
      return;
    }
    var kind = mediaKind(item.media_url);
    var media = kind === "video" ? document.createElement("video") : document.createElement("img");
    if (kind === "video") {
      media.controls = true;
      media.muted = true;
      media.loop = true;
      media.playsInline = true;
      media.preload = "metadata";
    } else {
      media.alt = "Xem trước Instagram media";
      media.loading = "lazy";
      media.decoding = "async";
    }
    media.src = item.media_url;
    media.addEventListener("error", function () {
      stage.replaceChildren();
      var failed = document.createElement("div");
      failed.className = "gm-ig-card__empty";
      failed.innerHTML = '<i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i><strong>Không thể xem trước</strong><span>Kiểm tra URL hoặc định dạng</span>';
      stage.appendChild(failed);
    }, { once: true });
    var type = document.createElement("span");
    type.className = "gm-ig-card__type";
    type.textContent = cleanPath(item.media_url).endsWith(".gif") ? "GIF" : kind;
    stage.append(media, type);
  }

  function itemById(id) {
    return items.find(function (item) { return item.id === id; });
  }

  function moveItem(id, offset) {
    var from = items.findIndex(function (item) { return item.id === id; });
    var to = Math.max(0, Math.min(items.length - 1, from + offset));
    if (from < 0 || from === to) return;
    var moved = items.splice(from, 1)[0];
    items.splice(to, 0, moved);
    render();
    saveAll("Đã thay đổi thứ tự Instagram.");
  }

  function validateFile(file) {
    if (!file || !file.size) throw new Error("Tệp rỗng hoặc không đọc được.");
    var path = cleanPath(file.name);
    var isVideo = hasExtension(path, VIDEO_EXTENSIONS);
    var isImage = hasExtension(path, IMAGE_EXTENSIONS);
    if (!isVideo && !isImage) throw new Error("Chỉ hỗ trợ JPG, PNG, WebP, AVIF, GIF, MP4, WebM hoặc MOV.");
    var limit = isVideo ? VIDEO_LIMIT : (path.endsWith(".gif") ? GIF_LIMIT : IMAGE_LIMIT);
    if (file.size > limit) {
      throw new Error("Tệp vượt giới hạn " + (isVideo ? "20MB" : (path.endsWith(".gif") ? "10MB" : "4MB")) + ".");
    }
  }

  async function uploadItem(item, file, note) {
    try { validateFile(file); } catch (error) {
      note.textContent = error.message;
      notify(error.message, "error");
      return;
    }
    note.textContent = "Đang tải media…";
    var formData = new FormData();
    formData.append("file", file);
    formData.append("slot_key", "instagram_dynamic_" + item.id);
    try {
      var response = await fetch(root.dataset.uploadUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": csrfToken(),
          "X-Requested-With": "XMLHttpRequest"
        },
        body: formData
      });
      var data = await response.json().catch(function () { return {}; });
      if (!response.ok || !data.ok || !data.url) throw new Error(data.message || "Không thể tải media.");
      item.media_url = String(data.url);
      render();
      await saveAll("Đã tải lên và lưu media Instagram.");
    } catch (error) {
      note.textContent = error.message || "Không thể tải media.";
      notify(note.textContent, "error");
    }
  }

  function buildCard(item, index) {
    var card = document.createElement("article");
    card.className = "gm-ig-card";
    card.dataset.itemId = item.id;
    card.draggable = false;
    card.innerHTML = [
      '<header class="gm-ig-card__bar">',
        '<div class="gm-ig-card__title"><button type="button" class="gm-ig-card__drag" data-item-drag aria-label="Kéo để đổi vị trí"><i class="fa-solid fa-grip-vertical" aria-hidden="true"></i></button><span class="gm-ig-card__order"></span><strong>Instagram media</strong></div>',
        '<div class="gm-ig-card__actions">',
          '<button type="button" data-item-up title="Đưa lên trước"><i class="fa-solid fa-arrow-left" aria-hidden="true"></i></button>',
          '<button type="button" data-item-down title="Đưa xuống sau"><i class="fa-solid fa-arrow-right" aria-hidden="true"></i></button>',
          '<button type="button" data-item-delete title="Xóa mục"><i class="fa-regular fa-trash-can" aria-hidden="true"></i></button>',
        '</div>',
      '</header>',
      '<div class="gm-ig-card__stage" data-item-stage></div>',
      '<div class="gm-ig-card__body">',
        '<div class="gm-ig-card__upload"><button type="button" data-item-choose><i class="fa-solid fa-cloud-arrow-up" aria-hidden="true"></i> Chọn ảnh/GIF/video</button><input type="file" hidden data-item-file accept="image/png,image/jpeg,image/webp,image/gif,image/avif,video/mp4,video/webm,video/quicktime"></div>',
        '<label class="gm-ig-field"><span>URL media bên ngoài</span><input type="url" data-item-media-url placeholder="https://...jpg hoặc ...mp4"></label>',
        '<label class="gm-ig-field"><span>Link Instagram khi khách bấm</span><input type="url" data-item-click-url placeholder="https://www.instagram.com/p/..."></label>',
        '<button type="button" class="gm-ig-card__save" data-item-save>Lưu nội dung</button>',
        '<small class="gm-ig-card__note" data-item-note></small>',
      '</div>'
    ].join("");

    card.querySelector(".gm-ig-card__order").textContent = String(index + 1);
    var stage = card.querySelector("[data-item-stage]");
    var mediaInput = card.querySelector("[data-item-media-url]");
    var clickInput = card.querySelector("[data-item-click-url]");
    var fileInput = card.querySelector("[data-item-file]");
    var note = card.querySelector("[data-item-note]");
    mediaInput.value = item.media_url;
    clickInput.value = item.click_url;
    setPreview(stage, item);

    card.querySelector("[data-item-choose]").addEventListener("click", function () { fileInput.click(); });
    fileInput.addEventListener("change", function () {
      var file = fileInput.files && fileInput.files[0];
      if (file) uploadItem(item, file, note);
      fileInput.value = "";
    });
    card.querySelector("[data-item-save]").addEventListener("click", function () {
      var mediaUrl = String(mediaInput.value || "").trim();
      var clickUrl = String(clickInput.value || "").trim();
      if (!isMediaUrl(mediaUrl)) {
        note.textContent = "URL media phải bắt đầu bằng https:// hoặc /static/.";
        mediaInput.focus();
        return;
      }
      if (!isInstagramUrl(clickUrl)) {
        note.textContent = "Link bấm ảnh phải là HTTPS thuộc instagram.com.";
        clickInput.focus();
        return;
      }
      item.media_url = mediaUrl;
      item.click_url = clickUrl;
      render();
      saveAll("Đã lưu nội dung Instagram.");
    });
    card.querySelector("[data-item-delete]").addEventListener("click", function () {
      if (!window.confirm("Xóa mục Instagram này? Media đã tải trên Storage sẽ không bị xóa vật lý.")) return;
      items = items.filter(function (candidate) { return candidate.id !== item.id; });
      render();
      saveAll("Đã xóa mục Instagram.");
    });
    card.querySelector("[data-item-up]").addEventListener("click", function () { moveItem(item.id, -1); });
    card.querySelector("[data-item-down]").addEventListener("click", function () { moveItem(item.id, 1); });

    var dragHandle = card.querySelector("[data-item-drag]");
    dragHandle.addEventListener("mousedown", function () {
      card.dataset.dragArmed = "1";
      card.draggable = true;
    });
    dragHandle.addEventListener("mouseup", function () {
      if (!card.classList.contains("is-dragging")) {
        card.draggable = false;
        delete card.dataset.dragArmed;
      }
    });

    card.addEventListener("dragstart", function (event) {
      if (card.dataset.dragArmed !== "1") {
        event.preventDefault();
        return;
      }
      draggedId = item.id;
      card.classList.add("is-dragging");
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", item.id);
      }
    });
    card.addEventListener("dragend", function () {
      draggedId = "";
      card.draggable = false;
      delete card.dataset.dragArmed;
      list.querySelectorAll(".gm-ig-card").forEach(function (node) {
        node.classList.remove("is-dragging", "is-drop-target");
      });
    });
    card.addEventListener("dragover", function (event) {
      if (!draggedId || draggedId === item.id) return;
      event.preventDefault();
      card.classList.add("is-drop-target");
    });
    card.addEventListener("dragleave", function () { card.classList.remove("is-drop-target"); });
    card.addEventListener("drop", function (event) {
      event.preventDefault();
      card.classList.remove("is-drop-target");
      var sourceId = draggedId || (event.dataTransfer ? event.dataTransfer.getData("text/plain") : "");
      var from = items.findIndex(function (candidate) { return candidate.id === sourceId; });
      var to = items.findIndex(function (candidate) { return candidate.id === item.id; });
      if (from < 0 || to < 0 || from === to) return;
      var moved = items.splice(from, 1)[0];
      if (from < to) to -= 1;
      var rect = card.getBoundingClientRect();
      var after = event.clientY > rect.top + rect.height / 2 || event.clientX > rect.left + rect.width / 2;
      items.splice(to + (after ? 1 : 0), 0, moved);
      draggedId = "";
      render();
      saveAll("Đã lưu thứ tự Instagram mới.");
    });
    return card;
  }

  function render() {
    list.replaceChildren();
    items.forEach(function (item, index) {
      item.position = index;
      list.appendChild(buildCard(item, index));
    });
    empty.hidden = items.length !== 0;
    list.hidden = items.length === 0;
    updateCounts();
  }

  function legacyClears() {
    var changes = {};
    for (var index = 1; index <= 6; index += 1) {
      changes["instagram_media_" + index + "_url"] = "";
      changes["instagram_link_" + index + "_url"] = "";
    }
    return changes;
  }

  async function saveAll(successMessage) {
    if (saving) {
      queuedSaveMessage = successMessage || "Đã lưu thay đổi Instagram mới nhất.";
      return;
    }
    saving = true;
    updateCounts();
    setManagerStatus("Đang lưu thư viện Instagram…", "saving");
    try {
      var changes = legacyClears();
      changes.instagram_media_items = items.map(function (item, index) {
        return { id: item.id, media_url: item.media_url, click_url: item.click_url, position: index };
      });
      var response = await fetch(root.dataset.saveUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({ changes: changes })
      });
      var data = await response.json().catch(function () { return {}; });
      if (!response.ok || !data.ok) throw new Error(data.message || "Không thể lưu thư viện Instagram.");
      setManagerStatus(successMessage || "Đã lưu thư viện Instagram.", "success");
      notify(successMessage || "Đã lưu thư viện Instagram.", "success");
    } catch (error) {
      setManagerStatus(error.message || "Không thể lưu thư viện Instagram.", "error");
      notify(error.message || "Không thể lưu thư viện Instagram.", "error");
    } finally {
      saving = false;
      updateCounts();
      if (queuedSaveMessage) {
        var nextMessage = queuedSaveMessage;
        queuedSaveMessage = "";
        saveAll(nextMessage);
      }
    }
  }

  function syncFilter() {
    var active = root.querySelector("[data-media-filter].is-active");
    var group = active ? active.dataset.mediaFilter : "home";
    manager.hidden = group !== "social" && group !== "all";
  }

  addButton.addEventListener("click", function () {
    if (items.length >= MAX_ITEMS) {
      notify("Thư viện đã đạt giới hạn an toàn " + MAX_ITEMS + " mục.", "error");
      return;
    }
    items.push({ id: uniqueId(), media_url: "", click_url: "", position: items.length });
    render();
    saveAll("Đã thêm mục Instagram mới.");
    window.setTimeout(function () {
      var cards = list.querySelectorAll(".gm-ig-card");
      var card = cards[cards.length - 1];
      if (card) card.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 30);
  });

  root.querySelectorAll("[data-media-filter]").forEach(function (button) {
    button.addEventListener("click", function () { window.setTimeout(syncFilter, 0); });
  });

  items = initialItems();
  render();
  syncFilter();
})();
