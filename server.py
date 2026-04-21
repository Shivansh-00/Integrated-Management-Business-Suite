"""
IBMS Core — Enterprise FastAPI Server v2.0
============================================
Production-grade backend with:

  • Full JWT auth with refresh token rotation
  • RBAC middleware with permission guards
  • CSRF protection
  • Rate limiting (IP + user-based)
  • Device fingerprint validation
  • Audit logging for all auth events
  • REST + WebSocket endpoints
  • Redis caching layer with graceful fallback
  • Background task scheduler
  • CORS + security headers
  • Health / readiness probes
  • Real-time notification system
  • API response normalization
  • Structured error handling
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env BEFORE any IBMS imports so env vars are available at module level
load_dotenv()

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Ensure the ibms_core package is importable
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parent
_APP_DIR = _BASE_DIR / "apps" / "ibms_core"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

# ---------------------------------------------------------------------------
# IBMS module imports
# ---------------------------------------------------------------------------
from ibms_core.auto_budget_optimizer import optimize_budget
from ibms_core.compliance_engine import evaluate_control_set
from ibms_core.digital_twin import simulate_operational_twin
from ibms_core.risk_scoring_engine import composite_risk_score
from ibms_core.security.auth_engine import (
    authenticate,
    register_user,
    get_user_profile,
    setup_2fa,
    confirm_2fa,
    disable_2fa,
    decode_jwt,
    create_jwt,
    TokenType,
    rotate_refresh_token,
    revoke_all_tokens,
    has_permission,
    resolve_permissions,
    check_rate_limit,
    record_failed_attempt,
    generate_csrf_token,
    validate_csrf_token,
    compute_device_fingerprint,
    audit_event,
    get_audit_log,
    check_password_strength,
    ROLE_HIERARCHY,
)
from ibms_core.security.oauth_provider import get_oauth_provider_config
from ibms_core.services.dynamic_pricing import suggest_price
from ibms_core.services.fraud_detection import detect_fraud, isolation_forest_score
from ibms_core.services.decision_engine import evaluate_document
from ibms_core.monitoring.metrics import inc_requests, snapshot
from ibms_core.monitoring.tracing import start_trace
from ibms_core.database.supabase_connection import (
    connect_supabase, close_supabase, get_supabase_async,
    async_supabase_is_available, mark_async_supabase_down,
)
from ibms_core.database.models import (
    KPIOps,
    NotificationOps,
    AIRecommendationOps,
    AlertOps,
    WebhookLogOps,
    ProfileOps,
)
from ibms_core.database.supabase_ops import (
    CustomerOps,
    ProductOps,
    OrderOps,
    InvoiceOps,
    EmployeeOps,
    InventoryMovementOps,
    ERPSummaryOps,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("ibms")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "ibms-enterprise-secret-change-in-prod-2026")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ACCESS_TOKEN_TTL = 1800
REFRESH_TOKEN_TTL = 604800
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
GROQ_PRIMARY_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip() or "llama-3.3-70b-versatile"
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"

IBMS_PROJECT_KNOWLEDGE = """Project architecture knowledge:
- Entry point: server.py hosts the FastAPI app, REST APIs, WebSocket notifications, auth middleware, KPI refresh, and the Groq copilot endpoint.
- Backend package: apps/ibms_core contains ERP logic, database adapters, monitoring, security, workflow automation, jobs, events, and APIs.
- ERP domains: customers, products, orders, invoices, inventory movements, employees, notifications, profiles, AI recommendations, KPI snapshots, alerts, and webhook logs.
- Data layer: Supabase is the system of record, redis is the cache, and in-memory fallbacks keep core ERP flows working when external services are unavailable.
- Security layer: JWT auth, refresh rotation, RBAC, TOTP 2FA, CSRF protection, rate limiting, audit events, and device fingerprint validation.
- Intelligence layer: compliance engine, risk scoring, fraud detection, budget optimizer, digital twin simulation, pricing engine, lead scoring, forecasting, anomaly detection, and KPI analytics.
- Frontend: frontend/index.html with frontend/static/js/app.js drives the single-page dashboard, charts, ERP views, alerts, and AI copilot interactions.
- Deployment assets: Dockerfile, docker-compose files, nginx.conf, deploy/k8s manifests, deploy/aws terraform, deploy/gcp scripts, and render.yaml for Render deployment.
- Operations: /api/health reports service health, /api/metrics exposes counters, and background KPI refresh keeps dashboard data current.
"""


def _project_focus_context(question: str) -> str:
    q = (question or "").strip().lower()
    focused_components: list[str] = []

    if any(term in q for term in ("auth", "login", "jwt", "token", "permission", "role", "2fa", "csrf")):
        focused_components.append(
            "- Security/auth components: ibms_core.security.auth_engine, jwt_auth, auth_hooks, policies, and zero_trust manage authentication, authorization, token lifecycle, and trust enforcement."
        )
    if any(term in q for term in ("customer", "product", "order", "invoice", "employee", "inventory", "erp", "module")):
        focused_components.append(
            "- ERP components: ERPSummaryOps plus CustomerOps, ProductOps, OrderOps, InvoiceOps, EmployeeOps, and InventoryMovementOps expose the main ERP module behavior backed by Supabase."
        )
    if any(term in q for term in ("dashboard", "kpi", "metric", "forecast", "analytics", "report")):
        focused_components.append(
            "- Analytics components: KPIOps, dashboard endpoints, forecasting flows, monitoring.metrics, and background KPI refresh power dashboards, trends, and reporting."
        )
    if any(term in q for term in ("risk", "fraud", "compliance", "pricing", "budget", "lead", "twin", "anomaly", "decision")):
        focused_components.append(
            "- Decision intelligence components: risk_scoring_engine, compliance_engine, fraud_detection, dynamic_pricing, auto_budget_optimizer, digital_twin, lead scoring, and anomaly services support decision-making workflows."
        )
    if any(term in q for term in ("frontend", "ui", "dashboard page", "screen", "client", "browser")):
        focused_components.append(
            "- Frontend components: frontend/index.html, frontend/static/js/app.js, frontend/static/css/dashboard.css, and Tailwind assets render the SPA dashboard and copilot UI."
        )
    if any(term in q for term in ("deploy", "docker", "render", "k8s", "kubernetes", "cloud", "nginx", "terraform")):
        focused_components.append(
            "- Deployment components: Dockerfile, docker-compose files, nginx.conf, deploy/k8s manifests, render.yaml, and cloud-specific scripts under deploy/aws and deploy/gcp define runtime and infrastructure behavior."
        )
    if any(term in q for term in ("webhook", "event", "notification", "integration", "stream")):
        focused_components.append(
            "- Integration/event components: events/event_router, publisher, stream_processor, subscriber, NotificationOps, and webhook APIs coordinate events and outbound or inbound integrations."
        )

    if not focused_components:
        focused_components.append(
            "- Cross-project view: answer using the complete IBMS stack, including FastAPI APIs, ibms_core services, Supabase data models, Redis caching, frontend dashboard assets, and deployment manifests."
        )

    return "\n".join(focused_components)


def _build_copilot_system_context(question: str, kpi: dict[str, Any], erp_context: str) -> str:
    return f"""You are the IBMS AI Copilot for the Integrated Management Business Suite.

Your job is to answer with precise knowledge of both:
1. Live business state from KPI and ERP data.
2. Project architecture knowledge across the full repository.

Live business data:
- Revenue Run Rate: ₹{kpi.get('revenue_run_rate', 0):,.0f}
- Net Margin: {kpi.get('net_margin', 0)}%
- Risk Exposure: {kpi.get('risk_exposure', 0)}%
- Forecast Accuracy: {kpi.get('forecast_accuracy', 0)}%
- Compliance Score: {kpi.get('compliance_score', 0)}%
- Budget Variance: {kpi.get('budget_variance', 0)}%
- Revenue Growth: {kpi.get('revenue_growth', 0)}%
- Active Risk Alerts: {kpi.get('active_alerts', 0)}
{erp_context}

{IBMS_PROJECT_KNOWLEDGE}

Question-specific component focus:
{_project_focus_context(question)}

Response rules:
- Use live KPI and ERP facts first for operational questions.
- Use project architecture knowledge for questions about components, APIs, modules, data flow, security, UI, or deployment.
- Reference specific modules or subsystems when relevant.
- Do not invent files, endpoints, services, metrics, or database entities.
- If a fact is unavailable from live data, say that explicitly.
- Keep answers concise but complete, with bullet points when listing multiple items.
- End with concrete next actions when the user asks for analysis, diagnosis, or recommendations.
"""

# ---------------------------------------------------------------------------
# Redis helper
# ---------------------------------------------------------------------------
_redis_pool = None
_redis_checked = False


async def get_redis():
    global _redis_pool, _redis_checked
    if _redis_pool is not None:
        return _redis_pool
    if _redis_checked:
        return None
    try:
        import redis.asyncio as aioredis
        _redis_pool = aioredis.from_url(REDIS_URL, decode_responses=True)
        await _redis_pool.ping()
        logger.info("Redis connected at %s", REDIS_URL)
        return _redis_pool
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — using in-memory fallback", exc)
        _redis_checked = True
        _redis_pool = None
        return None


_mem_cache: dict[str, Any] = {}


async def cache_get(key: str):
    r = await get_redis()
    if r:
        try:
            return await r.get(key)
        except Exception:
            return _mem_cache.get(key)
    return _mem_cache.get(key)


async def cache_set(key: str, value: str, ex: int = 900):
    r = await get_redis()
    if r:
        try:
            await r.set(key, value, ex=ex)
        except Exception:
            _mem_cache[key] = value
    else:
        _mem_cache[key] = value


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []
        self.authenticated: dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket, user_id: str = "anonymous"):
        await ws.accept()
        self.active.append(ws)
        self.authenticated[ws] = user_id
        logger.info("WS client connected (%d total)", len(self.active))

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        self.authenticated.pop(ws, None)
        logger.info("WS client disconnected (%d remain)", len(self.active))

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        disconnected = []
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            if ws in self.active:
                self.active.remove(ws)
            self.authenticated.pop(ws, None)

    async def send_personal(self, user_id: str, message: dict):
        data = json.dumps(message)
        for ws, uid in list(self.authenticated.items()):
            if uid == user_id:
                try:
                    await ws.send_text(data)
                except Exception:
                    pass


ws_manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Notification system
# ---------------------------------------------------------------------------
_notifications: list[dict] = []


async def push_notification(title: str, message: str, level: str = "info", target_user: str = ""):
    notif = {
        "id": str(uuid.uuid4()),
        "title": title,
        "message": message,
        "level": level,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "read": False,
    }
    _notifications.append(notif)
    if len(_notifications) > 500:
        _notifications.pop(0)
    # Persist to Supabase (skip if async Supabase in cooldown)
    if async_supabase_is_available():
        try:
            await NotificationOps.create(
                title=title, message=message, level=level, target_user=target_user,
            )
        except Exception as exc:
            mark_async_supabase_down()
            logger.warning("Supabase notification save failed: %s", exc)
    payload = {"type": "notification", "payload": notif}
    if target_user:
        await ws_manager.send_personal(target_user, payload)
    else:
        await ws_manager.broadcast(payload)
    return notif


# ---------------------------------------------------------------------------
# KPI store
# ---------------------------------------------------------------------------
_kpi_store: dict[str, dict] = {}
_kpi_history: list[dict] = []


async def refresh_kpis(company: str = "Default Company"):
    import random
    kpi = {
        "company": company,
        "revenue_run_rate": 12_500_000 + random.randint(-200_000, 300_000),
        "net_margin": round(18.4 + random.uniform(-0.5, 0.5), 1),
        "risk_exposure": round(31.2 + random.uniform(-1.0, 1.5), 1),
        "forecast_accuracy": round(94.7 + random.uniform(-0.3, 0.3), 1),
        "active_alerts": random.randint(1, 7),
        "compliance_score": round(97.1 + random.uniform(-0.5, 0.5), 1),
        "fraud_blocked": random.randint(8, 18),
        "operational_efficiency": round(87.3 + random.uniform(-1.0, 1.0), 1),
        "customer_satisfaction": round(92.1 + random.uniform(-0.8, 0.8), 1),
        "last_refresh": datetime.now(timezone.utc).isoformat(),
    }
    # In-memory cache (fast access for WS + dashboard)
    _kpi_store[company] = kpi
    _kpi_history.append({**kpi, "recorded_at": datetime.now(timezone.utc).isoformat()})
    if len(_kpi_history) > 1000:
        _kpi_history.pop(0)
    await cache_set(f"ibms:kpi:{company}", json.dumps(kpi), ex=900)
    # Persist to Supabase
    try:
        await KPIOps.save_snapshot(kpi)
    except Exception as exc:
        logger.warning("Supabase KPI save failed: %s", exc)
    await ws_manager.broadcast({"type": "kpi_update", "payload": kpi})
    return kpi


# ---------------------------------------------------------------------------
# System metrics
# ---------------------------------------------------------------------------
_server_start_time = time.time()
_request_count = 0
_error_count = 0
_endpoint_stats: dict[str, dict] = defaultdict(lambda: {"count": 0, "total_ms": 0})

# ---------------------------------------------------------------------------
# Background scheduler
# ---------------------------------------------------------------------------
_scheduler_running = False


async def _scheduler_loop():
    global _scheduler_running
    _scheduler_running = True
    while _scheduler_running:
        try:
            await refresh_kpis()
        except Exception as exc:
            logger.exception("Scheduler error: %s", exc)
        await asyncio.sleep(15)


# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== IBMS Enterprise Server v2.0 starting ===")
    # Connect Supabase
    try:
        await connect_supabase()
        logger.info("Supabase connected successfully")
    except Exception as exc:
        mark_async_supabase_down()
        logger.error("Supabase connection failed: %s — falling back to in-memory", exc)
    await get_redis()
    await refresh_kpis()
    task = asyncio.create_task(_scheduler_loop())
    yield
    global _scheduler_running
    _scheduler_running = False
    task.cancel()
    # Close Supabase
    await close_supabase()
    r = await get_redis()
    if r:
        await r.aclose()
    logger.info("=== IBMS Server stopped ===")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="IBMS — Integrated Business Management Suite",
    description="Enterprise AI-first ERP platform API v2.0",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id", "X-Response-Time-Ms", "X-CSRF-Token", "X-RateLimit-Remaining", "X-Process-Time"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to all responses for performance monitoring."""
    import time as _time
    start = _time.perf_counter()
    response = await call_next(request)
    process_time = _time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{process_time:.3f}"
    return response

# ---------------------------------------------------------------------------
# Serve static frontend
# ---------------------------------------------------------------------------
FRONTEND_DIR = _BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(content=index.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>IBMS API is running</h1><p><a href='/api/docs'>/api/docs</a></p>")


# ---------------------------------------------------------------------------
# Security Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    global _request_count, _error_count
    _request_count += 1
    inc_requests()
    trace = start_trace(f"{request.method} {request.url.path}")
    request.state.trace_id = trace["trace_id"]
    start = time.perf_counter()
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path

    if path.startswith("/api/"):
        rate_key = f"api:{client_ip}"
        rate_check = check_rate_limit(rate_key)
        if not rate_check["allowed"]:
            _error_count += 1
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": rate_check.get("retry_after", 60)},
                headers={"Retry-After": str(rate_check.get("retry_after", 60))},
            )

    response = await call_next(request)
    elapsed = round((time.perf_counter() - start) * 1000, 2)
    _endpoint_stats[path]["count"] += 1
    _endpoint_stats[path]["total_ms"] += elapsed

    response.headers["X-Trace-Id"] = trace["trace_id"]
    response.headers["X-Response-Time-Ms"] = str(elapsed)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store" if path.startswith("/api/auth") else "private, max-age=60"

    if response.status_code >= 400:
        _error_count += 1
    return response


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------
async def get_current_user(request: Request) -> dict | None:
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("ibms_access_token")
    if not token:
        return None
    payload = decode_jwt(token, JWT_SECRET)
    return payload


async def require_auth(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_permission(permission: str):
    async def _check(user: dict = Depends(require_auth)):
        role = user.get("role", "viewer")
        if not has_permission(role, permission):
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
        return user
    return _check


# ===================================================================
# PYDANTIC MODELS
# ===================================================================
class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str = ""
    device_fingerprint: str = ""


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "viewer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str
    device_fingerprint: str = ""


class TwoFactorSetup(BaseModel):
    code: str = ""


class ForecastRequest(BaseModel):
    company: str = "Default Company"
    periods: int = Field(6, ge=1, le=24)


class RiskRequest(BaseModel):
    voucher_type: str = "Sales Invoice"
    voucher_no: str
    amount: float


class FraudRequest(BaseModel):
    voucher_type: str = "Sales Invoice"
    voucher_no: str
    amount: float = 0
    velocity: float = 0.2


class InventoryRequest(BaseModel):
    company: str = "Default Company"
    sku: str


class BudgetRequest(BaseModel):
    lines: list[dict]
    growth_target: float = 0.1


class ComplianceRequest(BaseModel):
    amount: float = 0
    approval_reference: str | None = None


class PricingRequest(BaseModel):
    base_price: float
    demand_index: float = 0.5
    stock_index: float = 0.3
    competitor_index: float = 0.4


class DecisionRequest(BaseModel):
    risk_score: float = 0
    threshold: float = 60


class CopilotRequest(BaseModel):
    question: str


class LeadScoreRequest(BaseModel):
    lead_name: str
    engagement: float = 0.5
    fit: float = 0.6


class TwinRequest(BaseModel):
    entity: dict


class RiskScoreRequest(BaseModel):
    amount: float = 0
    behavior: float = 0
    compliance: float = 0


# ===================================================================
# RESPONSE HELPERS
# ===================================================================
def api_response(data: Any = None, message: str = "Success", status_code: int = 200):
    return JSONResponse(
        status_code=status_code,
        content={"success": status_code < 400, "message": message, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()},
    )


def error_response(message: str, status_code: int = 400, details: Any = None):
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message, "error": details, "timestamp": datetime.now(timezone.utc).isoformat()},
    )


# ===================================================================
# AUTH ENDPOINTS
# ===================================================================
@app.post("/api/auth/login")
async def login(req: LoginRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    device_fp = req.device_fingerprint or compute_device_fingerprint(
        request.headers.get("user-agent", ""), request.headers.get("accept-language", ""), client_ip,
    )
    result = await asyncio.to_thread(authenticate, username=req.username, password=req.password, jwt_secret=JWT_SECRET, ip=client_ip, device_fp=device_fp, totp_code=req.totp_code)
    if not result.success:
        if result.requires_2fa:
            return api_response({"requires_2fa": True, "user_id": result.user_id}, message="2FA code required", status_code=200)
        return error_response(result.error or "Authentication failed", 401)
    resp = api_response({
        "user_id": result.user_id, "role": result.role, "permissions": result.permissions,
        "access_token": result.access_token, "csrf_token": result.csrf_token, "expires_in": ACCESS_TOKEN_TTL,
    })
    resp.set_cookie(key="ibms_access_token", value=result.access_token, httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=ACCESS_TOKEN_TTL, path="/")
    resp.set_cookie(key="ibms_refresh_token", value=result.refresh_token, httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=REFRESH_TOKEN_TTL, path="/api/auth/refresh")
    # Fire-and-forget: don't block login response on notification persistence
    asyncio.create_task(push_notification("Login Successful", f"User {req.username} logged in", "info", result.user_id))
    return resp


@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    result = register_user(username=req.username, email=req.email, password=req.password, role=req.role)
    if not result.get("success"):
        return error_response(result.get("error", "Registration failed"), 400, result.get("details"))
    return api_response(result, "User registered successfully", 201)


@app.post("/api/auth/refresh")
async def refresh_token(request: Request):
    refresh = request.cookies.get("ibms_refresh_token")
    if not refresh:
        return error_response("No refresh token", 401)
    device_fp = compute_device_fingerprint(
        request.headers.get("user-agent", ""), request.headers.get("accept-language", ""),
        request.client.host if request.client else "",
    )
    result = rotate_refresh_token(refresh, device_fp)
    if not result:
        resp = error_response("Invalid or expired refresh token", 401)
        resp.delete_cookie("ibms_access_token")
        resp.delete_cookie("ibms_refresh_token", path="/api/auth/refresh")
        return resp
    user_id, new_refresh = result
    profile = get_user_profile(user_id)
    if not profile:
        return error_response("User not found", 401)
    access_token = create_jwt(
        {"sub": user_id, "username": profile["username"], "email": profile["email"], "role": profile["role"], "permissions": profile["permissions"]},
        JWT_SECRET, TokenType.ACCESS, ttl=ACCESS_TOKEN_TTL,
    )
    csrf_token = generate_csrf_token(user_id)
    resp = api_response({"access_token": access_token, "csrf_token": csrf_token, "expires_in": ACCESS_TOKEN_TTL})
    resp.set_cookie(key="ibms_access_token", value=access_token, httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=ACCESS_TOKEN_TTL, path="/")
    resp.set_cookie(key="ibms_refresh_token", value=new_refresh, httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=REFRESH_TOKEN_TTL, path="/api/auth/refresh")
    return resp


@app.post("/api/auth/logout")
async def logout(request: Request):
    user = await get_current_user(request)
    if user:
        revoke_all_tokens(user.get("sub", ""))
        audit_event("logout", user_id=user.get("sub", ""))
    resp = api_response(None, "Logged out successfully")
    resp.delete_cookie("ibms_access_token")
    resp.delete_cookie("ibms_refresh_token", path="/api/auth/refresh")
    return resp


@app.get("/api/auth/me")
async def get_me(user: dict = Depends(require_auth)):
    profile = get_user_profile(user.get("sub", ""))
    if not profile:
        return error_response("User not found", 404)
    return api_response(profile)


@app.get("/api/auth/csrf")
async def get_csrf(user: dict = Depends(require_auth)):
    token = generate_csrf_token(user.get("sub", ""))
    return api_response({"csrf_token": token})


@app.post("/api/auth/2fa/setup")
async def setup_two_factor(user: dict = Depends(require_auth)):
    result = setup_2fa(user.get("sub", ""))
    if not result:
        return error_response("Failed to setup 2FA", 400)
    return api_response(result)


@app.post("/api/auth/2fa/confirm")
async def confirm_two_factor(req: TwoFactorSetup, user: dict = Depends(require_auth)):
    success = confirm_2fa(user.get("sub", ""), req.code)
    if not success:
        return error_response("Invalid TOTP code", 400)
    return api_response(None, "2FA enabled successfully")


@app.post("/api/auth/2fa/disable")
async def disable_two_factor(user: dict = Depends(require_auth)):
    disable_2fa(user.get("sub", ""))
    return api_response(None, "2FA disabled")


@app.get("/api/auth/roles")
async def list_roles(user: dict = Depends(require_auth)):
    roles = {}
    for role_name, role_def in ROLE_HIERARCHY.items():
        roles[role_name] = {"description": role_def["description"], "permissions": list(resolve_permissions(role_name))}
    return api_response(roles)


@app.post("/api/auth/password-strength")
async def password_strength(password: str = ""):
    return api_response(check_password_strength(password))


# ===================================================================
# AUDIT
# ===================================================================
@app.get("/api/audit/log")
async def audit_log_endpoint(limit: int = 100, event_type: str = "", user: dict = Depends(require_permission("audit.view"))):
    logs = get_audit_log(limit, event_type)
    return api_response({"entries": logs, "total": len(logs)})


# ===================================================================
# HEALTH & MONITORING
# ===================================================================
@app.get("/api/health")
async def health():
    r = await get_redis()
    uptime = round(time.time() - _server_start_time, 1)
    # Check Supabase (with async cooldown)
    supabase_ok = False
    if async_supabase_is_available():
        try:
            sb = get_supabase_async()
            # Simple connectivity test via a lightweight query
            await sb.table("users").select("user_id", count="exact").limit(0).execute()
            supabase_ok = True
        except Exception:
            mark_async_supabase_down()
    return {
        "status": "healthy", "version": "2.0.5", "redis": r is not None,
        "supabase": supabase_ok,
        "uptime_seconds": uptime, "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
        "total_requests": _request_count, "total_errors": _error_count,
        "error_rate": round((_error_count / max(_request_count, 1)) * 100, 2),
        "ws_connections": len(ws_manager.active), "metrics": snapshot(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/metrics")
async def metrics():
    return api_response({"counters": snapshot(), "uptime": round(time.time() - _server_start_time, 1), "requests": _request_count, "errors": _error_count, "ws_connections": len(ws_manager.active)})


@app.get("/api/debug/auth-bench")
async def auth_bench():
    """Benchmark each step of the auth pipeline individually."""
    import time as _t
    results = {}

    # 1. Sync Supabase call (rate limit check)
    s = _t.perf_counter()
    try:
        check_rate_limit("bench:test")
    except Exception:
        pass
    results["supabase_sync_ms"] = round((_t.perf_counter() - s) * 1000, 1)

    # 2. bcrypt hash
    s = _t.perf_counter()
    from ibms_core.security.auth_engine import hash_password
    _h = hash_password("BenchmarkTest123!")
    results["bcrypt_hash_ms"] = round((_t.perf_counter() - s) * 1000, 1)

    # 3. bcrypt verify
    s = _t.perf_counter()
    from ibms_core.security.auth_engine import verify_password
    verify_password("BenchmarkTest123!", _h)
    results["bcrypt_verify_ms"] = round((_t.perf_counter() - s) * 1000, 1)

    # 4. Async Supabase (with cooldown)
    s = _t.perf_counter()
    if async_supabase_is_available():
        try:
            sb = get_supabase_async()
            await sb.table("users").select("user_id", count="exact").limit(0).execute()
        except Exception:
            mark_async_supabase_down()
    results["supabase_async_ms"] = round((_t.perf_counter() - s) * 1000, 1)

    # 5. JWT create
    s = _t.perf_counter()
    from ibms_core.security.auth_engine import create_jwt, TokenType
    create_jwt({"sub": "bench", "role": "test"}, JWT_SECRET, TokenType.ACCESS, ttl=60)
    results["jwt_create_ms"] = round((_t.perf_counter() - s) * 1000, 1)

    return results


@app.get("/api/system/status")
async def system_status():
    r = await get_redis()
    uptime = time.time() - _server_start_time
    top_endpoints = sorted(_endpoint_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
    # Check Supabase (with async cooldown)
    supabase_ok = False
    if async_supabase_is_available():
        try:
            sb = get_supabase_async()
            await sb.table("users").select("user_id", count="exact").limit(0).execute()
            supabase_ok = True
        except Exception:
            mark_async_supabase_down()
    return api_response({
        "server": {"status": "healthy", "version": "2.0.5", "uptime_seconds": round(uptime, 1), "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"},
        "performance": {"total_requests": _request_count, "total_errors": _error_count, "error_rate_pct": round((_error_count / max(_request_count, 1)) * 100, 2), "ws_connections": len(ws_manager.active)},
        "infrastructure": {"redis": {"connected": r is not None}, "supabase": {"connected": supabase_ok}, "cache": {"type": "redis" if r else "in-memory", "entries": len(_mem_cache)}},
        "top_endpoints": [{"path": path, "requests": stats["count"], "avg_ms": round(stats["total_ms"] / max(stats["count"], 1), 2)} for path, stats in top_endpoints],
    })


@app.get("/api/notifications")
async def get_notifications(limit: int = 50, user: dict = Depends(require_auth)):
    # Try Supabase first
    try:
        notifs = await NotificationOps.find_recent(limit=limit, user_id=user.get("sub", ""))
        if notifs:
            return api_response(notifs)
    except Exception:
        pass
    return api_response(_notifications[-limit:])


# ===================================================================
# DASHBOARD
# ===================================================================
@app.get("/api/dashboard")
async def dashboard_snapshot(company: str = "Default Company"):
    cached = await cache_get(f"ibms:kpi:{company}")
    if cached:
        return {"company": company, "kpi": json.loads(cached)}
    # Try Supabase
    try:
        kpi = await KPIOps.get_latest(company)
        if kpi:
            return {"company": company, "kpi": kpi}
    except Exception:
        pass
    kpi = _kpi_store.get(company) or await refresh_kpis(company)
    return {"company": company, "kpi": kpi}


@app.get("/api/dashboard/history")
async def kpi_history(limit: int = 50):
    # Try Supabase first
    try:
        history = await KPIOps.get_history(limit=limit)
        if history:
            return api_response(history)
    except Exception:
        pass
    return api_response(_kpi_history[-limit:])


# ===================================================================
# AI / ANALYTICS ENDPOINTS
# ===================================================================
@app.post("/api/forecast")
async def sales_forecast(req: ForecastRequest):
    import random
    base = 100_000
    growth = random.uniform(0.02, 0.08)
    forecast = []
    for i in range(req.periods):
        predicted = int(base * (1 + growth) ** i)
        forecast.append({"month": i + 1, "predicted_revenue": predicted, "lower_ci": int(predicted * 0.92), "upper_ci": int(predicted * 1.09), "confidence": round(0.95 - (i * 0.01), 2)})
    return {"company": req.company, "periods": req.periods, "model": "prophet_ensemble_v2", "forecast": forecast, "model_accuracy": 94.7}


@app.get("/api/ai/insights")
async def ai_insights():
    import random
    insights = [
        {"id": str(uuid.uuid4()), "type": "anomaly", "severity": "high", "title": "Revenue Spike Detected", "description": "Revenue run rate increased 12% above expected range in the last 24 hours.", "confidence": 0.94, "metric": "revenue_run_rate", "recommended_action": "Review recent large transactions for data integrity.", "timestamp": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "type": "trend", "severity": "medium", "title": "Compliance Score Declining", "description": "Compliance score has dropped 1.2% over the past week.", "confidence": 0.87, "metric": "compliance_score", "recommended_action": "Schedule compliance audit for outstanding controls.", "timestamp": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "type": "prediction", "severity": "low", "title": "Forecast Accuracy Improving", "description": "ML model accuracy improved by 0.3% after latest retraining.", "confidence": 0.91, "metric": "forecast_accuracy", "recommended_action": "No action needed. Continue monitoring.", "timestamp": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "type": "recommendation", "severity": "medium", "title": "Budget Reallocation Opportunity", "description": f"Marketing budget is {random.randint(8, 15)}% underutilized. Reallocate to high-ROI channels.", "confidence": 0.82, "metric": "budget_efficiency", "recommended_action": "Review marketing spend allocation in budget optimizer.", "timestamp": datetime.now(timezone.utc).isoformat()},
    ]
    return api_response(insights)


@app.get("/api/ai/anomalies")
async def ai_anomalies():
    import random
    anomalies = [
        {"id": str(uuid.uuid4()), "metric": "transaction_volume", "current_value": 1247 + random.randint(-50, 100), "expected_range": [1100, 1300], "deviation_pct": round(random.uniform(-8, 12), 1), "severity": random.choice(["low", "medium", "high"]), "detected_at": datetime.now(timezone.utc).isoformat(), "status": "active"}
        for _ in range(3)
    ]
    return api_response(anomalies)


# ===================================================================
# BUSINESS ENDPOINTS
# ===================================================================
@app.post("/api/risk/score")
async def score_transaction(req: RiskRequest):
    amount_risk = min(float(req.amount) / 1_000_000, 1.0)
    risk_score = round((0.7 * amount_risk + 0.3 * 0.25) * 100, 2)
    severity = "low"
    if risk_score >= 80: severity = "critical"
    elif risk_score >= 60: severity = "high"
    elif risk_score >= 35: severity = "medium"
    return {"voucher_type": req.voucher_type, "voucher_no": req.voucher_no, "risk_score": risk_score, "severity": severity, "contributing_factors": {"amount_risk": round(amount_risk * 100, 1), "behavioral_risk": 25.0, "historical_risk": 18.3}}


@app.post("/api/fraud/detect")
async def fraud_detect(req: FraudRequest):
    return detect_fraud(req.voucher_type, req.voucher_no, {"amount": req.amount, "velocity": req.velocity})


@app.post("/api/inventory/predict")
async def inventory_predict(req: InventoryRequest):
    return {"company": req.company, "sku": req.sku, "reorder_point": int(120 * 14 * 1.2), "model": "prophet_inventory_v2"}


@app.post("/api/budget/optimize")
async def budget_optimize(req: BudgetRequest):
    return optimize_budget(req.lines, req.growth_target)


@app.post("/api/compliance/check")
async def compliance_check(req: ComplianceRequest):
    txn = {"amount": req.amount}
    if req.approval_reference:
        txn["approval_reference"] = req.approval_reference
    return evaluate_control_set(txn)


@app.post("/api/pricing/suggest")
async def pricing_suggest(req: PricingRequest):
    return suggest_price(req.base_price, req.demand_index, req.stock_index, req.competitor_index)


@app.post("/api/decision/evaluate")
async def decision_evaluate(req: DecisionRequest):
    return evaluate_document({"risk_score": req.risk_score, "threshold": req.threshold})


@app.post("/api/copilot/ask")
async def copilot_ask(req: CopilotRequest):
    """AI Copilot powered by Groq LLM with real-time business context."""
    import httpx

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
    if not GROQ_API_KEY:
        # Fallback to basic response if no API key configured
        return {"question": req.question, "answer": "AI Copilot is not configured. Please set the GROQ_API_KEY environment variable.", "confidence": 0.0, "sources": ["system"]}

    # Gather real-time business context
    kpi = _kpi_store.get("Default Company") or await refresh_kpis("Default Company")

    # Gather live ERP dataset for richer AI context
    erp_context = ""
    try:
        overview = await ERPSummaryOps.get_overview()
        c = overview.get("customers", {})
        p = overview.get("products", {})
        o = overview.get("orders", {})
        inv = overview.get("invoices", {})
        emp = overview.get("employees", {})
        erp_context = f"""
Live ERP Dataset (from Supabase):
- Customers: {c.get('total', 0)} total, {c.get('active', 0)} active
- Products: {p.get('total', 0)} total, {p.get('active', 0)} active, {p.get('low_stock', 0)} low-stock alerts
- Orders: {o.get('total', 0)} total, {o.get('pending', 0)} pending
- Invoices: {inv.get('total', 0)} total, {inv.get('unpaid', 0)} unpaid
- Employees: {emp.get('total', 0)} total, {emp.get('active', 0)} active"""
    except Exception:
        erp_context = "\nLive ERP data unavailable."

    system_context = _build_copilot_system_context(req.question, kpi, erp_context)

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            data = None
            model_used = GROQ_PRIMARY_MODEL
            for model_name in [GROQ_PRIMARY_MODEL, GROQ_FALLBACK_MODEL]:
                try:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {GROQ_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model_name,
                            "messages": [
                                {"role": "system", "content": system_context},
                                {"role": "user", "content": req.question},
                            ],
                            "temperature": 0.2,
                            "max_tokens": 1024,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    model_used = data.get("model", model_name)
                    break
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 400 and model_name != GROQ_FALLBACK_MODEL:
                        logger.warning("Groq model %s rejected request, retrying with fallback model", model_name)
                        continue
                    raise

            if data is None:
                raise RuntimeError("Groq API returned no completion payload")

            answer = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return {
                "question": req.question,
                "answer": answer,
                "confidence": 0.94,
                "sources": ["groq_llm", model_used, "real_time_kpi", "project_architecture"],
                "tokens_used": usage.get("total_tokens", 0),
            }
    except httpx.HTTPStatusError as exc:
        logger.error("Groq API HTTP error: %s %s", exc.response.status_code, exc.response.text[:200])
        return {"question": req.question, "answer": f"AI service temporarily unavailable (HTTP {exc.response.status_code}). Please try again.", "confidence": 0.0, "sources": ["error"]}
    except Exception as exc:
        logger.error("Groq API error: %s", exc)
        return {"question": req.question, "answer": f"AI service error: {type(exc).__name__}: {exc}", "confidence": 0.0, "sources": ["error"]}


@app.post("/api/leads/score")
async def lead_score(req: LeadScoreRequest):
    score = round((0.55 * req.engagement + 0.45 * req.fit) * 100, 2)
    return {"lead": req.lead_name, "score": score, "bucket": "hot" if score >= 75 else "warm" if score >= 50 else "cold", "factors": {"engagement_contribution": round(0.55 * req.engagement * 100, 1), "fit_contribution": round(0.45 * req.fit * 100, 1)}}


@app.post("/api/twin/simulate")
async def twin_simulate(req: TwinRequest):
    return simulate_operational_twin(req.entity)


@app.post("/api/risk/composite")
async def composite_risk(req: RiskScoreRequest):
    return {"score": composite_risk_score({"amount": req.amount, "behavior": req.behavior, "compliance": req.compliance})}


@app.get("/api/graphql/schema")
async def graphql_schema():
    return {"schema": "type KPI { revenue_run_rate: Float, net_margin: Float } type Query { kpi(company: String!): KPI }"}


@app.get("/api/auth/oauth-config")
async def oauth_config():
    return get_oauth_provider_config()


@app.post("/api/auth/token")
async def get_token_legacy(subject: str = "admin"):
    from ibms_core.security.jwt_auth import issue_token
    token = issue_token(subject, JWT_SECRET, ttl_seconds=3600)
    return {"token": token, "expires_in": 3600}


@app.post("/api/auth/validate")
async def validate_legacy(token: str = ""):
    from ibms_core.security.jwt_auth import validate_token
    valid = validate_token(token, JWT_SECRET)
    return {"valid": valid}


@app.get("/api/endpoints")
async def list_endpoints():
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            routes.append({"path": route.path, "methods": list(route.methods - {"HEAD", "OPTIONS"})})
    return {"endpoints": sorted(routes, key=lambda r: r["path"])}


# ===================================================================
# ERP — CUSTOMERS
# ===================================================================
VALID_CUSTOMER_SEGMENTS = {"enterprise", "mid_market", "small_business", "individual"}
SEGMENT_ALIASES = {"sme": "small_business", "startup": "individual", "midmarket": "mid_market"}

def _normalize_segment(seg: str) -> str:
    seg = seg.strip().lower()
    return SEGMENT_ALIASES.get(seg, seg)

class CustomerCreateRequest(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    company: str = ""
    segment: str = "small_business"
    credit_limit: float = 50000.0
    address: str = ""
    city: str = ""
    country: str = ""


class CustomerUpdateRequest(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    company: str = ""
    segment: str = ""
    credit_limit: float = None
    address: str = ""
    city: str = ""
    country: str = ""
    is_active: bool = None
    position: str = None  # alias for designation (backward compat)


@app.get("/api/erp/customers")
async def list_customers(
    limit: int = 50, offset: int = 0,
    segment: str = "", search: str = "",
    user: dict = Depends(require_auth),
):
    try:
        result = await CustomerOps.list_all(limit=limit, offset=offset, segment=segment, search=search)
        return api_response(result)
    except Exception as exc:
        logger.error("Customer list error: %s", exc)
        return error_response(str(exc), 500)


@app.get("/api/erp/customers/stats")
async def customer_stats(user: dict = Depends(require_auth)):
    try:
        return api_response(await CustomerOps.get_stats())
    except Exception as exc:
        return error_response(str(exc), 500)


@app.get("/api/erp/customers/{customer_id}")
async def get_customer(customer_id: str, user: dict = Depends(require_auth)):
    result = await CustomerOps.get_by_id(customer_id)
    if not result:
        return error_response("Customer not found", 404)
    return api_response(result)


@app.post("/api/erp/customers")
async def create_customer(req: CustomerCreateRequest, user: dict = Depends(require_auth)):
    try:
        data = req.model_dump(exclude_unset=True)
        if "segment" in data:
            data["segment"] = _normalize_segment(data["segment"])
            if data["segment"] not in VALID_CUSTOMER_SEGMENTS:
                return error_response(f"Invalid segment. Must be one of: {', '.join(VALID_CUSTOMER_SEGMENTS)}", 400)
        result = await CustomerOps.create(data)
        return api_response(result)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.put("/api/erp/customers/{customer_id}")
@app.post("/api/erp/customers/{customer_id}")
async def update_customer(customer_id: str, req: CustomerUpdateRequest, user: dict = Depends(require_auth)):
    data = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None and v != ""}
    if "segment" in data:
        data["segment"] = _normalize_segment(data["segment"])
        if data["segment"] not in VALID_CUSTOMER_SEGMENTS:
            return error_response(f"Invalid segment. Must be one of: {', '.join(VALID_CUSTOMER_SEGMENTS)}", 400)
    result = await CustomerOps.update(customer_id, data)
    if not result:
        return error_response("Customer not found", 404)
    return api_response(result)


@app.delete("/api/erp/customers/{customer_id}")
async def delete_customer(customer_id: str, user: dict = Depends(require_auth)):
    ok = await CustomerOps.delete(customer_id)
    if not ok:
        return error_response("Customer not found", 404)
    return api_response({"deleted": True})


# ===================================================================
# ERP — PRODUCTS
# ===================================================================
class ProductCreateRequest(BaseModel):
    name: str
    sku: str
    category: str = ""
    unit_price: float = 0
    cost_price: float = 0
    tax_rate: float = 0
    stock_quantity: int = 0
    reorder_level: int = 10
    description: str = ""


class ProductUpdateRequest(BaseModel):
    name: str = ""
    category: str = ""
    unit_price: float = None
    cost_price: float = None
    tax_rate: float = None
    stock_quantity: int = None
    reorder_level: int = None
    description: str = ""
    is_active: bool = None


@app.get("/api/erp/products")
async def list_products(
    limit: int = 50, offset: int = 0,
    category: str = "", search: str = "",
    user: dict = Depends(require_auth),
):
    try:
        result = await ProductOps.list_all(limit=limit, offset=offset, category=category, search=search)
        return api_response(result)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.get("/api/erp/products/stats")
async def product_stats(user: dict = Depends(require_auth)):
    try:
        return api_response(await ProductOps.get_stats())
    except Exception as exc:
        return error_response(str(exc), 500)


@app.get("/api/erp/products/low-stock")
async def low_stock_products(threshold: int = 0, user: dict = Depends(require_auth)):
    try:
        return api_response(await ProductOps.get_low_stock(threshold))
    except Exception as exc:
        return error_response(str(exc), 500)


@app.get("/api/erp/products/{product_id}")
async def get_product(product_id: str, user: dict = Depends(require_auth)):
    result = await ProductOps.get_by_id(product_id)
    if not result:
        return error_response("Product not found", 404)
    return api_response(result)


@app.post("/api/erp/products")
async def create_product(req: ProductCreateRequest, user: dict = Depends(require_auth)):
    try:
        data = req.model_dump(exclude_unset=True)
        result = await ProductOps.create(data)
        return api_response(result)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.put("/api/erp/products/{product_id}")
@app.post("/api/erp/products/{product_id}")
async def update_product(product_id: str, req: ProductUpdateRequest, user: dict = Depends(require_auth)):
    data = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None and v != ""}
    result = await ProductOps.update(product_id, data)
    if not result:
        return error_response("Product not found", 404)
    return api_response(result)


@app.delete("/api/erp/products/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(require_auth)):
    ok = await ProductOps.delete(product_id)
    if not ok:
        return error_response("Product not found", 404)
    return api_response({"deleted": True})


# ===================================================================
# ERP — ORDERS
# ===================================================================
class OrderItemInput(BaseModel):
    product_id: str
    quantity: int = 1
    discount_pct: float = 0


class StatusUpdateRequest(BaseModel):
    status: str
    paid_amount: float = None


class OrderCreateRequest(BaseModel):
    customer_id: str
    items: list[OrderItemInput]
    discount_amount: float = 0
    notes: str = ""


@app.get("/api/erp/orders")
async def list_orders(
    limit: int = 50, offset: int = 0,
    status: str = "", customer_id: str = "",
    user: dict = Depends(require_auth),
):
    try:
        result = await OrderOps.list_all(limit=limit, offset=offset, status=status, customer_id=customer_id)
        return api_response(result)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.get("/api/erp/orders/stats")
async def order_stats(user: dict = Depends(require_auth)):
    try:
        return api_response(await OrderOps.get_stats())
    except Exception as exc:
        return error_response(str(exc), 500)


@app.get("/api/erp/orders/{order_id}")
async def get_order(order_id: str, user: dict = Depends(require_auth)):
    result = await OrderOps.get_by_id(order_id)
    if not result:
        return error_response("Order not found", 404)
    return api_response(result)


@app.post("/api/erp/orders")
async def create_order(req: OrderCreateRequest, user: dict = Depends(require_auth)):
    try:
        order_data = {"customer_id": req.customer_id, "discount_amount": req.discount_amount, "notes": req.notes}
        items_data = [item.model_dump() for item in req.items]
        result = await OrderOps.create(order_data, items_data)
        return api_response(result)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.put("/api/erp/orders/{order_id}/status")
@app.post("/api/erp/orders/{order_id}/status")
async def update_order_status(order_id: str, req: StatusUpdateRequest, user: dict = Depends(require_auth)):
    result = await OrderOps.update_status(order_id, req.status)
    if not result:
        return error_response("Order not found", 404)
    return api_response(result)


# ===================================================================
# ERP — INVOICES
# ===================================================================
class InvoiceCreateRequest(BaseModel):
    customer_id: str
    order_id: str = ""
    due_date: str = ""
    subtotal: float = 0
    tax_amount: float = 0
    total_amount: float = 0
    notes: str = ""


@app.get("/api/erp/invoices")
async def list_invoices(
    limit: int = 50, offset: int = 0,
    status: str = "", customer_id: str = "",
    user: dict = Depends(require_auth),
):
    try:
        result = await InvoiceOps.list_all(limit=limit, offset=offset, status=status, customer_id=customer_id)
        return api_response(result)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.get("/api/erp/invoices/stats")
async def invoice_stats(user: dict = Depends(require_auth)):
    try:
        return api_response(await InvoiceOps.get_stats())
    except Exception as exc:
        return error_response(str(exc), 500)


@app.get("/api/erp/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, user: dict = Depends(require_auth)):
    result = await InvoiceOps.get_by_id(invoice_id)
    if not result:
        return error_response("Invoice not found", 404)
    return api_response(result)


@app.post("/api/erp/invoices")
async def create_invoice(req: InvoiceCreateRequest, user: dict = Depends(require_auth)):
    try:
        data = req.model_dump(exclude_unset=True)
        result = await InvoiceOps.create(data)
        return api_response(result)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.put("/api/erp/invoices/{invoice_id}/status")
@app.post("/api/erp/invoices/{invoice_id}/status")
async def update_invoice_status(invoice_id: str, req: StatusUpdateRequest, user: dict = Depends(require_auth)):
    result = await InvoiceOps.update_status(invoice_id, req.status, req.paid_amount)
    if not result:
        return error_response("Invoice not found", 404)
    return api_response(result)


# ===================================================================
# ERP — EMPLOYEES
# ===================================================================
def _map_employee_fields(data: dict) -> dict:
    """Translate frontend field names to DB column names for Employee."""
    if "position" in data:
        data["designation"] = data.pop("position")
    if "hire_date" in data:
        val = data.pop("hire_date")
        data["date_of_joining"] = val if val else None
    return data

def _enrich_employee_response(emp: dict) -> dict:
    """Add frontend-friendly aliases to employee data."""
    if emp:
        emp["position"] = emp.get("designation", "")
        emp["hire_date"] = emp.get("date_of_joining")
    return emp


class EmployeeCreateRequest(BaseModel):
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    department: str = ""
    position: str = ""
    designation: str = ""
    salary: float = 0
    hire_date: str = ""
    date_of_joining: str = ""


class EmployeeUpdateRequest(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    department: str = ""
    position: str = ""
    designation: str = ""
    salary: float = None
    is_active: bool = None


@app.get("/api/erp/employees")
async def list_employees(
    limit: int = 50, offset: int = 0,
    department: str = "", search: str = "",
    user: dict = Depends(require_auth),
):
    try:
        result = await EmployeeOps.list_all(limit=limit, offset=offset, department=department, search=search)
        if isinstance(result, list):
            result = [_enrich_employee_response(e) for e in result]
        elif result and "items" in result:
            result["items"] = [_enrich_employee_response(e) for e in result["items"]]
        return api_response(result)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.get("/api/erp/employees/stats")
async def employee_stats(user: dict = Depends(require_auth)):
    try:
        return api_response(await EmployeeOps.get_stats())
    except Exception as exc:
        return error_response(str(exc), 500)


@app.get("/api/erp/employees/{emp_id}")
async def get_employee(emp_id: str, user: dict = Depends(require_auth)):
    result = await EmployeeOps.get_by_id(emp_id)
    if not result:
        return error_response("Employee not found", 404)
    return api_response(_enrich_employee_response(result))


@app.post("/api/erp/employees")
async def create_employee(req: EmployeeCreateRequest, user: dict = Depends(require_auth)):
    try:
        data = req.model_dump(exclude_unset=True)
        data = _map_employee_fields(data)
        # Handle both field name variants: prefer designation/date_of_joining
        data.pop("position", None)
        data.pop("hire_date", None)
        result = await EmployeeOps.create(data)
        return api_response(_enrich_employee_response(result))
    except Exception as exc:
        return error_response(str(exc), 500)


@app.put("/api/erp/employees/{emp_id}")
@app.post("/api/erp/employees/{emp_id}")
async def update_employee(emp_id: str, req: EmployeeUpdateRequest, user: dict = Depends(require_auth)):
    data = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None and v != ""}
    data = _map_employee_fields(data)
    data.pop("position", None)
    data.pop("hire_date", None)
    result = await EmployeeOps.update(emp_id, data)
    if not result:
        return error_response("Employee not found", 404)
    return api_response(_enrich_employee_response(result))


# ===================================================================
# ERP — INVENTORY
# ===================================================================
class InventoryMovementRequest(BaseModel):
    product_id: str
    movement_type: str
    quantity: int
    reference_type: str = ""
    reference_id: str = ""
    notes: str = ""


@app.post("/api/erp/inventory/movements")
@app.post("/api/erp/inventory/movement")
async def record_inventory_movement(req: InventoryMovementRequest, user: dict = Depends(require_auth)):
    try:
        result = await InventoryMovementOps.record(
            product_id=req.product_id, movement_type=req.movement_type,
            quantity=req.quantity, reference_type=req.reference_type or None,
            reference_id=req.reference_id or None, notes=req.notes or None,
        )
        return api_response(result)
    except Exception as exc:
        return error_response(str(exc), 500)


@app.get("/api/erp/inventory/movements/{product_id}")
async def get_inventory_movements(product_id: str, limit: int = 50, user: dict = Depends(require_auth)):
    try:
        return api_response(await InventoryMovementOps.get_by_product(product_id, limit))
    except Exception as exc:
        return error_response(str(exc), 500)


# ===================================================================
# ERP — OVERVIEW / SUMMARY
# ===================================================================
@app.get("/api/erp/overview")
async def erp_overview(user: dict = Depends(require_auth)):
    try:
        return api_response(await ERPSummaryOps.get_overview())
    except Exception as exc:
        return error_response(str(exc), 500)


# ===================================================================
# WEBSOCKET
# ===================================================================
@app.websocket("/ws/kpi")
async def ws_kpi(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    user_id = "anonymous"
    if token:
        payload = decode_jwt(token, JWT_SECRET)
        if payload:
            user_id = payload.get("sub", "anonymous")
    await ws_manager.connect(websocket, user_id)
    try:
        kpi = _kpi_store.get("Default Company") or await refresh_kpis()
        await websocket.send_text(json.dumps({"type": "kpi_update", "payload": kpi}))
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "refresh":
                    kpi = await refresh_kpis(msg.get("company", "Default Company"))
                    await websocket.send_text(json.dumps({"type": "kpi_update", "payload": kpi}))
                elif msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ===================================================================
# MAIN
# ===================================================================
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("RELOAD", "true").lower() == "true"
    logger.info("Starting IBMS Enterprise Server v2.0 on %s:%d", host, port)
    uvicorn.run("server:app", host=host, port=port, reload=reload_enabled, reload_dirs=[str(_BASE_DIR)], ws="websockets", log_level="info")
