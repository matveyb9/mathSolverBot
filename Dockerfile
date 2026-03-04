# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy bot source
COPY bot.py solver.py ./

# Non-root user for security
RUN useradd -m botuser
USER botuser

# BOT_TOKEN must be provided at runtime
ENV BOT_TOKEN=""
ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]
