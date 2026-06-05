(function () {
  function onReady(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, { once: true });
      return;
    }
    callback();
  }

  function debounce(callback, delay) {
    let timeoutId;
    return function debounced() {
      window.clearTimeout(timeoutId);
      timeoutId = window.setTimeout(callback, delay);
    };
  }

  onReady(() => {
    if (document.body?.dataset.page !== "builder") return;

    const mobileMediaQuery = window.matchMedia("(max-width: 1024px)");
    const phoneMediaQuery = window.matchMedia("(max-width: 768px)");
    const canvasIds = ["ligand-editor", "linker-editor", "ligase-editor", "protac-sketcher"];
    const protacContainer = document.getElementById("protac-container");
    const cheatsOverlay = document.getElementById("cheats-notes-overlay");
    const curatedLinkersModal = document.getElementById("curatedLinkersModal");
    const curatedLinkersModalBody = curatedLinkersModal?.querySelector(".modal-body");
    const filtersToggle = document.getElementById("toggle-filters");
    const filtersContainer = document.getElementById("filters-container");
    const linkersList = document.getElementById("linkers-list");
    const applyFiltersButton = document.getElementById("apply-filters");
    const prevPageButton = document.getElementById("prev-page");
    const nextPageButton = document.getElementById("next-page");
    const paramTooltip = document.querySelector(".param-tooltip");
    const isMobileBuilder = () => mobileMediaQuery.matches;
    const isPhoneBuilder = () => phoneMediaQuery.matches;

    function clearCanvasSize(canvas) {
      if (!canvas) return;
      canvas.style.width = "";
      canvas.style.height = "";
    }

    function fitCanvas(canvas) {
      if (!canvas) return;

      const widthAttr = Number(canvas.getAttribute("width")) || canvas.width || 0;
      const heightAttr = Number(canvas.getAttribute("height")) || canvas.height || 0;
      const frame = canvas.closest(".builder-canvas-frame");

      if (!frame || !widthAttr || !heightAttr) return;

      if (!isMobileBuilder()) {
        clearCanvasSize(canvas);
        return;
      }

      const availableWidth = Math.min(widthAttr, Math.max(frame.clientWidth - 8, 0));
      if (!availableWidth) return;

      canvas.style.width = availableWidth + "px";
      canvas.style.height = Math.round((availableWidth / widthAttr) * heightAttr) + "px";
    }

    function fitCanvases() {
      if (!isMobileBuilder()) {
        canvasIds.forEach((id) => clearCanvasSize(document.getElementById(id)));
        return;
      }
      canvasIds.forEach((id) => fitCanvas(document.getElementById(id)));
    }

    function syncSmilesPanelState() {
      document.querySelectorAll(".builder-editor-card").forEach((card) => {
        const hasOpenPanel = card.querySelector(".smiles-panel.open");
        card.classList.toggle("has-open-smiles", Boolean(hasOpenPanel));
      });
    }

    function scrollSmilesPanelIntoView(panel) {
      if (!panel || !isMobileBuilder()) return;

      const target = panel.closest(".builder-editor-card") || panel;
      const navHeightValue = window
        .getComputedStyle(document.documentElement)
        .getPropertyValue("--protac-nav-height-mobile");
      const navHeight = Number.parseInt(navHeightValue, 10) || 64;
      const rect = target.getBoundingClientRect();
      const topPadding = navHeight + 16;
      const bottomPadding = 24;
      const isVisible = rect.top >= topPadding && rect.bottom <= window.innerHeight - bottomPadding;

      if (isVisible) return;

      const absoluteTop = rect.top + window.scrollY;
      window.scrollTo({
        top: Math.max(absoluteTop - topPadding, 0),
        behavior: "smooth",
      });
    }

    function syncOutputState() {
      if (!protacContainer) return;
      const isVisible = protacContainer.style.display !== "none";
      document.body.classList.toggle("builder-has-output", isVisible);
    }

    function setFiltersToggleLabel(collapsed) {
      if (!filtersToggle) return;
      filtersToggle.textContent = collapsed ? "Show Filters ▼" : "Hide Filters ▲";
    }

    function setFiltersCollapsed(collapsed) {
      if (!filtersContainer) return;
      filtersContainer.classList.toggle("collapsed", collapsed);
      setFiltersToggleLabel(collapsed);
    }

    function syncMobilePaginationVisibility() {
      const hidePagination = isPhoneBuilder();
      [prevPageButton, nextPageButton].forEach((button) => {
        if (!button) return;
        button.style.display = hidePagination ? "none" : "";
      });

      const paginationControls = document.getElementById("pagination-controls");
      if (paginationControls) {
        paginationControls.style.display = hidePagination ? "none" : "";
      }
    }

    function scrollModalBodyTo(element) {
      if (!element || !curatedLinkersModalBody || !isMobileBuilder()) return;

      const bodyRect = curatedLinkersModalBody.getBoundingClientRect();
      const targetRect = element.getBoundingClientRect();
      const nextTop = targetRect.top - bodyRect.top + curatedLinkersModalBody.scrollTop - 12;

      curatedLinkersModalBody.scrollTo({
        top: Math.max(nextTop, 0),
        behavior: "smooth",
      });
    }

    function focusLinkerResults() {
      if (!linkersList) return;
      window.setTimeout(() => {
        scrollModalBodyTo(linkersList);
      }, 260);
    }

    function closeTooltip() {
      paramTooltip?.classList.remove("is-open");
    }

    fitCanvases();
    syncOutputState();
    syncSmilesPanelState();
    syncMobilePaginationVisibility();
    if (isMobileBuilder()) {
      window.setTimeout(fitCanvases, 250);
      window.setTimeout(fitCanvases, 900);
    }

    window.addEventListener("resize", debounce(fitCanvases, 120));
    window.addEventListener("orientationchange", () => {
      if (!isMobileBuilder()) {
        fitCanvases();
        return;
      }
      window.setTimeout(fitCanvases, 180);
    });
    mobileMediaQuery.addEventListener("change", fitCanvases);
    phoneMediaQuery.addEventListener("change", () => {
      syncMobilePaginationVisibility();
      if (!curatedLinkersModal?.classList.contains("show")) return;
      setFiltersCollapsed(isPhoneBuilder());
    });

    document.querySelectorAll(".smiles-toggle-btn").forEach((button) => {
      button.addEventListener("click", () => {
        window.setTimeout(() => {
          fitCanvases();
          syncSmilesPanelState();

          const targetId = button.getAttribute("onclick")?.match(/'([^']+)'/)?.[1];
          const panel = targetId ? document.getElementById(targetId) : null;
          if (!panel?.classList.contains("open") || window.innerWidth > 1024 || !isMobileBuilder()) return;

          window.setTimeout(() => {
            scrollSmilesPanelIntoView(panel);
          }, 60);
        }, 380);
      });
    });

    if (protacContainer) {
      const observer = new MutationObserver(() => {
        syncOutputState();
        window.setTimeout(fitCanvases, 180);
      });

      observer.observe(protacContainer, {
        attributes: true,
        attributeFilter: ["style", "class"],
      });
    }

    if (window.jQuery) {
      ["#curatedLinkersModal", "#protacModal"].forEach((selector) => {
        const modal = window.jQuery(selector);
        if (!modal.length) return;

        modal.on("shown.bs.modal hidden.bs.modal", () => {
          window.setTimeout(fitCanvases, 180);
          window.setTimeout(syncOutputState, 180);
        });
      });

      if (curatedLinkersModal) {
        const curatedModal = window.jQuery(curatedLinkersModal);
        curatedModal.on("shown.bs.modal", () => {
          syncMobilePaginationVisibility();
          if (curatedLinkersModalBody) {
            curatedLinkersModalBody.scrollTop = 0;
          }
          setFiltersCollapsed(isPhoneBuilder());
          if (isPhoneBuilder()) {
            focusLinkerResults();
          }
        });

        curatedModal.on("hidden.bs.modal", () => {
          syncMobilePaginationVisibility();
          setFiltersCollapsed(false);
        });
      }
    }

    filtersToggle?.addEventListener("click", (event) => {
      event.preventDefault();
      const collapsed = !filtersContainer?.classList.contains("collapsed");
      setFiltersCollapsed(collapsed);
      if (collapsed) {
        focusLinkerResults();
      } else {
        window.setTimeout(() => {
          scrollModalBodyTo(filtersToggle);
        }, 60);
      }
    });

    applyFiltersButton?.addEventListener("click", () => {
      if (!isPhoneBuilder()) return;
      setFiltersCollapsed(true);
      focusLinkerResults();
    });

    [prevPageButton, nextPageButton].forEach((button) => {
      button?.addEventListener("click", () => {
        if (!isMobileBuilder()) return;
        focusLinkerResults();
      });
    });

    if (cheatsOverlay) {
      const overlayObserver = new MutationObserver(() => {
        if (!cheatsOverlay.classList.contains("is-open")) {
          document.body.style.overflow = "";
        }
        window.setTimeout(fitCanvases, 120);
      });

      overlayObserver.observe(cheatsOverlay, {
        attributes: true,
        attributeFilter: ["class"],
      });
    }

    if (paramTooltip) {
      paramTooltip.setAttribute("tabindex", "0");
      paramTooltip.addEventListener("click", (event) => {
        event.stopPropagation();
        paramTooltip.classList.toggle("is-open");
      });

      document.addEventListener("click", (event) => {
        if (!paramTooltip.contains(event.target)) {
          closeTooltip();
        }
      });

      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          closeTooltip();
        }
      });
    }
  });
})();
