import frappe


SCHEMA_SDL = """
type KPI { revenue_run_rate: Float, net_margin: Float, risk_exposure: Float }
type Query { kpi(company: String!): KPI }
""".strip()


@frappe.whitelist(methods=["GET"])
def get_schema():
    return {"schema": SCHEMA_SDL}
