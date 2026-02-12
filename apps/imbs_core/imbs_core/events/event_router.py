import frappe


def route_event(topic: str, payload: dict):
    frappe.logger("imbs_events").info({"topic": topic, "payload": payload})
    if topic == "invoice.submitted":
        frappe.publish_realtime("imbs:event", {"topic": topic, "payload": payload})
    return {"status": "routed", "topic": topic}
