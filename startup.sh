#!/bin/bash
set -e

# blog_main/wsgi.py defaults to blog_main.settings_prod (Postgres/Redis/SMTP
# required) when DJANGO_SETTINGS_MODULE is unset. This first Azure deployment
# keeps SQLite, so pin to the env-var-driven blog_main.settings module unless
# an Azure App Setting already overrides DJANGO_SETTINGS_MODULE.
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-blog_main.settings}"

python manage.py collectstatic --noinput
python manage.py migrate
gunicorn blog_main.wsgi --bind=0.0.0.0:$PORT
