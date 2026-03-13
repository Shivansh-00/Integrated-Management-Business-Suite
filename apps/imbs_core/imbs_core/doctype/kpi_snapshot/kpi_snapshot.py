import frappe
from frappe.model.document import Document


class KPISnapshot(Document):
    def validate(self):
        if self.metric_value is None:
            frappe.throw("Metric value is required")
        if not self.recorded_at:
            self.recorded_at = frappe.utils.now_datetime()
