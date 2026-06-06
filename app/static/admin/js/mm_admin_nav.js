(function () {
  "use strict";

  const SELECTORS = {
    sidebar: "#mmAdminSidebar, #adminSidebar, [data-admin-sidebar]",
    backdrop: "#adminSidebarBackdrop, #mmAdminSidebarBackdrop, [data-admin-sidebar-backdrop]",
    progress: "#mmAdminProgress",

    userDropdown: "#adminUserDropdown",
    userDropdownBackdrop: "#adminUserDropdownBackdrop",
    userMenuButton: "#adminUserMenuButton",
    userMenuChevron: "#adminUserMenuChevron",

    sidebarToggle: "[data-admin-sidebar-toggle], #desktopSidebarToggle",
    mobileMenuToggle: "[data-admin-mobile-menu-toggle], #adminMobileMenuButton, #openAdminSidebar",
    mobileMenuClose: "[data-admin-mobile-menu-close], #closeAdminSidebar"
  };

  const STORAGE_KEYS = {
    collapsed: "mmAdminSidebarCollapsed",
    collapsedLegacy: "mm_admin_sidebar_collapsed"
  };

  const state = {
    progressStarted: false,
    progressTimer: null,
    initialized: false
  };

  function $(selector, root = document) {
    return root.querySelector(selector);
  }

  function $all(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function getSidebar() {
    return $(SELECTORS.sidebar);
  }

  function getBackdrop() {
    return $(SELECTORS.backdrop);
  }

  function isDesktop() {
    return window.matchMedia("(min-width: 1024px)").matches;
  }

  function readCollapsedState() {
    try {
      return (
        localStorage.getItem(STORAGE_KEYS.collapsed) === "1" ||
        localStorage.getItem(STORAGE_KEYS.collapsedLegacy) === "1"
      );
    } catch (_) {
      return false;
    }
  }

  function writeCollapsedState(collapsed) {
    try {
      localStorage.setItem(STORAGE_KEYS.collapsed, collapsed ? "1" : "0");
      localStorage.setItem(STORAGE_KEYS.collapsedLegacy, collapsed ? "1" : "0");
    } catch (_) {}
  }

  function setCollapsed(collapsed) {
    const enabled = Boolean(collapsed);
    const sidebar = getSidebar();

    document.documentElement.classList.toggle("mm-sidebar-collapsed", enabled);
    document.documentElement.classList.toggle("admin-sidebar-collapsed", enabled);
    document.documentElement.classList.toggle("mm-admin-sidebar-collapsed", enabled);

    document.body.classList.toggle("mm-sidebar-collapsed", enabled);
    document.body.classList.toggle("admin-sidebar-collapsed", enabled);
    document.body.classList.toggle("mm-admin-sidebar-collapsed", enabled);

    if (sidebar) {
      sidebar.dataset.collapsed = enabled ? "1" : "0";
      sidebar.setAttribute("aria-expanded", enabled ? "false" : "true");
    }

    $all(SELECTORS.sidebarToggle).forEach((button) => {
      const icon =
        button.querySelector("i") ||
        document.getElementById("desktopSidebarToggleIcon");

      button.setAttribute("aria-expanded", enabled ? "false" : "true");
      button.setAttribute(
        "aria-label",
        enabled ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng"
      );
      button.setAttribute(
        "title",
        enabled ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng"
      );

      if (icon) {
        icon.className = enabled
          ? "fa-solid fa-angles-right"
          : "fa-solid fa-bars-staggered";
      }
    });
  }

  function toggleCollapsed() {
    const next = !document.body.classList.contains("mm-sidebar-collapsed");

    writeCollapsedState(next);
    setCollapsed(next);

    window.dispatchEvent(
      new CustomEvent("mm-admin-sidebar-change", {
        detail: { collapsed: next }
      })
    );
  }

  const Progress = {
    start() {
      const progress = $(SELECTORS.progress);
      if (!progress || state.progressStarted) return;

      state.progressStarted = true;
      clearTimeout(state.progressTimer);

      progress.style.pointerEvents = "none";
      progress.style.opacity = "1";
      progress.style.transition = "none";
      progress.style.width = "0%";

      requestAnimationFrame(() => {
        progress.style.transition = "width 480ms cubic-bezier(0.16, 1, 0.3, 1)";
        progress.style.width = "78%";
      });
    },

    done() {
      const progress = $(SELECTORS.progress);
      if (!progress) return;

      clearTimeout(state.progressTimer);

      progress.style.pointerEvents = "none";
      progress.style.transition = "width 160ms ease-out";
      progress.style.width = "100%";

      state.progressTimer = setTimeout(() => {
        progress.style.transition = "opacity 220ms ease";
        progress.style.opacity = "0";

        setTimeout(() => {
          progress.style.transition = "none";
          progress.style.width = "0%";
          progress.style.opacity = "0";
          state.progressStarted = false;
        }, 240);
      }, 130);
    }
  };

  const AdminShell = {
    openSidebar() {
      const sidebar = getSidebar();
      const backdrop = getBackdrop();

      if (!sidebar) return;

      sidebar.classList.add("is-open");
      sidebar.setAttribute("aria-hidden", "false");

      if (backdrop) {
        backdrop.classList.add("is-open");
        backdrop.setAttribute("aria-hidden", "false");
      }

      document.body.classList.add("admin-sidebar-open", "mm-admin-sidebar-open");

      if (!isDesktop()) {
        document.body.style.overflow = "hidden";
      }
    },

    closeSidebar() {
      const sidebar = getSidebar();
      const backdrop = getBackdrop();

      if (sidebar) {
        sidebar.classList.remove("is-open");
        sidebar.setAttribute("aria-hidden", isDesktop() ? "false" : "true");
      }

      if (backdrop) {
        backdrop.classList.remove("is-open");
        backdrop.setAttribute("aria-hidden", "true");
      }

      document.body.classList.remove("admin-sidebar-open", "mm-admin-sidebar-open");

      if (!document.body.classList.contains("mm-modal-open")) {
        document.body.style.overflow = "";
      }
    },

    toggleSidebar() {
      const sidebar = getSidebar();

      if (!sidebar) return;

      if (isDesktop()) {
        toggleCollapsed();
        return;
      }

      if (sidebar.classList.contains("is-open")) {
        this.closeSidebar();
      } else {
        this.openSidebar();
      }
    },

    toggleDesktopSidebar() {
      toggleCollapsed();
    },

    openUserMenu() {
      const dropdown = $(SELECTORS.userDropdown);
      const backdrop = $(SELECTORS.userDropdownBackdrop);
      const button = $(SELECTORS.userMenuButton);
      const chevron = $(SELECTORS.userMenuChevron);

      if (!dropdown || !backdrop) return;

      dropdown.classList.remove("hidden");
      dropdown.setAttribute("aria-hidden", "false");

      backdrop.classList.remove("hidden");
      backdrop.setAttribute("aria-hidden", "false");

      button?.classList.add("is-open");
      button?.setAttribute("aria-expanded", "true");

      if (chevron) {
        chevron.style.transform = "rotate(180deg)";
      }
    },

    closeUserMenu() {
      const dropdown = $(SELECTORS.userDropdown);
      const backdrop = $(SELECTORS.userDropdownBackdrop);
      const button = $(SELECTORS.userMenuButton);
      const chevron = $(SELECTORS.userMenuChevron);

      if (!dropdown || !backdrop) return;

      dropdown.classList.add("hidden");
      dropdown.setAttribute("aria-hidden", "true");

      backdrop.classList.add("hidden");
      backdrop.setAttribute("aria-hidden", "true");

      button?.classList.remove("is-open");
      button?.setAttribute("aria-expanded", "false");

      if (chevron) {
        chevron.style.transform = "rotate(0deg)";
      }
    },

    toggleUserMenu(event) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }

      const dropdown = $(SELECTORS.userDropdown);
      if (!dropdown) return;

      if (dropdown.classList.contains("hidden")) {
        this.openUserMenu();
      } else {
        this.closeUserMenu();
      }
    }
  };

  function shouldHandleNav(anchor) {
    const href = anchor.getAttribute("href");

    if (!href) return false;
    if (href.startsWith("#")) return false;
    if (anchor.target === "_blank") return false;
    if (anchor.hasAttribute("download")) return false;

    try {
      const url = new URL(href, window.location.origin);

      if (url.origin !== window.location.origin) return false;

      if (
        url.pathname === window.location.pathname &&
        url.search === window.location.search
      ) {
        return false;
      }

      return true;
    } catch (_) {
      return false;
    }
  }

  function prefetchUrl(href) {
    if (!href) return;

    try {
      const url = new URL(href, window.location.origin);

      if (url.origin !== window.location.origin) return;
      if (document.querySelector(`link[rel="prefetch"][href="${url.href}"]`)) return;

      const link = document.createElement("link");
      link.rel = "prefetch";
      link.href = url.href;
      link.as = "document";
      document.head.appendChild(link);
    } catch (_) {}
  }

  function initSidebarState() {
    const sidebar = getSidebar();
    const backdrop = getBackdrop();

    setCollapsed(readCollapsedState());

    if (sidebar) {
      sidebar.setAttribute("aria-hidden", isDesktop() ? "false" : "true");
    }

    if (backdrop) {
      backdrop.setAttribute("aria-hidden", "true");
    }
  }

  function initSidebarControls() {
    document.addEventListener("click", (event) => {
      const toggle = event.target.closest(SELECTORS.sidebarToggle);
      if (toggle) {
        event.preventDefault();
        event.stopPropagation();

        if (isDesktop()) {
          toggleCollapsed();
        } else {
          AdminShell.toggleSidebar();
        }

        return;
      }

      const openButton = event.target.closest(SELECTORS.mobileMenuToggle);
      if (openButton) {
        event.preventDefault();
        event.stopPropagation();
        AdminShell.openSidebar();
        return;
      }

      const closeButton = event.target.closest(SELECTORS.mobileMenuClose);
      if (closeButton) {
        event.preventDefault();
        event.stopPropagation();
        AdminShell.closeSidebar();
        return;
      }

      const backdrop = event.target.closest(SELECTORS.backdrop);
      if (backdrop && backdrop.classList.contains("is-open")) {
        event.preventDefault();
        AdminShell.closeSidebar();
      }
    });

    window.addEventListener("storage", (event) => {
      if (
        event.key === STORAGE_KEYS.collapsed ||
        event.key === STORAGE_KEYS.collapsedLegacy
      ) {
        setCollapsed(readCollapsedState());
      }
    });

    window.addEventListener("resize", () => {
      if (isDesktop()) {
        AdminShell.closeSidebar();
        const sidebar = getSidebar();
        sidebar?.setAttribute("aria-hidden", "false");
      }
    }, { passive: true });
  }

  function initUserMenu() {
    const button = $(SELECTORS.userMenuButton);
    const backdrop = $(SELECTORS.userDropdownBackdrop);

    button?.addEventListener("click", (event) => {
      AdminShell.toggleUserMenu(event);
    });

    backdrop?.addEventListener("click", () => {
      AdminShell.closeUserMenu();
    });

    document.addEventListener("click", (event) => {
      const dropdown = $(SELECTORS.userDropdown);
      const menuButton = $(SELECTORS.userMenuButton);

      if (!dropdown || dropdown.classList.contains("hidden")) return;
      if (dropdown.contains(event.target)) return;
      if (menuButton && menuButton.contains(event.target)) return;

      AdminShell.closeUserMenu();
    });
  }

  function initPrefetch() {
    $all("a[data-prefetch]").forEach((anchor) => {
      const href = anchor.getAttribute("href");

      anchor.addEventListener("mouseenter", () => prefetchUrl(href), { passive: true });
      anchor.addEventListener("focus", () => prefetchUrl(href), { passive: true });
      anchor.addEventListener("touchstart", () => prefetchUrl(href), { passive: true });
    });
  }

  function initNavigationProgress() {
    $all("a[data-nav]").forEach((anchor) => {
      anchor.addEventListener("click", () => {
        if (!shouldHandleNav(anchor)) return;

        anchor.classList.add("is-loading");
        Progress.start();
        AdminShell.closeSidebar();
        AdminShell.closeUserMenu();
      });
    });

    $all("form[data-form-nav]").forEach((form) => {
      form.addEventListener("submit", () => {
        const button = form.querySelector('button[type="submit"]');

        if (button) {
          button.disabled = true;
          button.classList.add("opacity-70", "cursor-not-allowed");
        }

        Progress.start();
        AdminShell.closeUserMenu();
      });
    });

    window.addEventListener("pageshow", () => Progress.done());
    window.addEventListener("load", () => Progress.done());
    window.addEventListener("beforeunload", () => Progress.start());
  }

  function initKeyboardShortcuts() {
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        AdminShell.closeSidebar();
        AdminShell.closeUserMenu();
      }

      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
        event.preventDefault();
        AdminShell.toggleDesktopSidebar();
      }
    });
  }

  function exposeGlobals() {
    window.AdminShell = AdminShell;
    window.AdminProgress = Progress;

    window.MMAdminLayout = window.MMAdminLayout || {};
    window.MMAdminLayout.applySidebarState = function () {
      setCollapsed(readCollapsedState());
    };
    window.MMAdminLayout.toggleSidebarCollapsed = toggleCollapsed;
    window.MMAdminLayout.openSidebar = AdminShell.openSidebar.bind(AdminShell);
    window.MMAdminLayout.closeSidebar = AdminShell.closeSidebar.bind(AdminShell);
  }

  function init() {
    if (state.initialized) return;
    state.initialized = true;

    initSidebarState();
    initSidebarControls();
    initUserMenu();
    initPrefetch();
    initNavigationProgress();
    initKeyboardShortcuts();
    exposeGlobals();

    Progress.done();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();