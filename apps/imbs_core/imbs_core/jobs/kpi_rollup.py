from collections import defaultdict

import frappe


def run():
    rows = frappe.get_all(
        "KPI Snapshot",
        fields=["company", "metric_code", "metric_value"],
        limit_page_length=5000,
    )

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row.company, row.metric_code)].append(float(row.metric_value or 0))

    rollups = {}
    for key, values in grouped.items():
        rollups[f"{key[0]}:{key[1]}"] = {
            "count": len(values),
            "avg": round(sum(values) / max(len(values), 1), 4),
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
        }

    frappe.cache().set_value("imbs:kpi:rollups", rollups, expires_in_sec=3600)
    return rollups
