(function () {
  "use strict";

  if (window.GUAMAISONNewsletterV11) return;
  window.GUAMAISONNewsletterV11 = true;

  function setLoading(form, loading) {
    var button = form.querySelector("[data-newsletter-submit]");
    var label = form.querySelector("[data-newsletter-button-label]");
    var icon = button && button.querySelector("i");
    if (!button || !label) return;

    button.disabled = loading;
    button.classList.toggle("is-loading", loading);
    label.textContent = loading ? "Đang đăng ký…" : "Gia nhập danh sách";
    if (icon) {
      icon.className = loading ? "fa-solid fa-spinner" : "fa-solid fa-arrow-right";
    }
  }

  function setStatus(form, message, success) {
    var status = form.querySelector("[data-newsletter-status]");
    if (!status) return;
    status.textContent = message || "";
    status.classList.toggle("is-success", Boolean(success));
  }

  function showSuccess(form, message) {
    var section = form.closest("[data-newsletter-section]");
    var success = section && section.querySelector("[data-newsletter-success]");
    var successMessage = success && success.querySelector("[data-newsletter-success-message]");
    if (!success) return;

    if (successMessage) successMessage.textContent = message;
    form.hidden = true;
    success.hidden = false;
    success.setAttribute("tabindex", "-1");
    success.focus({ preventScroll: true });
  }

  document.addEventListener("submit", async function (event) {
    var form = event.target.closest && event.target.closest("[data-newsletter-form]");
    if (!form) return;
    event.preventDefault();

    if (!form.checkValidity()) {
      form.reportValidity();
      setStatus(form, "Vui lòng nhập email và đồng ý nhận tin.", false);
      return;
    }

    setLoading(form, true);
    setStatus(form, "", false);

    var token = form.querySelector('input[name="csrf_token"]');

    try {
      var response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        credentials: "same-origin",
        headers: {
          "Accept": "application/json",
          "X-CSRFToken": token ? token.value : ""
        }
      });

      var payload = await response.json().catch(function () { return {}; });
      if (!response.ok || payload.ok === false) {
        throw new Error(payload.message || "Chưa thể đăng ký lúc này. Vui lòng thử lại.");
      }

      showSuccess(form, payload.message || "Đăng ký nhận tin thành công.");
    } catch (error) {
      setStatus(form, error.message || "Đã có lỗi xảy ra. Vui lòng thử lại.", false);
    } finally {
      setLoading(form, false);
    }
  });

  document.addEventListener("click", function (event) {
    var reset = event.target.closest && event.target.closest("[data-newsletter-reset]");
    if (!reset) return;

    var section = reset.closest("[data-newsletter-section]");
    var form = section && section.querySelector("[data-newsletter-form]");
    var success = section && section.querySelector("[data-newsletter-success]");
    if (!form || !success) return;

    success.hidden = true;
    form.hidden = false;
    form.reset();
    setStatus(form, "", false);

    var email = form.querySelector('input[name="email"]');
    if (email) email.focus({ preventScroll: true });
  });

  if ("IntersectionObserver" in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var media = entry.target;
        if (!(media instanceof HTMLVideoElement)) return;

        if (
          entry.isIntersecting &&
          !window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ) {
          var promise = media.play();
          if (promise && promise.catch) promise.catch(function () {});
        } else {
          media.pause();
        }
      });
    }, { threshold: 0.2 });

    document.querySelectorAll("[data-newsletter-media]").forEach(function (media) {
      if (media instanceof HTMLVideoElement) observer.observe(media);
    });
  }
})();
