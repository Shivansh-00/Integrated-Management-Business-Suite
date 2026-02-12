import frappe
from imbs_core.services.anomaly import enqueue_invoice_anomaly_check


def on_sales_invoice_submit(doc, method=None):
    enqueue_invoice_anomaly_check(doc.name)
    frappe.publish_realtime(
        event="imbs:kpi_update",
        message={"doctype": doc.doctype, "name": doc.name, "event": "submitted"},
        user="Administrator",
    )
