from __future__ import annotations

import re
from typing import Any

import frappe


def _safe_metric_lookup(company: str) -> list[dict[str, Any]]:
    return frappe.get_all(
        "KPI Snapshot",
        filters={"company": company},
        fields=["metric_code", "metric_value", "recorded_at"],
        order_by="recorded_at desc",
        limit_page_length=20,
    )


def ask_assistant(question: str, company: str, user: str) -> dict[str, Any]:
    q = (question or "").strip().lower()
    metrics = _safe_metric_lookup(company)

    if not q:
        return {"answer": "Please provide a question.", "context": {"company": company}}

    if re.search(r"(risk|exposure|fraud)", q):
        risk_items = [m for m in metrics if "risk" in (m.get("metric_code") or "").lower()]
        return {
            "answer": "Current risk indicators are summarized in recent KPI snapshots.",
            "risk_metrics": risk_items,
            "user": user,
        }

    if re.search(r"(revenue|margin|kpi|dashboard)", q):
        return {
            "answer": "Here are the latest KPI metrics for your dashboard.",
            "kpis": metrics,
            "user": user,
        }

    return {
        "answer": "I can help with KPI trends, risks, forecasts, and recommendations. Ask a focused question for best results.",
        "user": user,
    }


def recommend_actions(company: str) -> dict[str, Any]:
    open_recommendations = frappe.get_all(
        "AI Recommendation",
        filters={"company": company, "status": "Open"},
        fields=["name", "recommendation_code", "confidence", "owner"],
        order_by="confidence desc",
        limit_page_length=25,
    )

    return {
        "company": company,
        "count": len(open_recommendations),
        "recommendations": open_recommendations,
    }
