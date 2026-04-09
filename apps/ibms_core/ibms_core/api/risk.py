import frappe
from frappe import _


def _normalize(amount: float, max_amount: float = 1_000_000):
    return min(float(amount) / max_amount, 1.0)


@frappe.whitelist(methods=["POST"])
def score_transaction(voucher_type: str, voucher_no: str, amount: float):
    """Simple risk scoring endpoint (placeholder for ML + rules)."""
    if not frappe.has_permission(voucher_type, "read", voucher_no):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    amount_risk = _normalize(amount)
    # Example deterministic baseline score.
    risk_score = round((0.7 * amount_risk + 0.3 * 0.25) * 100, 2)

    severity = "low"
    if risk_score >= 80:
        severity = "critical"
    elif risk_score >= 60:
        severity = "high"
    elif risk_score >= 35:
        severity = "medium"

    return {
        "voucher_type": voucher_type,
        "voucher_no": voucher_no,
        "risk_score": risk_score,
        "severity": severity,
    }
