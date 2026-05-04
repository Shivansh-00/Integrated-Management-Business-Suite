# UML Diagrams — IBMS (Integrated Business Management Suite)

| Field              | Detail                                              |
|--------------------|-----------------------------------------------------|
| **Project Name**   | Integrated Business Management Suite (IBMS) v2.0    |
| **Team**           | Shivansh Srivastava (Product Developer), Prahallad Padhan (Product Owner), Ranveer Rai Khare (Scrum Master) |
| **Sprint**         | Sprint 2                                            |
| **Date**           | April 24, 2026                                      |
| **Course**         | SEPM (Software Engineering and Project Management)  |
| **Standard**       | UML 2.5 (Unified Modeling Language)                 |

---

## Diagram Index

| # | Diagram Type      | Title                              | Purpose                                          |
|---|-------------------|------------------------------------|--------------------------------------------------|
| 1 | Use Case Diagram  | IBMS System — Actor Use Cases      | Defines actors and their interactions with IBMS  |
| 2 | Class Diagram     | IBMS ERP — Domain Model             | Shows ERP entity structure and associations      |
| 3 | Sequence Diagram  | Order-to-Cash Business Flow        | Traces full lifecycle from order to payment      |

---

## Diagram 1: Use Case Diagram

**Purpose:** Shows all primary actors in the IBMS system and the use cases each actor can perform. Relationships include `<<include>>` (mandatory sub-flow) and `<<extend>>` (optional sub-flow).

```mermaid
flowchart LR
    %% ── Actor definitions ──────────────────────────────────────
    classDef actor  fill:#dbeafe,stroke:#1d4ed8,stroke-width:2px,color:#0f172a,rx:8
    classDef uc     fill:#fefce8,stroke:#ca8a04,stroke-width:1.5px,color:#0f172a,rx:20
    classDef system fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#0f172a
    classDef ext    fill:#fdf4ff,stroke:#9333ea,stroke-width:1.5px,color:#0f172a,rx:8

    %% ── Actors ──────────────────────────────────────────────────
    ExecActor(["👤 Executive"])
    FinActor(["👤 Finance Manager"])
    OpsActor(["👤 Operations Manager"])
    CompActor(["👤 Compliance Officer"])
    AdminActor(["👤 System Admin"])
    ExtActor(["👤 External Partner"])

    %% ── System boundary ─────────────────────────────────────────
    subgraph IBMS["  IBMS System Boundary  "]
        direction TB

        subgraph AUTH ["Authentication & Access"]
            UC_Login["Login with Credentials"]
            UC_2FA["Verify MFA / 2FA"]
            UC_Logout["Logout"]
            UC_Token["Refresh JWT Token"]
        end

        subgraph ERP ["ERP Operations"]
            UC_ManCust["Manage Customers"]
            UC_ManProd["Manage Products"]
            UC_ManInv["Record Inventory Movement"]
            UC_CreateOrder["Create & Confirm Order"]
            UC_GenInv["Generate Invoice"]
            UC_RecPay["Record Payment"]
        end

        subgraph ANALYTICS ["Analytics & Intelligence"]
            UC_KPI["View KPI Dashboard"]
            UC_Risk["Run Risk Assessment"]
            UC_Forecast["View Demand Forecast"]
            UC_AI["Get AI Insights"]
            UC_Copilot["Use AI Copilot"]
        end

        subgraph COMPLIANCE ["Compliance & Audit"]
            UC_CompCheck["Run Compliance Check"]
            UC_AuditLog["View Audit Log"]
            UC_ApproveInv["Approve High-Value Invoice"]
        end

        subgraph ADMIN ["System Administration"]
            UC_ManUsers["Manage Users & Roles"]
            UC_ViewMetrics["View System Metrics"]
            UC_CfgSecurity["Configure Security Settings"]
            UC_ViewHealth["View Health & Uptime"]
        end
    end

    %% ── Auth associations ────────────────────────────────────────
    ExecActor  -->|uses| UC_Login
    FinActor   -->|uses| UC_Login
    OpsActor   -->|uses| UC_Login
    CompActor  -->|uses| UC_Login
    AdminActor -->|uses| UC_Login
    UC_Login   -.->|"<<include>>"| UC_2FA

    %% ── ERP associations ─────────────────────────────────────────
    OpsActor  -->|uses| UC_ManCust
    OpsActor  -->|uses| UC_ManProd
    OpsActor  -->|uses| UC_ManInv
    OpsActor  -->|uses| UC_CreateOrder
    FinActor  -->|uses| UC_GenInv
    FinActor  -->|uses| UC_RecPay
    UC_CreateOrder -.->|"<<include>>"| UC_GenInv
    UC_GenInv      -.->|"<<extend>>"| UC_ApproveInv

    %% ── Analytics associations ───────────────────────────────────
    ExecActor  -->|uses| UC_KPI
    ExecActor  -->|uses| UC_AI
    ExecActor  -->|uses| UC_Copilot
    FinActor   -->|uses| UC_Forecast
    OpsActor   -->|uses| UC_Risk
    UC_KPI     -.->|"<<include>>"| UC_Risk

    %% ── Compliance associations ──────────────────────────────────
    CompActor  -->|uses| UC_CompCheck
    CompActor  -->|uses| UC_AuditLog
    CompActor  -->|uses| UC_ApproveInv

    %% ── Admin associations ───────────────────────────────────────
    AdminActor -->|uses| UC_ManUsers
    AdminActor -->|uses| UC_ViewMetrics
    AdminActor -->|uses| UC_CfgSecurity
    AdminActor -->|uses| UC_ViewHealth

    %% ── External partner ─────────────────────────────────────────
    ExtActor   -->|uses| UC_Login
    ExtActor   -->|uses| UC_KPI

    %% ── Apply styles ─────────────────────────────────────────────
    class ExecActor,FinActor,OpsActor,CompActor,AdminActor,ExtActor actor
    class UC_Login,UC_2FA,UC_Logout,UC_Token uc
    class UC_ManCust,UC_ManProd,UC_ManInv,UC_CreateOrder,UC_GenInv,UC_RecPay uc
    class UC_KPI,UC_Risk,UC_Forecast,UC_AI,UC_Copilot uc
    class UC_CompCheck,UC_AuditLog,UC_ApproveInv uc
    class UC_ManUsers,UC_ViewMetrics,UC_CfgSecurity,UC_ViewHealth uc
```

### 1.1 Actor Descriptions

| Actor               | Role Description                                                                         |
|---------------------|------------------------------------------------------------------------------------------|
| **Executive**       | Views KPI dashboards, AI insights, and strategic forecasts; read-only on most ERP data   |
| **Finance Manager** | Generates invoices, records payments, views financial forecasts; write access to ERP finance flows |
| **Operations Manager** | Full CRUD on customers, products, inventory; creates and confirms orders              |
| **Compliance Officer** | Runs compliance checks, reviews audit logs, approves high-value invoices (> ₹500k)  |
| **System Admin**    | Manages all users and roles; views system metrics and health; configures security settings |
| **External Partner** | Limited access via dedicated partner token; views KPI dashboard and submits requests   |

### 1.2 Use Case Relationships

| Relationship          | From                    | To                       | Type         | Notes                                     |
|-----------------------|-------------------------|--------------------------|--------------|-------------------------------------------|
| Login → 2FA           | Login with Credentials  | Verify MFA / 2FA         | `<<include>>`| 2FA is mandatory for all users            |
| Create Order → Invoice | Create & Confirm Order | Generate Invoice         | `<<include>>`| Invoice auto-generated on order confirm   |
| Generate Invoice → Approve | Generate Invoice  | Approve High-Value Invoice | `<<extend>>`| Triggered only when amount > ₹500,000   |
| View KPI → Risk       | View KPI Dashboard      | Run Risk Assessment      | `<<include>>`| KPI dashboard embeds risk scores          |

---

## Diagram 2: Class Diagram

**Purpose:** Defines the complete IBMS ERP domain model — all entity classes, their attributes, methods, and inter-class relationships (associations, compositions, dependencies).

```mermaid
classDiagram
    direction TB

    %% ── User & Auth ──────────────────────────────────────────────
    class User {
        +String id
        +String username
        +String email
        +String password_hash
        +String role
        +Boolean is_active
        +Boolean mfa_enabled
        +DateTime created_at
        +DateTime last_login
        +login(credentials) Token
        +logout(token_id) void
        +refresh_token(token) Token
        +verify_mfa(otp) Boolean
    }

    class AuditLog {
        +String id
        +String user_id
        +String entity_type
        +String entity_id
        +String action
        +JSON diff
        +DateTime timestamp
        +String ip_address
        +record(user, entity, action, diff) void
        +query(filters) List~AuditLog~
    }

    %% ── ERP Core Entities ────────────────────────────────────────
    class Customer {
        +String id
        +String name
        +String email
        +String phone
        +String company
        +String address
        +Boolean is_active
        +DateTime created_at
        +DateTime updated_at
        +create(data) Customer
        +update(id, data) Customer
        +soft_delete(id) void
        +get_orders() List~Order~
    }

    class Product {
        +String id
        +String name
        +String sku
        +String category
        +Float unit_price
        +Integer quantity
        +Integer reorder_threshold
        +Boolean is_active
        +DateTime created_at
        +create(data) Product
        +update(id, data) Product
        +is_low_stock() Boolean
        +get_movements() List~InventoryMovement~
    }

    class InventoryMovement {
        +String id
        +String product_id
        +String movement_type
        +Integer quantity
        +String note
        +String created_by
        +DateTime created_at
        +record(product_id, type, qty, note) InventoryMovement
        +validate_stock(product, delta) void
    }

    class Order {
        +String id
        +String customer_id
        +String status
        +Float total_amount
        +String created_by
        +DateTime created_at
        +DateTime updated_at
        +create(customer_id, items) Order
        +confirm() void
        +ship() void
        +deliver() void
        +cancel() void
        +calculate_total() Float
    }

    class OrderLineItem {
        +String id
        +String order_id
        +String product_id
        +Integer quantity
        +Float unit_price
        +Float subtotal
        +calculate_subtotal() Float
    }

    class Invoice {
        +String id
        +String order_id
        +Float amount
        +String status
        +Boolean compliance_hold
        +String approval_reference
        +String issued_by
        +DateTime issued_at
        +DateTime due_date
        +generate(order) Invoice
        +approve(approval_ref) void
        +trigger_compliance_check() ComplianceResult
        +mark_paid() void
    }

    class Payment {
        +String id
        +String invoice_id
        +Float amount
        +String payment_method
        +String transaction_ref
        +String recorded_by
        +DateTime payment_date
        +record(invoice_id, amount, method) Payment
        +confirm() void
        +get_receipt() PaymentReceipt
    }

    %% ── Service Layer ────────────────────────────────────────────
    class ERPBaseService {
        <<abstract>>
        +DB db
        +AuditLog audit
        +paginate(query, page, size) Page
        +validate_role(user, min_role) void
        +log_mutation(user, entity, diff) void
    }

    class OrderService {
        +create_order(user, data) Order
        +confirm_order(user, order_id) Order
        +ship_order(user, order_id) Order
        +deliver_order(user, order_id) Order
        +cancel_order(user, order_id) Order
    }

    class InvoiceService {
        +generate_invoice(order_id) Invoice
        +approve_invoice(invoice_id, ref) Invoice
        +get_compliance_status(invoice_id) ComplianceResult
    }

    class ComplianceEngine {
        +THRESHOLD : Float
        +check(invoice) ComplianceResult
        +notify_compliance_officer(invoice) void
        +release_hold(invoice_id, approver) void
    }

    %% ── Relationships ────────────────────────────────────────────
    User "1" --> "0..*" AuditLog         : generates
    User "1" --> "0..*" Order            : manages

    Customer "1" --> "0..*" Order        : places

    Order "1" *-- "1..*" OrderLineItem   : composed of
    Order "1" --> "0..1" Invoice         : generates

    OrderLineItem "0..*" --> "1" Product : references

    Product "1" --> "0..*" InventoryMovement : tracked by

    Invoice "1" --> "0..1" Payment       : settled by
    Invoice "1" ..> ComplianceEngine     : <<uses>>

    ERPBaseService <|-- OrderService     : extends
    ERPBaseService <|-- InvoiceService   : extends
    OrderService "1" ..> InvoiceService  : <<uses>>
    InvoiceService "1" ..> ComplianceEngine : <<uses>>
```

### 2.1 Class Relationship Summary

| Relationship                   | Type          | Multiplicity | Description                                          |
|--------------------------------|---------------|--------------|------------------------------------------------------|
| Customer → Order               | Association   | 1 to 0..*    | A customer can place multiple orders                 |
| Order → OrderLineItem          | Composition   | 1 to 1..*    | Line items cannot exist without their order          |
| OrderLineItem → Product        | Association   | many to 1    | Each line item references one product                |
| Product → InventoryMovement    | Association   | 1 to 0..*    | All stock in/out movements are linked to a product   |
| Order → Invoice               | Association   | 1 to 0..1    | An invoice is generated when an order is confirmed   |
| Invoice → Payment              | Association   | 1 to 0..1    | An invoice is settled by at most one payment         |
| ERPBaseService → OrderService  | Inheritance   | —            | OrderService inherits common CRUD/auth/audit helpers |
| Invoice → ComplianceEngine     | Dependency    | —            | Invoice checks compliance for amounts > ₹500k       |
| User → AuditLog                | Association   | 1 to 0..*    | Every user mutation creates an audit entry           |

### 2.2 Role Enumeration

| Role       | Permissions                                                                |
|------------|----------------------------------------------------------------------------|
| `admin`    | Full system access including user management and metrics                   |
| `manager`  | Full ERP CRUD, compliance actions, approve invoices                        |
| `analyst`  | Read ERP data, run analytics, use AI copilot                               |
| `viewer`   | Read-only access to KPIs and dashboards; no write operations               |

---

## Diagram 3: Sequence Diagram — Order-to-Cash Business Flow

**Purpose:** Traces the complete Order-to-Cash business workflow across all IBMS system components — from an authenticated API request through order creation, invoice generation, compliance checking, payment recording, and live KPI push.

```mermaid
sequenceDiagram
    autonumber

    actor Client as 👤 Client (Operations Manager)
    participant NGX  as Nginx Reverse Proxy
    participant API  as FastAPI Application
    participant AUTH as Auth Middleware (JWT + RBAC)
    participant OS   as OrderService
    participant IS   as InvoiceService
    participant CE   as ComplianceEngine
    participant PS   as PaymentService
    participant DB   as PostgreSQL / MongoDB
    participant WS   as WebSocket Hub

    rect rgb(219, 234, 254)
        Note over Client, AUTH: Phase 1 — Authentication
        Client ->> NGX  : POST /api/v1/auth/login {email, password}
        NGX    ->> API  : Forward request + security headers
        API    ->> DB   : SELECT user WHERE email = ?
        DB     -->> API : User record {hashed_pwd, role, mfa_enabled}
        API    ->> AUTH : Verify password hash + issue JWT
        AUTH   -->> Client : 200 OK {access_token, expires_in: 3600}
    end

    rect rgb(240, 253, 244)
        Note over Client, DB: Phase 2 — Create Order
        Client ->> NGX  : POST /api/v1/orders {customer_id, items:[{product_id, qty}]}
        NGX    ->> API  : Forward + rate-limit check
        API    ->> AUTH : Validate Bearer JWT
        AUTH   -->> API : User context {id, role: "manager"}
        API    ->> OS   : create_order(user, customer_id, items)

        OS     ->> DB   : SELECT customer WHERE id = customer_id
        DB     -->> OS  : Customer record (valid)
        OS     ->> DB   : SELECT products WHERE id IN (item_ids) FOR UPDATE
        DB     -->> OS  : Product records {quantities}

        OS     ->> DB   : BEGIN TRANSACTION
        OS     ->> DB   : INSERT INTO orders (customer_id, status="pending", total)
        OS     ->> DB   : INSERT INTO order_line_items (order_id, product_id, qty, price)
        OS     ->> DB   : UPDATE products SET quantity -= delta [per item]
        OS     ->> DB   : INSERT INTO audit_log (user_id, entity="Order", action="create")
        OS     ->> DB   : COMMIT TRANSACTION
        DB     -->> OS  : order_id = "ORD-2026-0312"

        OS     -->> API : Order {id, status: "pending", total: ₹6,250}
        API    -->> Client : 201 Created {order}
    end

    rect rgb(254, 252, 232)
        Note over Client, WS: Phase 3 — Confirm Order & Generate Invoice
        Client ->> API  : PATCH /api/v1/orders/ORD-2026-0312/confirm
        API    ->> AUTH : Validate JWT + check role >= manager
        AUTH   -->> API : Authorised
        API    ->> OS   : confirm_order(order_id)
        OS     ->> DB   : UPDATE orders SET status = "confirmed"

        OS     ->> IS   : generate_invoice(order_id)
        IS     ->> DB   : INSERT INTO invoices {order_id, amount=₹6250, status="issued"}
        DB     -->> IS  : invoice_id = "INV-2026-0201"

        alt Invoice amount > ₹500,000
            IS  ->> CE  : check_compliance(invoice)
            CE  ->> DB  : Log compliance check event
            CE  -->> IS : {hold: true, reason: "High-value approval required"}
            IS  ->> DB  : UPDATE invoices SET compliance_hold = true
            IS  -->> OS : Invoice {compliance_hold: true, status: "pending_approval"}
            OS  -->> API : Order confirmed; invoice on hold
            API -->> Client : 200 OK {order: confirmed, invoice: pending_approval}
        else Invoice amount <= ₹500,000
            IS  -->> OS : Invoice {compliance_hold: false, status: "issued"}
            OS  -->> API : Order confirmed; invoice issued
            API -->> Client : 200 OK {order: confirmed, invoice: issued}
        end
    end

    rect rgb(253, 242, 248)
        Note over Client, WS: Phase 4 — Record Payment
        Client ->> API  : POST /api/v1/payments {invoice_id, method: "bank_transfer", amount: ₹6250}
        API    ->> AUTH : Validate JWT + check role >= manager
        AUTH   -->> API : Authorised
        API    ->> PS   : record_payment(invoice_id, amount, method)

        PS     ->> DB   : BEGIN TRANSACTION
        PS     ->> DB   : INSERT INTO payments {invoice_id, amount, method, date}
        PS     ->> DB   : UPDATE invoices SET status = "paid"
        PS     ->> DB   : INSERT INTO audit_log (user_id, entity="Payment", action="create")
        PS     ->> DB   : COMMIT TRANSACTION
        DB     -->> PS  : payment_id = "PAY-2026-0155"

        PS     -->> API : Payment confirmed {payment_id, invoice_status: "paid"}

        API    ->> WS   : Broadcast {event: "kpi_update", revenue_delta: ₹6250}
        WS    -->> Client : Real-time KPI dashboard refresh {total_revenue: updated}

        API    -->> Client : 201 Created {payment, receipt_url: "/invoices/INV-2026-0201/receipt"}
    end
```

### 3.1 Sequence Flow Summary

| Phase | Step | Component | Description                                            |
|-------|------|-----------|--------------------------------------------------------|
| 1     | 1–6  | Auth layer | Client authenticates; JWT issued with role = manager  |
| 2     | 7–18 | OrderService + DB | Transactional order creation; products updated atomically |
| 3     | 19–31 | OrderService + InvoiceService + ComplianceEngine | Invoice auto-generated; compliance evaluated |
| 4     | 32–42 | PaymentService + WebSocket | Payment recorded; dashboard KPI updated in real time |

### 3.2 Exception / Alternate Flows

| Condition                           | Response                                                    |
|-------------------------------------|-------------------------------------------------------------|
| Invalid / expired JWT               | `401 Unauthorized` — returned by `Auth Middleware`         |
| Viewer role attempts order creation | `403 Forbidden` — RBAC gate in `Auth Middleware`           |
| Product not found during order      | `404 Not Found` — `OrderService` transaction rolled back   |
| Insufficient stock for line item    | `422 Unprocessable Entity` — stock guard in `OrderService` |
| Duplicate order submission          | `409 Conflict` — idempotency key check at API layer        |
| Invoice amount > ₹500,000          | Invoice created with `compliance_hold: true`; payment blocked until approved |
| DB transaction failure              | `500 Internal Server Error` — ROLLBACK; no partial data    |

---

## Appendix — UML Notation Reference

| Symbol / Notation    | Meaning                                                     |
|----------------------|-------------------------------------------------------------|
| `<<include>>`        | Sub-use-case always executes as part of the base case       |
| `<<extend>>`         | Sub-use-case executes only when a condition is met          |
| `*--`                | Composition — child cannot exist without parent             |
| `-->` (class)        | Association — one class references another                  |
| `..>`                | Dependency — uses relationship (weaker coupling)            |
| `<|--`               | Inheritance — subclass extends base class                   |
| `alt` (sequence)     | Conditional branch (if / else)                              |
| `rect` (sequence)    | Grouping box for a logical phase                            |
| `->>` / `-->>`       | Synchronous call / return message in sequence               |
| `autonumber`         | Auto-numbered steps in sequence diagram                     |
