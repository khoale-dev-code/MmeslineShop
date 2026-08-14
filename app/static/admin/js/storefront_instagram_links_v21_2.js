(function () {
  "use strict";

  var root = document.querySelector("[data-media-studio]");
  if (!root || root.dataset.instagramLinksReady === "1") return;
  root.dataset.instagramLinksReady = "1";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return root.dataset.csrf || (meta ? meta.content : "") || "";
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

  function setStatus(panel, message, state) {
    var status = panel.querySelector("[data-instagram-link-status]");
    if (!status) return;
    status.textContent = message;
    status.classList.remove("is-dirty", "is-success", "is-error");
    if (state) status.classList.add("is-" + state);
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

  async function savePanel(panel) {
    var input = panel.querySelector("[data-instagram-link-input]");
    var button = panel.querySelector("[data-instagram-link-save]");
    var key = panel.dataset.instagramLinkKey || "";
    var value = String(input ? input.value : "").trim();
    if (!key || !input || !button) return;
    if (!isInstagramUrl(value)) {
      setStatus(panel, "Chỉ chấp nhận link HTTPS thuộc instagram.com.", "error");
      notify("Link Instagram không hợp lệ.", "error");
      input.focus();
      return;
    }

    button.disabled = true;
    setStatus(panel, "Đang lưu link…", "");
    try {
      var changes = {};
      changes[key] = value;
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
      if (!response.ok || !data.ok) throw new Error(data.message || "Không thể lưu link Instagram.");
      input.dataset.savedValue = value;
      setStatus(panel, value ? "Đã lưu — khách bấm ảnh sẽ mở link này." : "Đã gỡ link khỏi ảnh.", "success");
      notify(value ? "Đã lưu link Instagram cho ảnh." : "Đã gỡ link Instagram khỏi ảnh.", "success");
    } catch (error) {
      setStatus(panel, error.message || "Không thể lưu link.", "error");
      notify(error.message || "Không thể lưu link Instagram.", "error");
    } finally {
      button.disabled = false;
    }
  }

  root.querySelectorAll("[data-instagram-link-panel]").forEach(function (panel) {
    var input = panel.querySelector("[data-instagram-link-input]");
    var button = panel.querySelector("[data-instagram-link-save]");
    if (!input || !button) return;
    input.dataset.savedValue = String(input.value || "").trim();
    input.addEventListener("input", function () {
      var changed = String(input.value || "").trim() !== input.dataset.savedValue;
      setStatus(panel, changed ? "Link chưa lưu — nhấn Lưu link." : "Link đã được lưu.", changed ? "dirty" : "");
    });
    input.addEventListener("keydown", function (event) {
      if (event.key !== "Enter") return;
      event.preventDefault();
      savePanel(panel);
    });
    button.addEventListener("click", function () { savePanel(panel); });
  });
})();
