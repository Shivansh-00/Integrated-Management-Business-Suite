import frappe
from frappe.model.document import Document


class EnterpriseProfile(Document):
    def validate(self):
        if not self.user:
            frappe.throw("User is required")

        existing = frappe.get_all(
            "Enterprise Profile",
            filters={"user": self.user, "name": ["!=", self.name]},
            pluck="name",
        )
        if existing:
            frappe.throw("Only one enterprise profile is allowed per user")
