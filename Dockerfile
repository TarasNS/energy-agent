# KPI agent chat: one small image for local runs and Azure.
# Settings and the API key come in as environment variables; nothing secret is in the image.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KPI_LAB_HOST=0.0.0.0 \
    KPI_LAB_PORT=8000 \
    KPI_CAP_FILE=/data/cap.json \
    AUDIT_LOG_PATH=/data/audit.jsonl

WORKDIR /app
RUN pip install --no-cache-dir "pydantic>=2.6,<3" "httpx>=0.27,<1"

# Only the runtime code (see .dockerignore, which is an allowlist).
COPY harness/ harness/
COPY model/model_gateway/ model/model_gateway/
COPY mcp/kpi-solar/kpi_solar/ mcp/kpi-solar/kpi_solar/
COPY mcp/actions/actions/ mcp/actions/actions/
COPY tools/kpi-lab/server.py tools/kpi-lab/index.html tools/kpi-lab/charts.js tools/kpi-lab/config.js tools/kpi-lab/

# Runs as root: Azure App Service mounts /home (cap and audit files) writable for root only.
# Acceptable for the POC; for production, use a writable volume and a non-root user.
RUN mkdir -p /data

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"
CMD ["python", "tools/kpi-lab/server.py"]
