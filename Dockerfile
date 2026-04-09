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
RUN playwright install-deps chromium

# ─── Final Image ──────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

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
    fonts-liberation \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r agentos && useradd -r -g agentos -d /home/agentos -m agentos

# Copy Playwright browsers from builder
COPY --from=builder /root/.cache/ms-playwright /home/agentos/.cache/ms-playwright

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY main.py .
COPY src/ src/
COPY connectors/ connectors/
COPY qwen_bridge.py .

# Create config directory and set permissions
RUN mkdir -p /home/agentos/.agent-os && \
    chown -R agentos:agentos /app /home/agentos

# Switch to non-root user
USER agentos

# Set Playwright cache path for non-root user
ENV PLAYWRIGHT_BROWSERS_PATH=/home/agentos/.cache/ms-playwright

# Expose ports
# 8000 = WebSocket (agents connect here)
# 8001 = HTTP REST API (curl / any HTTP client)
# 8002 = Visual Debug UI (browser dashboard)
EXPOSE 8000 8001 8002

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/status || exit 1

# Default: run headless with auto-generated token
ENTRYPOINT ["python3", "main.py"]
CMD ["--port", "8000"]
