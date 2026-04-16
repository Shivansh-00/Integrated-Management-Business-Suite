# =============================================================================
# IBMS Enterprise — Production Dockerfile (Multi-stage)
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build-only system deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Security: run as non-root
RUN groupadd -r ibms && useradd -r -g ibms -d /app -s /sbin/nologin ibms

WORKDIR /app

# Install only runtime system deps (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl tini && \
    rm -rf /var/lib/apt/lists/*

# Copy pre-built Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=ibms:ibms . .

# Remove dev/deploy files from image
RUN rm -rf deploy/ docs/ scripts/ tests/ .git/ .env* \
    requirements-dev.txt docker-compose*.yml *.md __pycache__/ \
    run_tests.py test_endpoints.py pyproject.toml

# Set secure defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    RELOAD=false \
    LOG_LEVEL=warning

# Health check — PORT comes from env (default 8000, Cloud Run sets 8080)
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

EXPOSE ${PORT:-8000}

# Drop to non-root user
USER ibms

# Use tini as init system for proper signal handling
ENTRYPOINT ["tini", "--"]
CMD ["python", "server.py"]
