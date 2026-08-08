(function () {
  "use strict";

  if (window.GUAClientRouter && window.GUAClientRouter.version) {
    return;
  }

  var VERSION = "20260807.5";
  var root = document.documentElement;
  var status = document.querySelector("[data-client-route-status]");
  var label = document.querySelector("[data-client-route-label]");
  var initialHref = window.location.href;
  var busy = false;
  var labelTimer = 0;
  var resetTimer = 0;
  var prefetchCount = 0;
  var prefetched = Object.create(null);
  var prefetchTimers = new WeakMap();

  var PUBLIC_EXACT_PATHS = [
    "/",
    "/home",
    "/shop",
    "/collections",
    "/about",
    "/contact",
    "/size-guide"
  ];

  var PUBLIC_PATH_PREFIXES = [
    "/product/",
    "/collections/"
  ];

  function toUrl(value) {
    try {
      return new URL(String(value || ""), window.location.href);
    } catch (_) {
      return null;
    }
  }

  function sameDocumentHashOnly(url) {
    return Boolean(
      url &&
      url.origin === window.location.origin &&
      url.pathname === window.location.pathname &&
      url.search === window.location.search &&
      url.hash
    );
  }

  function isHttpUrl(url) {
    return Boolean(url && (url.protocol === "http:" || url.protocol === "https:"));
  }

  function isEligibleLink(link, event) {
    if (!link || !link.href) return false;
    if (event && event.button !== 0) return false;
    if (event && (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)) {
      return false;
    }
    if (link.hasAttribute("download")) return false;
    if (link.target && link.target.toLowerCase() !== "_self") return false;
    if (link.closest("[data-router-ignore], [data-no-router]")) return false;

    var rel = (link.getAttribute("rel") || "").toLowerCase();
    if (rel.split(/\s+/).indexOf("external") !== -1) return false;

    var url = toUrl(link.href);
    if (!isHttpUrl(url) || url.origin !== window.location.origin) return false;
    if (sameDocumentHashOnly(url)) return false;

    return url;
  }

  function setLabel(message) {
    if (label) {
      label.textContent = message || "Đang mở trang...";
    }
  }

  function begin(message) {
    if (busy) return false;

    busy = true;
    window.clearTimeout(labelTimer);
    window.clearTimeout(resetTimer);

    setLabel(message);
    root.classList.add("gua-route-pending");

    if (document.body) {
      document.body.setAttribute("aria-busy", "true");
    }

    labelTimer = window.setTimeout(function () {
      if (status && busy) {
        status.hidden = false;
      }
    }, 140);

    // Recovery guard for a navigation cancelled by another page component.
    resetTimer = window.setTimeout(function () {
      if (window.location.href === initialHref && document.visibilityState === "visible") {
        reset();
      }
    }, 6500);

    return true;
  }

  function reset() {
    busy = false;
    window.clearTimeout(labelTimer);
    window.clearTimeout(resetTimer);
    root.classList.remove("gua-route-pending");

    if (document.body) {
      document.body.removeAttribute("aria-busy");
    }

    if (status) {
      status.hidden = true;
    }
  }

  function navigate(value, options) {
    var url = toUrl(value);
    var config = options || {};

    if (!url) return false;

    if (!isHttpUrl(url) || url.origin !== window.location.origin) {
      window.location.assign(url.href);
      return true;
    }

    if (sameDocumentHashOnly(url)) {
      window.location.assign(url.href);
      return true;
    }

    if (!begin(config.label || "Đang mở trang...")) {
      return false;
    }

    window.requestAnimationFrame(function () {
      if (config.replace) {
        window.location.replace(url.href);
      } else {
        window.location.assign(url.href);
      }
    });

    return true;
  }

  function isPublicPrefetchUrl(url) {
    if (!url || url.origin !== window.location.origin) return false;
    if (url.hash && sameDocumentHashOnly(url)) return false;

    if (PUBLIC_EXACT_PATHS.indexOf(url.pathname) !== -1) {
      return true;
    }

    return PUBLIC_PATH_PREFIXES.some(function (prefix) {
      return url.pathname.indexOf(prefix) === 0;
    });
  }

  function connectionAllowsPrefetch() {
    var connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;

    if (!connection) return true;
    if (connection.saveData) return false;

    return ["slow-2g", "2g"].indexOf(connection.effectiveType) === -1;
  }

  function hasPrefetchLink(href) {
    return Array.prototype.some.call(
      document.querySelectorAll('link[rel="prefetch"]'),
      function (item) {
        return item.href === href;
      }
    );
  }

  function prefetch(value) {
    var url = toUrl(value);

    if (
      !isPublicPrefetchUrl(url) ||
      !connectionAllowsPrefetch() ||
      prefetchCount >= 6 ||
      prefetched[url.href] ||
      hasPrefetchLink(url.href)
    ) {
      return false;
    }

    prefetched[url.href] = true;
    prefetchCount += 1;

    var hint = document.createElement("link");
    hint.rel = "prefetch";
    hint.as = "document";
    hint.href = url.href;
    hint.setAttribute("fetchpriority", "low");
    document.head.appendChild(hint);

    return true;
  }

  function schedulePrefetch(link) {
    var url = isEligibleLink(link);

    if (!url || !isPublicPrefetchUrl(url) || prefetchTimers.has(link)) {
      return;
    }

    var timer = window.setTimeout(function () {
      prefetchTimers.delete(link);
      prefetch(url.href);
    }, 110);

    prefetchTimers.set(link, timer);
  }

  function cancelPrefetch(link) {
    if (!link || !prefetchTimers.has(link)) return;
    window.clearTimeout(prefetchTimers.get(link));
    prefetchTimers.delete(link);
  }

  document.addEventListener("click", function (event) {
    var link = event.target.closest ? event.target.closest("a[href]") : null;
    var url = isEligibleLink(link, event);

    if (!url) return;

    var before = window.location.href;

    queueMicrotask(function () {
      var programmaticNavigationStarted = window.location.href !== before;

      if (event.defaultPrevented && !programmaticNavigationStarted) {
        return;
      }

      begin("Đang mở trang...");
    });
  }, true);

  document.addEventListener("submit", function (event) {
    var form = event.target;

    if (!(form instanceof HTMLFormElement)) return;
    if (form.closest("[data-router-ignore], [data-no-router]")) return;
    if (form.target && form.target.toLowerCase() !== "_self") return;

    var url = toUrl(form.action || window.location.href);
    if (!url || url.origin !== window.location.origin) return;

    queueMicrotask(function () {
      if (event.defaultPrevented) return;

      var method = String(form.method || "get").toLowerCase();
      begin(method === "get" ? "Đang tìm kiếm..." : "Đang xử lý...");
    });
  }, true);

  document.addEventListener("pointerover", function (event) {
    if (!event.target.closest) return;
    schedulePrefetch(event.target.closest("a[href]"));
  }, { passive: true, capture: true });

  document.addEventListener("pointerout", function (event) {
    if (!event.target.closest) return;
    cancelPrefetch(event.target.closest("a[href]"));
  }, { passive: true, capture: true });

  document.addEventListener("focusin", function (event) {
    if (!event.target.closest) return;
    schedulePrefetch(event.target.closest("a[href]"));
  }, true);

  window.addEventListener("pageshow", function () {
    initialHref = window.location.href;
    reset();
  });

  window.addEventListener("pagehide", function () {
    window.clearTimeout(labelTimer);
    window.clearTimeout(resetTimer);
  });

  window.GUAClientRouter = Object.freeze({
    version: VERSION,
    begin: begin,
    reset: reset,
    navigate: navigate,
    prefetch: prefetch,
    isBusy: function () {
      return busy;
    }
  });
})();
