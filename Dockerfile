# Agent-OS — Docker build
FROM python:3.12-slim

WORKDIR /app

# Install ALL Chromium deps manually (playwright install-deps fails on some base images)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget gnupg ca-certificates \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libatspi2.0-0 libxshmfence1 libxfixes3 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY main.py .
COPY src/ src/
COPY connectors/ connectors/
COPY qwen_bridge.py .

RUN mkdir -p /root/.agent-os

EXPOSE 8000 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/status || exit 1

ENTRYPOINT ["python3", "main.py"]
CMD ["--port", "8000"]
