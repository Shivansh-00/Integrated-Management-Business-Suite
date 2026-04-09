import frappe


def enqueue_retraining():
    frappe.enqueue("ibms_core.jobs.retrain_models.run", queue="ml-heavy", job_name="ibms-retrain-models")


def run():
    frappe.logger("ibms_jobs").info("Retraining AI models via background pipeline")
