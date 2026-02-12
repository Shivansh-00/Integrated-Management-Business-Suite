app_name = "imbs_core"
app_title = "IMBS Core"
app_publisher = "IMBS Team"
app_description = "AI-first ERP extensions for Frappe"
app_email = "engineering@example.com"
app_license = "MIT"

doc_events = {
    "Sales Invoice": {
        "on_submit": "imbs_core.events.publisher.on_sales_invoice_submit",
    }
}

scheduler_events = {
    "cron": {
        "*/15 * * * *": ["imbs_core.services.anomaly.refresh_anomaly_models"],
        "0 2 * * *": ["imbs_core.jobs.retrain_models.run"],
        "0 3 * * *": ["imbs_core.jobs.nightly_kpi_refresh.run"],
        "30 3 * * *": ["imbs_core.jobs.compliance_check.run"],
        "0 4 * * 0": ["imbs_core.jobs.auto_workflow_optimizer.run"],
    }
}

permission_query_conditions = {
    "AI Alert": "imbs_core.security.policies.ai_alert_query_condition",
}

has_permission = {
    "AI Alert": "imbs_core.security.policies.ai_alert_has_permission",
}

app_include_js = ["/assets/imbs_core/ui/real_time_kpi.js", "/assets/imbs_core/ui/ai_insights_panel.js"]
app_include_css = ["/assets/imbs_core/ui/dark_mode.css"]
