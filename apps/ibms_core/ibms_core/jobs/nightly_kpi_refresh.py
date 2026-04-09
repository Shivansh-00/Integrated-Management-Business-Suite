from ibms_core.services.kpi_engine import refresh_kpis


def run():
    for company in ["Default Company"]:
        refresh_kpis(company)
