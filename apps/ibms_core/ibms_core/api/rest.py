import json
from typing import Any

import frappe
from frappe import _

ALLOWED_DOCTYPES = {
    "Enterprise Profile",
    "Smart Decision Rule",
    "KPI Snapshot",
    "AI Recommendation",
    "Integration Webhook Log",
}


def _ensure_supported_doctype(doctype: str):
    if doctype not in ALLOWED_DOCTYPES:
        frappe.throw(_("Doctype is not exposed by the public REST layer"), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def list_resources(doctype: str, limit_start: int = 0, limit_page_length: int = 20, filters: str = "{}"):
    _ensure_supported_doctype(doctype)
    parsed_filters = json.loads(filters or "{}")

    rows = frappe.get_all(
        doctype,
        filters=parsed_filters,
        fields=["name", "owner", "modified"],
        limit_start=int(limit_start),
        limit_page_length=min(int(limit_page_length), 200),
    )
    return {"doctype": doctype, "rows": rows}


@frappe.whitelist(methods=["POST"])
def create_resource(doctype: str, payload: str):
    _ensure_supported_doctype(doctype)
    data = json.loads(payload or "{}")
    data["doctype"] = doctype

    doc = frappe.get_doc(data)
    doc.insert()
    return {"message": "created", "name": doc.name}


@frappe.whitelist(methods=["PUT"])
def update_resource(doctype: str, name: str, payload: str):
    _ensure_supported_doctype(doctype)
    data = json.loads(payload or "{}")

    doc = frappe.get_doc(doctype, name)
    doc.update(data)
    doc.save()
    return {"message": "updated", "name": doc.name}


@frappe.whitelist(methods=["DELETE"])
def delete_resource(doctype: str, name: str):
    _ensure_supported_doctype(doctype)
    frappe.delete_doc(doctype, name)
    return {"message": "deleted", "name": name}


@frappe.whitelist(methods=["POST"])
def bulk_import_json(doctype: str, payload: str):
    _ensure_supported_doctype(doctype)
    rows: list[dict[str, Any]] = json.loads(payload or "[]")

    created = []
    for row in rows:
        row["doctype"] = doctype
        doc = frappe.get_doc(row)
        doc.insert()
        created.append(doc.name)

    return {"message": "bulk import complete", "count": len(created), "names": created}


@frappe.whitelist(methods=["GET"])
def export_json(doctype: str, filters: str = "{}"):
    _ensure_supported_doctype(doctype)
    parsed_filters = json.loads(filters or "{}")
    rows = frappe.get_all(doctype, filters=parsed_filters, fields=["*"])
    return {"doctype": doctype, "count": len(rows), "rows": rows}
