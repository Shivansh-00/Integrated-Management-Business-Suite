frappe.provide("ibms.enterprise");

ibms.enterprise.mountDashboardEnhancements = function () {
  const root = document.querySelector(".layout-main-section");
  if (!root || root.dataset.ibmsEnhanced === "1") {
    return;
  }

  root.dataset.ibmsEnhanced = "1";
  root.classList.add("ibms-glass-shell");

  const cards = root.querySelectorAll(".widget, .number-widget, .chart-widget");
  cards.forEach((card, idx) => {
    card.classList.add("ibms-glass-card");
    card.style.animationDelay = `${Math.min(idx * 80, 500)}ms`;
    card.classList.add("ibms-fade-up");
  });
};

frappe.after_ajax(() => {
  ibms.enterprise.mountDashboardEnhancements();
});
