import frappe


def run():
    frappe.logger("imbs_jobs").info("Running nightly compliance checks")
