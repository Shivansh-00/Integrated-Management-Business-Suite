import frappe


def refresh_kpis(company: str):
    snapshot = {
        "company": company,
        "revenue_run_rate": 12500000,
        "net_margin": 18.4,
        "risk_exposure": 31.2,
    }

    for metric_code, metric_value in {
        "revenue_run_rate": snapshot["revenue_run_rate"],
        "net_margin": snapshot["net_margin"],
        "risk_exposure": snapshot["risk_exposure"],
    }.items():
        doc = frappe.get_doc(
            {
                "doctype": "KPI Snapshot",
                "company": company,
                "metric_code": metric_code,
                "metric_value": metric_value,
                "source": "scheduler",
                "recorded_at": frappe.utils.now_datetime(),
            }
        )
        doc.flags.ignore_permissions = True
        doc.insert()

    frappe.cache().set_value(f"ibms:kpi:{company}", snapshot, expires_in_sec=900)
    frappe.publish_realtime("ibms:kpi_update", snapshot)
    return snapshot
