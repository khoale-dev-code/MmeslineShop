
(function () {
  const sidebar = document.getElementById("adminSidebar");
  const backdrop = document.getElementById("adminSidebarBackdrop");
  const progress = document.getElementById("mmAdminProgress");
  const SIDEBAR_KEY = "mm_admin_sidebar_collapsed";

  function setCollapsed(collapsed) {
    document.body.classList.toggle("admin-sidebar-collapsed", Boolean(collapsed));

    const icon = document.getElementById("desktopSidebarToggleIcon");
    const button = document.getElementById("desktopSidebarToggle");

    if (icon) {
      icon.className = collapsed
        ? "fa-solid fa-angles-right"
        : "fa-solid fa-bars-staggered";
    }

    if (button) {
      button.title = collapsed ? "Mở rộng sidebar" : "Thu gọn sidebar";
      button.setAttribute("aria-label", button.title);
    }
  }

  try {
    setCollapsed(localStorage.getItem(SIDEBAR_KEY) === "1");
  } catch (_) {
    setCollapsed(false);
  }

  const Progress = {
    started: false,
    timer: null,

    start() {
      if (!progress || this.started) return;

      this.started = true;
      clearTimeout(this.timer);

      progress.style.opacity = "1";
      progress.style.transition = "none";
      progress.style.width = "0%";

      requestAnimationFrame(() => {
        progress.style.transition = "width 480ms cubic-bezier(0.16, 1, 0.3, 1)";
        progress.style.width = "78%";
      });
    },

    done() {
      if (!progress) return;

      progress.style.transition = "width 160ms ease-out";
      progress.style.width = "100%";

      this.timer = setTimeout(() => {
        progress.style.transition = "opacity 220ms ease";
        progress.style.opacity = "0";

        setTimeout(() => {
          progress.style.transition = "none";
          progress.style.width = "0%";
          progress.style.opacity = "1";
          this.started = false;
        }, 240);
      }, 130);
    }
  };

  const AdminShell = {
    openSidebar() {
      if (!sidebar || !backdrop) return;

      sidebar.classList.add("is-open");
      backdrop.classList.add("is-open");
      document.body.style.overflow = "hidden";
    },

    closeSidebar() {
      if (!sidebar || !backdrop) return;

      sidebar.classList.remove("is-open");
      backdrop.classList.remove("is-open");
      document.body.style.overflow = "";
    },

    toggleDesktopSidebar() {
      const willCollapse = !document.body.classList.contains("admin-sidebar-collapsed");
      setCollapsed(willCollapse);

      try {
        localStorage.setItem(SIDEBAR_KEY, willCollapse ? "1" : "0");
      } catch (_) {}
    },

    openUserMenu() {
      const dropdown = document.getElementById("adminUserDropdown");
      const menuBackdrop = document.getElementById("adminUserDropdownBackdrop");
      const button = document.getElementById("adminUserMenuButton");
      const chevron = document.getElementById("adminUserMenuChevron");

      if (!dropdown || !menuBackdrop) return;

      dropdown.classList.remove("hidden");
      menuBackdrop.classList.remove("hidden");

      if (button) {
        button.classList.add("is-open");
        button.setAttribute("aria-expanded", "true");
      }

      if (chevron) {
        chevron.style.transform = "rotate(180deg)";
      }
    },

    closeUserMenu() {
      const dropdown = document.getElementById("adminUserDropdown");
      const menuBackdrop = document.getElementById("adminUserDropdownBackdrop");
      const button = document.getElementById("adminUserMenuButton");
      const chevron = document.getElementById("adminUserMenuChevron");

      if (!dropdown || !menuBackdrop) return;

      dropdown.classList.add("hidden");
      menuBackdrop.classList.add("hidden");

      if (button) {
        button.classList.remove("is-open");
        button.setAttribute("aria-expanded", "false");
      }

      if (chevron) {
        chevron.style.transform = "rotate(0deg)";
      }
    },

    toggleUserMenu(event) {
      if (event) {
        event.preventDefault();
        event.stopPropagation();
      }

      const dropdown = document.getElementById("adminUserDropdown");
      if (!dropdown) return;

      if (dropdown.classList.contains("hidden")) {
        this.openUserMenu();
      } else {
        this.closeUserMenu();
      }
    }
  };

  window.AdminShell = AdminShell;
  window.AdminProgress = Progress;

  function shouldHandleNav(anchor) {
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

  document.querySelectorAll("a[data-prefetch]").forEach((anchor) => {
    const href = anchor.getAttribute("href");

    anchor.addEventListener("mouseenter", () => prefetchUrl(href), { passive: true });
    anchor.addEventListener("focus", () => prefetchUrl(href), { passive: true });
    anchor.addEventListener("touchstart", () => prefetchUrl(href), { passive: true });
  });

  document.querySelectorAll("a[data-nav]").forEach((anchor) => {
    anchor.addEventListener("click", () => {
      if (!shouldHandleNav(anchor)) return;

      anchor.classList.add("is-loading");
      Progress.start();
      AdminShell.closeSidebar();
      AdminShell.closeUserMenu();
    });
  });

  document.querySelectorAll("form[data-form-nav]").forEach((form) => {
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
})();