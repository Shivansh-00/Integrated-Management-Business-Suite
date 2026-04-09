frappe.realtime.on("ibms:kpi_update", (payload) => {
  console.log("KPI update", payload);
});
