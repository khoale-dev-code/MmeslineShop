(() => {
  "use strict";

  const modal = document.querySelector("[data-size-chart-modal]");
  const openButtons = document.querySelectorAll("[data-size-chart-open]");

  if (!modal || !openButtons.length) return;

  // Render as a body-level portal so navbar transforms/z-index cannot cover it.
  if (modal.parentElement !== document.body) {
    document.body.appendChild(modal);
  }

  const dialog = modal.querySelector(".pd-size-chart-dialog");
  const closeButtons = modal.querySelectorAll("[data-size-chart-close]");
  const image = modal.querySelector("[data-size-chart-image]");
  const imageError = modal.querySelector("[data-size-chart-error]");

  let lastFocusedElement = null;

  const isOpen = () => modal.classList.contains("is-open");

  const getFocusableElements = () => Array.from(
    modal.querySelectorAll(
      'button:not([disabled]):not([tabindex="-1"]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
  ).filter((element) => !element.hidden && element.offsetParent !== null);

  const lockPage = () => {
    document.documentElement.classList.add("has-size-chart-modal");
    document.body.classList.add("has-size-chart-modal");
  };

  const unlockPage = () => {
    document.documentElement.classList.remove("has-size-chart-modal");
    document.body.classList.remove("has-size-chart-modal");
  };

  const open = (trigger) => {
    if (isOpen()) return;

    lastFocusedElement = trigger || document.activeElement;
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    lockPage();

    const focusTarget = modal.querySelector(".pd-size-chart-close") || dialog;
    window.requestAnimationFrame(() => focusTarget?.focus());
  };

  const close = () => {
    if (!isOpen()) return;

    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    unlockPage();

    if (lastFocusedElement instanceof HTMLElement) {
      lastFocusedElement.focus();
    }
  };

  openButtons.forEach((button) => {
    button.addEventListener("click", () => open(button));
  });

  closeButtons.forEach((button) => {
    button.addEventListener("click", close);
  });

  modal.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }

    if (event.key !== "Tab") return;

    const focusable = getFocusableElements();
    if (!focusable.length) {
      event.preventDefault();
      dialog?.focus();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  image?.addEventListener("error", () => {
    image.hidden = true;
    if (imageError) imageError.hidden = false;
  });

  window.addEventListener("pagehide", unlockPage);
})();
