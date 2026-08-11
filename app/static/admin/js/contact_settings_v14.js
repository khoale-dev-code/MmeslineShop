(function () {
  "use strict";

  var root = document.querySelector("[data-contact-settings]");
  if (!root || root.dataset.ready === "1") return;
  root.dataset.ready = "1";

  var form = root.querySelector("[data-contact-settings-form]");
  var initial = form ? new FormData(form) : null;
  var uploading = false;
  var mapTimer = 0;

  function notify(message, type) {
    if (window.GUA && typeof window.GUA.snackbar === "function") {
      window.GUA.snackbar(message, type || "info");
      return;
    }
    if (window.GUA && typeof window.GUA.toast === "function") {
      window.GUA.toast(message, type || "info");
      return;
    }
    window.alert(message);
  }

  function formChanged() {
    if (!form || !initial) return false;
    var now = new FormData(form);
    var keys = new Set(Array.from(initial.keys()).concat(Array.from(now.keys())));
    return Array.from(keys).some(function (key) {
      return String(initial.get(key) || "") !== String(now.get(key) || "");
    });
  }

  function updateSaveState() {
    var changed = formChanged();
    var label = root.querySelector("[data-contact-save-label]");
    if (label) label.textContent = uploading ? "Đang tải ảnh lên..." : (changed ? "Có thay đổi chưa lưu" : "Sẵn sàng chỉnh sửa");
    var submit = form?.querySelector('button[type="submit"]');
    if (submit) submit.disabled = uploading || submit.dataset.migrationDisabled === "1";
  }

  function extractMapUrl(value) {
    var raw = String(value || "").trim();
    if (!raw) return "";
    var candidate = raw;
    if (raw.indexOf("<") >= 0) {
      var doc = new DOMParser().parseFromString(raw, "text/html");
      candidate = doc.querySelector("iframe")?.getAttribute("src") || "";
    }
    try {
      var parsed = new URL(candidate);
      var host = parsed.hostname.toLowerCase().replace(/\.$/, "");
      var allowed = host === "google.com" || host.endsWith(".google.com");
      if (parsed.protocol !== "https:" || !allowed || !parsed.pathname.startsWith("/maps/embed")) return null;
      return parsed.href;
    } catch (_) {
      return null;
    }
  }

  function previewMap() {
    var input = root.querySelector("[data-map-embed]");
    var iframe = root.querySelector("[data-map-preview]");
    var empty = root.querySelector("[data-map-empty]");
    var message = root.querySelector("[data-map-message]");
    if (!input || !iframe || !empty) return;
    var url = extractMapUrl(input.value);
    message?.classList.remove("is-error", "is-success");
    if (url === "") {
      iframe.hidden = true;
      empty.hidden = false;
      iframe.src = "about:blank";
      if (message) message.textContent = "Google Maps → Chia sẻ → Nhúng bản đồ → Sao chép HTML.";
      return;
    }
    if (url === null) {
      if (message) {
        message.textContent = "Mã chưa đúng. Hãy dùng iframe từ Google Maps → Nhúng bản đồ.";
        message.classList.add("is-error");
      }
      return;
    }
    iframe.src = url;
    iframe.hidden = false;
    empty.hidden = true;
    if (message) {
      message.textContent = "Mã nhúng hợp lệ · preview đã cập nhật.";
      message.classList.add("is-success");
    }
  }

  var mapInput = root.querySelector("[data-map-embed]");
  mapInput?.addEventListener("input", function () {
    window.clearTimeout(mapTimer);
    mapTimer = window.setTimeout(previewMap, 180);
    updateSaveState();
  });

  var mapDrop = root.querySelector("[data-map-drop]");
  ["dragenter", "dragover"].forEach(function (name) {
    mapDrop?.addEventListener(name, function (event) {
      event.preventDefault();
      mapDrop.classList.add("is-dragging");
    });
  });
  ["dragleave", "drop"].forEach(function (name) {
    mapDrop?.addEventListener(name, function (event) {
      event.preventDefault();
      mapDrop.classList.remove("is-dragging");
    });
  });
  mapDrop?.addEventListener("drop", function (event) {
    var text = event.dataTransfer?.getData("text/html") || event.dataTransfer?.getData("text/plain") || "";
    if (!text) {
      notify("Hãy thả đoạn iframe hoặc URL Google Maps.", "warning");
      return;
    }
    mapInput.value = text;
    previewMap();
    updateSaveState();
  });

  var mediaDrop = root.querySelector("[data-contact-media-drop]");
  var mediaFile = root.querySelector("[data-contact-media-file]");
  var mediaInput = root.querySelector("[data-contact-media-url]");
  var mediaPreview = root.querySelector("[data-contact-media-preview]");
  var mediaProgress = root.querySelector("[data-contact-media-progress]");
  var mediaRemove = root.querySelector("[data-contact-media-remove]");
  var blobUrl = "";

  function revokeBlob() {
    if (blobUrl) {
      try { URL.revokeObjectURL(blobUrl); } catch (_) {}
      blobUrl = "";
    }
  }

  function renderMedia(url, local) {
    if (!mediaPreview) return;
    if (!local) revokeBlob();
    mediaPreview.replaceChildren();
    if (!url) {
      var empty = document.createElement("div");
      var icon = document.createElement("i");
      icon.className = "fa-regular fa-image";
      var strong = document.createElement("strong");
      strong.textContent = "Thả ảnh vào đây";
      var span = document.createElement("span");
      span.textContent = "JPG, PNG, WebP, GIF, AVIF";
      empty.append(icon, strong, span);
      mediaPreview.appendChild(empty);
      if (mediaRemove) mediaRemove.disabled = true;
      return;
    }
    var image = document.createElement("img");
    image.src = url;
    image.alt = "Xem trước ảnh cover Liên hệ";
    image.decoding = "async";
    mediaPreview.appendChild(image);
    if (mediaRemove) mediaRemove.disabled = false;
    if (local) blobUrl = url;
  }

  function chooseMedia() { if (!uploading) mediaFile?.click(); }
  mediaDrop?.addEventListener("click", chooseMedia);
  mediaDrop?.addEventListener("keydown", function (event) {
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); chooseMedia(); }
  });
  root.querySelector("[data-contact-media-choose]")?.addEventListener("click", chooseMedia);
  ["dragenter", "dragover"].forEach(function (name) {
    mediaDrop?.addEventListener(name, function (event) { event.preventDefault(); if (!uploading) mediaDrop.classList.add("is-dragging"); });
  });
  ["dragleave", "drop"].forEach(function (name) {
    mediaDrop?.addEventListener(name, function (event) { event.preventDefault(); mediaDrop.classList.remove("is-dragging"); });
  });
  mediaDrop?.addEventListener("drop", function (event) {
    var file = event.dataTransfer?.files?.[0];
    if (file && !uploading) uploadMedia(file);
  });
  mediaFile?.addEventListener("change", function () {
    var file = mediaFile.files?.[0];
    if (file) uploadMedia(file);
    mediaFile.value = "";
  });

  function uploadMedia(file) {
    if (!file.type.startsWith("image/")) { notify("Ảnh cover không chấp nhận video.", "error"); return; }
    if (!file.size || file.size > 4 * 1024 * 1024) { notify("Ảnh phải nhỏ hơn 4MB.", "error"); return; }
    revokeBlob();
    renderMedia(URL.createObjectURL(file), true);
    uploading = true;
    updateSaveState();
    if (mediaProgress) { mediaProgress.hidden = false; mediaProgress.querySelector("span").style.width = "1%"; }

    var payload = new FormData();
    payload.append("file", file);
    payload.append("slot_key", "contact_hero_media_url");
    var xhr = new XMLHttpRequest();
    xhr.open("POST", root.dataset.uploadUrl, true);
    xhr.setRequestHeader("X-CSRFToken", root.dataset.csrf || "");
    xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
    xhr.upload.addEventListener("progress", function (event) {
      if (event.lengthComputable && mediaProgress) mediaProgress.querySelector("span").style.width = Math.round(event.loaded / event.total * 100) + "%";
    });
    xhr.addEventListener("load", function () {
      var data = {};
      try { data = JSON.parse(xhr.responseText || "{}"); } catch (_) {}
      if (xhr.status < 200 || xhr.status >= 300 || !data.ok || !data.url) {
        renderMedia(mediaInput?.value || "", false);
        notify(data.message || "Không thể tải ảnh lên.", "error");
        return;
      }
      if (mediaInput) mediaInput.value = data.url;
      renderMedia(data.url, false);
      notify("Đã tải ảnh. Nhấn Lưu để áp dụng.", "success");
    });
    xhr.addEventListener("error", function () { renderMedia(mediaInput?.value || "", false); notify("Mất kết nối khi tải ảnh.", "error"); });
    xhr.addEventListener("loadend", function () {
      uploading = false;
      revokeBlob();
      if (mediaProgress) window.setTimeout(function () { mediaProgress.hidden = true; }, 180);
      updateSaveState();
    });
    xhr.send(payload);
  }

  mediaRemove?.addEventListener("click", function () {
    if (mediaInput) mediaInput.value = "";
    renderMedia("", false);
    updateSaveState();
  });

  form?.addEventListener("input", updateSaveState);
  form?.addEventListener("change", updateSaveState);
  form?.addEventListener("submit", function (event) {
    if (uploading) { event.preventDefault(); notify("Vui lòng chờ ảnh tải xong.", "warning"); return; }
    var mapValue = extractMapUrl(mapInput?.value || "");
    if (mapValue === null) { event.preventDefault(); mapInput?.focus(); notify("Mã nhúng Google Maps chưa hợp lệ.", "error"); return; }
    if (!form.checkValidity()) { event.preventDefault(); form.reportValidity(); return; }
    form.dataset.submitting = "1";
    var submit = form.querySelector('button[type="submit"]');
    if (submit) { submit.disabled = true; submit.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang lưu'; }
  });

  var help = root.querySelector("[data-contact-help-dialog]");
  root.querySelector("[data-contact-help]")?.addEventListener("click", function () { help?.showModal ? help.showModal() : help?.setAttribute("open", ""); });
  help?.addEventListener("click", function (event) { if (event.target === help) help.close?.(); });

  window.addEventListener("beforeunload", function (event) {
    if (form?.dataset.submitting === "1" || (!formChanged() && !uploading)) return;
    event.preventDefault();
    event.returnValue = "";
  });

  previewMap();
  updateSaveState();
})();
