import frappe


def run():
    frappe.logger("imbs_jobs").info("Optimizing workflows from historical approval telemetry")
