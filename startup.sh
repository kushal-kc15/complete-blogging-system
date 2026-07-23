#!/bin/bash
set -e

echo "=== STARTUP.SH STARTED ==="
echo "Current directory: $(pwd)"
echo "Listing current directory:"
ls -la

# Activate virtual environment (located in the current directory)
if [ -d "antenv" ]; then
    echo "Activating virtual environment..."
    source antenv/bin/activate
else
    echo "ERROR: Virtual environment not found in current directory!"
    exit 1
fi

# Use the settings file that matches your environment
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-blog_main.settings}"

echo "Running collectstatic..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate

echo "Starting Gunicorn..."
gunicorn blog_main.wsgi --bind=0.0.0.0:$PORT
