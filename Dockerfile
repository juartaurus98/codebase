# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.8.3

COPY pyproject.toml poetry.lock* ./

# Install only production deps into an in-project venv
RUN poetry config virtualenvs.in-project true \
 && poetry install --no-interaction --no-ansi --only main

# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Non-root user for security
RUN groupadd --gid 1001 appgroup \
 && useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Copy only the pre-built venv — no build tools in the final image
COPY --from=builder /app/.venv .venv

COPY app/ app/

RUN chown -R appuser:appgroup /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
