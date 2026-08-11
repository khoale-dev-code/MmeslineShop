/* GUAMAISON Contact Editorial v15.1 */
(function () {
  "use strict";

  var resultTimer = 0;

  function initReveal(root) {
    var items = root.querySelectorAll("[data-reveal]");
    var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced || !("IntersectionObserver" in window)) {
      items.forEach(function (item) { item.classList.add("is-visible"); });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.06, rootMargin: "0px 0px -5% 0px" });

    items.forEach(function (item, index) {
      item.style.transitionDelay = Math.min(index, 3) * 45 + "ms";
      observer.observe(item);
    });
  }

  function setResult(box, message, isError, reference) {
    if (!box) return;
    window.clearTimeout(resultTimer);
    box.hidden = false;
    box.classList.toggle("is-error", Boolean(isError));
    box.textContent = reference ? message + " Mã tham chiếu: " + reference + "." : message;
    box.setAttribute("tabindex", "-1");
    box.focus({ preventScroll: true });

    if (!isError) {
      resultTimer = window.setTimeout(function () {
        box.hidden = true;
      }, 8500);
    }
  }

  function initForm(root) {
    var form = root.querySelector("[data-contact-form]");
    if (!form || form.dataset.bound === "1") return;
    form.dataset.bound = "1";

    var message = form.querySelector("#contactMessage");
    var counter = form.querySelector("[data-message-count]");
    var button = form.querySelector("[data-contact-submit]");
    var resultBox = form.querySelector("[data-contact-result]");

    function updateCount() {
      if (counter && message) counter.textContent = String(message.value.length);
    }

    function clearFieldState() {
      form.querySelectorAll("[aria-invalid='true']").forEach(function (field) {
        field.removeAttribute("aria-invalid");
      });
      form.querySelectorAll("[data-field-error]").forEach(function (item) {
        item.textContent = "";
      });
    }

    function showFirstNativeError() {
      var invalid = form.querySelector(":invalid");
      if (!invalid) return false;
      invalid.setAttribute("aria-invalid", "true");
      var error = form.querySelector('[data-field-error="' + invalid.name + '"]');
      if (error) error.textContent = invalid.validationMessage;
      invalid.focus();
      return true;
    }

    if (message) message.addEventListener("input", updateCount, { passive: true });
    updateCount();

    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      clearFieldState();
      if (!form.checkValidity()) {
        showFirstNativeError();
        return;
      }
      if (!button || button.disabled) return;

      var original = button.innerHTML;
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      button.innerHTML = '<span>Đang gửi</span><i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i>';
      if (resultBox) resultBox.hidden = true;

      try {
        var csrf = form.querySelector('input[name="csrf_token"]');
        var response = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          credentials: "same-origin",
          headers: {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrf ? csrf.value : ""
          }
        });
        var contentType = response.headers.get("content-type") || "";
        var payload = contentType.indexOf("application/json") >= 0
          ? await response.json()
          : { ok: false, message: "Phiên làm việc đã hết hạn. Vui lòng tải lại trang." };

        if (!response.ok || !payload.ok) {
          throw new Error(payload.message || "Chưa thể gửi lời nhắn lúc này.");
        }

        setResult(resultBox, payload.message, false, payload.reference || "");
        form.reset();
        updateCount();
      } catch (error) {
        setResult(
          resultBox,
          error && error.message ? error.message : "Chưa thể gửi lời nhắn lúc này. Vui lòng thử lại.",
          true,
          ""
        );
      } finally {
        button.disabled = false;
        button.removeAttribute("aria-busy");
        button.innerHTML = original;
      }
    });
  }

  function initAnchors(root) {
    var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    root.querySelectorAll('a[href^="#"]').forEach(function (link) {
      link.addEventListener("click", function (event) {
        var target = root.querySelector(link.getAttribute("href"));
        if (!target) return;
        event.preventDefault();
        target.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
      });
    });
  }

  function initLazyMap(root) {
    var frame = root.querySelector("[data-contact-map-src]");
    if (!frame || frame.dataset.loaded === "1") return;

    function load() {
      if (frame.dataset.loaded === "1") return;
      frame.dataset.loaded = "1";
      frame.src = frame.dataset.contactMapSrc;
    }

    if (!("IntersectionObserver" in window)) {
      load();
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      if (!entries.some(function (entry) { return entry.isIntersecting; })) return;
      load();
      observer.disconnect();
    }, { rootMargin: "280px 0px", threshold: 0.01 });
    observer.observe(frame);
  }

  function initContactPage() {
    var root = document.querySelector("[data-contact-page]");
    if (!root || root.dataset.initialized === "1") return;
    root.dataset.initialized = "1";
    initReveal(root);
    initForm(root);
    initAnchors(root);
    initLazyMap(root);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initContactPage, { once: true });
  } else {
    initContactPage();
  }
})();
