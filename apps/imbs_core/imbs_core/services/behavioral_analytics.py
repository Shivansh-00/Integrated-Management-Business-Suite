import frappe


def capture_user_signal(user: str, event: str, metadata: dict | None = None):
    metadata = metadata or {}
    frappe.logger("imbs_behavioral").info({"user": user, "event": event, "metadata": metadata})


def compute_risk_profile(user: str):
    return {"user": user, "behavior_risk": "low", "score": 22}
