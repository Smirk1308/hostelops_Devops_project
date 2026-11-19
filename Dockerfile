FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-root user and group.
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

# Install dependencies before copying application code for better caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Train the ML model during the image build once Module 3 is integrated.
# The conditional keeps early module branches buildable before ml/train.py
# has been merged into the repository.
RUN if [ -f ml/train.py ]; then \
        python -m ml.train; \
    else \
        echo "ML training script not present; skipping model training."; \
    fi

# Ensure persistent SQLite storage exists and appuser owns the app files.
RUN mkdir -p /app/instance && chown -R appuser:appuser /app

USER appuser

# Verify the application health endpoint inside the container.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health')" || exit 1

CMD gunicorn -b 0.0.0.0:${PORT:-8000} "hostelops:create_app()"
