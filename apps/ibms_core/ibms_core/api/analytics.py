import frappe

from ibms_core.services.predictive_inventory import forecast_reorder_point


@frappe.whitelist(methods=["POST"])
def get_inventory_prediction(company: str, sku: str):
    if not frappe.has_permission("Item", "read"):
        frappe.throw("Not permitted", frappe.PermissionError)
    return forecast_reorder_point(company, sku)
