#!/bin/bash
set -e

# Dynamically locate and activate antenv if it exists, otherwise rely on PYTHONPATH
if [ -f "./antenv/bin/activate" ]; then
    source ./antenv/bin/activate
elif [ -f "/tmp/8dee7fc0b3cea69/antenv/bin/activate" ]; then
    # Fallback if executing outside root working directory
    source /tmp/*/antenv/bin/activate 2>/dev/null || true
fi

# Default Django settings module if not explicitly set in Azure Configuration
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-blog_main.settings}"

# Default Port fallback if $PORT is unset
PORT="${PORT:-8000}"

# Run migrations and static collection using the container's Python executable
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn blog_main.wsgi --bind=0.0.0.0:$PORT