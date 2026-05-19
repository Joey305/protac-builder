document.addEventListener("DOMContentLoaded", () => {
  const footer = document.querySelector(".glow-footer");
  const hamburger = document.getElementById("hamburgerBtn");
  const menu = document.getElementById("mobileMenu");
  const year = document.getElementById("year");

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

  if (hamburger && menu) {
    hamburger.addEventListener("click", () => {
      hamburger.classList.toggle("active");
      menu.classList.toggle("show");
    });

    menu.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        hamburger.classList.remove("active");
        menu.classList.remove("show");
      });
    });

    document.addEventListener("click", (event) => {
      const insideMenu = menu.contains(event.target);
      const insideButton = hamburger.contains(event.target);
      if (!insideMenu && !insideButton) {
        hamburger.classList.remove("active");
        menu.classList.remove("show");
      }
    });
  }

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
