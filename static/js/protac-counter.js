(function () {
  function animateCountUp(target, endValue, duration = 2000) {
    const startValue = Number(target.dataset.currentValue || 0);
    const startTime = performance.now();

    function easeOutCubic(value) {
      return 1 - Math.pow(1 - value, 3);
    }

    function update(now) {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = easeOutCubic(progress);
      const value = Math.floor(startValue + (endValue - startValue) * eased);

      target.textContent = value.toLocaleString();
      target.dataset.currentValue = String(value);

      if (progress < 1) {
        requestAnimationFrame(update);
        return;
      }

      target.textContent = endValue.toLocaleString();
      target.dataset.currentValue = String(endValue);
      target.classList.remove("glow-flash", "prestige-glow");
      void target.offsetWidth;
      target.classList.add("glow-flash");
      setTimeout(() => {
        target.classList.add("prestige-glow");
      }, 750);
    }

    requestAnimationFrame(update);
  }

  async function updateProtacCounter() {
    const counterEl = document.getElementById("protac-counter");
    if (!counterEl) return;

    try {
      const response = await fetch("/api/protac/builder/usage", { cache: "no-store" });
      if (!response.ok) throw new Error("usage endpoint failed");

      const data = await response.json();
      animateCountUp(counterEl, Number(data.total || 0), 2000);
    } catch (error) {
      console.error("Counter load error:", error);
      animateCountUp(counterEl, 0, 1200);
    }
  }

  function initBuilderPopup() {
    const popup = document.getElementById("builder-popup-overlay");
    if (!popup) return;

    const close = () => {
      popup.classList.add("is-closing");
      popup.classList.remove("is-visible");
      window.setTimeout(() => {
        popup.style.display = "none";
        popup.classList.remove("is-closing");
      }, 220);
    };

    popup.style.display = "flex";
    requestAnimationFrame(() => {
      popup.classList.add("is-visible");
    });

    const closeButton = document.getElementById("builder-close-btn");
    if (closeButton) closeButton.addEventListener("click", close);

    popup.addEventListener("click", (event) => {
      if (event.target === popup) close();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initBuilderPopup();
    updateProtacCounter();
  });
})();
