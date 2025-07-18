#!/bin/bash
set -e

echo "Starting Academic SaaS Backend..."

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput || echo "Migration warning (non-fatal)"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Collectstatic warning (non-fatal)"

# Start gunicorn
echo "Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class sync \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    core.wsgi:application