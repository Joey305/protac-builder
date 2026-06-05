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

    const canvasIds = ["ligand-editor", "linker-editor", "ligase-editor", "protac-sketcher"];
    const protacContainer = document.getElementById("protac-container");
    const cheatsOverlay = document.getElementById("cheats-notes-overlay");
    const paramTooltip = document.querySelector(".param-tooltip");

    function fitCanvas(canvas) {
      if (!canvas) return;

      const widthAttr = Number(canvas.getAttribute("width")) || canvas.width || 0;
      const heightAttr = Number(canvas.getAttribute("height")) || canvas.height || 0;
      const frame = canvas.closest(".builder-canvas-frame");

      if (!frame || !widthAttr || !heightAttr) return;

      if (window.innerWidth > 1024) {
        canvas.style.width = "";
        canvas.style.height = "";
        return;
      }

      const availableWidth = Math.min(widthAttr, Math.max(frame.clientWidth - 8, 0));
      if (!availableWidth) return;

      canvas.style.width = availableWidth + "px";
      canvas.style.height = Math.round((availableWidth / widthAttr) * heightAttr) + "px";
    }

    function fitCanvases() {
      canvasIds.forEach((id) => fitCanvas(document.getElementById(id)));
    }

    function syncOutputState() {
      if (!protacContainer) return;
      const isVisible = protacContainer.style.display !== "none";
      document.body.classList.toggle("builder-has-output", isVisible);
    }

    function closeTooltip() {
      paramTooltip?.classList.remove("is-open");
    }

    fitCanvases();
    syncOutputState();
    window.setTimeout(fitCanvases, 250);
    window.setTimeout(fitCanvases, 900);

    window.addEventListener("resize", debounce(fitCanvases, 120));
    window.addEventListener("orientationchange", () => {
      window.setTimeout(fitCanvases, 180);
    });

    document.querySelectorAll(".smiles-toggle-btn").forEach((button) => {
      button.addEventListener("click", () => {
        window.setTimeout(() => {
          fitCanvases();

          if (window.innerWidth > 768) return;
          const targetId = button.getAttribute("onclick")?.match(/'([^']+)'/)?.[1];
          const panel = targetId ? document.getElementById(targetId) : null;
          if (panel?.classList.contains("open")) {
            panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }
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
    }

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
