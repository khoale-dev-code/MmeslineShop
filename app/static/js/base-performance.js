/* ==========================================================================
   app/static/js/base-performance.js
   GUAMAISON - Stable Base JS
   Fix:
   - Không chặn scroll dọc.
   - Không auto lazy ảnh bằng JS để tránh mất ảnh.
   - Không dùng pointermove kéo carousel.
   - Chỉ tối ưu video và anchor scroll nhẹ.
========================================================================== */

(function () {
  "use strict";

  var SCROLLER_SELECTOR = [
    "[data-mm-x-scroll]",
    "[data-featured-scroll]",
    "[data-home-collection-scroll]",
    "[data-horizontal-scroll]",
    ".mm-x-viewport",
    ".mm-horizontal-scroll",
    "#slider-container"
  ].join(",");

  var PAGE_LOCK_CLASS = "mm-page-locked";
  var OLD_SCROLL_LOCK_CLASS = "mm-scroll-locked";

  var videoObserver = null;
  var anchorReady = false;
  var globalApiReady = false;
  var resizeTimer = null;

  function qs(selector, root) {
    try {
      return (root || document).querySelector(selector);
    } catch (_) {
      return null;
    }
  }

  function qsa(selector, root) {
    try {
      return Array.prototype.slice.call((root || document).querySelectorAll(selector));
    } catch (_) {
      return [];
    }
  }

  function getCSRFToken() {
    var meta = qs('meta[name="csrf-token"]');

    if (meta) {
      return meta.getAttribute("content") || "";
    }

    var input = qs('input[name="csrf_token"]');

    if (input) {
      return input.value || "";
    }

    return "";
  }

  function safeJson(response) {
    return response.text().then(function (text) {
      if (!text) return {};

      try {
        return JSON.parse(text);
      } catch (_) {
        return {};
      }
    });
  }

  function isReducedMotion() {
    return Boolean(
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function cleanupScrollLocks() {
    /*
      Class cũ từng gây lỗi không scroll được.
    */
    document.body.classList.remove(OLD_SCROLL_LOCK_CLASS);

    if (!document.body.classList.contains("mm-mobile-menu-open") &&
        !document.body.classList.contains("mm-modal-open") &&
        !document.documentElement.classList.contains(PAGE_LOCK_CLASS)) {
      if (document.body.style.overflow === "hidden") {
        document.body.style.overflow = "";
      }

      if (document.documentElement.style.overflow === "hidden") {
        document.documentElement.style.overflow = "";
      }
    }
  }

  function lockPageScroll() {
    document.documentElement.classList.add(PAGE_LOCK_CLASS);
  }

  function unlockPageScroll() {
    document.documentElement.classList.remove(PAGE_LOCK_CLASS);
    cleanupScrollLocks();
  }

  function showToast(message, isError) {
    var wrap = document.getElementById("mmToastWrap");

    if (!wrap) {
      wrap = document.createElement("div");
      wrap.id = "mmToastWrap";
      wrap.className = "fixed bottom-6 left-1/2 -translate-x-1/2 z-[9999] flex flex-col gap-2";
      document.body.appendChild(wrap);
    }

    while (wrap.children.length >= 4) {
      wrap.firstElementChild.remove();
    }

    var toast = document.createElement("div");
    toast.className =
      "bg-white px-5 py-3 border shadow-lg text-[11px] font-bold uppercase tracking-widest " +
      (isError ? "border-red-500 text-red-600" : "border-neutral-200 text-black");

    toast.textContent = message || "";
    wrap.appendChild(toast);

    window.setTimeout(function () {
      toast.remove();
    }, 2500);
  }

  async function toggleHeart(productId, btn) {
    if (window.event && typeof window.event.preventDefault === "function") {
      window.event.preventDefault();
    }

    var icon = btn && btn.querySelector ? btn.querySelector(".heart-icon") : null;

    if (!productId) {
      showToast("Không tìm thấy sản phẩm", true);
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.classList.add("opacity-60", "pointer-events-none");
    }

    try {
      var res = await fetch("/api/favorites/toggle", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken()
        },
        body: JSON.stringify({
          product_id: productId
        })
      });

      if (res.status === 401) {
        showToast("Vui lòng đăng nhập", true);

        window.setTimeout(function () {
          window.location.href = "/auth/login";
        }, 1000);

        return;
      }

      var data = await safeJson(res);

      if (!res.ok) {
        throw new Error(data.message || data.error || "Không thể cập nhật yêu thích");
      }

      if (data.status === "success") {
        var added = data.action === "added";

        if (icon) {
          icon.classList.toggle("text-neutral-300", !added);
          icon.classList.toggle("text-black", added);
          icon.classList.toggle("fill-black", added);
        }

        showToast(added ? "Đã thêm vào yêu thích" : "Đã xóa khỏi yêu thích");
      }
    } catch (err) {
      showToast(err.message || "Lỗi kết nối", true);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.classList.remove("opacity-60", "pointer-events-none");
      }
    }
  }

  function getHeaderOffset() {
    var rootStyle = getComputedStyle(document.documentElement);
    var headerH = parseFloat(rootStyle.getPropertyValue("--header-h")) || 72;
    var topbarH = parseFloat(rootStyle.getPropertyValue("--topbar-h")) || 0;

    return headerH + topbarH + 16;
  }

  function scrollToTarget(target, options) {
    var el = null;

    if (typeof target === "string") {
      try {
        el = document.querySelector(target);
      } catch (_) {
        el = null;
      }
    } else if (target instanceof Element) {
      el = target;
    }

    if (!el) return;

    var rect = el.getBoundingClientRect();
    var top = window.scrollY + rect.top - getHeaderOffset();

    window.scrollTo({
      top: Math.max(0, top),
      behavior: isReducedMotion() ? "auto" : ((options && options.behavior) || "smooth")
    });
  }

  function initGlobalAPI() {
    if (globalApiReady) return;

    globalApiReady = true;

    window.getCSRFToken = getCSRFToken;
    window.showToast = showToast;
    window.toggleHeart = toggleHeart;

    window.MMScroll = {
      instance: null,
      stop: lockPageScroll,
      start: unlockPageScroll,
      resize: function () {},
      scrollTo: scrollToTarget
    };

    window.MMScrollDebug = {
      unlock: unlockPageScroll,
      cleanupLocks: cleanupScrollLocks,
      diagnostics: function () {
        var main = document.getElementById("main-content");

        return {
          scrollY: window.scrollY,
          htmlOverflowY: getComputedStyle(document.documentElement).overflowY,
          bodyOverflowY: getComputedStyle(document.body).overflowY,
          mainOverflowY: main ? getComputedStyle(main).overflowY : null,
          htmlClass: document.documentElement.className,
          bodyClass: document.body.className,
          htmlInlineOverflow: document.documentElement.style.overflow || "",
          bodyInlineOverflow: document.body.style.overflow || "",
          documentHeight: document.documentElement.scrollHeight,
          viewportHeight: window.innerHeight
        };
      }
    };
  }

  function initAnchorScroll() {
    if (anchorReady) return;

    anchorReady = true;

    document.addEventListener("click", function (e) {
      var link = e.target && e.target.closest
        ? e.target.closest('a[href^="#"]')
        : null;

      if (!link) return;

      var href = link.getAttribute("href");

      if (!href || href === "#") return;

      var target = null;

      try {
        target = document.querySelector(href);
      } catch (_) {
        target = null;
      }

      if (!target) return;

      e.preventDefault();
      scrollToTarget(target);
    });
  }

  function initRevealSafe() {
    qsa("[data-reveal]").forEach(function (el) {
      el.classList.add("is-visible");
      el.style.opacity = "1";
      el.style.transform = "none";
      el.style.animation = "none";
      el.style.transition = "none";
      el.style.willChange = "auto";
    });
  }

  function prepareVideo(video) {
    if (!(video instanceof HTMLVideoElement)) return;

    video.muted = true;
    video.playsInline = true;
    video.setAttribute("playsinline", "");
    video.setAttribute("webkit-playsinline", "");

    if (!video.hasAttribute("preload")) {
      video.setAttribute("preload", "metadata");
    }

    if (isReducedMotion()) {
      video.pause();

      if (video.hasAttribute("autoplay")) {
        video.removeAttribute("autoplay");
      }
    }
  }

  function playVideo(video) {
    if (!(video instanceof HTMLVideoElement)) return;
    if (isReducedMotion()) return;

    try {
      var promise = video.play();

      if (promise && typeof promise.catch === "function") {
        promise.catch(function () {});
      }
    } catch (_) {}
  }

  function pauseVideo(video) {
    if (!(video instanceof HTMLVideoElement)) return;

    try {
      video.pause();
    } catch (_) {}
  }

  function initVideoObserver() {
    var videos = qsa("video[autoplay], .mm-video, [data-scroll-video]");

    if (!videos.length) return;

    videos.forEach(prepareVideo);

    if (!("IntersectionObserver" in window)) return;

    if (videoObserver) {
      videoObserver.disconnect();
      videoObserver = null;
    }

    videoObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var video = entry.target;

        if (!(video instanceof HTMLVideoElement)) return;

        if (entry.isIntersecting && entry.intersectionRatio > 0.1) {
          playVideo(video);
        } else {
          pauseVideo(video);
        }
      });
    }, {
      threshold: [0, 0.1, 0.3],
      rootMargin: "120px 0px 160px 0px"
    });

    videos.forEach(function (video) {
      if (video instanceof HTMLVideoElement) {
        videoObserver.observe(video);
      }
    });
  }

  function initHorizontalWheelSupport() {
    /*
      Không chặn wheel dọc.
      Chỉ Shift + wheel mới chuyển thành cuộn ngang.
    */
    qsa(SCROLLER_SELECTOR).forEach(function (scroller) {
      if (!(scroller instanceof HTMLElement)) return;
      if (scroller.dataset.mmWheelReady === "1") return;

      scroller.dataset.mmWheelReady = "1";

      scroller.addEventListener("wheel", function (e) {
        if (!e.shiftKey) return;
        if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
        if (scroller.scrollWidth <= scroller.clientWidth + 4) return;

        e.preventDefault();
        scroller.scrollLeft += e.deltaY;
      }, {
        passive: false
      });
    });
  }

  function updateProgress(scroller, progress) {
    if (!(scroller instanceof HTMLElement)) return;
    if (!(progress instanceof HTMLElement)) return;

    var max = scroller.scrollWidth - scroller.clientWidth;

    if (max <= 0) {
      progress.style.width = "100%";
      return;
    }

    var percent = (scroller.scrollLeft / max) * 100;
    progress.style.width = Math.max(8, Math.min(100, percent)) + "%";
  }

  function bindProgress(scroller, progress) {
    if (!(scroller instanceof HTMLElement)) return;
    if (!(progress instanceof HTMLElement)) return;
    if (progress.dataset.mmProgressReady === "1") return;

    progress.dataset.mmProgressReady = "1";

    var ticking = false;

    function scheduleUpdate() {
      if (ticking) return;

      ticking = true;

      requestAnimationFrame(function () {
        updateProgress(scroller, progress);
        ticking = false;
      });
    }

    scroller.addEventListener("scroll", scheduleUpdate, {
      passive: true
    });

    updateProgress(scroller, progress);
  }

  function initProgressBars() {
    bindProgress(
      qs("[data-home-collection-scroll]"),
      qs("[data-collection-progress]")
    );

    bindProgress(
      qs("[data-featured-scroll]"),
      qs("[data-featured-progress]")
    );
  }

  function initPage() {
    document.documentElement.classList.remove("mm-no-fouc");
    document.documentElement.classList.add("mm-page-ready");

    cleanupScrollLocks();
    initGlobalAPI();
    initAnchorScroll();
    initRevealSafe();
    initVideoObserver();
    initHorizontalWheelSupport();
    initProgressBars();

    window.addEventListener("pageshow", function () {
      cleanupScrollLocks();
      initRevealSafe();
      initProgressBars();
    }, {
      passive: true
    });

    window.addEventListener("resize", function () {
      window.clearTimeout(resizeTimer);

      resizeTimer = window.setTimeout(function () {
        cleanupScrollLocks();
        initProgressBars();
      }, 180);
    }, {
      passive: true
    });
  }

  function destroy() {
    if (videoObserver) {
      videoObserver.disconnect();
      videoObserver = null;
    }

    window.clearTimeout(resizeTimer);
  }

  window.addEventListener("beforeunload", destroy);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPage, {
      once: true
    });
  } else {
    initPage();
  }
})();