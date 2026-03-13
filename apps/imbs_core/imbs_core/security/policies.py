import frappe


def ai_alert_query_condition(user=None):
    user = user or frappe.session.user
    if "AI Admin" in frappe.get_roles(user):
        return "1=1"

    employee_company = frappe.db.get_value("Employee", {"user_id": user}, "company")
    if not employee_company:
        return "1=0"

    return f"`tabAI Alert`.company = {frappe.db.escape(employee_company)}"


def ai_alert_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if "AI Admin" in frappe.get_roles(user):
        return True

    employee_company = frappe.db.get_value("Employee", {"user_id": user}, "company")
    return bool(employee_company and doc.company == employee_company)


def enterprise_profile_query_condition(user=None):
    user = user or frappe.session.user
    if "System Manager" in frappe.get_roles(user) or "AI Admin" in frappe.get_roles(user):
        return "1=1"
    return f"`tabEnterprise Profile`.user = {frappe.db.escape(user)}"


def enterprise_profile_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if "System Manager" in frappe.get_roles(user) or "AI Admin" in frappe.get_roles(user):
        return True
    return doc.user == user
