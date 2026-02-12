frappe.realtime.on("imbs:kpi_update", (payload) => {
  console.log("KPI update", payload);
});
