import json
from typing import Any

import frappe


SCHEMA_SDL = """
type KPISnapshot {
  name: String!
  company: String!
  metric_code: String!
  metric_value: Float!
  recorded_at: String!
}

type AIRecommendation {
  name: String!
  company: String
  recommendation_code: String!
  confidence: Float!
  status: String!
}

type Query {
  kpiSnapshots(company: String!, limit: Int = 20): [KPISnapshot!]!
  recommendations(company: String!, status: String = "Open", limit: Int = 20): [AIRecommendation!]!
}
""".strip()


def _query_kpi_snapshots(company: str, limit: int) -> list[dict[str, Any]]:
    return frappe.get_all(
        "KPI Snapshot",
        filters={"company": company},
        fields=["name", "company", "metric_code", "metric_value", "recorded_at"],
        order_by="recorded_at desc",
        limit_page_length=min(max(int(limit), 1), 200),
    )


def _query_recommendations(company: str, status: str, limit: int) -> list[dict[str, Any]]:
    return frappe.get_all(
        "AI Recommendation",
        filters={"company": company, "status": status},
        fields=["name", "company", "recommendation_code", "confidence", "status"],
        order_by="modified desc",
        limit_page_length=min(max(int(limit), 1), 200),
    )


@frappe.whitelist(methods=["GET"])
def get_schema():
    return {"schema": SCHEMA_SDL}


@frappe.whitelist(methods=["POST"])
def execute(query: str, variables: str = "{}"):
    """Lightweight GraphQL-like gateway for enterprise dashboards.

    For production, replace this parser with graphql-core execution engine.
    """
    parsed_vars = json.loads(variables or "{}")

    if "kpiSnapshots" in query:
        company = parsed_vars.get("company")
        limit = parsed_vars.get("limit", 20)
        if not company:
            frappe.throw("Variable 'company' is required")
        return {"data": {"kpiSnapshots": _query_kpi_snapshots(company, limit)}}

    if "recommendations" in query:
        company = parsed_vars.get("company")
        status = parsed_vars.get("status", "Open")
        limit = parsed_vars.get("limit", 20)
        if not company:
            frappe.throw("Variable 'company' is required")
        return {"data": {"recommendations": _query_recommendations(company, status, limit)}}

    return {"errors": [{"message": "Query not supported by lightweight executor"}]}
