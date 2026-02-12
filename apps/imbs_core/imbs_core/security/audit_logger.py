import base64
import json

import frappe


def log_audit_event(event_type: str, payload: dict):
    encoded = base64.b64encode(json.dumps(payload, sort_keys=True).encode()).decode()
    frappe.logger("imbs_audit").info({"event_type": event_type, "payload_enc": encoded})
