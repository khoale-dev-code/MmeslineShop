(function () {
  "use strict";
  var lastCount = null;
  var endpoint = "/admin/notifications/events/unread-count";

  function badgeFor(link) {
    var badge = link.querySelector("[data-admin-event-badge], .mm-dot-badge, .mm-sidebar-badge");
    if (!badge) {
      badge = document.createElement("span");
      badge.setAttribute("data-admin-event-badge", "");
      badge.className = "gm-admin-event-live-badge";
      link.appendChild(badge);
    }
    return badge;
  }

  function render(count) {
    document.querySelectorAll('a[href="/admin/notifications"],a[href^="/admin/notifications?"]').forEach(function (link) {
      var badge = badgeFor(link);
      badge.textContent = count > 99 ? "99+" : String(count);
      badge.hidden = count < 1;
      badge.setAttribute("aria-label", count + " việc mới cần xử lý");
    });
    if (lastCount !== null && count > lastCount) {
      window.dispatchEvent(new CustomEvent("gua:admin-event", { detail: { count: count, added: count - lastCount } }));
    }
    lastCount = count;
  }

  async function refresh() {
    if (document.hidden) return;
    try {
      var response = await fetch(endpoint, { credentials: "same-origin", headers: { Accept: "application/json" } });
      if (!response.ok) return;
      var payload = await response.json();
      if (payload && payload.ok) render(Math.max(0, Number(payload.count) || 0));
    } catch (_) {}
  }

  refresh();
  window.setInterval(refresh, 45000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) refresh(); });
})();
