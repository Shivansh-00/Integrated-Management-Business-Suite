import frappe
import httpx

from ibms_core.services.anomaly import enqueue_invoice_anomaly_check


def on_sales_invoice_submit(doc, method=None):
    enqueue_invoice_anomaly_check(doc.name)
    frappe.publish_realtime(
        event="ibms:kpi_update",
        message={"doctype": doc.doctype, "name": doc.name, "event": "submitted"},
        user="Administrator",
    )


def post_webhook(url: str, body: str, headers: dict | None = None):
    headers = headers or {}
    timeout = float(frappe.conf.get("ibms_webhook_timeout_seconds", 8.0))

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, content=body.encode(), headers=headers)

    frappe.logger("ibms_integrations").info(
        {
            "event": "webhook_delivery",
            "url": url,
            "status_code": response.status_code,
        }
    )
    return {"status_code": response.status_code, "text": response.text[:1000]}
