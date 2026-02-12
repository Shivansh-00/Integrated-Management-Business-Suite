import frappe
from frappe.model.document import Document


class SmartDecisionRule(Document):
    def validate(self):
        if self.threshold < 0 or self.threshold > 100:
            frappe.throw("Threshold must be between 0 and 100")
