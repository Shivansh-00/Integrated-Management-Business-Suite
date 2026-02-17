/* ═══════════════════════════════════════════════════════════════════
   IMBS Enterprise Dashboard — Frontend Application Engine v2.0
   ═══════════════════════════════════════════════════════════════════
   • Centralized API service layer with interceptors
   • JWT auth with automatic token refresh
   • CSRF protection
   • WebSocket real-time updates with auth
   • Structured response normalization
   • Retry mechanism for failed requests
   • Global error handling
   • KPI spotlight tracking & 3D tilt
   • Animated counter bounce
   • Theme persistence
   • Toast notification system
   • Sidebar navigation with page routing
   • Reduced-motion awareness
   • 60fps GPU-accelerated animations
   ═══════════════════════════════════════════════════════════════════ */

"use strict";

const IMBS = (() => {
    // ─── Configuration ───────────────────────────────────────────
    const CONFIG = {
        API_BASE: window.location.origin,
        WS_URL: `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/kpi`,
        MAX_RETRIES: 3,
        RETRY_DELAY: 1000,
        TOKEN_REFRESH_BUFFER: 120,
        KPI_ANIMATION_DURATION: 600,
        TOAST_DURATION: 5000,
        MAX_EVENTS: 200,
        MAX_TOASTS: 5,
    };

    // ─── Application State ───────────────────────────────────────
    const state = {
        user: null,
        accessToken: null,
        csrfToken: null,
        tokenExpiry: 0,
        refreshTimer: null,
        ws: null,
        wsReconnectDelay: 1000,
        wsReconnectTimer: null,
        activePage: "dashboard",
        sidebarCollapsed: false,
        theme: localStorage.getItem("imbs_theme") || "dark",
        forecastChart: null,
        analyticsChart: null,
        kpiHistoryChart: null,
        eventCount: 0,
        notifications: [],
        previousKPIs: {},
        prefersReducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    };

    // ─── Utility Helpers ─────────────────────────────────────────
    const $ = (sel) => document.getElementById(sel);
    const $$ = (sel) => document.querySelectorAll(sel);
    const escHtml = (s) => { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; };
    const fmt = (n) => {
        if (n === undefined || n === null) return "—";
        if (typeof n !== "number") return String(n);
        if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
        if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
        return String(n);
    };
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    const now = () => new Date().toLocaleTimeString();

    // ═══════════════════════════════════════════════════════════════
    // API SERVICE LAYER — Centralized with interceptors & retry
    // ═══════════════════════════════════════════════════════════════
    const api = {
        async request(method, url, body = null, opts = {}) {
            const fullUrl = CONFIG.API_BASE + url;
            const headers = { "Content-Type": "application/json" };

            if (state.accessToken) {
                headers["Authorization"] = `Bearer ${state.accessToken}`;
            }
            if (state.csrfToken && ["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
                headers["X-CSRF-Token"] = state.csrfToken;
            }

            const config = {
                method,
                headers,
                credentials: "include",
            };
            if (body && method !== "GET") {
                config.body = JSON.stringify(body);
            }

            let lastError = null;
            const maxRetries = opts.retries ?? CONFIG.MAX_RETRIES;

            for (let attempt = 0; attempt <= maxRetries; attempt++) {
                try {
                    const res = await fetch(fullUrl, config);

                    // Handle 401 — try token refresh once
                    if (res.status === 401 && !opts._refreshed) {
                        const refreshed = await auth.refreshToken();
                        if (refreshed) {
                            return api.request(method, url, body, { ...opts, _refreshed: true });
                        }
                        auth.forceLogout();
                        return null;
                    }

                    if (res.status === 429) {
                        const retryAfter = parseInt(res.headers.get("Retry-After") || "5");
                        toast.show("Rate Limited", `Too many requests. Retry in ${retryAfter}s`, "warning");
                        await sleep(retryAfter * 1000);
                        continue;
                    }

                    const data = await res.json();

                    // Normalize response structure
                    if (data.success === false && data.message) {
                        if (!opts.silent) {
                            console.warn(`API ${method} ${url}:`, data.message);
                        }
                    }

                    return data;
                } catch (err) {
                    lastError = err;
                    console.warn(`API ${method} ${url} attempt ${attempt + 1} failed:`, err.message);
                    if (attempt < maxRetries) {
                        await sleep(CONFIG.RETRY_DELAY * (attempt + 1));
                    }
                }
            }

            if (!opts.silent) {
                console.error(`API ${method} ${url} failed after ${maxRetries + 1} attempts`, lastError);
            }
            return null;
        },

        get(url, opts) { return api.request("GET", url, null, opts); },
        post(url, body, opts) { return api.request("POST", url, body, opts); },
    };

    // ═══════════════════════════════════════════════════════════════
    // TOAST NOTIFICATION SYSTEM
    // ═══════════════════════════════════════════════════════════════
    const toast = {
        _count: 0,
        show(title, message, type = "info", duration = CONFIG.TOAST_DURATION) {
            const container = $("toastContainer");
            if (!container) return;

            const icons = { info: "ℹ️", success: "✅", warning: "⚠️", error: "❌" };
            const id = `toast-${++this._count}`;

            const el = document.createElement("div");
            el.className = `toast toast--${type}`;
            el.id = id;
            el.innerHTML = `
                <span class="toast__icon">${icons[type] || icons.info}</span>
                <div class="toast__content">
                    <div class="toast__title">${escHtml(title)}</div>
                    <div class="toast__message">${escHtml(message)}</div>
                </div>
                <button class="toast__close" onclick="IMBS.toast.dismiss('${id}')">✕</button>
            `;
            container.appendChild(el);

            // Auto-dismiss
            setTimeout(() => this.dismiss(id), duration);

            // Limit visible toasts
            while (container.children.length > CONFIG.MAX_TOASTS) {
                container.removeChild(container.firstChild);
            }
        },
        dismiss(id) {
            const el = $(id);
            if (!el) return;
            el.classList.add("removing");
            setTimeout(() => el.remove(), 300);
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // AUTHENTICATION ENGINE
    // ═══════════════════════════════════════════════════════════════
    const auth = {
        async login(event) {
            event.preventDefault();
            const btn = $("loginBtn");
            const errEl = $("loginError");
            errEl.classList.remove("visible");
            btn.textContent = "Signing in…";
            btn.disabled = true;

            const username = $("loginUsername").value.trim();
            const password = $("loginPassword").value;
            const totpCode = $("loginTotp")?.value?.trim() || "";

            // Compute device fingerprint
            const fp = await this._deviceFingerprint();

            const data = await api.post("/api/auth/login", {
                username, password, totp_code: totpCode, device_fingerprint: fp,
            }, { retries: 1, silent: true });

            btn.textContent = "Sign In";
            btn.disabled = false;

            if (!data) {
                errEl.textContent = "Network error. Please try again.";
                errEl.classList.add("visible");
                return false;
            }

            if (data.data?.requires_2fa) {
                $("totpGroup").style.display = "block";
                $("loginTotp").focus();
                toast.show("2FA Required", "Enter your 6-digit TOTP code", "info");
                return false;
            }

            if (!data.success) {
                errEl.textContent = data.message || "Invalid credentials";
                errEl.classList.add("visible");
                return false;
            }

            // Success — store tokens and enter app
            const d = data.data;
            state.accessToken = d.access_token;
            state.csrfToken = d.csrf_token;
            state.tokenExpiry = Date.now() + (d.expires_in * 1000);
            state.user = { id: d.user_id, role: d.role, permissions: d.permissions };

            this._scheduleRefresh(d.expires_in);
            this._enterApp();
            toast.show("Welcome", `Signed in as ${username}`, "success");
            events.log("auth", `User ${username} logged in`);
            return false;
        },

        async register(event) {
            event.preventDefault();
            const btn = $("regBtn");
            const errEl = $("registerError");
            errEl.classList.remove("visible");
            btn.textContent = "Creating…";
            btn.disabled = true;

            const username = $("regUsername").value.trim();
            const email = $("regEmail").value.trim();
            const password = $("regPassword").value;

            const data = await api.post("/api/auth/register", { username, email, password }, { retries: 1, silent: true });

            btn.textContent = "Create Account";
            btn.disabled = false;

            if (!data || !data.success) {
                errEl.textContent = data?.message || "Registration failed";
                errEl.classList.add("visible");
                return false;
            }

            toast.show("Account Created", "You can now sign in", "success");
            this.showLogin();
            $("loginUsername").value = username;
            return false;
        },

        async refreshToken() {
            const data = await api.post("/api/auth/refresh", {}, { retries: 1, silent: true, _refreshed: true });
            if (!data || !data.success) return false;

            const d = data.data;
            state.accessToken = d.access_token;
            state.csrfToken = d.csrf_token;
            state.tokenExpiry = Date.now() + (d.expires_in * 1000);
            this._scheduleRefresh(d.expires_in);
            return true;
        },

        async logout() {
            await api.post("/api/auth/logout", {}, { retries: 0, silent: true });
            state.accessToken = null;
            state.csrfToken = null;
            state.user = null;
            state.tokenExpiry = 0;
            if (state.refreshTimer) clearTimeout(state.refreshTimer);
            websocket.disconnect();
            $("appLayout").style.display = "none";
            $("authOverlay").classList.remove("hidden");
            $("loginForm").reset();
            $("totpGroup").style.display = "none";
            toast.show("Signed Out", "Session ended securely", "info");
        },

        forceLogout() {
            state.accessToken = null;
            state.csrfToken = null;
            state.user = null;
            websocket.disconnect();
            $("appLayout").style.display = "none";
            $("authOverlay").classList.remove("hidden");
            toast.show("Session Expired", "Please sign in again", "warning");
        },

        async checkSession() {
            const data = await api.get("/api/auth/me", { retries: 1, silent: true });
            if (data?.success && data.data) {
                state.user = {
                    id: data.data.user_id || data.data.username,
                    role: data.data.role,
                    permissions: data.data.permissions,
                    username: data.data.username,
                    email: data.data.email,
                };
                this._enterApp();
                return true;
            }
            return false;
        },

        showLogin() {
            $("loginForm").style.display = "";
            $("registerForm").style.display = "none";
            $("loginError").classList.remove("visible");
        },

        showRegister() {
            $("loginForm").style.display = "none";
            $("registerForm").style.display = "";
            $("registerError").classList.remove("visible");
        },

        showProfile() {
            if (!state.user) return;
            toast.show("User Profile", `${state.user.username || state.user.id} • Role: ${state.user.role}`, "info");
        },

        _enterApp() {
            $("authOverlay").classList.add("hidden");
            $("appLayout").style.display = "";

            // Update user display
            if (state.user) {
                const name = state.user.username || state.user.id || "User";
                $("userName").textContent = name;
                $("userRole").textContent = state.user.role || "viewer";
                $("userAvatar").textContent = name.charAt(0).toUpperCase();
            }

            // Initialize app modules
            kpi.refreshAll();
            forecast.load();
            websocket.connect();
            ai.loadInsights();
            system.checkHealth();

            // Stagger KPI card animations
            if (!state.prefersReducedMotion) {
                const cards = $$(".kpi-card");
                cards.forEach((card, i) => {
                    card.style.opacity = "0";
                    card.style.transform = "translateY(20px)";
                    setTimeout(() => {
                        card.style.transition = `opacity 0.5s var(--ease-out), transform 0.5s var(--ease-out)`;
                        card.style.opacity = "1";
                        card.style.transform = "translateY(0)";
                    }, 100 + i * 80);
                });
            }
        },

        _scheduleRefresh(expiresIn) {
            if (state.refreshTimer) clearTimeout(state.refreshTimer);
            const refreshAt = Math.max((expiresIn - CONFIG.TOKEN_REFRESH_BUFFER) * 1000, 30000);
            state.refreshTimer = setTimeout(() => this.refreshToken(), refreshAt);
        },

        async _deviceFingerprint() {
            const canvas = document.createElement("canvas");
            const ctx = canvas.getContext("2d");
            ctx.textBaseline = "top";
            ctx.font = "14px Arial";
            ctx.fillText("IMBS-FP", 2, 2);
            const canvasData = canvas.toDataURL().slice(-32);
            const ua = navigator.userAgent;
            const lang = navigator.language;
            const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
            const raw = `${ua}|${lang}|${tz}|${screen.width}x${screen.height}|${canvasData}`;
            // Simple hash
            let hash = 0;
            for (let i = 0; i < raw.length; i++) {
                hash = ((hash << 5) - hash + raw.charCodeAt(i)) | 0;
            }
            return "fp-" + Math.abs(hash).toString(36);
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // WEBSOCKET — Real-time updates with auth
    // ═══════════════════════════════════════════════════════════════
    const websocket = {
        connect() {
            if (state.ws && state.ws.readyState <= 1) return;

            const wsUrl = state.accessToken
                ? `${CONFIG.WS_URL}?token=${state.accessToken}`
                : CONFIG.WS_URL;

            try {
                state.ws = new WebSocket(wsUrl);
            } catch (e) {
                console.warn("WebSocket connection failed:", e);
                this._setStatus("offline");
                return;
            }

            state.ws.onopen = () => {
                this._setStatus("online");
                state.wsReconnectDelay = 1000;
                events.log("system", "WebSocket connected");

                // Heartbeat
                this._heartbeat = setInterval(() => {
                    if (state.ws?.readyState === WebSocket.OPEN) {
                        state.ws.send(JSON.stringify({ type: "ping" }));
                    }
                }, 30000);
            };

            state.ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === "kpi_update" && msg.payload) {
                        kpi.update(msg.payload);
                    } else if (msg.type === "notification" && msg.payload) {
                        notifications.push(msg.payload);
                    } else if (msg.type === "pong") {
                        // Heartbeat response
                    }
                } catch (e) {
                    console.error("WS message parse error:", e);
                }
            };

            state.ws.onclose = () => {
                this._setStatus("offline");
                clearInterval(this._heartbeat);
                if (state.accessToken) {
                    state.wsReconnectTimer = setTimeout(() => {
                        state.wsReconnectDelay = Math.min(state.wsReconnectDelay * 1.5, 15000);
                        this.connect();
                    }, state.wsReconnectDelay);
                }
            };

            state.ws.onerror = () => { state.ws?.close(); };
        },

        disconnect() {
            clearTimeout(state.wsReconnectTimer);
            clearInterval(this._heartbeat);
            if (state.ws) {
                state.ws.onclose = null;
                state.ws.close();
                state.ws = null;
            }
            this._setStatus("offline");
        },

        send(data) {
            if (state.ws?.readyState === WebSocket.OPEN) {
                state.ws.send(JSON.stringify(data));
            }
        },

        _setStatus(status) {
            const el = $("wsStatus");
            if (!el) return;
            const map = {
                online: { cls: "status-indicator--online", text: "Connected" },
                offline: { cls: "status-indicator--offline", text: "Disconnected" },
                connecting: { cls: "status-indicator--connecting", text: "Connecting" },
            };
            const s = map[status] || map.connecting;
            el.className = `status-indicator ${s.cls}`;
            $("wsStatusText").textContent = s.text;
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // KPI ENGINE — Animated counters & spotlight tracking
    // ═══════════════════════════════════════════════════════════════
    const kpi = {
        update(data) {
            const mapping = {
                "kpi-revenue": { v: `₹${fmt(data.revenue_run_rate)}`, raw: data.revenue_run_rate, key: "revenue_run_rate" },
                "kpi-margin": { v: `${data.net_margin}%`, raw: data.net_margin, key: "net_margin" },
                "kpi-risk": { v: `${data.risk_exposure}%`, raw: data.risk_exposure, key: "risk_exposure" },
                "kpi-forecast": { v: `${data.forecast_accuracy}%`, raw: data.forecast_accuracy, key: "forecast_accuracy" },
                "kpi-compliance": { v: `${data.compliance_score}%`, raw: data.compliance_score, key: "compliance_score" },
                "kpi-fraud": { v: data.fraud_blocked, raw: data.fraud_blocked, key: "fraud_blocked" },
            };

            for (const [id, { v, raw, key }] of Object.entries(mapping)) {
                const el = $(id);
                if (!el) continue;

                const prev = state.previousKPIs[key];
                el.textContent = v;

                // Animated bounce on value change
                if (!state.prefersReducedMotion && prev !== undefined && prev !== raw) {
                    el.setAttribute("data-animate", "");
                    setTimeout(() => el.removeAttribute("data-animate"), 500);
                }

                // Flash card
                const card = el.closest(".kpi-card");
                if (card && !state.prefersReducedMotion) {
                    card.classList.remove("flash");
                    void card.offsetWidth;
                    card.classList.add("flash");
                }

                state.previousKPIs[key] = raw;
            }

            // Update compliance bar if on that page
            const compBar = $("complianceBar");
            if (compBar && data.compliance_score) {
                compBar.style.width = data.compliance_score + "%";
                const sv = $("complianceScoreValue");
                if (sv) sv.textContent = data.compliance_score + "%";
            }

            $("lastUpdate").textContent = now();
            $("footerUpdate").textContent = `Last update: ${now()}`;
        },

        async refreshAll() {
            if (state.ws?.readyState === WebSocket.OPEN) {
                websocket.send({ type: "refresh", company: "Default Company" });
            } else {
                const data = await api.get("/api/dashboard?company=Default+Company");
                if (data?.kpi) this.update(data.kpi);
            }
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // 3D TILT & SPOTLIGHT TRACKING
    // ═══════════════════════════════════════════════════════════════
    const motionEffects = {
        init() {
            if (state.prefersReducedMotion) return;

            // KPI card spotlight tracking
            document.addEventListener("mousemove", (e) => {
                $$(".kpi-card").forEach(card => {
                    const rect = card.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    card.style.setProperty("--mouse-x", `${x}px`);
                    card.style.setProperty("--mouse-y", `${y}px`);
                });
            });

            // 3D tilt on KPI cards
            $$(".kpi-card").forEach(card => {
                card.addEventListener("mousemove", (e) => {
                    const rect = card.getBoundingClientRect();
                    const x = (e.clientX - rect.left) / rect.width;
                    const y = (e.clientY - rect.top) / rect.height;
                    const tiltX = (y - 0.5) * 6;
                    const tiltY = (x - 0.5) * -6;
                    card.style.transform = `perspective(800px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateY(-3px)`;
                });
                card.addEventListener("mouseleave", () => {
                    card.style.transform = "";
                });
            });

            // Ripple effect on buttons
            document.addEventListener("click", (e) => {
                const btn = e.target.closest(".btn");
                if (!btn) return;
                const rect = btn.getBoundingClientRect();
                const ripple = document.createElement("span");
                ripple.className = "ripple";
                const size = Math.max(rect.width, rect.height);
                ripple.style.width = ripple.style.height = `${size}px`;
                ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
                ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
                btn.appendChild(ripple);
                setTimeout(() => ripple.remove(), 600);
            });
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // FORECAST CHART ENGINE
    // ═══════════════════════════════════════════════════════════════
    const forecast = {
        _chartConfig(labels, predicted, lowerCI, upperCI, model) {
            return {
                type: "line",
                data: {
                    labels,
                    datasets: [
                        {
                            label: "Predicted Revenue",
                            data: predicted,
                            borderColor: "#3b82f6",
                            backgroundColor: "rgba(59,130,246,0.08)",
                            fill: false,
                            tension: 0.35,
                            pointRadius: 4,
                            pointHoverRadius: 7,
                            pointBackgroundColor: "#3b82f6",
                            borderWidth: 2.5,
                        },
                        {
                            label: "Upper CI",
                            data: upperCI,
                            borderColor: "rgba(16,185,129,0.4)",
                            backgroundColor: "rgba(16,185,129,0.06)",
                            fill: "+1",
                            borderDash: [4, 4],
                            tension: 0.35,
                            pointRadius: 0,
                            borderWidth: 1,
                        },
                        {
                            label: "Lower CI",
                            data: lowerCI,
                            borderColor: "rgba(239,68,68,0.4)",
                            backgroundColor: "rgba(239,68,68,0.06)",
                            fill: false,
                            borderDash: [4, 4],
                            tension: 0.35,
                            pointRadius: 0,
                            borderWidth: 1,
                        },
                    ],
                },
                options: this._chartOptions(),
            };
        },

        _chartOptions() {
            const isDark = state.theme === "dark";
            return {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                animation: {
                    duration: state.prefersReducedMotion ? 0 : 800,
                    easing: "easeOutQuart",
                },
                plugins: {
                    legend: {
                        labels: {
                            color: isDark ? "#94a3c0" : "#6b7280",
                            font: { size: 11, family: "'Inter', sans-serif" },
                            pointStyle: "circle",
                            usePointStyle: true,
                        },
                    },
                    tooltip: {
                        backgroundColor: isDark ? "#1a2035" : "#ffffff",
                        titleColor: isDark ? "#e8ecf5" : "#111827",
                        bodyColor: isDark ? "#94a3c0" : "#4b5563",
                        borderColor: isDark ? "#2a3555" : "#e5e7eb",
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ₹${ctx.parsed.y?.toLocaleString() || 0}`,
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { color: isDark ? "rgba(42,53,85,0.3)" : "rgba(0,0,0,0.05)" },
                        ticks: { color: isDark ? "#6b7a99" : "#9ca3af", font: { size: 11 } },
                    },
                    y: {
                        grid: { color: isDark ? "rgba(42,53,85,0.3)" : "rgba(0,0,0,0.05)" },
                        ticks: {
                            color: isDark ? "#6b7a99" : "#9ca3af",
                            font: { size: 11 },
                            callback: (v) => "₹" + (v / 1000).toFixed(0) + "K",
                        },
                    },
                },
            };
        },

        async load() {
            const periodEl = $("forecastPeriods");
            if (!periodEl) return;
            const periods = parseInt(periodEl.value);
            const data = await api.post("/api/forecast", { company: "Default Company", periods });
            if (!data?.forecast) return;

            const labels = data.forecast.map(f => `Month ${f.month}`);
            const predicted = data.forecast.map(f => f.predicted_revenue);
            const lowerCI = data.forecast.map(f => f.lower_ci);
            const upperCI = data.forecast.map(f => f.upper_ci);

            if (state.forecastChart) state.forecastChart.destroy();
            const ctx = $("forecastChart")?.getContext("2d");
            if (!ctx) return;
            state.forecastChart = new Chart(ctx, this._chartConfig(labels, predicted, lowerCI, upperCI, data.model));
            events.log("forecast", `Loaded ${periods}-month forecast (model: ${data.model})`);
        },

        async loadAnalytics() {
            const periodEl = $("analyticsperiods");
            if (!periodEl) return;
            const periods = parseInt(periodEl.value);
            const data = await api.post("/api/forecast", { company: "Default Company", periods });
            if (!data?.forecast) return;

            const labels = data.forecast.map(f => `Month ${f.month}`);
            const predicted = data.forecast.map(f => f.predicted_revenue);
            const lowerCI = data.forecast.map(f => f.lower_ci);
            const upperCI = data.forecast.map(f => f.upper_ci);

            if (state.analyticsChart) state.analyticsChart.destroy();
            const ctx = $("analyticsChart")?.getContext("2d");
            if (!ctx) return;
            state.analyticsChart = new Chart(ctx, this._chartConfig(labels, predicted, lowerCI, upperCI, data.model));
        },

        async loadKPIHistory() {
            const data = await api.get("/api/dashboard/history?limit=30");
            if (!data?.success || !data.data?.length) return;

            const history = data.data.slice(-20);
            const labels = history.map((_, i) => `T-${history.length - i}`);
            const revenue = history.map(h => h.revenue_run_rate / 1_000_000);
            const margin = history.map(h => h.net_margin);

            if (state.kpiHistoryChart) state.kpiHistoryChart.destroy();
            const ctx = $("kpiHistoryChart")?.getContext("2d");
            if (!ctx) return;

            const isDark = state.theme === "dark";
            state.kpiHistoryChart = new Chart(ctx, {
                type: "line",
                data: {
                    labels,
                    datasets: [
                        { label: "Revenue (M)", data: revenue, borderColor: "#3b82f6", backgroundColor: "rgba(59,130,246,0.1)", fill: true, tension: 0.4, yAxisID: "y", borderWidth: 2 },
                        { label: "Net Margin (%)", data: margin, borderColor: "#10b981", backgroundColor: "rgba(16,185,129,0.1)", fill: true, tension: 0.4, yAxisID: "y1", borderWidth: 2 },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: state.prefersReducedMotion ? 0 : 800 },
                    interaction: { mode: "index", intersect: false },
                    plugins: { legend: { labels: { color: isDark ? "#94a3c0" : "#6b7280", font: { size: 11 } } } },
                    scales: {
                        x: { ticks: { color: isDark ? "#6b7a99" : "#9ca3af" }, grid: { display: false } },
                        y: { type: "linear", position: "left", ticks: { color: "#3b82f6", callback: v => v.toFixed(1) + "M" }, grid: { color: isDark ? "rgba(42,53,85,0.2)" : "rgba(0,0,0,0.04)" } },
                        y1: { type: "linear", position: "right", ticks: { color: "#10b981", callback: v => v + "%" }, grid: { display: false } },
                    },
                },
            });
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // AI COPILOT
    // ═══════════════════════════════════════════════════════════════
    const copilot = {
        async ask(inputId = "copilotInput", msgContainerId = "copilotMessages") {
            const inputEl = $(inputId);
            const msgsEl = $(msgContainerId);
            if (!inputEl || !msgsEl) return;

            const question = inputEl.value.trim();
            if (!question) return;

            // User message
            msgsEl.innerHTML += `<div class="copilot__msg copilot__msg--user">${escHtml(question)}</div>`;
            inputEl.value = "";
            msgsEl.scrollTop = msgsEl.scrollHeight;

            // Loading indicator
            const loadingId = `loading-${Date.now()}`;
            msgsEl.innerHTML += `<div class="copilot__msg copilot__msg--bot" id="${loadingId}"><span class="skeleton skeleton--text" style="width:60%;display:inline-block"></span></div>`;
            msgsEl.scrollTop = msgsEl.scrollHeight;

            const data = await api.post("/api/copilot/ask", { question });

            const loadEl = $(loadingId);
            if (loadEl) loadEl.remove();

            const answer = data?.answer || "Sorry, I couldn't process that request.";
            const confidence = data?.confidence || 0;
            const confClass = confidence >= 0.85 ? "high" : confidence >= 0.7 ? "medium" : "low";
            const confPct = Math.round(confidence * 100);

            msgsEl.innerHTML += `
                <div class="copilot__msg copilot__msg--bot">
                    ${escHtml(answer).replace(/\n/g, "<br>")}
                    <div class="confidence-badge confidence-badge--${confClass}">${confPct}% confidence</div>
                </div>
            `;
            msgsEl.scrollTop = msgsEl.scrollHeight;

            // Update badge
            const badge = $("copilotConfidence");
            if (badge && inputId === "copilotInput") {
                badge.style.display = "";
                badge.textContent = `${confPct}% confidence`;
                badge.className = `badge badge--${confClass === "high" ? "success" : confClass === "medium" ? "" : "danger"}`;
            }

            events.log("copilot", `Q: "${question.slice(0, 40)}…"`);
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // AI INSIGHTS & ANOMALY DETECTION
    // ═══════════════════════════════════════════════════════════════
    const ai = {
        async loadInsights() {
            const data = await api.get("/api/ai/insights");
            if (!data?.success || !data.data) return;

            const grid = $("insightsGrid");
            if (!grid) return;

            grid.innerHTML = data.data.map((insight, idx) => {
                const typeIcons = { anomaly: "🔴", trend: "📊", prediction: "🔮", recommendation: "💡" };
                const icon = typeIcons[insight.type] || "📋";
                const confPct = Math.round((insight.confidence || 0) * 100);
                const confClass = confPct >= 85 ? "high" : confPct >= 70 ? "medium" : "low";

                return `
                    <div class="insight-card" style="animation-delay:${idx * 0.1}s">
                        <div class="insight-card__icon insight-card__icon--${insight.type}">${icon}</div>
                        <div class="insight-card__content">
                            <div class="insight-card__title">${escHtml(insight.title)}</div>
                            <div class="insight-card__desc">${escHtml(insight.description)}</div>
                            <div class="confidence-badge confidence-badge--${confClass}" style="margin-top:8px">${confPct}% confidence</div>
                        </div>
                    </div>
                `;
            }).join("");

            // Update badge
            const badge = $("insightsBadge");
            if (badge && data.data.length) {
                badge.textContent = data.data.length;
                badge.style.display = "";
            }
        },

        async loadAnomalies() {
            const el = $("anomalyResults");
            if (!el) return;

            el.innerHTML = '<div class="skeleton skeleton--card"></div>';
            const data = await api.get("/api/ai/anomalies");
            if (!data?.success || !data.data) {
                el.innerHTML = '<div class="text-muted">No anomalies detected</div>';
                return;
            }

            el.innerHTML = data.data.map(a => {
                const sevColor = a.severity === "high" ? "danger" : a.severity === "medium" ? "warning" : "success";
                return `
                    <div class="insight-card">
                        <div class="insight-card__icon insight-card__icon--anomaly">🔴</div>
                        <div class="insight-card__content">
                            <div class="insight-card__title">${escHtml(a.metric)} — Deviation: ${a.deviation_pct}%</div>
                            <div class="insight-card__desc">Current: ${a.current_value} | Expected: ${a.expected_range.join("–")} | Status: ${a.status}</div>
                            <span class="badge badge--${sevColor}" style="margin-top:6px">${a.severity}</span>
                        </div>
                    </div>
                `;
            }).join("");
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // BUSINESS TOOL ENDPOINTS
    // ═══════════════════════════════════════════════════════════════
    const tools = {
        async scoreRisk() {
            const body = {
                voucher_type: $("riskVoucherType").value,
                voucher_no: $("riskVoucherNo").value,
                amount: parseFloat($("riskAmount").value),
            };
            const data = await api.post("/api/risk/score", body);
            const el = $("riskResult");
            if (data && el) {
                el.textContent = JSON.stringify(data, null, 2);
                el.className = `result-box ${data.severity === "critical" || data.severity === "high" ? "danger" : data.severity === "medium" ? "warning" : "success"}`;
                events.log("risk", `${data.voucher_no}: score=${data.risk_score}, severity=${data.severity}`);
                toast.show("Risk Scored", `${data.voucher_no}: ${data.severity} (${data.risk_score})`, data.severity === "high" || data.severity === "critical" ? "error" : "success");
            }
        },

        async detectFraud() {
            const body = {
                voucher_no: $("fraudVoucherNo").value,
                amount: parseFloat($("fraudAmount").value),
                velocity: parseFloat($("fraudVelocity").value),
            };
            const data = await api.post("/api/fraud/detect", body);
            const el = $("fraudResult");
            if (data && el) {
                el.textContent = JSON.stringify(data, null, 2);
                el.className = `result-box ${data.requires_review ? "danger" : "success"}`;
                events.log("fraud", `${data.voucher_no}: score=${data.fraud_score}, review=${data.requires_review}`);
                toast.show("Fraud Detection", data.requires_review ? "⚠️ Fraud review required!" : "✅ Transaction appears clean", data.requires_review ? "error" : "success");
            }
        },

        async suggestPrice() {
            const body = {
                base_price: parseFloat($("pricingBase").value),
                demand_index: parseFloat($("pricingDemand").value),
                stock_index: parseFloat($("pricingStock").value),
                competitor_index: parseFloat($("pricingComp").value),
            };
            const data = await api.post("/api/pricing/suggest", body);
            const el = $("pricingResult");
            if (data && el) {
                el.textContent = JSON.stringify(data, null, 2);
                el.className = "result-box success";
                events.log("pricing", `₹${data.base_price} → ₹${data.suggested_price} (×${data.multiplier})`);
                toast.show("Price Optimized", `₹${data.base_price} → ₹${data.suggested_price}`, "success");
            }
        },

        async checkCompliance() {
            const body = {
                amount: parseFloat($("compAmount").value),
                approval_reference: $("compApproval").value || null,
            };
            const data = await api.post("/api/compliance/check", body);
            const el = $("complianceResult");
            if (data && el) {
                el.textContent = JSON.stringify(data, null, 2);
                el.className = `result-box ${data.passed ? "success" : "danger"}`;
                events.log("compliance", data.passed ? "PASSED" : `VIOLATIONS: ${data.violations.join(", ")}`);
                toast.show("Compliance Check", data.passed ? "All controls passed" : `${data.violations.length} violation(s) found`, data.passed ? "success" : "error");
            }
        },

        async optimizeBudget() {
            let lines;
            try { lines = JSON.parse($("budgetLines").value); }
            catch { $("budgetResult").textContent = "Invalid JSON — please check format"; return; }

            const body = { lines, growth_target: parseFloat($("budgetGrowth").value) / 100 };
            const data = await api.post("/api/budget/optimize", body);
            const el = $("budgetResult");
            if (data && el) {
                el.textContent = JSON.stringify(data, null, 2);
                el.className = "result-box success";
                events.log("budget", `Current: ₹${fmt(data.current_total)} → Optimized: ₹${fmt(data.optimized_total)}`);
                toast.show("Budget Optimized", `Savings: ₹${fmt((data.current_total || 0) - (data.optimized_total || 0))}`, "success");
            }
        },

        async scoreLead() {
            const body = {
                lead_name: $("leadName").value,
                engagement: parseFloat($("leadEngagement").value),
                fit: parseFloat($("leadFit").value),
            };
            const data = await api.post("/api/leads/score", body);
            const el = $("leadResult");
            if (data && el) {
                el.textContent = JSON.stringify(data, null, 2);
                el.className = `result-box ${data.bucket === "hot" ? "success" : data.bucket === "warm" ? "warning" : ""}`;
                events.log("lead", `${data.lead}: score=${data.score}, bucket=${data.bucket}`);
                toast.show("Lead Scored", `${data.lead}: ${data.bucket} (${data.score})`, data.bucket === "hot" ? "success" : "info");
            }
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // SYSTEM HEALTH & STATUS
    // ═══════════════════════════════════════════════════════════════
    const system = {
        async checkHealth() {
            const data = await api.get("/api/system/status");
            if (!data?.success || !data.data) return;

            const d = data.data;
            const healthGrid = $("healthGrid");
            if (healthGrid) {
                const uptime = d.server?.uptime_human || "—";
                const errRate = d.performance?.error_rate_pct || 0;
                const reqs = d.performance?.total_requests || 0;
                const wsConns = d.performance?.ws_connections || 0;
                const redis = d.infrastructure?.redis?.connected;

                healthGrid.innerHTML = `
                    <div class="health-item">
                        <div class="health-item__label">Server Status</div>
                        <div class="health-item__value" style="color:var(--success)">● Healthy</div>
                        <div class="health-item__bar"><div class="health-item__bar-fill health-item__bar-fill--good" style="width:100%"></div></div>
                    </div>
                    <div class="health-item">
                        <div class="health-item__label">Uptime</div>
                        <div class="health-item__value">${uptime}</div>
                        <div class="health-item__bar"><div class="health-item__bar-fill health-item__bar-fill--good" style="width:95%"></div></div>
                    </div>
                    <div class="health-item">
                        <div class="health-item__label">Total Requests</div>
                        <div class="health-item__value">${reqs.toLocaleString()}</div>
                        <div class="health-item__bar"><div class="health-item__bar-fill health-item__bar-fill--good" style="width:${Math.min(reqs / 100, 100)}%"></div></div>
                    </div>
                    <div class="health-item">
                        <div class="health-item__label">Error Rate</div>
                        <div class="health-item__value">${errRate}%</div>
                        <div class="health-item__bar"><div class="health-item__bar-fill ${errRate > 5 ? "health-item__bar-fill--bad" : errRate > 2 ? "health-item__bar-fill--warn" : "health-item__bar-fill--good"}" style="width:${Math.max(100 - errRate * 10, 5)}%"></div></div>
                    </div>
                    <div class="health-item">
                        <div class="health-item__label">WebSocket Clients</div>
                        <div class="health-item__value">${wsConns}</div>
                    </div>
                    <div class="health-item">
                        <div class="health-item__label">Redis</div>
                        <div class="health-item__value" style="color:${redis ? "var(--success)" : "var(--warning)"}">${redis ? "● Connected" : "● In-Memory Fallback"}</div>
                    </div>
                    <div class="health-item">
                        <div class="health-item__label">Cache Type</div>
                        <div class="health-item__value">${d.infrastructure?.cache?.type || "—"}</div>
                    </div>
                    <div class="health-item">
                        <div class="health-item__label">API Version</div>
                        <div class="health-item__value">v${d.server?.version || "2.0.0"}</div>
                    </div>
                `;
            }

            // API endpoint stats
            const apiEl = $("apiStatusResult");
            if (apiEl && d.top_endpoints) {
                apiEl.textContent = "Top API Endpoints:\n" + d.top_endpoints.map(ep =>
                    `  ${ep.path.padEnd(35)} ${String(ep.requests).padStart(6)} reqs  ${ep.avg_ms.toFixed(1)}ms avg`
                ).join("\n");
                apiEl.className = "result-box success";
            }

            events.log("system", "Health check completed");
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // AUDIT LOG
    // ═══════════════════════════════════════════════════════════════
    const audit = {
        async load() {
            const el = $("auditLog");
            if (!el) return;

            const data = await api.get("/api/audit/log?limit=100", { silent: true });
            if (!data?.success || !data.data?.entries?.length) {
                el.innerHTML = '<div class="event-log__empty">No audit entries found. Audit events are recorded for login attempts, 2FA operations, and more.</div>';
                return;
            }

            el.innerHTML = data.data.entries.map(entry => `
                <div class="event-log__entry">
                    <span class="event-log__time">${new Date(entry.timestamp).toLocaleString()}</span>
                    <span class="event-log__type">${escHtml(entry.event_type || entry.event || "—")}</span>
                    <span class="event-log__data">${escHtml(entry.user_id || "")} ${escHtml(entry.details || entry.ip || "")}</span>
                </div>
            `).join("");
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // NOTIFICATION SYSTEM
    // ═══════════════════════════════════════════════════════════════
    const notifications = {
        _unread: 0,

        push(notif) {
            state.notifications.unshift(notif);
            if (state.notifications.length > 100) state.notifications.pop();
            this._unread++;
            this._updateBadge();
            toast.show(notif.title, notif.message, notif.level || "info");
            events.log("notification", notif.title);
        },

        toggle() {
            this._unread = 0;
            this._updateBadge();
            // Show notifications in toast for now
            if (state.notifications.length === 0) {
                toast.show("Notifications", "No new notifications", "info");
            } else {
                const latest = state.notifications.slice(0, 3);
                latest.forEach(n => toast.show(n.title, n.message, n.level || "info", 3000));
            }
        },

        _updateBadge() {
            const badge = $("notifBadge");
            if (!badge) return;
            if (this._unread > 0) {
                badge.textContent = this._unread > 99 ? "99+" : this._unread;
                badge.style.display = "";
            } else {
                badge.style.display = "none";
            }
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // EVENT LOG
    // ═══════════════════════════════════════════════════════════════
    const events = {
        log(type, msg) {
            state.eventCount++;
            const log = $("eventLog");
            if (!log) return;

            const empty = log.querySelector(".event-log__empty");
            if (empty) empty.remove();

            const entry = document.createElement("div");
            entry.className = "event-log__entry";
            entry.innerHTML = `
                <span class="event-log__time">${now()}</span>
                <span class="event-log__type">${escHtml(type)}</span>
                <span class="event-log__data">${escHtml(msg)}</span>
            `;
            log.prepend(entry);

            while (log.children.length > CONFIG.MAX_EVENTS) {
                log.removeChild(log.lastChild);
            }

            const countEl = $("eventCount");
            if (countEl) countEl.textContent = `${state.eventCount} events`;

            // Update sidebar badge
            const badge = $("eventBadge");
            if (badge && state.activePage !== "events") {
                const current = parseInt(badge.textContent) || 0;
                badge.textContent = current + 1;
                badge.style.display = "";
            }
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // NAVIGATION — Page routing & sidebar
    // ═══════════════════════════════════════════════════════════════
    const nav = {
        goto(page) {
            // Hide all pages
            $$("[id^='page-']").forEach(el => { el.style.display = "none"; });

            // Show target page
            const targetEl = $(`page-${page}`);
            if (targetEl) {
                targetEl.style.display = "";

                // Page enter animation
                if (!state.prefersReducedMotion) {
                    targetEl.style.opacity = "0";
                    targetEl.style.transform = "translateY(10px)";
                    requestAnimationFrame(() => {
                        targetEl.style.transition = "opacity 0.35s var(--ease-out), transform 0.35s var(--ease-out)";
                        targetEl.style.opacity = "1";
                        targetEl.style.transform = "translateY(0)";
                    });
                }
            }

            // Update nav active state
            $$(".nav-item").forEach(item => {
                item.classList.toggle("active", item.dataset.page === page);
            });

            // Update breadcrumb
            const names = {
                dashboard: "Dashboard", analytics: "Analytics", "ai-insights": "AI Insights",
                risk: "Risk & Fraud", compliance: "Compliance", pricing: "Dynamic Pricing",
                budget: "Budget Optimizer", leads: "Lead Scoring", events: "Event Stream",
                system: "System Health", audit: "Audit Log",
            };
            $("breadcrumb").textContent = names[page] || page;

            // Clear event badge when visiting events page
            if (page === "events") {
                const badge = $("eventBadge");
                if (badge) { badge.textContent = "0"; badge.style.display = "none"; }
            }

            // Load page-specific data
            if (page === "analytics") {
                forecast.loadAnalytics();
                forecast.loadKPIHistory();
            } else if (page === "ai-insights") {
                ai.loadInsights();
                ai.loadAnomalies();
            } else if (page === "system") {
                system.checkHealth();
            } else if (page === "audit") {
                audit.load();
            }

            state.activePage = page;

            // Close sidebar on mobile
            if (window.innerWidth <= 1024) {
                $("sidebar")?.classList.remove("open");
            }
        },

        toggleSidebar() {
            const sidebar = $("sidebar");
            if (!sidebar) return;

            if (window.innerWidth <= 1024) {
                sidebar.classList.toggle("open");
            } else {
                sidebar.classList.toggle("collapsed");
                state.sidebarCollapsed = sidebar.classList.contains("collapsed");
                const label = $("sidebarToggleLabel");
                if (label) label.textContent = state.sidebarCollapsed ? "▷" : "◁ Collapse";
            }
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // THEME ENGINE
    // ═══════════════════════════════════════════════════════════════
    const theme = {
        toggle() {
            state.theme = state.theme === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", state.theme);
            document.body.setAttribute("data-theme", state.theme);
            localStorage.setItem("imbs_theme", state.theme);
            $("themeBtn").textContent = state.theme === "dark" ? "🌙" : "☀️";

            // Rebuild charts with new theme colors
            if (state.forecastChart) forecast.load();
            if (state.analyticsChart) forecast.loadAnalytics();
            if (state.kpiHistoryChart) forecast.loadKPIHistory();
        },

        init() {
            document.documentElement.setAttribute("data-theme", state.theme);
            document.body.setAttribute("data-theme", state.theme);
            const btn = $("themeBtn");
            if (btn) btn.textContent = state.theme === "dark" ? "🌙" : "☀️";
        },
    };

    // ═══════════════════════════════════════════════════════════════
    // PASSWORD STRENGTH CHECKER
    // ═══════════════════════════════════════════════════════════════
    function initPasswordStrength() {
        const input = $("regPassword");
        const display = $("passwordStrength");
        if (!input || !display) return;

        input.addEventListener("input", () => {
            const pw = input.value;
            let score = 0;
            if (pw.length >= 8) score++;
            if (pw.length >= 12) score++;
            if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
            if (/\d/.test(pw)) score++;
            if (/[^a-zA-Z\d]/.test(pw)) score++;

            const labels = ["Very Weak", "Weak", "Fair", "Strong", "Very Strong"];
            const colors = ["var(--danger)", "var(--danger)", "var(--warning)", "var(--success)", "var(--success)"];
            const idx = Math.min(score, labels.length) - 1;

            if (pw.length === 0) {
                display.innerHTML = "";
            } else {
                display.innerHTML = `<div style="margin-top:6px;font-size:var(--text-xs);color:${colors[Math.max(idx, 0)]}">${labels[Math.max(idx, 0)]} — ${score}/5</div>`;
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════
    // RESPONSIVE HANDLERS
    // ═══════════════════════════════════════════════════════════════
    function initResponsive() {
        const mql = window.matchMedia("(max-width: 1024px)");
        const update = (e) => {
            const mobileBtn = $("mobileMenuBtn");
            if (mobileBtn) mobileBtn.style.display = e.matches ? "inline-flex" : "none";
        };
        mql.addEventListener("change", update);
        update(mql);

        // Listen for reduced motion preference changes
        window.matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change", (e) => {
            state.prefersReducedMotion = e.matches;
        });
    }

    // ═══════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ═══════════════════════════════════════════════════════════════
    async function init() {
        theme.init();
        initPasswordStrength();
        initResponsive();
        motionEffects.init();

        // Try to restore session from HttpOnly cookies
        const hasSession = await auth.checkSession();
        if (!hasSession) {
            $("authOverlay").classList.remove("hidden");
            $("appLayout").style.display = "none";
        }
    }

    // Boot
    document.addEventListener("DOMContentLoaded", init);

    // ─── Public API ──────────────────────────────────────────────
    return {
        auth,
        kpi,
        forecast,
        copilot,
        ai,
        tools,
        system,
        audit,
        nav,
        theme,
        toast,
        notifications,
        events,
    };
})();
