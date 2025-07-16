#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! python manage.py check --database default; do
    echo "Database is unavailable - sleeping"
    sleep 1
done

echo "Database is up - continuing..."

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist
echo "Creating superuser if needed..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Superuser created")
else:
    print("Superuser already exists")
EOF

# Start the application
echo "Starting application..."
exec "$@"