import frappe


@frappe.whitelist(methods=["GET"], allow_guest=True)
def health():
    db_ok = bool(frappe.db.sql("select 1"))
    return {"status": "ok" if db_ok else "degraded", "db": db_ok}
