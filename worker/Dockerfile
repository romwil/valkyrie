# Multi-stage Dockerfile for Valkyrie Worker Service

# Stage 1: Builder
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY worker/requirements.txt ./worker/
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r worker/requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 valkyrie && \
    mkdir -p /app && \
    chown -R valkyrie:valkyrie /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=valkyrie:valkyrie ./src ./src
COPY --chown=valkyrie:valkyrie ./worker ./worker
COPY --chown=valkyrie:valkyrie ./valkyrie_config.yaml .

# Switch to non-root user
USER valkyrie

# Health check for Celery worker
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD celery -A worker.tasks inspect ping || exit 1

# Run Celery worker
CMD ["celery", "-A", "worker.tasks", "worker", "--loglevel=info", "--concurrency=2"]
