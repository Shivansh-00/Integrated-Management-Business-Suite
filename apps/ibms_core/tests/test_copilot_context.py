import server


def test_project_focus_context_covers_security_and_deployment():
    context = server._project_focus_context("How do auth tokens and Render deployment work?")
    assert "Security/auth components" in context
    assert "Deployment components" in context


def test_build_copilot_system_context_contains_project_knowledge_and_live_data():
    kpi = {
        "revenue_run_rate": 12500000,
        "net_margin": 18.4,
        "risk_exposure": 31.2,
        "forecast_accuracy": 94.7,
        "compliance_score": 97.1,
        "active_alerts": 3,
    }
    context = server._build_copilot_system_context(
        "Explain the frontend and ERP modules",
        kpi,
        "\nLive ERP Dataset:\n- Customers: 12 total\n- Products: 8 total",
    )

    assert "frontend/index.html" in context
    assert "ERPSummaryOps" in context
    assert "Revenue Run Rate" in context
    assert "Live ERP Dataset" in context
    assert "Do not invent files" in context