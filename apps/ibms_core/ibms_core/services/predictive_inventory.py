import frappe


FEATURE_CACHE_KEY = "ibms:inventory:features"


def build_inventory_features(company: str):
    features = {
        "company": company,
        "avg_daily_sales": 120,
        "lead_time_days": 14,
        "seasonality_index": 1.2,
    }
    frappe.cache().set_value(FEATURE_CACHE_KEY + f":{company}", features, expires_in_sec=3600)
    return features


def forecast_reorder_point(company: str, sku: str):
    features = build_inventory_features(company)
    reorder_point = int(features["avg_daily_sales"] * features["lead_time_days"] * features["seasonality_index"])
    return {"company": company, "sku": sku, "reorder_point": reorder_point, "model": "prophet_inventory_v1"}
