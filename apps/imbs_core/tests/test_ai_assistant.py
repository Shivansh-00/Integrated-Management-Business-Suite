from imbs_core.services import ai_assistant


class FakeFrappe:
    def get_all(self, doctype, filters=None, fields=None, order_by=None, limit_page_length=None):
        if doctype == "KPI Snapshot":
            return [
                {"metric_code": "risk_exposure", "metric_value": 32.1, "recorded_at": "2026-03-13T00:00:00"},
                {"metric_code": "revenue_run_rate", "metric_value": 12500000, "recorded_at": "2026-03-13T00:00:00"},
            ]
        if doctype == "AI Recommendation":
            return [
                {"name": "REC-0001", "recommendation_code": "WF-REDUCE-APPROVAL-HOPS", "confidence": 0.78, "owner": "Administrator"}
            ]
        return []


def test_assistant_risk_query(monkeypatch):
    monkeypatch.setattr(ai_assistant, "frappe", FakeFrappe())
    result = ai_assistant.ask_assistant("show risk details", "Default Company", "alice@example.com")
    assert "risk_metrics" in result
    assert len(result["risk_metrics"]) >= 1


def test_recommendations_payload(monkeypatch):
    monkeypatch.setattr(ai_assistant, "frappe", FakeFrappe())
    result = ai_assistant.recommend_actions("Default Company")
    assert result["count"] == 1
    assert result["recommendations"][0]["recommendation_code"] == "WF-REDUCE-APPROVAL-HOPS"
