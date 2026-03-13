import json

import frappe

from imbs_core.events.subscriber import on_event


def process_batch(events: list[dict]):
    results = []
    for event in events:
        results.append(on_event(event.get("topic", "unknown"), event.get("payload", {})))
    return results


def process_webhook_log(log_name: str):
    doc = frappe.get_doc("Integration Webhook Log", log_name)
    payload = json.loads(doc.request_body or "{}")
    topic = f"webhook.{doc.provider}.{doc.event_type}"

    result = on_event(topic, payload)

    doc.processed = 1
    doc.http_status = 200
    doc.response_body = json.dumps(result)
    doc.save(ignore_permissions=True)
    return result
