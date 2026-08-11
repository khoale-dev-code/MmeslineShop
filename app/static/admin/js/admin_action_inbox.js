(function () {
  "use strict";
  var root = document.querySelector("[data-admin-inbox]");
  if (!root) return;

  root.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.getAttribute("data-confirm") || "Tiếp tục thao tác?")) {
        event.preventDefault();
      }
    });
  });

  root.querySelectorAll("[data-relative-time]").forEach(function (element) {
    var value = element.getAttribute("datetime");
    var date = value ? new Date(value) : null;
    if (!date || Number.isNaN(date.getTime())) return;
    var diff = Math.max(0, Date.now() - date.getTime());
    var minutes = Math.floor(diff / 60000);
    var label = minutes < 1 ? "Vừa xong" : minutes < 60 ? minutes + " phút trước" : minutes < 1440 ? Math.floor(minutes / 60) + " giờ trước" : Math.floor(minutes / 1440) + " ngày trước";
    element.textContent = label;
    element.title = date.toLocaleString("vi-VN");
  });
})();

