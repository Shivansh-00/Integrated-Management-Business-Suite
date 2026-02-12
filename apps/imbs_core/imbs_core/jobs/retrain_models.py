import frappe


def enqueue_retraining():
    frappe.enqueue("imbs_core.jobs.retrain_models.run", queue="ml-heavy", job_name="imbs-retrain-models")


def run():
    frappe.logger("imbs_jobs").info("Retraining AI models via background pipeline")
