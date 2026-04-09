frappe.ui.form.on("KPI Snapshot", {
  metric_value(frm) {
    if (frm.doc.metric_value < 0) {
      frappe.msgprint("Metric value is negative. Verify whether this is expected.");
    }
  },
});
