import frappe
from frappe.model.document import Document


class IntegrationWebhookLog(Document):
    def validate(self):
        if not self.received_at:
            self.received_at = frappe.utils.now_datetime()
        if self.http_status is None:
            self.http_status = 0
