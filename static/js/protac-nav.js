document.addEventListener("DOMContentLoaded", () => {
  if (document.documentElement.dataset.protacNavReady === "true") {
    return;
  }
  document.documentElement.dataset.protacNavReady = "true";

  const footer = document.querySelector(".glow-footer");
  const nav = document.querySelector(".protac-site-nav");
  const toggle = document.getElementById("protacNavToggle");
  const drawer = document.getElementById("protacNavDrawer");
  const closeButton = document.getElementById("protacNavClose");
  const backdrop = document.getElementById("protacNavBackdrop");
  const year = document.getElementById("year");
  const mobileQuery = window.matchMedia("(max-width: 1024px)");

  let isOpen = false;
  let lastFocusedElement = null;
  let savedScrollY = 0;
  let bodyLockStyles = null;

  if (year) year.textContent = new Date().getFullYear();

  if (footer && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          footer.classList.add("visible");
          observer.unobserve(footer);
        }
      });
    }, { threshold: 0.1 });
    observer.observe(footer);
  }

  function handleNavScroll() {
    if (!nav) return;
    nav.classList.toggle("nav-scrolled", window.scrollY > 14);
  }

  function lockBodyScroll() {
    if (bodyLockStyles) return;

    savedScrollY = window.scrollY || window.pageYOffset || 0;
    bodyLockStyles = {
      overflow: document.body.style.overflow,
      position: document.body.style.position,
      top: document.body.style.top,
      left: document.body.style.left,
      right: document.body.style.right,
      width: document.body.style.width,
    };

    document.body.classList.add("protac-nav-open");
    document.body.style.overflow = "hidden";
    document.body.style.position = "fixed";
    document.body.style.top = `-${savedScrollY}px`;
    document.body.style.left = "0";
    document.body.style.right = "0";
    document.body.style.width = "100%";
  }

  function unlockBodyScroll() {
    if (!bodyLockStyles) return;

    document.body.classList.remove("protac-nav-open");
    document.body.style.overflow = bodyLockStyles.overflow;
    document.body.style.position = bodyLockStyles.position;
    document.body.style.top = bodyLockStyles.top;
    document.body.style.left = bodyLockStyles.left;
    document.body.style.right = bodyLockStyles.right;
    document.body.style.width = bodyLockStyles.width;

    bodyLockStyles = null;
    window.scrollTo(0, savedScrollY);
  }

  function setOpen(nextOpen) {
    if (!toggle || !drawer || !backdrop) return;
    if (nextOpen === isOpen) return;

    isOpen = nextOpen;
    toggle.classList.toggle("is-open", nextOpen);
    toggle.setAttribute("aria-expanded", String(nextOpen));
    toggle.setAttribute("aria-label", nextOpen ? "Close navigation" : "Open navigation");

    drawer.classList.toggle("is-open", nextOpen);
    drawer.setAttribute("aria-hidden", String(!nextOpen));

    backdrop.hidden = !nextOpen;
    backdrop.classList.toggle("is-open", nextOpen);

    if (nextOpen) {
      lastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      lockBodyScroll();
      window.setTimeout(() => {
        if (closeButton) {
          closeButton.focus();
        } else {
          drawer.focus();
        }
      }, 0);
    } else {
      unlockBodyScroll();
      if (lastFocusedElement instanceof HTMLElement) {
        lastFocusedElement.focus();
      }
    }
  }

  function closeDrawer() {
    setOpen(false);
  }

  function toggleDrawer() {
    if (!mobileQuery.matches) return;
    setOpen(!isOpen);
  }

  if (nav && toggle && drawer && backdrop) {
    toggle.addEventListener("click", (event) => {
      event.preventDefault();
      toggleDrawer();
    });

    if (closeButton) {
      closeButton.addEventListener("click", (event) => {
        event.preventDefault();
        closeDrawer();
      });
    }

    backdrop.addEventListener("click", closeDrawer);

    drawer.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        closeDrawer();
      });
    });

    document.addEventListener("keydown", (event) => {
      if (!isOpen || !drawer) return;

      if (event.key === "Escape") {
        event.preventDefault();
        closeDrawer();
        return;
      }

      if (event.key !== "Tab") return;

      const focusable = Array.from(
        drawer.querySelectorAll(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      ).filter((element) => {
        return element instanceof HTMLElement && !element.hasAttribute("disabled");
      });

      if (!focusable.length) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;

      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    });

    if (mobileQuery.addEventListener) {
      mobileQuery.addEventListener("change", (event) => {
        if (!event.matches) {
          closeDrawer();
        }
      });
    } else if (mobileQuery.addListener) {
      mobileQuery.addListener((event) => {
        if (!event.matches) {
          closeDrawer();
        }
      });
    }
  }

  window.addEventListener("scroll", handleNavScroll, { passive: true });
  handleNavScroll();

  document.querySelectorAll("a[href^='/']").forEach((link) => {
    link.addEventListener("click", (event) => {
      const href = link.getAttribute("href");
      if (!href || href.startsWith("//")) return;
      event.preventDefault();
      document.body.classList.add("fade-out");
      setTimeout(() => {
        window.location.href = href;
      }, 120);
    });
  });
});
