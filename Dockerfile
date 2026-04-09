# Agent-OS — Multi-stage Docker build
# Final image: ~350MB (vs ~1.2GB without multi-stage)
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system deps for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium
RUN playwright install chromium
RUN playwright install-deps chromium 2>/dev/null || true

# ─── Final Image ──────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy Playwright browsers from builder
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Install runtime system deps (smaller set)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libxfixes3 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY main.py .
COPY src/ src/
COPY connectors/ connectors/
COPY qwen_bridge.py .

# Create config directory
RUN mkdir -p /root/.agent-os

# Bind to 0.0.0.0 for Docker (not 127.0.0.1)
ENV AGENT_OS_HOST=0.0.0.0

# Expose ports
# 8000 = WebSocket (agents connect here)
# 8001 = HTTP REST API (curl / any HTTP client)
EXPOSE 8000 8001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/status || exit 1

# Default: run headless with auto-generated token
ENTRYPOINT ["python3", "main.py"]
CMD ["--port", "8000"]
