import frappe


def route_event(topic: str, payload: dict):
    frappe.logger("ibms_events").info({"topic": topic, "payload": payload})
    if topic == "invoice.submitted":
        frappe.publish_realtime("ibms:event", {"topic": topic, "payload": payload})
        return {"status": "routed", "topic": topic, "action": "realtime_published"}

    if topic.startswith("webhook."):
        frappe.publish_realtime("ibms:webhook", {"topic": topic, "payload": payload})
        return {"status": "routed", "topic": topic, "action": "webhook_processed"}

    if topic == "ai.recommendation.created":
        frappe.publish_realtime("ibms:ai_recommendation", payload)
        return {"status": "routed", "topic": topic, "action": "recommendation_notified"}

    return {"status": "routed", "topic": topic}


def on_webhook_log_insert(doc, method=None):
    frappe.enqueue("ibms_core.events.stream_processor.process_webhook_log", log_name=doc.name, queue="short")
