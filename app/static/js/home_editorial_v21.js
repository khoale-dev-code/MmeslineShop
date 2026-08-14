(() => {
  "use strict";

  const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  function revealElements() {
    const elements = Array.from(document.querySelectorAll("[data-latest-reveal], [data-home-media-reveal]"));
    if (!elements.length) return;

    if (reducedMotion || !("IntersectionObserver" in window)) {
      elements.forEach((element) => element.classList.add("is-revealed"));
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-revealed");
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -7% 0px", threshold: 0.12 });

    elements.forEach((element) => observer.observe(element));
  }

  function latestProgress() {
    const viewport = document.querySelector("[data-latest-viewport]");
    const progress = document.querySelector("[data-latest-progress]");
    if (!viewport || !progress) return;

    let frame = 0;
    const update = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(() => {
        const maximum = Math.max(0, viewport.scrollWidth - viewport.clientWidth);
        const ratio = maximum ? viewport.scrollLeft / maximum : 1;
        progress.style.width = `${Math.max(12, Math.min(100, ratio * 100))}%`;
        frame = 0;
      });
    };

    viewport.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update, { passive: true });
    update();
  }

  function socialVideos() {
    const videos = Array.from(document.querySelectorAll("[data-home-social-video]"));
    if (!videos.length) return;

    videos.forEach((video) => {
      video.muted = true;
      video.playsInline = true;
    });

    if (reducedMotion || !("IntersectionObserver" in window)) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const video = entry.target;
        if (entry.isIntersecting && entry.intersectionRatio >= 0.35) {
          const promise = video.play();
          promise?.catch?.(() => {});
        } else {
          video.pause();
        }
      });
    }, { rootMargin: "100px 0px", threshold: [0, 0.35, 0.8] });

    videos.forEach((video) => observer.observe(video));
  }

  function init() {
    revealElements();
    latestProgress();
    socialVideos();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
