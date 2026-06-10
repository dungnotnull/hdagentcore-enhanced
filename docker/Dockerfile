FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1001 agentuser && \
    useradd --uid 1001 --gid 1001 --no-create-home agentuser

WORKDIR /app

FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM deps AS app

COPY --chown=agentuser:agentuser . /app

RUN mkdir -p /app/data /app/models /app/workspace && \
    chown -R agentuser:agentuser /app/data /app/models /app/workspace

USER agentuser

EXPOSE 7865

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7865/health')" || exit 1

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "-m", "agent.main", "serve", "--host", "0.0.0.0", "--port", "7865", "--start-scheduler"]
