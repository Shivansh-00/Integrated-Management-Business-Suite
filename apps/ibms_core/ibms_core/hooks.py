app_name = "ibms_core"
app_title = "IBMS Core"
app_publisher = "IBMS Team"
app_description = "AI-first ERP extensions for Frappe"
app_email = "engineering@example.com"
app_license = "MIT"
app_version = "2.1.0"

auth_hooks = ["ibms_core.security.auth_hooks.validate_api_token"]

doc_events = {
    "Sales Invoice": {
        "on_submit": "ibms_core.events.publisher.on_sales_invoice_submit",
    },
    "Integration Webhook Log": {
        "after_insert": "ibms_core.events.event_router.on_webhook_log_insert",
    },
}

scheduler_events = {
    "cron": {
        "*/15 * * * *": ["ibms_core.services.anomaly.refresh_anomaly_models"],
        "0 2 * * *": ["ibms_core.jobs.retrain_models.run"],
        "0 3 * * *": ["ibms_core.jobs.nightly_kpi_refresh.run"],
        "30 3 * * *": ["ibms_core.jobs.compliance_check.run"],
        "0 4 * * 0": ["ibms_core.jobs.auto_workflow_optimizer.run"],
    },
    "hourly": ["ibms_core.jobs.kpi_rollup.run"],
    "all": ["ibms_core.jobs.process_webhook_queue.run"],
}

permission_query_conditions = {
    "AI Alert": "ibms_core.security.policies.ai_alert_query_condition",
    "Enterprise Profile": "ibms_core.security.policies.enterprise_profile_query_condition",
}

has_permission = {
    "AI Alert": "ibms_core.security.policies.ai_alert_has_permission",
    "Enterprise Profile": "ibms_core.security.policies.enterprise_profile_has_permission",
}

app_include_js = [
    "/assets/ibms_core/ui/real_time_kpi.js",
    "/assets/ibms_core/ui/ai_insights_panel.js",
    "/assets/ibms_core/js/enterprise_dashboard.js",
]
app_include_css = [
    "/assets/ibms_core/ui/dark_mode.css",
    "/assets/ibms_core/css/enterprise_theme.css",
]

doctype_js = {
    "Enterprise Profile": "public/js/enterprise_profile.js",
    "KPI Snapshot": "public/js/kpi_snapshot.js",
}
