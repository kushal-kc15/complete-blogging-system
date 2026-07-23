#!/bin/bash
set -e

# Activate Oryx virtual environment if present
if [ -d "/home/site/wwwroot/antenv" ]; then
    source /home/site/wwwroot/antenv/bin/activate
fi

# Ensure settings default to settings.py (SQLite) unless overridden
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-blog_main.settings}"

# Collect static files & run migrations
python manage.py collectstatic --noinput
python manage.py migrate

# Start Gunicorn
gunicorn blog_main.wsgi --bind=0.0.0.0:$PORT