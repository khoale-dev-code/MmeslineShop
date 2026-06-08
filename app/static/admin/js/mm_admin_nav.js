(function () {
  "use strict";

  const CONFIG = {
    fullWidth: 300,
    miniWidth: 92,
    breakpoint: 1024,
    storageKeys: [
      "mm_admin_sidebar_collapsed",
      "mmAdminSidebarCollapsed",
      "admin_sidebar_collapsed"
    ]
  };

  const SELECTOR = {
    sidebar: "#mmAdminSidebar, #adminSidebar, [data-admin-sidebar]",
    sidebarToggle: "[data-admin-sidebar-toggle]",
    mobileToggle: "[data-admin-mobile-menu-toggle]",
    mobileClose: "[data-admin-mobile-menu-close]",
    backdrop: "#mmAdminSidebarBackdrop, #adminSidebarBackdrop, [data-admin-sidebar-backdrop]",

    topbar: "#adminTopbar, .mm-topbar",
    main: "#adminMain, .admin-main, .mm-admin-main",

    userButton: "#adminUserMenuButton",
    userDropdown: "#adminUserDropdown",
    userBackdrop: "#adminUserDropdownBackdrop",
    userChevron: "#adminUserMenuChevron",

    progress: "#mmAdminProgress",
    navLink: "a[data-nav]",
    prefetchLink: "a[data-prefetch]",
    navForm: "form[data-form-nav]"
  };

  const CLASS = {
    collapsed: [
      "mm-admin-sidebar-collapsed",
      "mm-sidebar-collapsed",
      "admin-sidebar-collapsed"
    ],
    mobileOpen: [
      "mm-admin-mobile-sidebar-open",
      "admin-sidebar-open",
      "mm-sidebar-open"
    ],
    loading: "mm-admin-loading",
    open: "is-open",
    hidden: "hidden"
  };

  let initialized = false;
  let progressTimer = null;
  let resizeTimer = null;

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function isDesktop() {
    return window.innerWidth >= CONFIG.breakpoint;
  }

  function getSidebar() {
    return $(SELECTOR.sidebar);
  }

  function getTopbar() {
    return $(SELECTOR.topbar);
  }

  function getMain() {
    return $(SELECTOR.main);
  }

  function getBackdrop() {
    return $(SELECTOR.backdrop);
  }

  function setRootClasses(classNames, enabled) {
    classNames.forEach((name) => {
      document.documentElement.classList.toggle(name, enabled);
      document.body.classList.toggle(name, enabled);
    });
  }

  function readCollapsed() {
    try {
      return CONFIG.storageKeys.some((key) => localStorage.getItem(key) === "1");
    } catch (_) {
      return false;
    }
  }

  function saveCollapsed(collapsed) {
    try {
      CONFIG.storageKeys.forEach((key) => {
        localStorage.setItem(key, collapsed ? "1" : "0");
      });
    } catch (_) {}
  }

  function isCollapsed() {
    return CLASS.collapsed.some((name) => {
      return (
        document.documentElement.classList.contains(name) ||
        document.body.classList.contains(name)
      );
    });
  }

  function setCssVar(name, value) {
    document.documentElement.style.setProperty(name, value);
    document.body.style.setProperty(name, value);
  }

  function applyLayout(collapsed) {
    const sidebar = getSidebar();
    const topbar = getTopbar();
    const main = getMain();

    const width = collapsed ? CONFIG.miniWidth : CONFIG.fullWidth;
    const widthPx = width + "px";

    setCssVar("--mm-admin-sidebar-w", widthPx);
    setCssVar("--admin-sidebar-width", widthPx);
    setCssVar("--admin-content-ml", widthPx);

    if (isDesktop()) {
      if (sidebar) {
        sidebar.style.width = widthPx;
        sidebar.style.transform = "translateX(0)";
        sidebar.setAttribute("aria-hidden", "false");
      }

      if (topbar) {
        topbar.style.left = widthPx;
      }

      if (main) {
        main.style.marginLeft = widthPx;
      }

      document.body.style.overflow = "";
    } else {
      if (sidebar) {
        sidebar.style.width = "";
      }

      if (topbar) {
        topbar.style.left = "0px";
      }

      if (main) {
        main.style.marginLeft = "0px";
      }
    }
  }

  function setCollapsed(collapsed, shouldSave = true) {
    const enabled = Boolean(collapsed);
    const sidebar = getSidebar();

    setRootClasses(CLASS.collapsed, enabled);
    applyLayout(enabled);

    if (sidebar) {
      sidebar.dataset.collapsed = enabled ? "1" : "0";
      sidebar.setAttribute("aria-expanded", enabled ? "false" : "true");
      sidebar.setAttribute("aria-hidden", "false");
    }

    $$(SELECTOR.sidebarToggle).forEach((button) => {
      button.setAttribute("aria-expanded", enabled ? "false" : "true");
      button.setAttribute(
        "aria-label",
        enabled ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng"
      );
      button.setAttribute(
        "title",
        enabled ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng"
      );
    });

    if (shouldSave) saveCollapsed(enabled);

    window.dispatchEvent(
      new CustomEvent("mm-admin-sidebar-change", {
        detail: { collapsed: enabled }
      })
    );
  }

  function toggleCollapsed() {
    setCollapsed(!isCollapsed());
  }

  function openMobileSidebar() {
    const sidebar = getSidebar();
    const backdrop = getBackdrop();

    setRootClasses(CLASS.mobileOpen, true);

    if (sidebar) {
      sidebar.classList.add(CLASS.open);
      sidebar.style.transform = "translateX(0)";
      sidebar.setAttribute("aria-hidden", "false");
    }

    if (backdrop) {
      backdrop.classList.add(CLASS.open);
      backdrop.setAttribute("aria-hidden", "false");
    }

    document.body.style.overflow = "hidden";
  }

  function closeMobileSidebar() {
    const sidebar = getSidebar();
    const backdrop = getBackdrop();

    setRootClasses(CLASS.mobileOpen, false);

    if (sidebar) {
      sidebar.classList.remove(CLASS.open);
      sidebar.style.transform = isDesktop() ? "translateX(0)" : "";
      sidebar.setAttribute("aria-hidden", isDesktop() ? "false" : "true");
    }

    if (backdrop) {
      backdrop.classList.remove(CLASS.open);
      backdrop.setAttribute("aria-hidden", "true");
    }

    if (!document.body.classList.contains("mm-modal-open")) {
      document.body.style.overflow = "";
    }
  }

  function toggleSidebar() {
    if (isDesktop()) {
      toggleCollapsed();
      return;
    }

    const opened = CLASS.mobileOpen.some((name) => {
      return document.body.classList.contains(name);
    });

    opened ? closeMobileSidebar() : openMobileSidebar();
  }

  function syncMobileButton(opened) {
    $$(SELECTOR.mobileToggle).forEach((button) => {
      button.setAttribute("aria-expanded", opened ? "true" : "false");
    });
  }

  function getUserDropdownOpened() {
    const dropdown = $(SELECTOR.userDropdown);
    if (!dropdown) return false;

    return dropdown.classList.contains(CLASS.open) || !dropdown.classList.contains(CLASS.hidden);
  }

  function openUserMenu() {
    const dropdown = $(SELECTOR.userDropdown);
    const backdrop = $(SELECTOR.userBackdrop);
    const button = $(SELECTOR.userButton);
    const chevron = $(SELECTOR.userChevron);

    if (!dropdown || !button) return;

    dropdown.classList.remove(CLASS.hidden);
    dropdown.classList.add(CLASS.open);
    dropdown.setAttribute("aria-hidden", "false");

    if (backdrop) {
      backdrop.classList.remove(CLASS.hidden);
      backdrop.classList.add(CLASS.open);
      backdrop.setAttribute("aria-hidden", "false");
    }

    button.classList.add(CLASS.open);
    button.setAttribute("aria-expanded", "true");

    if (chevron) chevron.style.transform = "rotate(180deg)";
  }

  function closeUserMenu() {
    const dropdown = $(SELECTOR.userDropdown);
    const backdrop = $(SELECTOR.userBackdrop);
    const button = $(SELECTOR.userButton);
    const chevron = $(SELECTOR.userChevron);

    if (!dropdown || !button) return;

    dropdown.classList.remove(CLASS.open);
    dropdown.classList.add(CLASS.hidden);
    dropdown.setAttribute("aria-hidden", "true");

    if (backdrop) {
      backdrop.classList.remove(CLASS.open);
      backdrop.classList.add(CLASS.hidden);
      backdrop.setAttribute("aria-hidden", "true");
    }

    button.classList.remove(CLASS.open);
    button.setAttribute("aria-expanded", "false");

    if (chevron) chevron.style.transform = "";
  }

  function toggleUserMenu(event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }

    getUserDropdownOpened() ? closeUserMenu() : openUserMenu();
  }

  const Progress = {
    start() {
      const progress = $(SELECTOR.progress);
      if (!progress) return;

      clearTimeout(progressTimer);

      document.body.classList.add(CLASS.loading);
      progress.style.pointerEvents = "none";
      progress.style.opacity = "1";
      progress.style.width = "0%";
      progress.style.transition = "none";

      requestAnimationFrame(() => {
        progress.style.transition = "width 480ms cubic-bezier(0.16, 1, 0.3, 1)";
        progress.style.width = "72%";
      });
    },

    done() {
      const progress = $(SELECTOR.progress);
      if (!progress) return;

      clearTimeout(progressTimer);

      progress.style.pointerEvents = "none";
      progress.style.transition = "width 160ms ease-out";
      progress.style.width = "100%";

      progressTimer = setTimeout(() => {
        progress.style.transition = "opacity 220ms ease";
        progress.style.opacity = "0";
        document.body.classList.remove(CLASS.loading);

        progressTimer = setTimeout(() => {
          progress.style.transition = "none";
          progress.style.width = "0%";
          progress.style.opacity = "0";
        }, 240);
      }, 130);
    }
  };

  function shouldShowProgress(anchor) {
    const href = anchor.getAttribute("href");

    if (!href) return false;
    if (href.startsWith("#")) return false;
    if (anchor.target === "_blank") return false;
    if (anchor.hasAttribute("download")) return false;

    try {
      const url = new URL(href, window.location.origin);

      if (url.origin !== window.location.origin) return false;

      if (url.pathname === window.location.pathname && url.search === window.location.search) {
        return false;
      }

      return true;
    } catch (_) {
      return false;
    }
  }

  function prefetch(href) {
    if (!href) return;

    try {
      const url = new URL(href, window.location.origin);

      if (url.origin !== window.location.origin) return;
      if (document.querySelector(`link[rel="prefetch"][href="${url.href}"]`)) return;

      const link = document.createElement("link");
      link.rel = "prefetch";
      link.as = "document";
      link.href = url.href;
      document.head.appendChild(link);
    } catch (_) {}
  }

  function initState() {
    const savedCollapsed = readCollapsed();

    setCollapsed(savedCollapsed, false);

    if (isDesktop()) {
      closeMobileSidebar();
      applyLayout(savedCollapsed);
      getSidebar()?.setAttribute("aria-hidden", "false");
    } else {
      applyLayout(false);
      closeMobileSidebar();
      getSidebar()?.setAttribute("aria-hidden", "true");
    }

    getBackdrop()?.setAttribute("aria-hidden", "true");

    const progress = $(SELECTOR.progress);
    if (progress) progress.style.pointerEvents = "none";
  }

  function bindSidebar() {
    document.addEventListener("click", (event) => {
      const sidebarToggle = event.target.closest(SELECTOR.sidebarToggle);
      if (sidebarToggle) {
        event.preventDefault();
        event.stopPropagation();
        toggleSidebar();
        return;
      }

      const mobileToggle = event.target.closest(SELECTOR.mobileToggle);
      if (mobileToggle) {
        event.preventDefault();
        event.stopPropagation();
        openMobileSidebar();
        syncMobileButton(true);
        return;
      }

      const mobileClose = event.target.closest(SELECTOR.mobileClose);
      if (mobileClose) {
        event.preventDefault();
        event.stopPropagation();
        closeMobileSidebar();
        syncMobileButton(false);
        return;
      }

      const backdrop = event.target.closest(SELECTOR.backdrop);
      if (backdrop && !isDesktop()) {
        event.preventDefault();
        closeMobileSidebar();
        syncMobileButton(false);
      }
    });
  }

  function bindUserMenu() {
    const userButton = $(SELECTOR.userButton);
    const userBackdrop = $(SELECTOR.userBackdrop);

    userButton?.addEventListener("click", toggleUserMenu);

    userBackdrop?.addEventListener("click", (event) => {
      event.preventDefault();
      closeUserMenu();
    });

    document.addEventListener("click", (event) => {
      const dropdown = $(SELECTOR.userDropdown);
      const button = $(SELECTOR.userButton);

      if (!dropdown || !button) return;
      if (!getUserDropdownOpened()) return;
      if (dropdown.contains(event.target)) return;
      if (button.contains(event.target)) return;

      closeUserMenu();
    });
  }

  function bindNavigationProgress() {
    document.addEventListener("click", (event) => {
      const anchor = event.target.closest(SELECTOR.navLink);
      if (!anchor) return;
      if (!shouldShowProgress(anchor)) return;

      anchor.classList.add("is-loading");
      Progress.start();
      closeMobileSidebar();
      closeUserMenu();
    });

    $$(SELECTOR.navForm).forEach((form) => {
      form.addEventListener("submit", () => {
        const button = form.querySelector('button[type="submit"]');

        if (button) {
          button.disabled = true;
          button.classList.add("opacity-70", "cursor-not-allowed");
        }

        Progress.start();
        closeUserMenu();
      });
    });

    window.addEventListener("beforeunload", () => Progress.start());
    window.addEventListener("pageshow", () => Progress.done());
    window.addEventListener("load", () => Progress.done());
  }

  function bindPrefetch() {
    $$(SELECTOR.prefetchLink).forEach((anchor) => {
      const href = anchor.getAttribute("href");

      anchor.addEventListener("mouseenter", () => prefetch(href), { passive: true });
      anchor.addEventListener("focus", () => prefetch(href), { passive: true });
      anchor.addEventListener("touchstart", () => prefetch(href), { passive: true });
    });
  }

  function bindKeyboard() {
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeMobileSidebar();
        closeUserMenu();
        syncMobileButton(false);
        return;
      }

      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
        event.preventDefault();

        if (isDesktop()) {
          toggleCollapsed();
        }
      }
    });
  }

  function bindResizeAndStorage() {
    window.addEventListener(
      "resize",
      () => {
        clearTimeout(resizeTimer);

        resizeTimer = setTimeout(() => {
          const collapsed = readCollapsed();

          if (isDesktop()) {
            closeMobileSidebar();
            setCollapsed(collapsed, false);
            getSidebar()?.setAttribute("aria-hidden", "false");
          } else {
            applyLayout(false);
            closeMobileSidebar();
            getSidebar()?.setAttribute("aria-hidden", "true");
            syncMobileButton(false);
          }
        }, 120);
      },
      { passive: true }
    );

    window.addEventListener("storage", (event) => {
      if (CONFIG.storageKeys.includes(event.key)) {
        setCollapsed(readCollapsed(), false);
      }
    });
  }

  function exposeGlobals() {
    window.AdminShell = {
      setCollapsed,
      toggleDesktopSidebar: toggleCollapsed,
      toggleSidebar,
      openMobileSidebar,
      closeMobileSidebar,
      openSidebar: openMobileSidebar,
      closeSidebar: closeMobileSidebar,
      openUserMenu,
      closeUserMenu,
      toggleUserMenu,
      refreshLayout: () => applyLayout(isCollapsed())
    };

    window.AdminProgress = Progress;

    window.MMAdminLayout = window.MMAdminLayout || {};
    window.MMAdminLayout.applySidebarState = () => setCollapsed(readCollapsed(), false);
    window.MMAdminLayout.toggleSidebarCollapsed = toggleCollapsed;
    window.MMAdminLayout.openSidebar = openMobileSidebar;
    window.MMAdminLayout.closeSidebar = closeMobileSidebar;
    window.MMAdminLayout.refreshLayout = () => applyLayout(isCollapsed());
  }

  function init() {
    if (initialized) return;
    initialized = true;

    exposeGlobals();
    initState();
    bindSidebar();
    bindUserMenu();
    bindNavigationProgress();
    bindPrefetch();
    bindKeyboard();
    bindResizeAndStorage();
    Progress.done();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();