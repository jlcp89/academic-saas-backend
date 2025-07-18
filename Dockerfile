# Multi-stage build for production optimization
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Change ownership to app user
RUN chown -R app:app /app

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Run migrations\n\
python manage.py migrate --noinput || true\n\
\n\
# Collect static files\n\
python manage.py collectstatic --noinput || true\n\
\n\
# Start gunicorn with sync workers (gevent compatibility issues)\n\
exec gunicorn --bind 0.0.0.0:8000 --workers 4 --worker-class sync --timeout 120 --access-logfile - --error-logfile - core.wsgi:application\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Switch to app user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/ || exit 1

# Expose port
EXPOSE 8000

# Use entrypoint script
CMD ["/app/entrypoint.sh"]