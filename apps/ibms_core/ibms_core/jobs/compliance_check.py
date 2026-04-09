import frappe


def run():
    stale_webhooks = frappe.db.count("Integration Webhook Log", {"processed": 0})
    if stale_webhooks > 0:
        doc = frappe.get_doc(
            {
                "doctype": "AI Recommendation",
                "company": "Default Company",
                "context_type": "Compliance",
                "recommendation_code": "CMP-UNPROCESSED-WEBHOOKS",
                "confidence": 0.86,
                "status": "Open",
                "payload": f"{{\"pending_webhooks\":{stale_webhooks}}}",
                "generated_at": frappe.utils.now_datetime(),
            }
        )
        doc.flags.ignore_permissions = True
        doc.insert()

    frappe.logger("ibms_jobs").info({"job": "compliance_check", "pending_webhooks": stale_webhooks})
