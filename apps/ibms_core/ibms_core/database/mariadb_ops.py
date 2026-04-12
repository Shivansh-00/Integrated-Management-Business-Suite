"""
MariaDB CRUD Operations for ERP Entities
==========================================
Async operations matching the pattern of MongoDB models.py
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ibms_core.database.mariadb_connection import get_session
from ibms_core.database.mariadb_models import (
    Customer,
    Employee,
    InventoryMovement,
    Invoice,
    Order,
    OrderItem,
    Product,
)


def _new_id() -> str:
    return str(uuid.uuid4())


def _serialize(obj) -> dict:
    """Convert an ORM object to a JSON-serializable dict."""
    if obj is None:
        return None
    d = {}
    for col in obj.__table__.columns:
        v = getattr(obj, col.name)
        if isinstance(v, datetime):
            v = v.isoformat()
        elif isinstance(v, Decimal):
            v = float(v)
        d[col.name] = v
    return d


def _serialize_list(objs: list) -> list[dict]:
    return [_serialize(o) for o in objs]


# ===================================================================
# CUSTOMER OPS
# ===================================================================

class CustomerOps:
    @staticmethod
    async def create(data: dict) -> dict:
        async with get_session() as session:
            customer = Customer(id=_new_id(), **data)
            session.add(customer)
            await session.flush()
            return _serialize(customer)

    @staticmethod
    async def get_by_id(customer_id: str) -> dict | None:
        async with get_session() as session:
            obj = await session.get(Customer, customer_id)
            return _serialize(obj)

    @staticmethod
    async def list_all(
        limit: int = 50, offset: int = 0,
        segment: str = "", search: str = "", active_only: bool = True,
    ) -> dict:
        async with get_session() as session:
            q = select(Customer)
            cq = select(func.count(Customer.id))
            if active_only:
                q = q.where(Customer.is_active == True)
                cq = cq.where(Customer.is_active == True)
            if segment:
                q = q.where(Customer.segment == segment)
                cq = cq.where(Customer.segment == segment)
            if search:
                pattern = f"%{search}%"
                q = q.where(Customer.name.ilike(pattern) | Customer.email.ilike(pattern))
                cq = cq.where(Customer.name.ilike(pattern) | Customer.email.ilike(pattern))
            total = (await session.execute(cq)).scalar_one()
            result = await session.execute(
                q.order_by(Customer.created_at.desc()).offset(offset).limit(limit)
            )
            return {"items": _serialize_list(result.scalars().all()), "total": total}

    @staticmethod
    async def update(customer_id: str, data: dict) -> dict | None:
        async with get_session() as session:
            obj = await session.get(Customer, customer_id)
            if not obj:
                return None
            for k, v in data.items():
                if hasattr(obj, k) and k != "id":
                    setattr(obj, k, v)
            await session.flush()
            return _serialize(obj)

    @staticmethod
    async def delete(customer_id: str) -> bool:
        async with get_session() as session:
            obj = await session.get(Customer, customer_id)
            if not obj:
                return False
            await session.delete(obj)
            return True

    @staticmethod
    async def get_stats() -> dict:
        async with get_session() as session:
            total = (await session.execute(select(func.count(Customer.id)))).scalar_one()
            active = (await session.execute(
                select(func.count(Customer.id)).where(Customer.is_active == True)
            )).scalar_one()
            total_outstanding = (await session.execute(
                select(func.coalesce(func.sum(Customer.outstanding_balance), 0))
            )).scalar_one()
            return {
                "total_customers": total,
                "active_customers": active,
                "total_outstanding": float(total_outstanding),
            }


# ===================================================================
# PRODUCT OPS
# ===================================================================

class ProductOps:
    @staticmethod
    async def create(data: dict) -> dict:
        async with get_session() as session:
            product = Product(id=_new_id(), **data)
            session.add(product)
            await session.flush()
            return _serialize(product)

    @staticmethod
    async def get_by_id(product_id: str) -> dict | None:
        async with get_session() as session:
            obj = await session.get(Product, product_id)
            return _serialize(obj)

    @staticmethod
    async def get_by_sku(sku: str) -> dict | None:
        async with get_session() as session:
            result = await session.execute(select(Product).where(Product.sku == sku))
            obj = result.scalar_one_or_none()
            return _serialize(obj)

    @staticmethod
    async def list_all(
        limit: int = 50, offset: int = 0,
        category: str = "", search: str = "", active_only: bool = True,
    ) -> dict:
        async with get_session() as session:
            q = select(Product)
            cq = select(func.count(Product.id))
            if active_only:
                q = q.where(Product.is_active == True)
                cq = cq.where(Product.is_active == True)
            if category:
                q = q.where(Product.category == category)
                cq = cq.where(Product.category == category)
            if search:
                pattern = f"%{search}%"
                q = q.where(Product.name.ilike(pattern) | Product.sku.ilike(pattern))
                cq = cq.where(Product.name.ilike(pattern) | Product.sku.ilike(pattern))
            total = (await session.execute(cq)).scalar_one()
            result = await session.execute(
                q.order_by(Product.created_at.desc()).offset(offset).limit(limit)
            )
            return {"items": _serialize_list(result.scalars().all()), "total": total}

    @staticmethod
    async def update(product_id: str, data: dict) -> dict | None:
        async with get_session() as session:
            obj = await session.get(Product, product_id)
            if not obj:
                return None
            for k, v in data.items():
                if hasattr(obj, k) and k != "id":
                    setattr(obj, k, v)
            await session.flush()
            return _serialize(obj)

    @staticmethod
    async def delete(product_id: str) -> bool:
        async with get_session() as session:
            obj = await session.get(Product, product_id)
            if not obj:
                return False
            await session.delete(obj)
            return True

    @staticmethod
    async def get_low_stock(threshold: int = 0) -> list[dict]:
        async with get_session() as session:
            q = select(Product).where(
                Product.is_active == True,
                Product.stock_quantity <= Product.reorder_level,
            )
            if threshold > 0:
                q = q.where(Product.stock_quantity <= threshold)
            result = await session.execute(q.order_by(Product.stock_quantity.asc()))
            return _serialize_list(result.scalars().all())

    @staticmethod
    async def get_stats() -> dict:
        async with get_session() as session:
            total = (await session.execute(select(func.count(Product.id)))).scalar_one()
            total_value = (await session.execute(
                select(func.coalesce(func.sum(Product.unit_price * Product.stock_quantity), 0))
            )).scalar_one()
            low_stock = (await session.execute(
                select(func.count(Product.id)).where(
                    Product.is_active == True,
                    Product.stock_quantity <= Product.reorder_level,
                )
            )).scalar_one()
            return {
                "total_products": total,
                "total_inventory_value": float(total_value),
                "low_stock_count": low_stock,
            }


# ===================================================================
# ORDER OPS
# ===================================================================

class OrderOps:
    @staticmethod
    async def create(data: dict, items: list[dict]) -> dict:
        async with get_session() as session:
            order_id = _new_id()
            order_number = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            subtotal = Decimal("0")
            tax_total = Decimal("0")
            order_items = []

            for item_data in items:
                product = await session.get(Product, item_data["product_id"])
                if not product:
                    continue
                qty = item_data.get("quantity", 1)
                unit_price = product.unit_price
                discount_pct = Decimal(str(item_data.get("discount_pct", 0)))
                line_total = unit_price * qty * (1 - discount_pct / 100)
                tax = line_total * product.tax_rate / 100

                order_items.append(OrderItem(
                    id=_new_id(), order_id=order_id, product_id=product.id,
                    quantity=qty, unit_price=unit_price, discount_pct=discount_pct,
                    line_total=line_total,
                ))
                subtotal += line_total
                tax_total += tax

            discount_amount = Decimal(str(data.get("discount_amount", 0)))
            total = subtotal + tax_total - discount_amount

            order = Order(
                id=order_id, order_number=order_number,
                customer_id=data["customer_id"],
                status=data.get("status", "draft"),
                subtotal=subtotal, tax_amount=tax_total,
                discount_amount=discount_amount, total_amount=total,
                notes=data.get("notes"),
            )
            session.add(order)
            for oi in order_items:
                session.add(oi)
            await session.flush()
            result = _serialize(order)
            result["items"] = _serialize_list(order_items)
            result["order_number"] = order_number
            return result

    @staticmethod
    async def get_by_id(order_id: str) -> dict | None:
        async with get_session() as session:
            obj = await session.get(Order, order_id)
            if not obj:
                return None
            result = _serialize(obj)
            items_q = select(OrderItem).where(OrderItem.order_id == order_id)
            items_result = await session.execute(items_q)
            result["items"] = _serialize_list(items_result.scalars().all())
            return result

    @staticmethod
    async def list_all(
        limit: int = 50, offset: int = 0,
        status: str = "", customer_id: str = "",
    ) -> dict:
        async with get_session() as session:
            q = select(Order)
            cq = select(func.count(Order.id))
            if status:
                q = q.where(Order.status == status)
                cq = cq.where(Order.status == status)
            if customer_id:
                q = q.where(Order.customer_id == customer_id)
                cq = cq.where(Order.customer_id == customer_id)
            total = (await session.execute(cq)).scalar_one()
            result = await session.execute(
                q.order_by(Order.created_at.desc()).offset(offset).limit(limit)
            )
            return {"items": _serialize_list(result.scalars().all()), "total": total}

    @staticmethod
    async def update_status(order_id: str, new_status: str) -> dict | None:
        async with get_session() as session:
            obj = await session.get(Order, order_id)
            if not obj:
                return None
            obj.status = new_status
            await session.flush()
            return _serialize(obj)

    @staticmethod
    async def get_stats() -> dict:
        async with get_session() as session:
            total = (await session.execute(select(func.count(Order.id)))).scalar_one()
            total_value = (await session.execute(
                select(func.coalesce(func.sum(Order.total_amount), 0))
            )).scalar_one()
            pending = (await session.execute(
                select(func.count(Order.id)).where(Order.status.in_(["draft", "confirmed", "processing"]))
            )).scalar_one()
            return {
                "total_orders": total,
                "total_order_value": float(total_value),
                "pending_orders": pending,
            }


# ===================================================================
# INVOICE OPS
# ===================================================================

class InvoiceOps:
    @staticmethod
    async def create(data: dict) -> dict:
        async with get_session() as session:
            inv_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            invoice = Invoice(
                id=_new_id(), invoice_number=inv_number,
                customer_id=data["customer_id"],
                order_id=data.get("order_id"),
                due_date=data.get("due_date"),
                subtotal=Decimal(str(data.get("subtotal", 0))),
                tax_amount=Decimal(str(data.get("tax_amount", 0))),
                total_amount=Decimal(str(data.get("total_amount", 0))),
                notes=data.get("notes"),
            )
            session.add(invoice)
            await session.flush()
            return _serialize(invoice)

    @staticmethod
    async def get_by_id(invoice_id: str) -> dict | None:
        async with get_session() as session:
            obj = await session.get(Invoice, invoice_id)
            return _serialize(obj)

    @staticmethod
    async def list_all(
        limit: int = 50, offset: int = 0,
        status: str = "", customer_id: str = "",
    ) -> dict:
        async with get_session() as session:
            q = select(Invoice)
            cq = select(func.count(Invoice.id))
            if status:
                q = q.where(Invoice.status == status)
                cq = cq.where(Invoice.status == status)
            if customer_id:
                q = q.where(Invoice.customer_id == customer_id)
                cq = cq.where(Invoice.customer_id == customer_id)
            total = (await session.execute(cq)).scalar_one()
            result = await session.execute(
                q.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)
            )
            return {"items": _serialize_list(result.scalars().all()), "total": total}

    @staticmethod
    async def update_status(invoice_id: str, new_status: str, paid_amount: float = None) -> dict | None:
        async with get_session() as session:
            obj = await session.get(Invoice, invoice_id)
            if not obj:
                return None
            obj.status = new_status
            if paid_amount is not None:
                obj.paid_amount = Decimal(str(paid_amount))
            await session.flush()
            return _serialize(obj)

    @staticmethod
    async def get_stats() -> dict:
        async with get_session() as session:
            total = (await session.execute(select(func.count(Invoice.id)))).scalar_one()
            total_value = (await session.execute(
                select(func.coalesce(func.sum(Invoice.total_amount), 0))
            )).scalar_one()
            total_paid = (await session.execute(
                select(func.coalesce(func.sum(Invoice.paid_amount), 0))
            )).scalar_one()
            overdue = (await session.execute(
                select(func.count(Invoice.id)).where(Invoice.status == "overdue")
            )).scalar_one()
            return {
                "total_invoices": total,
                "total_invoiced": float(total_value),
                "total_collected": float(total_paid),
                "outstanding": float(total_value - total_paid),
                "overdue_count": overdue,
            }


# ===================================================================
# EMPLOYEE OPS
# ===================================================================

class EmployeeOps:
    @staticmethod
    async def create(data: dict) -> dict:
        async with get_session() as session:
            emp = Employee(id=_new_id(), **data)
            session.add(emp)
            await session.flush()
            return _serialize(emp)

    @staticmethod
    async def get_by_id(emp_id: str) -> dict | None:
        async with get_session() as session:
            obj = await session.get(Employee, emp_id)
            return _serialize(obj)

    @staticmethod
    async def list_all(
        limit: int = 50, offset: int = 0,
        department: str = "", search: str = "", active_only: bool = True,
    ) -> dict:
        async with get_session() as session:
            q = select(Employee)
            cq = select(func.count(Employee.id))
            if active_only:
                q = q.where(Employee.is_active == True)
                cq = cq.where(Employee.is_active == True)
            if department:
                q = q.where(Employee.department == department)
                cq = cq.where(Employee.department == department)
            if search:
                pattern = f"%{search}%"
                q = q.where(
                    Employee.first_name.ilike(pattern) |
                    Employee.last_name.ilike(pattern) |
                    Employee.email.ilike(pattern)
                )
                cq = cq.where(
                    Employee.first_name.ilike(pattern) |
                    Employee.last_name.ilike(pattern) |
                    Employee.email.ilike(pattern)
                )
            total = (await session.execute(cq)).scalar_one()
            result = await session.execute(
                q.order_by(Employee.created_at.desc()).offset(offset).limit(limit)
            )
            return {"items": _serialize_list(result.scalars().all()), "total": total}

    @staticmethod
    async def update(emp_id: str, data: dict) -> dict | None:
        async with get_session() as session:
            obj = await session.get(Employee, emp_id)
            if not obj:
                return None
            for k, v in data.items():
                if hasattr(obj, k) and k != "id":
                    setattr(obj, k, v)
            await session.flush()
            return _serialize(obj)

    @staticmethod
    async def get_stats() -> dict:
        async with get_session() as session:
            total = (await session.execute(select(func.count(Employee.id)))).scalar_one()
            active = (await session.execute(
                select(func.count(Employee.id)).where(Employee.is_active == True)
            )).scalar_one()
            total_salary = (await session.execute(
                select(func.coalesce(func.sum(Employee.salary), 0)).where(Employee.is_active == True)
            )).scalar_one()
            return {
                "total_employees": total,
                "active_employees": active,
                "total_monthly_salary": float(total_salary),
            }


# ===================================================================
# INVENTORY MOVEMENT OPS
# ===================================================================

class InventoryMovementOps:
    @staticmethod
    async def record(product_id: str, movement_type: str, quantity: int,
                     reference_type: str = None, reference_id: str = None,
                     notes: str = None) -> dict:
        async with get_session() as session:
            movement = InventoryMovement(
                id=_new_id(), product_id=product_id,
                movement_type=movement_type, quantity=quantity,
                reference_type=reference_type, reference_id=reference_id,
                notes=notes,
            )
            session.add(movement)

            # Update product stock
            product = await session.get(Product, product_id)
            if product:
                if movement_type in ("purchase", "return"):
                    product.stock_quantity += quantity
                elif movement_type in ("sale",):
                    product.stock_quantity -= quantity
                elif movement_type == "adjustment":
                    product.stock_quantity = quantity

            await session.flush()
            return _serialize(movement)

    @staticmethod
    async def get_by_product(product_id: str, limit: int = 50) -> list[dict]:
        async with get_session() as session:
            q = select(InventoryMovement).where(
                InventoryMovement.product_id == product_id
            ).order_by(InventoryMovement.created_at.desc()).limit(limit)
            result = await session.execute(q)
            return _serialize_list(result.scalars().all())


# ===================================================================
# ERP SUMMARY (cross-table aggregations)
# ===================================================================

class ERPSummaryOps:
    @staticmethod
    async def get_overview() -> dict:
        customer_stats = await CustomerOps.get_stats()
        product_stats = await ProductOps.get_stats()
        order_stats = await OrderOps.get_stats()
        invoice_stats = await InvoiceOps.get_stats()
        employee_stats = await EmployeeOps.get_stats()
        return {
            "customers": customer_stats,
            "products": product_stats,
            "orders": order_stats,
            "invoices": invoice_stats,
            "employees": employee_stats,
        }
