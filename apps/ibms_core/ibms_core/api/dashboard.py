import frappe


@frappe.whitelist(methods=["GET"])
def get_dashboard_snapshot(company: str = "Default Company"):
    kpi = frappe.cache().get_value(f"ibms:kpi:{company}") or {}
    return {"company": company, "kpi": kpi}
