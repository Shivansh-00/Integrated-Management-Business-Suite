import frappe
from frappe.model.document import Document


class AIRecommendation(Document):
    def validate(self):
        if self.confidence is not None and (self.confidence < 0 or self.confidence > 1):
            frappe.throw("Confidence must be between 0 and 1")
        if not self.generated_at:
            self.generated_at = frappe.utils.now_datetime()
