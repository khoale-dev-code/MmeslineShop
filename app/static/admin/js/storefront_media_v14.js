(function () {
  "use strict";

  var root = document.querySelector("[data-media-studio]");
  if (!root || root.dataset.ready === "1") return;
  root.dataset.ready = "1";

  var IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".jfif", ".webp", ".gif", ".avif"];
  var VIDEO_EXTENSIONS = [".mp4", ".webm", ".mov"];
  var IMAGE_LIMIT = 4 * 1024 * 1024;
  var VIDEO_LIMIT = 20 * 1024 * 1024;
  var IMAGE_SOURCE_LIMIT = 30 * 1024 * 1024;

  var cards = Array.prototype.slice.call(root.querySelectorAll("[data-media-card]"));
  var dirty = new Set();
  var original = new Map();
  var current = new Map();
  var uploadCount = 0;
  var pendingSaves = 0;
  var savingKeys = new Set();
  var saveQueue = Promise.resolve();

  function notify(message, type) {
    type = type === "danger" ? "error" : (type || "info");
    var stack = root.querySelector("[data-media-snackbar-stack]");
    if (stack) {
      var snack = document.createElement("div");
      snack.className = "gm-media-snack is-" + type;
      snack.setAttribute("role", type === "error" ? "alert" : "status");

      var icon = document.createElement("i");
      icon.className = "fa-solid " + (
        type === "success" ? "fa-circle-check" :
        type === "error" || type === "danger" ? "fa-circle-exclamation" :
        "fa-circle-info"
      );
      icon.setAttribute("aria-hidden", "true");

      var textNode = document.createElement("span");
      textNode.textContent = String(message || "");
      var close = document.createElement("button");
      close.type = "button";
      close.setAttribute("aria-label", "Đóng thông báo");
      close.innerHTML = '<i class="fa-solid fa-xmark" aria-hidden="true"></i>';

      function dismiss() {
        if (!snack.isConnected || snack.classList.contains("is-leaving")) return;
        snack.classList.add("is-leaving");
        window.setTimeout(function () { snack.remove(); }, 180);
      }
      close.addEventListener("click", dismiss);
      snack.append(icon, textNode, close);
      stack.prepend(snack);
      while (stack.children.length > 3) stack.lastElementChild.remove();
      window.setTimeout(dismiss, type === "error" ? 6500 : 4200);
      return;
    }
    if (window.GUA && typeof window.GUA.snackbar === "function") {
      window.GUA.snackbar(message, type);
      return;
    }
    if (window.GUA && typeof window.GUA.toast === "function") {
      window.GUA.toast(message, type);
      return;
    }
    window.alert(message);
  }

  function cleanPath(value) {
    return String(value || "").trim().toLowerCase().split("?")[0].split("#")[0];
  }

  function hasExtension(path, list) {
    return list.some(function (extension) { return path.endsWith(extension); });
  }

  function mediaKind(url, mime) {
    if (String(mime || "").startsWith("video/")) return "video";
    if (String(mime || "").startsWith("image/")) return "image";
    return hasExtension(cleanPath(url), VIDEO_EXTENSIONS) ? "video" : "image";
  }

  function csrfToken() {
    return root.dataset.csrf || document.querySelector('meta[name="csrf-token"]')?.content || "";
  }

  function revokeCardBlob(card) {
    var previous = card.dataset.blobUrl || "";
    if (previous.indexOf("blob:") === 0) {
      try { URL.revokeObjectURL(previous); } catch (_) {}
    }
    delete card.dataset.blobUrl;
  }

  function emptyNode(card) {
    var box = document.createElement("div");
    box.className = "gm-media-empty";
    box.dataset.mediaEmpty = "";
    var icon = document.createElement("i");
    icon.className = "fa-regular fa-image";
    icon.setAttribute("aria-hidden", "true");
    var strong = document.createElement("strong");
    strong.textContent = "Thả ảnh vào đây";
    var span = document.createElement("span");
    span.textContent = "hoặc chạm để chọn tệp";
    box.append(icon, strong, span);
    return box;
  }

  function setStatus(card, label) {
    var status = card.querySelector("[data-media-status] b");
    if (status) status.textContent = label;
  }

  function setMeta(card, label) {
    var meta = card.querySelector("[data-media-meta]");
    if (meta) meta.textContent = label || "Xem đầy đủ, không cắt ảnh";
  }

  function setPreview(card, url, kind, isBlob) {
    var stage = card.querySelector("[data-media-stage]");
    if (!stage) return;
    if (!isBlob) revokeCardBlob(card);
    stage.replaceChildren();
    var finalUrl = String(url || "").trim();
    card.classList.toggle("has-media", Boolean(finalUrl));
    var remove = card.querySelector("[data-media-remove]");
    if (remove) remove.disabled = !finalUrl;

    if (!finalUrl) {
      stage.appendChild(emptyNode(card));
      setStatus(card, dirty.has(card.dataset.mediaKey) ? "Sẽ gỡ khi lưu" : "Chưa thiết lập");
      return;
    }

    var media = kind === "video" ? document.createElement("video") : document.createElement("img");
    media.className = "is-contain";
    if (kind === "video") {
      media.muted = true;
      media.controls = true;
      media.playsInline = true;
      media.preload = "metadata";
    } else {
      media.alt = "Xem trước media storefront";
      media.loading = "lazy";
      media.decoding = "async";
      media.addEventListener("load", function () {
        if (media.naturalWidth && media.naturalHeight) {
          setMeta(card, media.naturalWidth + " × " + media.naturalHeight + " px · hiển thị trọn ảnh");
        }
      }, { once: true });
    }
    if (kind === "video") {
      media.addEventListener("loadedmetadata", function () {
        if (media.videoWidth && media.videoHeight) {
          setMeta(card, media.videoWidth + " × " + media.videoHeight + " px · video");
        }
      }, { once: true });
    }
    media.addEventListener("error", function () {
      stage.replaceChildren();
      var fallback = emptyNode(card);
      fallback.querySelector("strong").textContent = "Không thể xem trước";
      fallback.querySelector("span").textContent = "Kiểm tra lại URL hoặc định dạng tệp";
      stage.appendChild(fallback);
    }, { once: true });
    media.src = finalUrl;
    stage.appendChild(media);
    if (isBlob) card.dataset.blobUrl = finalUrl;
    setStatus(card, card.classList.contains("is-uploading") ? "Đang tải lên" : (savingKeys.has(card.dataset.mediaKey) ? "Đang lưu" : (dirty.has(card.dataset.mediaKey) ? "Chưa lưu" : "Đang dùng")));
  }

  function updateDirtyUI() {
    cards.forEach(function (card) {
      var key = card.dataset.mediaKey;
      card.classList.toggle("is-dirty", dirty.has(key));
      if (!card.classList.contains("is-uploading")) {
        var value = current.get(key) || "";
        setStatus(card, savingKeys.has(key) ? "Đang lưu" : (dirty.has(key) ? (value ? "Chưa lưu" : "Sẽ gỡ khi lưu") : (value ? "Đang dùng" : "Chưa thiết lập")));
      }
    });
    var blocked = uploadCount > 0 || pendingSaves > 0;
    root.querySelectorAll("[data-media-save]").forEach(function (button) {
      button.disabled = dirty.size === 0 || blocked;
      var count = button.querySelector("[data-dirty-count]");
      if (count) count.textContent = String(dirty.size);
    });
    var savebar = root.querySelector("[data-media-savebar]");
    if (savebar) savebar.hidden = dirty.size === 0;
    var label = root.querySelector("[data-savebar-label]");
    if (label) label.textContent = dirty.size + " vị trí chưa lưu";
  }

  function setValue(card, url, kind, previewOnly) {
    var key = card.dataset.mediaKey;
    var value = String(url || "").trim();
    current.set(key, value);
    var input = card.querySelector("[data-media-url]");
    if (input && !previewOnly) input.value = value;
    if (!previewOnly) {
      if (value === (original.get(key) || "")) dirty.delete(key);
      else dirty.add(key);
    }
    setPreview(card, value, kind || mediaKind(value), previewOnly);
    updateDirtyUI();
  }

  function validateFile(card, file, allowOptimization) {
    if (!file || !file.size) throw new Error("Tệp rỗng hoặc không đọc được.");
    var kind = mediaKind(file.name, file.type);
    var allowVideo = card.dataset.allowVideo === "1";
    if (kind === "video" && !allowVideo) throw new Error("Vị trí này chỉ chấp nhận hình ảnh.");
    if (kind === "video" && !hasExtension(cleanPath(file.name), VIDEO_EXTENSIONS)) throw new Error("Video phải là MP4, WebM hoặc MOV.");
    if (kind === "image" && !hasExtension(cleanPath(file.name), IMAGE_EXTENSIONS)) throw new Error("Ảnh phải là JPG, PNG, JFIF, WebP, GIF hoặc AVIF.");
    var limit = kind === "video" ? VIDEO_LIMIT : IMAGE_LIMIT;
    if (kind === "image" && file.size > IMAGE_SOURCE_LIMIT) throw new Error("Ảnh nguồn vượt 30MB. Hãy chọn ảnh nhẹ hơn.");
    if (file.size > limit && !(kind === "image" && allowOptimization)) {
      throw new Error("Tệp vượt giới hạn " + (kind === "video" ? "20MB" : "4MB") + ".");
    }
    return kind;
  }

  function canvasToBlob(canvas, type, quality) {
    return new Promise(function (resolve, reject) {
      canvas.toBlob(function (blob) {
        if (blob) resolve(blob);
        else reject(new Error("Trình duyệt không thể tối ưu ảnh này."));
      }, type, quality);
    });
  }

  async function optimizeLargeImage(file) {
    var path = cleanPath(file.name);
    if (hasExtension(path, [".gif", ".avif"])) {
      throw new Error("GIF/AVIF vượt 4MB không thể tự tối ưu an toàn. Hãy xuất tệp nhỏ hơn.");
    }
    if (!("createImageBitmap" in window)) {
      throw new Error("Ảnh vượt 4MB. Trình duyệt này không hỗ trợ tối ưu tự động.");
    }

    var bitmap;
    try {
      bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
      var maxEdges = [2400, 2000, 1600, 1280];
      var qualities = [.86, .76, .66];
      for (var edgeIndex = 0; edgeIndex < maxEdges.length; edgeIndex += 1) {
        var scale = Math.min(1, maxEdges[edgeIndex] / Math.max(bitmap.width, bitmap.height));
        var width = Math.max(1, Math.round(bitmap.width * scale));
        var height = Math.max(1, Math.round(bitmap.height * scale));
        var canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        var context = canvas.getContext("2d", { alpha: true });
        context.imageSmoothingEnabled = true;
        context.imageSmoothingQuality = "high";
        context.drawImage(bitmap, 0, 0, width, height);

        for (var qualityIndex = 0; qualityIndex < qualities.length; qualityIndex += 1) {
          var blob = await canvasToBlob(canvas, "image/webp", qualities[qualityIndex]);
          if (blob.size <= IMAGE_LIMIT) {
            var stem = String(file.name || "storefront").replace(/\.[^.]+$/, "") || "storefront";
            return new File([blob], stem + ".webp", { type: "image/webp", lastModified: Date.now() });
          }
        }
      }
    } catch (error) {
      if (error instanceof Error) throw error;
      throw new Error("Không thể tối ưu ảnh này.");
    } finally {
      if (bitmap && typeof bitmap.close === "function") bitmap.close();
    }
    throw new Error("Không thể giảm ảnh xuống dưới 4MB. Hãy chọn ảnh nhẹ hơn.");
  }

  async function prepareFile(card, file) {
    var kind = validateFile(card, file, true);
    if (kind !== "image" || file.size <= IMAGE_LIMIT) return { file: file, kind: kind, optimized: false };
    setStatus(card, "Đang tối ưu ảnh");
    var optimized = await optimizeLargeImage(file);
    validateFile(card, optimized, false);
    return { file: optimized, kind: "image", optimized: true, originalSize: file.size };
  }

  function setUploadProgress(card, percent) {
    var wrap = card.querySelector("[data-media-progress]");
    var bar = wrap?.querySelector("span");
    if (!wrap || !bar) return;
    wrap.hidden = percent < 0;
    bar.style.width = Math.max(0, Math.min(100, percent)) + "%";
  }

  async function uploadFile(card, sourceFile) {
    var prepared;
    card.classList.remove("is-error");
    try {
      card.classList.add("is-uploading");
      uploadCount += 1;
      updateDirtyUI();
      prepared = await prepareFile(card, sourceFile);
    } catch (error) {
      card.classList.remove("is-uploading");
      card.classList.add("is-error");
      uploadCount = Math.max(0, uploadCount - 1);
      setStatus(card, "Không thể tải");
      updateDirtyUI();
      notify(error.message, "error");
      return;
    }

    var file = prepared.file;
    var kind = prepared.kind;

    revokeCardBlob(card);
    var blobUrl = URL.createObjectURL(file);
    setPreview(card, blobUrl, kind, true);
    setUploadProgress(card, 1);
    updateDirtyUI();

    var formData = new FormData();
    formData.append("file", file);
    formData.append("slot_key", card.dataset.mediaKey);

    var xhr = new XMLHttpRequest();
    xhr.open("POST", root.dataset.uploadUrl, true);
    xhr.setRequestHeader("X-CSRFToken", csrfToken());
    xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
    xhr.upload.addEventListener("progress", function (event) {
      if (event.lengthComputable) setUploadProgress(card, Math.round((event.loaded / event.total) * 100));
    });
    xhr.addEventListener("load", function () {
      var data = {};
      try { data = JSON.parse(xhr.responseText || "{}"); } catch (_) {}
      if (xhr.status < 200 || xhr.status >= 300 || !data.ok || !data.url) {
        setPreview(card, current.get(card.dataset.mediaKey) || "", mediaKind(current.get(card.dataset.mediaKey) || ""), false);
        card.classList.add("is-error");
        setStatus(card, "Không thể tải");
        var message = data.message || "Không thể tải media lên.";
        if (data.error_code === "invalid_slot") message += " Hãy Ctrl + F5 để đồng bộ mã mới.";
        notify(message, "error");
        return;
      }
      setValue(card, data.url, data.media_type || kind, false);
      var label = card.dataset.mediaLabel || "vị trí media";
      var optimizedNote = prepared.optimized
        ? " Ảnh đã được tối ưu từ " + (prepared.originalSize / 1024 / 1024).toFixed(1) + "MB xuống " + (file.size / 1024 / 1024).toFixed(1) + "MB."
        : "";
      queueSave((function () {
        var snapshot = {};
        snapshot[card.dataset.mediaKey] = data.url;
        return snapshot;
      })(), "Đã tải lên và lưu “" + label + "”." + optimizedNote, "Tệp đã tải lên nhưng chưa thể lưu vào giao diện. Hãy nhấn Lưu lại.");
    });
    xhr.addEventListener("error", function () {
      setPreview(card, current.get(card.dataset.mediaKey) || "", mediaKind(current.get(card.dataset.mediaKey) || ""), false);
      card.classList.add("is-error");
      setStatus(card, "Mất kết nối");
      notify("Mất kết nối khi tải media.", "error");
    });
    xhr.addEventListener("loadend", function () {
      revokeCardBlob(card);
      card.classList.remove("is-uploading");
      uploadCount = Math.max(0, uploadCount - 1);
      window.setTimeout(function () { setUploadProgress(card, -1); }, 180);
      updateDirtyUI();
    });
    xhr.send(formData);
  }

  function bindCard(card) {
    var key = card.dataset.mediaKey;
    var initial = String(card.dataset.initialUrl || "").trim();
    original.set(key, initial);
    current.set(key, initial);
    var input = card.querySelector("[data-media-file]");
    var drop = card.querySelector("[data-media-drop]");

    function chooseFile() { if (!card.classList.contains("is-uploading")) input?.click(); }
    drop?.addEventListener("click", function (event) {
      if (event.target.closest("video") || event.target.closest("button") || event.target.closest("a")) return;
      chooseFile();
    });
    drop?.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); chooseFile(); }
    });
    card.querySelector("[data-media-replace]")?.addEventListener("click", chooseFile);
    input?.addEventListener("change", function () {
      var file = input.files && input.files[0];
      if (file) uploadFile(card, file);
      input.value = "";
    });

    ["dragenter", "dragover"].forEach(function (name) {
      drop?.addEventListener(name, function (event) {
        event.preventDefault();
        if (!card.classList.contains("is-uploading")) card.classList.add("is-dragging");
      });
    });
    ["dragleave", "drop"].forEach(function (name) {
      drop?.addEventListener(name, function (event) {
        event.preventDefault();
        card.classList.remove("is-dragging");
      });
    });
    drop?.addEventListener("drop", function (event) {
      var file = event.dataTransfer?.files?.[0];
      if (file && !card.classList.contains("is-uploading")) uploadFile(card, file);
    });

    card.querySelector("[data-media-remove]")?.addEventListener("click", function () {
      setValue(card, "", "image", false);
    });
    card.querySelector("[data-media-url-apply]")?.addEventListener("click", function () {
      var url = String(card.querySelector("[data-media-url]")?.value || "").trim();
      if (url && !/^https:\/\//i.test(url) && !url.startsWith("/static/")) {
        notify("URL media phải bắt đầu bằng https://", "error");
        return;
      }
      if (mediaKind(url) === "video" && card.dataset.allowVideo !== "1") {
        notify("Vị trí này chỉ chấp nhận hình ảnh.", "error");
        return;
      }
      setValue(card, url, mediaKind(url), false);
    });
  }

  function hydratePreviews() {
    function hydrate(card) {
      if (card.dataset.hydrated === "1") return;
      card.dataset.hydrated = "1";
      var value = current.get(card.dataset.mediaKey) || "";
      setPreview(card, value, mediaKind(value), false);
    }
    if (!("IntersectionObserver" in window)) { cards.forEach(hydrate); return; }
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        hydrate(entry.target);
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "320px 0px", threshold: .01 });
    cards.forEach(function (card, index) {
      if (index < 2) hydrate(card); else observer.observe(card);
    });
  }

  async function performSave(changes, successMessage, failureMessage) {
    try {
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
      if (!response.ok || !data.ok) throw new Error(data.message || "Không thể lưu cấu hình.");
      Object.keys(changes).forEach(function (key) {
        original.set(key, changes[key]);
        if ((current.get(key) || "") === changes[key]) dirty.delete(key);
        else dirty.add(key);
      });
      updateDirtyUI();
      notify(successMessage || data.message || "Đã cập nhật giao diện cửa hàng.", "success");
      return data;
    } catch (error) {
      var reason = error && error.message ? String(error.message) : "";
      var message = failureMessage
        ? failureMessage + (reason ? " Chi tiết: " + reason : "")
        : (reason || "Không thể lưu cấu hình.");
      notify(message, "error");
      updateDirtyUI();
      throw error;
    }
  }

  function queueSave(changes, successMessage, failureMessage) {
    var snapshot = Object.assign({}, changes || {});
    var keys = Object.keys(snapshot);
    if (!keys.length) return Promise.resolve();
    pendingSaves += 1;
    keys.forEach(function (key) { savingKeys.add(key); });
    updateDirtyUI();

    var operation = saveQueue.then(function () {
      return performSave(snapshot, successMessage, failureMessage);
    });
    var handled = operation.catch(function () {});
    saveQueue = handled;
    return handled.finally(function () {
      pendingSaves = Math.max(0, pendingSaves - 1);
      keys.forEach(function (key) { savingKeys.delete(key); });
      updateDirtyUI();
    });
  }

  function save() {
    if (!dirty.size || uploadCount || pendingSaves) return;
    var changes = {};
    dirty.forEach(function (key) { changes[key] = current.get(key) || ""; });
    queueSave(changes, "Đã lưu " + Object.keys(changes).length + " thay đổi trên giao diện cửa hàng.");
  }

  function reset() {
    dirty.forEach(function (key) {
      var card = cards.find(function (item) { return item.dataset.mediaKey === key; });
      var value = original.get(key) || "";
      current.set(key, value);
      if (card) {
        var input = card.querySelector("[data-media-url]");
        if (input) input.value = value;
        setPreview(card, value, mediaKind(value), false);
      }
    });
    dirty.clear();
    updateDirtyUI();
  }

  cards.forEach(bindCard);
  hydratePreviews();
  updateDirtyUI();

  function applyFilter(button) {
    var group = button.dataset.mediaFilter;
    root.querySelectorAll("[data-media-filter]").forEach(function (item) { item.classList.toggle("is-active", item === button); });
    cards.forEach(function (card) { card.hidden = group !== "all" && card.dataset.mediaGroup !== group; });
  }

  root.querySelectorAll("[data-media-filter]").forEach(function (button) {
    button.addEventListener("click", function () {
      applyFilter(button);
    });
  });
  var initialFilter = root.querySelector("[data-media-filter].is-active");
  if (initialFilter) applyFilter(initialFilter);
  root.querySelectorAll("[data-media-save]").forEach(function (button) { button.addEventListener("click", save); });
  root.querySelector("[data-media-reset]")?.addEventListener("click", reset);

  var helpDialog = root.querySelector("[data-media-help-dialog]");
  root.querySelector("[data-media-help]")?.addEventListener("click", function () {
    if (helpDialog?.showModal) helpDialog.showModal();
    else helpDialog?.setAttribute("open", "");
  });
  helpDialog?.addEventListener("click", function (event) {
    if (event.target === helpDialog) helpDialog.close?.();
  });

  window.addEventListener("beforeunload", function (event) {
    if (!dirty.size && !uploadCount && !pendingSaves) return;
    event.preventDefault();
    event.returnValue = "";
  });
})();
