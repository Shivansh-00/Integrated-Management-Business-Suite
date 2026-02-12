import frappe


def refresh_kpis(company: str):
    snapshot = {
        "company": company,
        "revenue_run_rate": 12500000,
        "net_margin": 18.4,
        "risk_exposure": 31.2,
    }
    frappe.cache().set_value(f"imbs:kpi:{company}", snapshot, expires_in_sec=900)
    return snapshot
