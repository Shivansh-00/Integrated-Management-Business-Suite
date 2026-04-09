import frappe

from ibms_core.security.jwt_auth import JWTValidationError, decode_token


def _auth_secret() -> str:
    return frappe.conf.get("ibms_jwt_secret") or frappe.local.conf.get("encryption_key") or "ibms-default-secret"


def validate_api_token():
    auth_header = (frappe.get_request_header("Authorization") or "").strip()
    if not auth_header.startswith("Bearer "):
        return

    token = auth_header.replace("Bearer ", "", 1).strip()
    if not token:
        return

    try:
        payload = decode_token(token, _auth_secret())
    except JWTValidationError:
        frappe.throw("Invalid API token", frappe.AuthenticationError)

    user = payload.get("sub")
    if user and frappe.db.exists("User", user):
        frappe.set_user(user)
