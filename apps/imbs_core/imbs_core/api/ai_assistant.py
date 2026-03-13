import frappe

from imbs_core.services.ai_assistant import ask_assistant, recommend_actions


@frappe.whitelist(methods=["POST"])
def chat(question: str, company: str = "Default Company"):
    if frappe.session.user == "Guest":
        frappe.throw("Authentication required", frappe.AuthenticationError)
    return ask_assistant(question=question, company=company, user=frappe.session.user)


@frappe.whitelist(methods=["GET"])
def recommendations(company: str = "Default Company"):
    if not frappe.has_permission("AI Recommendation", "read"):
        frappe.throw("Not permitted", frappe.PermissionError)
    return recommend_actions(company)
