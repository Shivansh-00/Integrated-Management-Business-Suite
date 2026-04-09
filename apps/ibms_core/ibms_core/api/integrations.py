import hashlib
import hmac
import json

import frappe


@frappe.whitelist(allow_guest=True, methods=["POST"])
def ingest_webhook(provider: str, event_type: str, payload: str = "{}"):
    body = payload or "{}"
    signature = frappe.get_request_header("X-Signature") or ""

    doc = frappe.get_doc(
        {
            "doctype": "Integration Webhook Log",
            "provider": provider,
            "event_type": event_type,
            "signature": signature,
            "request_body": body,
            "processed": 0,
            "received_at": frappe.utils.now_datetime(),
        }
    )
    doc.flags.ignore_permissions = True
    doc.insert()

    frappe.enqueue("ibms_core.events.stream_processor.process_webhook_log", log_name=doc.name, queue="short")
    return {"message": "Webhook accepted", "log": doc.name}


@frappe.whitelist(methods=["POST"])
def register_outbound_webhook(url: str, event: str, secret: str = ""):
    settings = frappe.get_doc("Integration Settings") if frappe.db.exists("DocType", "Integration Settings") else None
    if not settings:
        return {
            "message": "Create Integration Settings doctype in your tenant to persist outbound webhooks",
            "url": url,
            "event": event,
        }

    settings.append("webhooks", {"target_url": url, "event": event, "shared_secret": secret})
    settings.save()
    return {"message": "Outbound webhook registered"}


def compute_signature(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def emit_signed_webhook(url: str, payload: dict, secret: str = ""):
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Signature"] = compute_signature(body, secret)

    # Keep network operations out of request cycle and run from worker queue.
    frappe.enqueue(
        "ibms_core.events.publisher.post_webhook",
        url=url,
        body=body,
        headers=headers,
        queue="short",
    )
    return {"message": "Queued webhook delivery"}
