(function () {
  "use strict";

  const prefersReducedMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const TRANSPARENT_PIXEL = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==";
  const FALLBACK = "https://placehold.co/900x1200/010101/fef9ed?text=GUAMAISON";

  function markLoaded(img) {
    const wrap = img.closest(".mm-about-image");
    if (!wrap) return;

    wrap.classList.remove("is-loading");
    wrap.classList.add("is-loaded");
  }

  function markError(img) {
    const wrap = img.closest(".mm-about-image");
    if (!wrap) return;

    wrap.classList.remove("is-loading");
    wrap.classList.add("is-error");
  }

  function loadImage(img) {
    if (!img || img.dataset.loaded === "1") return;

    const src = img.dataset.mmSrc || img.getAttribute("src");

    if (!src || src === TRANSPARENT_PIXEL) {
      markError(img);
      return;
    }

    img.dataset.loaded = "1";

    const preloader = new Image();
    preloader.decoding = "async";

    preloader.onload = function () {
      img.src = src;
      img.removeAttribute("data-mm-src");
      markLoaded(img);
    };

    preloader.onerror = function () {
      img.src = FALLBACK;
      markError(img);
    };

    preloader.src = src;
  }

  function initEagerImages() {
    document.querySelectorAll("[data-about-eager]").forEach(function (img) {
      if (img.complete && img.naturalWidth > 0) {
        markLoaded(img);
      } else {
        img.addEventListener("load", function () {
          markLoaded(img);
        }, { once: true });

        img.addEventListener("error", function () {
          markError(img);
        }, { once: true });
      }
    });
  }

  function initSmartImages() {
    const lazyImages = Array.from(document.querySelectorAll("img[data-mm-src]"));

    if (!lazyImages.length) return;

    if (!("IntersectionObserver" in window)) {
      lazyImages.forEach(loadImage);
      return;
    }

    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;

        loadImage(entry.target);
        observer.unobserve(entry.target);
      });
    }, {
      root: null,
      rootMargin: "420px 0px",
      threshold: 0.01
    });

    lazyImages.forEach(function (img) {
      observer.observe(img);
    });
  }

  function initReveal() {
    const items = document.querySelectorAll(".mm-about-reveal");

    if (!items.length) return;

    if (!("IntersectionObserver" in window) || prefersReducedMotion) {
      items.forEach(function (item) {
        item.classList.add("is-visible");
      });
      return;
    }

    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;

        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, {
      root: null,
      rootMargin: "0px 0px -12% 0px",
      threshold: 0.12
    });

    items.forEach(function (item, index) {
      item.style.transitionDelay = Math.min(index % 5, 4) * 65 + "ms";
      observer.observe(item);
    });
  }

  function initParallax() {
    if (prefersReducedMotion) return;

    const items = Array.from(document.querySelectorAll("[data-parallax]"));
    if (!items.length) return;

    let ticking = false;

    function update() {
      const vh = window.innerHeight || 1;

      items.forEach(function (item) {
        const rect = item.getBoundingClientRect();
        const strength = Number(item.dataset.parallax || 0.06);
        const progress = (rect.top + rect.height / 2 - vh / 2) / vh;
        const y = Math.max(-26, Math.min(26, -progress * 100 * strength));

        item.style.transform = "translate3d(0," + y.toFixed(2) + "px,0)";
      });

      ticking = false;
    }

    function requestUpdate() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(update);
    }

    window.addEventListener("scroll", requestUpdate, { passive: true });
    window.addEventListener("resize", requestUpdate, { passive: true });
    requestUpdate();
  }

  function initTilt() {
    if (
      prefersReducedMotion ||
      !window.matchMedia("(hover: hover) and (pointer: fine)").matches
    ) {
      return;
    }

    document.querySelectorAll("[data-tilt]").forEach(function (item) {
      let frame = null;

      item.addEventListener("mousemove", function (event) {
        if (frame) return;

        frame = requestAnimationFrame(function () {
          const rect = item.getBoundingClientRect();
          const x = (event.clientX - rect.left) / rect.width - .5;
          const y = (event.clientY - rect.top) / rect.height - .5;

          item.style.transform =
            "perspective(1000px) rotateX(" + (-y * 2.2) + "deg) rotateY(" + (x * 2.2) + "deg) translateY(-2px)";

          frame = null;
        });
      }, { passive: true });

      item.addEventListener("mouseleave", function () {
        item.style.transform = "";
      }, { passive: true });
    });
  }

  function initMagneticButtons() {
    if (
      prefersReducedMotion ||
      !window.matchMedia("(hover: hover) and (pointer: fine)").matches
    ) {
      return;
    }

    document.querySelectorAll("[data-magnetic]").forEach(function (btn) {
      let frame = null;

      btn.addEventListener("mousemove", function (event) {
        if (frame) return;

        frame = requestAnimationFrame(function () {
          const rect = btn.getBoundingClientRect();
          const x = (event.clientX - rect.left - rect.width / 2) * .16;
          const y = (event.clientY - rect.top - rect.height / 2) * .16;

          btn.style.transform = "translate3d(" + x.toFixed(2) + "px," + y.toFixed(2) + "px,0)";
          frame = null;
        });
      }, { passive: true });

      btn.addEventListener("mouseleave", function () {
        btn.style.transform = "";
      }, { passive: true });
    });
  }

  function initCursor() {
    if (
      prefersReducedMotion ||
      !window.matchMedia("(hover: hover) and (pointer: fine)").matches
    ) {
      return;
    }

    const cursor = document.querySelector("[data-about-cursor]");
    if (!cursor) return;

    let x = 0;
    let y = 0;
    let tx = 0;
    let ty = 0;

    function loop() {
      x += (tx - x) * .18;
      y += (ty - y) * .18;
      cursor.style.transform = "translate3d(" + x + "px," + y + "px,0) translate(-50%, -50%)";
      requestAnimationFrame(loop);
    }

    document.addEventListener("mousemove", function (event) {
      tx = event.clientX;
      ty = event.clientY;
      cursor.classList.add("is-visible");
    }, { passive: true });

    document.querySelectorAll("a, button, .mm-about-image").forEach(function (item) {
      item.addEventListener("mouseenter", function () {
        cursor.classList.add("is-big");
      }, { passive: true });

      item.addEventListener("mouseleave", function () {
        cursor.classList.remove("is-big");
      }, { passive: true });
    });

    loop();
  }

  function initAboutPage() {
    initEagerImages();
    initSmartImages();
    initReveal();
    initParallax();
    initTilt();
    initMagneticButtons();
    initCursor();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAboutPage, { once: true });
  } else {
    initAboutPage();
  }
})();
