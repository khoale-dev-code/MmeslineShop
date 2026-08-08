(() => {
  "use strict";

  const modal = document.querySelector("[data-size-chart-modal]");
  const openButtons = document.querySelectorAll("[data-size-chart-open]");

  if (!modal || !openButtons.length) return;

  const card = modal.querySelector(".pd-modal-card");
  const closeButtons = modal.querySelectorAll("[data-size-chart-close]");
  const image = modal.querySelector("[data-size-chart-image]");
  const imageError = modal.querySelector("[data-size-chart-error]");
  let lastFocusedElement = null;
  let previousBodyOverflow = "";

  const isOpen = () => modal.classList.contains("open");

  const getFocusableElements = () => Array.from(
    modal.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
  ).filter((element) => element.offsetParent !== null);

  const open = (trigger) => {
    if (isOpen()) return;

    lastFocusedElement = trigger || document.activeElement;
    previousBodyOverflow = document.body.style.overflow;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";

    const focusTarget = modal.querySelector(".pd-size-chart-close") || card;
    window.requestAnimationFrame(() => focusTarget?.focus());
  };

  const close = () => {
    if (!isOpen()) return;

    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = previousBodyOverflow;

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
      card?.focus();
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
})();