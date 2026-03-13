import frappe


def run():
    pending = frappe.get_all(
        "Integration Webhook Log",
        filters={"processed": 0},
        fields=["name"],
        limit_page_length=100,
        order_by="creation asc",
    )

    for row in pending:
        frappe.enqueue("imbs_core.events.stream_processor.process_webhook_log", log_name=row.name, queue="short")
