import frappe
from frappe import _


@frappe.whitelist(methods=["POST"])
def get_sales_forecast(company: str, periods: int = 6):
    """Return forecast payload for dashboard cards/charts."""
    if not frappe.has_permission("Sales Invoice", "read"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    periods = int(periods)
    if periods < 1 or periods > 24:
        frappe.throw(_("Periods must be between 1 and 24"))

    # Placeholder: production should call model service (Prophet/LSTM).
    forecast = [
        {
            "month": i + 1,
            "predicted_revenue": 100000 + (i * 8000),
            "lower_ci": 95000 + (i * 7600),
            "upper_ci": 106000 + (i * 8600),
        }
        for i in range(periods)
    ]

    return {
        "company": company,
        "periods": periods,
        "model": "prophet_baseline_v1",
        "forecast": forecast,
    }
