(function () {
  "use strict";

  var activeResolve = null;
  var lastFocus = null;

  function clean(value) {
    return String(value == null ? "" : value).trim();
  }

  function escapeSelector(value) {
    if (window.CSS && typeof window.CSS.escape === "function") return window.CSS.escape(value);
    return clean(value).replace(/["\\]/g, "\\$&");
  }

  function buildDialog() {
    var existed = document.getElementById("guaAdminDeleteBackdrop");
    if (existed) return existed;

    var backdrop = document.createElement("div");
    backdrop.id = "guaAdminDeleteBackdrop";
    backdrop.className = "gua-delete-backdrop";
    backdrop.setAttribute("aria-hidden", "true");
    backdrop.innerHTML = [
      '<section class="gua-delete-dialog" role="alertdialog" aria-modal="true" aria-labelledby="guaDeleteTitle" aria-describedby="guaDeleteMessage" data-tone="danger">',
      '  <header class="gua-delete-head">',
      '    <span class="gua-delete-icon"><i class="fa-solid fa-triangle-exclamation"></i></span>',
      '    <h2 id="guaDeleteTitle">Xác nhận xóa</h2>',
      '    <button type="button" class="gua-delete-close" data-gua-delete-cancel aria-label="Đóng"><i class="fa-solid fa-xmark"></i></button>',
      '  </header>',
      '  <div class="gua-delete-body">',
      '    <p class="gua-delete-message" id="guaDeleteMessage"></p>',
      '    <p class="gua-delete-detail" id="guaDeleteDetail" hidden></p>',
      '  </div>',
      '  <footer class="gua-delete-actions">',
      '    <button type="button" class="gua-delete-button gua-delete-cancel" data-gua-delete-cancel>Hủy</button>',
      '    <button type="button" class="gua-delete-button gua-delete-confirm" data-gua-delete-confirm>Xóa</button>',
      '  </footer>',
      '</section>'
    ].join("");
    document.body.appendChild(backdrop);

    backdrop.addEventListener("click", function (event) {
      if (event.target === backdrop || event.target.closest("[data-gua-delete-cancel]")) close(false);
      if (event.target.closest("[data-gua-delete-confirm]")) close(true);
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && backdrop.classList.contains("is-open")) close(false);
    });
    return backdrop;
  }

  function close(result) {
    var backdrop = document.getElementById("guaAdminDeleteBackdrop");
    if (!backdrop || !activeResolve) return;
    var resolve = activeResolve;
    activeResolve = null;
    backdrop.classList.remove("is-open");
    backdrop.setAttribute("aria-hidden", "true");
    document.documentElement.classList.remove("gua-delete-lock");
    document.body.classList.remove("gua-delete-lock");
    window.setTimeout(function () {
      if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
      resolve(Boolean(result));
    }, 120);
  }

  function confirmAction(options) {
    options = options || {};
    var backdrop = buildDialog();
    var dialog = backdrop.querySelector(".gua-delete-dialog");
    var title = backdrop.querySelector("#guaDeleteTitle");
    var message = backdrop.querySelector("#guaDeleteMessage");
    var detail = backdrop.querySelector("#guaDeleteDetail");
    var cancel = backdrop.querySelector(".gua-delete-actions [data-gua-delete-cancel]");
    var submit = backdrop.querySelector("[data-gua-delete-confirm]");

    if (activeResolve) activeResolve(false);
    lastFocus = document.activeElement;
    dialog.dataset.tone = options.tone === "warning" ? "warning" : "danger";
    title.textContent = clean(options.title) || "Xác nhận xóa";
    message.textContent = clean(options.message) || "Bạn có chắc muốn xóa mục này?";
    detail.textContent = clean(options.detail);
    detail.hidden = !detail.textContent;
    cancel.textContent = clean(options.cancelText) || "Hủy";
    submit.textContent = clean(options.confirmText) || "Xóa";

    backdrop.classList.add("is-open");
    backdrop.setAttribute("aria-hidden", "false");
    document.documentElement.classList.add("gua-delete-lock");
    document.body.classList.add("gua-delete-lock");
    window.setTimeout(function () { submit.focus(); }, 20);

    return new Promise(function (resolve) { activeResolve = resolve; });
  }

  function formTarget(form, submitter) {
    return clean((submitter && submitter.getAttribute("formaction")) || form.getAttribute("action") || form.action);
  }

  function isDeleteSubmission(form, submitter) {
    if (form.hasAttribute("data-delete-confirm") || (submitter && submitter.hasAttribute("data-delete-confirm"))) return true;
    var action = formTarget(form, submitter).toLowerCase();
    return /(?:\/delete(?:\/|$)|\/remove(?:\/|$))/.test(action);
  }

  function nativeSubmit(form, submitter) {
    var action = submitter && submitter.getAttribute("formaction");
    var method = submitter && submitter.getAttribute("formmethod");
    if (action) form.setAttribute("action", action);
    if (method) form.setAttribute("method", method);
    HTMLFormElement.prototype.submit.call(form);
  }

  function productDeleteFlow(form, submitter) {
    var name = clean(form.dataset.productName) || "sản phẩm này";
    var known = form.dataset.inventoryKnown !== "0";
    var stock = Number(form.dataset.inventoryStock || 0);
    var adjustUrl = clean(form.dataset.inventoryAdjustUrl);

    if (!known) {
      return confirmAction({
        title: "Chưa thể xác minh tồn kho",
        message: "Hệ thống không đọc được số lượng tồn hiện tại nên đã chặn thao tác xóa.",
        detail: "Hãy tải lại trang hoặc kiểm tra kết nối database. Khi không xác minh được kho, backend luôn từ chối xóa.",
        confirmText: "Đã hiểu",
        cancelText: "Đóng",
        tone: "warning"
      }).then(function () { return false; });
    }

    return confirmAction({
      title: "Xóa sản phẩm",
      message: "Bạn có muốn xóa “" + name + "”?",
      detail: clean(form.dataset.deleteDetail) || "Sản phẩm bị xóa sẽ được chuyển vào thùng rác và ngừng hiển thị trên website.",
      confirmText: "Tiếp tục",
      tone: "danger"
    }).then(function (ok) {
      if (!ok) return false;
      if (!(stock > 0)) {
        nativeSubmit(form, submitter);
        return true;
      }
      return confirmAction({
        title: "Điều chỉnh tồn kho",
        message: "Sản phẩm đang còn " + stock + " trong kho. Bạn phải điều chỉnh sản phẩm và tất cả biến thể về 0 trước khi xóa.",
        detail: "Bước tiếp theo sẽ hiển thị từng biến thể, số lượng giảm và yêu cầu ghi lý do điều chỉnh.",
        confirmText: "Điều chỉnh tồn kho",
        tone: "warning"
      }).then(function (goAdjust) {
        if (goAdjust && adjustUrl) window.location.assign(adjustUrl);
        return goAdjust;
      });
    });
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    var submitter = event.submitter || null;
    if (!isDeleteSubmission(form, submitter)) return;

    event.preventDefault();
    event.stopImmediatePropagation();

    if (form.hasAttribute("data-product-delete")) {
      productDeleteFlow(form, submitter);
      return;
    }

    var subject = clean(
      (submitter && submitter.dataset.deleteName) ||
      form.dataset.deleteName ||
      (submitter && submitter.getAttribute("title")) ||
      "mục này"
    );
    var message = clean((submitter && submitter.dataset.deleteMessage) || form.dataset.deleteMessage);
    confirmAction({
      title: clean((submitter && submitter.dataset.deleteTitle) || form.dataset.deleteTitle) || "Xác nhận xóa",
      message: message || "Bạn có chắc muốn xóa “" + subject + "”?",
      detail: clean((submitter && submitter.dataset.deleteDetail) || form.dataset.deleteDetail) || "Hãy kiểm tra kỹ trước khi tiếp tục. Thao tác xóa có thể không thể hoàn tác.",
      confirmText: clean((submitter && submitter.dataset.deleteConfirmText) || form.dataset.deleteConfirmText) || "Xóa",
      tone: "danger"
    }).then(function (ok) {
      if (ok) nativeSubmit(form, submitter);
    });
  }, true);

  window.GuaAdminDelete = {
    confirm: confirmAction,
    submit: function (form, options) {
      if (!form) return Promise.resolve(false);
      return confirmAction(options).then(function (ok) {
        if (ok) nativeSubmit(form, null);
        return ok;
      });
    },
    byId: function (id, options) {
      var form = document.querySelector("#" + escapeSelector(id));
      return window.GuaAdminDelete.submit(form, options);
    }
  };
})();
