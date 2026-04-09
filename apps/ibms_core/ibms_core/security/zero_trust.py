import frappe


def enforce_service_identity(service_name: str, presented_identity: str):
    if service_name != presented_identity:
        frappe.throw("Service identity validation failed", frappe.PermissionError)
    return True


def rate_limit_key(user: str, endpoint: str):
    return f"ibms:ratelimit:{user}:{endpoint}"
