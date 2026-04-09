import frappe


def run():
    open_count = frappe.db.count("AI Recommendation", {"status": "Open"})

    if open_count < 10:
        recommendation = frappe.get_doc(
            {
                "doctype": "AI Recommendation",
                "company": "Default Company",
                "context_type": "Operations",
                "recommendation_code": "WF-REDUCE-APPROVAL-HOPS",
                "confidence": 0.78,
                "status": "Open",
                "payload": "{\"proposal\":\"Reduce approval chain for low-risk vouchers below threshold\"}",
                "generated_at": frappe.utils.now_datetime(),
            }
        )
        recommendation.flags.ignore_permissions = True
        recommendation.insert()

    frappe.logger("ibms_jobs").info("Workflow optimization job completed")
