(function () {
  "use strict";

  var MOBILE_QUERY = "(max-width: 767.98px)";

  function setupFooter(footer) {
    if (!footer || footer.dataset.footerEnhanced === "true") return;
    footer.dataset.footerEnhanced = "true";

    var media = window.matchMedia(MOBILE_QUERY);
    var toggles = Array.prototype.slice.call(
      footer.querySelectorAll(".gua-footer-column-toggle")
    );

    function syncAccordionMode() {
      toggles.forEach(function (toggle, index) {
        var column = toggle.closest(".gua-footer-column");
        if (media.matches) {
          if (!toggle.dataset.mobileReady) {
            toggle.setAttribute("aria-expanded", index === 0 ? "true" : "false");
            toggle.dataset.mobileReady = "true";
          }
          toggle.removeAttribute("tabindex");
          if (column) column.dataset.expanded = toggle.getAttribute("aria-expanded");
        } else {
          toggle.setAttribute("aria-expanded", "true");
          toggle.setAttribute("tabindex", "-1");
          if (column) delete column.dataset.expanded;
          delete toggle.dataset.mobileReady;
        }
      });
    }

    toggles.forEach(function (toggle) {
      toggle.addEventListener("click", function () {
        if (!media.matches) return;

        var willOpen = toggle.getAttribute("aria-expanded") !== "true";
        toggles.forEach(function (item) {
          item.setAttribute("aria-expanded", "false");
          var itemColumn = item.closest(".gua-footer-column");
          if (itemColumn) itemColumn.dataset.expanded = "false";
        });
        toggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
        var column = toggle.closest(".gua-footer-column");
        if (column) column.dataset.expanded = willOpen ? "true" : "false";
      });
    });

    if (typeof media.addEventListener === "function") {
      media.addEventListener("change", syncAccordionMode);
    } else if (typeof media.addListener === "function") {
      media.addListener(syncAccordionMode);
    }
    syncAccordionMode();

    var toTop = footer.querySelector("[data-footer-to-top]");
    if (toTop) {
      toTop.addEventListener("click", function () {
        var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
      });
    }
  }

  function init() {
    document.querySelectorAll(".gua-footer[data-footer-version='7']").forEach(setupFooter);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }

  window.addEventListener("pageshow", init);
})();
