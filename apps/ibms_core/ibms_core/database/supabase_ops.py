"""
Supabase ERP Operations — replaces mariadb_ops.py
===================================================
All async operations for ERP modules:
Customers, Products, Orders, Invoices, Employees, InventoryMovements.

Column mapping: Supabase tables use ``id`` and ``name`` as generic PK/name
columns.  Code & API layer expect ``customer_id``, ``product_name``, etc.
_remap_from_db / _remap_to_db helpers handle the translation transparently.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from ibms_core.database.supabase_connection import get_supabase_async

_logger = logging.getLogger("ibms.supabase_ops")

# In-memory fallback stores (used when Supabase is unavailable)
_mem: dict[str, dict] = {
    "customers": {},
    "products": {},
    "orders": {},
    "order_items": {},
    "invoices": {},
    "employees": {},
    "inventory_movements": {},
}


def _try_get_async():
    """Return async Supabase client or None if unavailable."""
    try:
        return get_supabase_async()
    except RuntimeError:
        return None


# ===================================================================
# HELPERS
# ===================================================================

def _new_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize(row: dict | None) -> dict | None:
    """Normalize row for JSON (handle Decimal, datetime)."""
    if row is None:
        return None
    out = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def _serialize_list(rows: list[dict]) -> list[dict]:
    return [_serialize(r) for r in rows]


def _first_or_none(response) -> dict | None:
    data = response.data
    if data and len(data) > 0:
        return data[0]
    return None


# --- DB ↔ API column mapping helpers ---

def _remap_from_db(row: dict | None, id_alias: str, name_alias: str | None = None) -> dict | None:
    """Remap Supabase ``id``/``name`` columns back to API-expected names.

    Keeps both the original key (``id``, ``name``) **and** the alias so that
    callers using either convention work correctly.
    """
    if row is None:
        return None
    out = dict(row)
    if "id" in out and id_alias != "id":
        out[id_alias] = out["id"]          # keep both "id" and alias
    if name_alias and "name" in out and name_alias != "name":
        out[name_alias] = out["name"]      # keep both "name" and alias
    return out


def _remap_from_db_list(rows: list[dict], id_alias: str, name_alias: str | None = None) -> list[dict]:
    return [_remap_from_db(r, id_alias, name_alias) for r in rows]


# ===================================================================
# CUSTOMERS
# ===================================================================

class CustomerOps:

    @staticmethod
    async def create(data: dict) -> dict:
        customer_id = _new_id()
        doc = {
            "id": customer_id,
            "name": data.get("name", data.get("customer_name", "")),
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "company": data.get("company", ""),
            "segment": data.get("segment", "Regular"),
            "credit_limit": float(data.get("credit_limit", 0)),
            "outstanding_balance": float(data.get("outstanding_balance", 0)),
            "is_active": data.get("is_active", True),
            "address": data.get("address", ""),
            "city": data.get("city", ""),
            "country": data.get("country", ""),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        sb = _try_get_async()
        if sb:
            result = await sb.table("customers").insert(doc).execute()
            row = result.data[0] if result.data else doc
            return _serialize(_remap_from_db(row, "customer_id", "customer_name"))
        _mem["customers"][customer_id] = doc
        return _serialize(_remap_from_db(doc.copy(), "customer_id", "customer_name"))

    @staticmethod
    async def get_by_id(customer_id: str) -> dict | None:
        sb = _try_get_async()
        if sb:
            result = await sb.table("customers").select("*").eq("id", customer_id).limit(1).execute()
            return _serialize(_remap_from_db(_first_or_none(result), "customer_id", "customer_name"))
        return _serialize(_remap_from_db(_mem["customers"].get(customer_id), "customer_id", "customer_name"))

    @staticmethod
    async def list_all(limit: int = 50, offset: int = 0, segment: str = "",
                       search: str = "", active_only: bool = False) -> list[dict]:
        sb = _try_get_async()
        if sb:
            q = sb.table("customers").select("*").order("created_at", desc=True)
            if segment:
                q = q.eq("segment", segment)
            if active_only:
                q = q.eq("is_active", True)
            if search:
                q = q.or_(f"name.ilike.%{search}%,email.ilike.%{search}%,company.ilike.%{search}%")
            q = q.range(offset, offset + limit - 1)
            result = await q.execute()
            return _serialize_list(_remap_from_db_list(result.data or [], "customer_id", "customer_name"))
        items = list(_mem["customers"].values())
        if segment:
            items = [i for i in items if i.get("segment") == segment]
        if search:
            s = search.lower()
            items = [i for i in items if s in (i.get("name", "") + i.get("email", "")).lower()]
        return _serialize_list(_remap_from_db_list(items[offset:offset + limit], "customer_id", "customer_name"))

    @staticmethod
    async def update(customer_id: str, data: dict) -> dict | None:
        sb = _try_get_async()
        if sb:
            data["updated_at"] = _now_iso()
            data.pop("customer_id", None)
            data.pop("created_at", None)
            # API sends "name"; DB column is also "name" — no rename needed
            result = await sb.table("customers").update(data).eq("id", customer_id).execute()
            return _serialize(_remap_from_db(result.data[0] if result.data else None, "customer_id", "customer_name"))
        if customer_id in _mem["customers"]:
            _mem["customers"][customer_id].update(data)
            _mem["customers"][customer_id]["updated_at"] = _now_iso()
            return _serialize(_remap_from_db(_mem["customers"][customer_id], "customer_id", "customer_name"))
        return None

    @staticmethod
    async def delete(customer_id: str) -> bool:
        sb = _try_get_async()
        if sb:
            result = await sb.table("customers").delete().eq("id", customer_id).execute()
            return bool(result.data)
        return bool(_mem["customers"].pop(customer_id, None))

    @staticmethod
    async def get_stats() -> dict:
        sb = _try_get_async()
        if sb:
            total_res = await sb.table("customers").select("id", count="exact").execute()
            active_res = await sb.table("customers").select("id", count="exact").eq("is_active", True).execute()
            return {
                "total": total_res.count or 0,
                "active": active_res.count or 0,
            }
        items = list(_mem["customers"].values())
        return {
            "total": len(items),
            "active": sum(1 for i in items if i.get("is_active", True)),
        }


# ===================================================================
# PRODUCTS
# ===================================================================

class ProductOps:

    @staticmethod
    async def create(data: dict) -> dict:
        product_id = _new_id()
        doc = {
            "id": product_id,
            "name": data.get("name", data.get("product_name", "")),
            "sku": data.get("sku", ""),
            "category": data.get("category", ""),
            "unit_price": float(data.get("unit_price", 0)),
            "cost_price": float(data.get("cost_price", 0)),
            "tax_rate": float(data.get("tax_rate", 0)),
            "stock_quantity": int(data.get("stock_quantity", 0)),
            "reorder_level": int(data.get("reorder_level", 10)),
            "is_active": data.get("is_active", True),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        sb = _try_get_async()
        if sb:
            result = await sb.table("products").insert(doc).execute()
            row = result.data[0] if result.data else doc
            return _serialize(_remap_from_db(row, "product_id", "product_name"))
        _mem["products"][product_id] = doc
        return _serialize(_remap_from_db(doc.copy(), "product_id", "product_name"))

    @staticmethod
    async def get_by_id(product_id: str) -> dict | None:
        sb = _try_get_async()
        if sb:
            result = await sb.table("products").select("*").eq("id", product_id).limit(1).execute()
            return _serialize(_remap_from_db(_first_or_none(result), "product_id", "product_name"))
        return _serialize(_remap_from_db(_mem["products"].get(product_id), "product_id", "product_name"))

    @staticmethod
    async def get_by_sku(sku: str) -> dict | None:
        sb = _try_get_async()
        if sb:
            result = await sb.table("products").select("*").eq("sku", sku).limit(1).execute()
            return _serialize(_remap_from_db(_first_or_none(result), "product_id", "product_name"))
        for p in _mem["products"].values():
            if p.get("sku") == sku:
                return _serialize(_remap_from_db(p, "product_id", "product_name"))
        return None

    @staticmethod
    async def list_all(limit: int = 50, offset: int = 0, category: str = "",
                       search: str = "", active_only: bool = False) -> list[dict]:
        sb = _try_get_async()
        if sb:
            q = sb.table("products").select("*").order("created_at", desc=True)
            if category:
                q = q.eq("category", category)
            if active_only:
                q = q.eq("is_active", True)
            if search:
                q = q.or_(f"name.ilike.%{search}%,sku.ilike.%{search}%,category.ilike.%{search}%")
            q = q.range(offset, offset + limit - 1)
            result = await q.execute()
            return _serialize_list(_remap_from_db_list(result.data or [], "product_id", "product_name"))
        items = list(_mem["products"].values())
        if category:
            items = [i for i in items if i.get("category") == category]
        if search:
            s = search.lower()
            items = [i for i in items if s in (i.get("name", "") + i.get("sku", "")).lower()]
        return _serialize_list(_remap_from_db_list(items[offset:offset + limit], "product_id", "product_name"))

    @staticmethod
    async def update(product_id: str, data: dict) -> dict | None:
        sb = _try_get_async()
        if sb:
            data["updated_at"] = _now_iso()
            data.pop("product_id", None)
            data.pop("created_at", None)
            # API sends "name"; DB column is also "name" — no rename needed
            result = await sb.table("products").update(data).eq("id", product_id).execute()
            return _serialize(_remap_from_db(result.data[0] if result.data else None, "product_id", "product_name"))
        if product_id in _mem["products"]:
            _mem["products"][product_id].update(data)
            _mem["products"][product_id]["updated_at"] = _now_iso()
            return _serialize(_remap_from_db(_mem["products"][product_id], "product_id", "product_name"))
        return None

    @staticmethod
    async def delete(product_id: str) -> bool:
        sb = _try_get_async()
        if sb:
            result = await sb.table("products").delete().eq("id", product_id).execute()
            return bool(result.data)
        return bool(_mem["products"].pop(product_id, None))

    @staticmethod
    async def get_low_stock(threshold: int = 10) -> list[dict]:
        sb = _try_get_async()
        if sb:
            result = await sb.table("products").select("*").eq("is_active", True).lte("stock_quantity", threshold).execute()
            return _serialize_list(_remap_from_db_list(result.data or [], "product_id", "product_name"))
        return _serialize_list(_remap_from_db_list(
            [p for p in _mem["products"].values() if int(p.get("stock_quantity", 0)) <= threshold],
            "product_id", "product_name"))

    @staticmethod
    async def get_stats() -> dict:
        sb = _try_get_async()
        if sb:
            total_res = await sb.table("products").select("id", count="exact").execute()
            active_res = await sb.table("products").select("id", count="exact").eq("is_active", True).execute()
            low_stock_res = await sb.table("products").select("id", count="exact").eq("is_active", True).lte("stock_quantity", 10).execute()
            return {
                "total": total_res.count or 0,
                "active": active_res.count or 0,
                "low_stock": low_stock_res.count or 0,
            }
        items = list(_mem["products"].values())
        return {
            "total": len(items),
            "active": sum(1 for i in items if i.get("is_active", True)),
            "low_stock": sum(1 for i in items if int(i.get("stock_quantity", 0)) <= 10),
        }


# ===================================================================
# ORDERS
# ===================================================================

class OrderOps:

    @staticmethod
    async def _next_order_number() -> str:
        sb = _try_get_async()
        if sb:
            result = await sb.table("orders").select("order_number").order("created_at", desc=True).limit(1).execute()
            if result.data:
                last = result.data[0].get("order_number", "ORD-0000")
                try:
                    num = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    num = 1
            else:
                num = 1
            return f"ORD-{num:04d}"
        num = len(_mem["orders"]) + 1
        return f"ORD-{num:04d}"

    @staticmethod
    async def create(data: dict, items_list: list | None = None) -> dict:
        order_id = _new_id()
        order_number = await OrderOps._next_order_number()
        items = items_list if items_list is not None else data.get("items", [])

        # Calculate totals from items
        total_amount = 0.0
        order_items = []
        for item in items:
            product_id = item.get("product_id", "")
            qty = int(item.get("quantity", 1))
            unit_price = float(item.get("unit_price", 0))
            discount_pct = float(item.get("discount_pct", 0))

            # If unit_price not provided, look up product
            if unit_price == 0 and product_id:
                product = await ProductOps.get_by_id(product_id)
                if product:
                    unit_price = float(product.get("unit_price", 0))

            line_total = round(qty * unit_price * (1 - discount_pct / 100), 2)
            total_amount += line_total
            order_items.append({
                "id": _new_id(),
                "order_id": order_id,
                "product_id": product_id,
                "quantity": qty,
                "unit_price": unit_price,
                "discount_pct": discount_pct,
                "line_total": line_total,
            })

        discount_amount = float(data.get("discount_amount", 0))
        total_amount = max(0, round(total_amount - discount_amount, 2))

        order_doc = {
            "id": order_id,
            "order_number": order_number,
            "customer_id": data.get("customer_id", ""),
            "order_date": _now_iso(),
            "status": data.get("status", "Draft"),
            "subtotal": total_amount + discount_amount,
            "discount_amount": discount_amount,
            "tax_amount": 0.0,
            "total_amount": total_amount,
            "notes": data.get("notes", ""),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }

        sb = _try_get_async()
        if sb:
            await sb.table("orders").insert(order_doc).execute()
            if order_items:
                await sb.table("order_items").insert(order_items).execute()
        else:
            _mem["orders"][order_id] = order_doc
            for oi in order_items:
                _mem["order_items"][oi["id"]] = oi

        result = _remap_from_db(order_doc.copy(), "order_id")
        result["items"] = order_items
        return _serialize(result)

    @staticmethod
    async def get_by_id(order_id: str) -> dict | None:
        sb = _try_get_async()
        if sb:
            result = await sb.table("orders").select("*").eq("id", order_id).limit(1).execute()
            order = _first_or_none(result)
            if not order:
                return None
            items_result = await sb.table("order_items").select("*").eq("order_id", order_id).execute()
            order["items"] = items_result.data or []
            return _serialize(_remap_from_db(order, "order_id"))
        order = _mem["orders"].get(order_id)
        if not order:
            return None
        order = order.copy()
        order["items"] = [v for v in _mem["order_items"].values() if v.get("order_id") == order_id]
        return _serialize(_remap_from_db(order, "order_id"))

    @staticmethod
    async def list_all(limit: int = 50, offset: int = 0, status: str = "",
                       customer_id: str = "", search: str = "") -> list[dict]:
        sb = _try_get_async()
        if sb:
            q = sb.table("orders").select("*").order("created_at", desc=True)
            if status:
                q = q.eq("status", status)
            if customer_id:
                q = q.eq("customer_id", customer_id)
            if search:
                q = q.or_(f"order_number.ilike.%{search}%")
            q = q.range(offset, offset + limit - 1)
            result = await q.execute()
            return _serialize_list(_remap_from_db_list(result.data or [], "order_id"))
        items = list(_mem["orders"].values())
        if status:
            items = [i for i in items if i.get("status") == status]
        if customer_id:
            items = [i for i in items if i.get("customer_id") == customer_id]
        return _serialize_list(_remap_from_db_list(items[offset:offset + limit], "order_id"))

    @staticmethod
    async def update_status(order_id: str, status: str) -> dict | None:
        sb = _try_get_async()
        if sb:
            result = await sb.table("orders").update({
                "status": status,
                "updated_at": _now_iso(),
            }).eq("id", order_id).execute()
            return _serialize(_remap_from_db(result.data[0] if result.data else None, "order_id"))
        if order_id in _mem["orders"]:
            _mem["orders"][order_id]["status"] = status
            _mem["orders"][order_id]["updated_at"] = _now_iso()
            return _serialize(_remap_from_db(_mem["orders"][order_id], "order_id"))
        return None

    @staticmethod
    async def get_stats() -> dict:
        sb = _try_get_async()
        if sb:
            total_res = await sb.table("orders").select("id", count="exact").execute()
            pending_res = await sb.table("orders").select("id", count="exact").in_("status", ["Draft", "Pending"]).execute()
            return {
                "total": total_res.count or 0,
                "pending": pending_res.count or 0,
            }
        items = list(_mem["orders"].values())
        return {
            "total": len(items),
            "pending": sum(1 for i in items if i.get("status") in ("Draft", "Pending")),
        }


# ===================================================================
# INVOICES
# ===================================================================

class InvoiceOps:

    @staticmethod
    async def _next_invoice_number() -> str:
        sb = _try_get_async()
        if sb:
            result = await sb.table("invoices").select("invoice_number").order("created_at", desc=True).limit(1).execute()
            if result.data:
                last = result.data[0].get("invoice_number", "INV-0000")
                try:
                    num = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    num = 1
            else:
                num = 1
            return f"INV-{num:04d}"
        num = len(_mem["invoices"]) + 1
        return f"INV-{num:04d}"

    @staticmethod
    async def create(data: dict) -> dict:
        invoice_id = _new_id()
        invoice_number = await InvoiceOps._next_invoice_number()
        doc = {
            "id": invoice_id,
            "invoice_number": invoice_number,
            "order_id": data.get("order_id") or None,
            "customer_id": data.get("customer_id", ""),
            "invoice_date": _now_iso(),
            "due_date": data.get("due_date"),
            "status": data.get("status", "Draft"),
            "subtotal": float(data.get("subtotal", 0)),
            "tax_amount": float(data.get("tax_amount", 0)),
            "total_amount": float(data.get("total_amount", 0)),
            "paid_amount": float(data.get("paid_amount", 0)),
            "notes": data.get("notes", ""),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        sb = _try_get_async()
        if sb:
            result = await sb.table("invoices").insert(doc).execute()
            row = result.data[0] if result.data else doc
            return _serialize(_remap_from_db(row, "invoice_id"))
        _mem["invoices"][invoice_id] = doc
        return _serialize(_remap_from_db(doc.copy(), "invoice_id"))

    @staticmethod
    async def get_by_id(invoice_id: str) -> dict | None:
        sb = _try_get_async()
        if sb:
            result = await sb.table("invoices").select("*").eq("id", invoice_id).limit(1).execute()
            return _serialize(_remap_from_db(_first_or_none(result), "invoice_id"))
        return _serialize(_remap_from_db(_mem["invoices"].get(invoice_id), "invoice_id"))

    @staticmethod
    async def list_all(limit: int = 50, offset: int = 0, status: str = "",
                       customer_id: str = "", search: str = "") -> list[dict]:
        sb = _try_get_async()
        if sb:
            q = sb.table("invoices").select("*").order("created_at", desc=True)
            if status:
                q = q.eq("status", status)
            if customer_id:
                q = q.eq("customer_id", customer_id)
            if search:
                q = q.or_(f"invoice_number.ilike.%{search}%")
            q = q.range(offset, offset + limit - 1)
            result = await q.execute()
            return _serialize_list(_remap_from_db_list(result.data or [], "invoice_id"))
        items = list(_mem["invoices"].values())
        if status:
            items = [i for i in items if i.get("status") == status]
        if customer_id:
            items = [i for i in items if i.get("customer_id") == customer_id]
        return _serialize_list(_remap_from_db_list(items[offset:offset + limit], "invoice_id"))

    @staticmethod
    async def update_status(invoice_id: str, status: str, paid_amount: float | None = None) -> dict | None:
        sb = _try_get_async()
        if sb:
            updates: dict = {"status": status, "updated_at": _now_iso()}
            if paid_amount is not None:
                updates["paid_amount"] = float(paid_amount)
            result = await sb.table("invoices").update(updates).eq("id", invoice_id).execute()
            return _serialize(_remap_from_db(result.data[0] if result.data else None, "invoice_id"))
        if invoice_id in _mem["invoices"]:
            _mem["invoices"][invoice_id]["status"] = status
            if paid_amount is not None:
                _mem["invoices"][invoice_id]["paid_amount"] = float(paid_amount)
            _mem["invoices"][invoice_id]["updated_at"] = _now_iso()
            return _serialize(_remap_from_db(_mem["invoices"][invoice_id], "invoice_id"))
        return None

    @staticmethod
    async def get_stats() -> dict:
        sb = _try_get_async()
        if sb:
            total_res = await sb.table("invoices").select("id", count="exact").execute()
            unpaid_res = await sb.table("invoices").select("id", count="exact").in_("status", ["Draft", "Sent", "Overdue"]).execute()
            return {
                "total": total_res.count or 0,
                "unpaid": unpaid_res.count or 0,
            }
        items = list(_mem["invoices"].values())
        return {
            "total": len(items),
            "unpaid": sum(1 for i in items if i.get("status") in ("Draft", "Sent", "Overdue")),
        }


# ===================================================================
# EMPLOYEES
# ===================================================================

class EmployeeOps:

    @staticmethod
    async def create(data: dict) -> dict:
        employee_id = _new_id()
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        doc = {
            "id": employee_id,
            "employee_code": data.get("employee_code", ""),
            "first_name": first_name,
            "last_name": last_name,
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "department": data.get("department", ""),
            "designation": data.get("designation", data.get("position", "")),
            "date_of_joining": data.get("date_of_joining", data.get("hire_date", _now_iso())),
            "salary": float(data.get("salary", 0)),
            "is_active": data.get("is_active", True),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        sb = _try_get_async()
        if sb:
            result = await sb.table("employees").insert(doc).execute()
            row = result.data[0] if result.data else doc
            out = _remap_from_db(row, "employee_id")
            out["employee_name"] = f"{out.get('first_name', '')} {out.get('last_name', '')}".strip()
            return _serialize(out)
        _mem["employees"][employee_id] = doc
        out = _remap_from_db(doc.copy(), "employee_id")
        out["employee_name"] = f"{out.get('first_name', '')} {out.get('last_name', '')}".strip()
        return _serialize(out)

    @staticmethod
    async def get_by_id(employee_id: str) -> dict | None:
        sb = _try_get_async()
        if sb:
            result = await sb.table("employees").select("*").eq("id", employee_id).limit(1).execute()
            row = _first_or_none(result)
            if not row:
                return None
            out = _remap_from_db(row, "employee_id")
            out["employee_name"] = f"{out.get('first_name', '')} {out.get('last_name', '')}".strip()
            return _serialize(out)
        row = _mem["employees"].get(employee_id)
        if not row:
            return None
        out = _remap_from_db(row, "employee_id")
        out["employee_name"] = f"{out.get('first_name', '')} {out.get('last_name', '')}".strip()
        return _serialize(out)

    @staticmethod
    async def list_all(limit: int = 50, offset: int = 0, department: str = "",
                       search: str = "", status: str = "") -> list[dict]:
        sb = _try_get_async()
        if sb:
            q = sb.table("employees").select("*").order("created_at", desc=True)
            if department:
                q = q.eq("department", department)
            if status == "Active":
                q = q.eq("is_active", True)
            elif status == "Inactive":
                q = q.eq("is_active", False)
            if search:
                q = q.or_(f"first_name.ilike.%{search}%,last_name.ilike.%{search}%,email.ilike.%{search}%,department.ilike.%{search}%")
            q = q.range(offset, offset + limit - 1)
            result = await q.execute()
            rows = _remap_from_db_list(result.data or [], "employee_id")
            for r in rows:
                r["employee_name"] = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
            return _serialize_list(rows)
        items = list(_mem["employees"].values())
        if department:
            items = [i for i in items if i.get("department") == department]
        if search:
            s = search.lower()
            items = [i for i in items if s in (i.get("first_name", "") + " " + i.get("last_name", "") + i.get("email", "")).lower()]
        rows = _remap_from_db_list(items[offset:offset + limit], "employee_id")
        for r in rows:
            r["employee_name"] = f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
        return _serialize_list(rows)

    @staticmethod
    async def update(employee_id: str, data: dict) -> dict | None:
        sb = _try_get_async()
        data["updated_at"] = _now_iso()
        if "position" in data:
            data["designation"] = data.pop("position")
        if "hire_date" in data:
            data["date_of_joining"] = data.pop("hire_date")
        data.pop("employee_id", None)
        data.pop("employee_name", None)
        data.pop("created_at", None)
        if sb:
            result = await sb.table("employees").update(data).eq("id", employee_id).execute()
            row = result.data[0] if result.data else None
            if not row:
                return None
            out = _remap_from_db(row, "employee_id")
            out["employee_name"] = f"{out.get('first_name', '')} {out.get('last_name', '')}".strip()
            return _serialize(out)
        if employee_id in _mem["employees"]:
            _mem["employees"][employee_id].update(data)
            out = _remap_from_db(_mem["employees"][employee_id], "employee_id")
            out["employee_name"] = f"{out.get('first_name', '')} {out.get('last_name', '')}".strip()
            return _serialize(out)
        return None

    @staticmethod
    async def get_stats() -> dict:
        sb = _try_get_async()
        if sb:
            total_res = await sb.table("employees").select("id", count="exact").execute()
            active_res = await sb.table("employees").select("id", count="exact").eq("is_active", True).execute()
            return {
                "total": total_res.count or 0,
                "active": active_res.count or 0,
            }
        items = list(_mem["employees"].values())
        return {
            "total": len(items),
            "active": sum(1 for i in items if i.get("is_active", True)),
        }


# ===================================================================
# INVENTORY MOVEMENTS
# ===================================================================

class InventoryMovementOps:

    @staticmethod
    async def record(product_id: str = "", movement_type: str = "IN",
                     quantity: int = 0, reference_type: str = None,
                     reference_id: str = None, notes: str = None, **kwargs) -> dict:
        movement_id = _new_id()
        qty = int(quantity)

        # Get current stock
        product = await ProductOps.get_by_id(product_id)
        current_stock = int(product.get("stock_quantity", 0)) if product else 0
        if movement_type == "IN":
            new_stock = current_stock + qty
        else:
            new_stock = max(0, current_stock - qty)

        # DB columns: id, product_id, movement_type, quantity, reference_type, reference_id, notes, created_at
        db_doc = {
            "id": movement_id,
            "product_id": product_id,
            "movement_type": movement_type,
            "quantity": qty,
            "reference_type": reference_type or "",
            "reference_id": reference_id or "",
            "notes": notes or "",
            "created_at": _now_iso(),
        }

        sb = _try_get_async()
        if sb:
            await sb.table("inventory_movements").insert(db_doc).execute()
            await sb.table("products").update({
                "stock_quantity": new_stock,
                "updated_at": _now_iso(),
            }).eq("id", product_id).execute()
        else:
            _mem["inventory_movements"][movement_id] = db_doc
            if product_id in _mem["products"]:
                _mem["products"][product_id]["stock_quantity"] = new_stock

        # Return enriched response for API consumers
        api_doc = _remap_from_db(db_doc.copy(), "movement_id")
        api_doc["stock_after"] = new_stock
        return _serialize(api_doc)

    @staticmethod
    async def get_by_product(product_id: str, limit: int = 50) -> list[dict]:
        sb = _try_get_async()
        if sb:
            result = await sb.table("inventory_movements").select("*").eq("product_id", product_id).order("created_at", desc=True).limit(limit).execute()
            return _serialize_list(_remap_from_db_list(result.data or [], "movement_id"))
        items = [v for v in _mem["inventory_movements"].values() if v.get("product_id") == product_id]
        return _serialize_list(_remap_from_db_list(items[:limit], "movement_id"))


# ===================================================================
# ERP SUMMARY
# ===================================================================

class ERPSummaryOps:

    @staticmethod
    async def get_overview() -> dict:
        try:
            customer_stats = await CustomerOps.get_stats()
        except Exception:
            customer_stats = {"total": 0, "active": 0}
        try:
            product_stats = await ProductOps.get_stats()
        except Exception:
            product_stats = {"total": 0, "active": 0, "low_stock": 0}
        try:
            order_stats = await OrderOps.get_stats()
        except Exception:
            order_stats = {"total": 0, "pending": 0}
        try:
            invoice_stats = await InvoiceOps.get_stats()
        except Exception:
            invoice_stats = {"total": 0, "unpaid": 0}
        try:
            employee_stats = await EmployeeOps.get_stats()
        except Exception:
            employee_stats = {"total": 0, "active": 0}
        return {
            "customers": customer_stats,
            "products": product_stats,
            "orders": order_stats,
            "invoices": invoice_stats,
            "employees": employee_stats,
        }
