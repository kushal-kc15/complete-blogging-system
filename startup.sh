#!/bin/bash
set -e

# Activate the virtual environment created by Oryx
source /home/site/wwwroot/antenv/bin/activate

# Use the settings file that matches your environment
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-blog_main.settings}"

# Now these will use the correct Python and packages
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn blog_main.wsgi --bind=0.0.0.0:$PORT