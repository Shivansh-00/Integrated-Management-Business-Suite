frappe.provide("imbs.enterprise");

imbs.enterprise.mountDashboardEnhancements = function () {
  const root = document.querySelector(".layout-main-section");
  if (!root || root.dataset.imbsEnhanced === "1") {
    return;
  }

  root.dataset.imbsEnhanced = "1";
  root.classList.add("imbs-glass-shell");

  const cards = root.querySelectorAll(".widget, .number-widget, .chart-widget");
  cards.forEach((card, idx) => {
    card.classList.add("imbs-glass-card");
    card.style.animationDelay = `${Math.min(idx * 80, 500)}ms`;
    card.classList.add("imbs-fade-up");
  });
};

frappe.after_ajax(() => {
  imbs.enterprise.mountDashboardEnhancements();
});
