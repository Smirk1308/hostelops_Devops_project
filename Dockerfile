FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

# Copy and install dependencies first for optimal layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Ensure instance directory exists for SQLite database storage and appuser owns /app
RUN mkdir -p /app/instance && chown -R appuser:appuser /app

USER appuser

# Health check using python urllib against /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health')" || exit 1

# Shell form of CMD so $PORT expands dynamically at runtime (Render, Cloud Run, etc.)
CMD gunicorn -b 0.0.0.0:${PORT:-8000} "hostelops:create_app()"
