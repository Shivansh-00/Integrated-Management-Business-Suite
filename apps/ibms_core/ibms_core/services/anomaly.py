import frappe


def refresh_anomaly_models():
    """Scheduled task entrypoint for model refresh."""
    frappe.logger("ibms_core").info("Refreshing anomaly model snapshots")


def enqueue_invoice_anomaly_check(invoice_name: str):
    frappe.enqueue(
        "ibms_core.services.anomaly.run_invoice_anomaly_check",
        queue="ml-heavy",
        invoice_name=invoice_name,
        job_name=f"invoice-anomaly-{invoice_name}",
    )


def run_invoice_anomaly_check(invoice_name: str):
    score = 0.83  # Placeholder from external model service.
    if score < 0.75:
        return

    alert = frappe.get_doc(
        {
            "doctype": "AI Alert",
            "title": f"Potential anomaly for invoice {invoice_name}",
            "severity": "high",
            "reference_doctype": "Sales Invoice",
            "reference_name": invoice_name,
            "status": "Open",
            "risk_score": score * 100,
        }
    )
    alert.insert(ignore_permissions=True)
