# InkSpire - Deployment Guide

## Redis cache

- Development uses Django's local-memory cache and does not require Redis.
- Production requires a shared Redis cache for all application workers. Set `REDIS_URL` to a `redis://` or encrypted `rediss://` URL, along with optional `CACHE_DEFAULT_TIMEOUT` and `CACHE_KEY_PREFIX` values.
- Redis is temporary cache storage, not permanent application storage. Production startup intentionally fails when `REDIS_URL` is absent.
- A later task will use this shared cache for rate limiting.

## 🚀 Quick Deployment Checklist

### Before Deployment:

1. **Generate a new `DJANGO_SECRET_KEY`:**
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

2. **Set environment variables:**
   ```bash
   export DJANGO_SETTINGS_MODULE=blog_main.settings_prod
   export DJANGO_SECRET_KEY="your-generated-secret-key"
   export DJANGO_ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"
   export DJANGO_CSRF_TRUSTED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
   export POSTGRES_DB="inkspire"
   export POSTGRES_USER="inkspire_user"
   export POSTGRES_PASSWORD="set-by-hosting-platform"
   export POSTGRES_HOST="database-host"
   export POSTGRES_PORT="5432"
   ```

3. **Install production dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Collect static files:**
   ```bash
   python manage.py collectstatic --settings=blog_main.settings_prod
   ```

5. **Run migrations:**
   ```bash
   python manage.py migrate --settings=blog_main.settings_prod
   python manage.py check --settings=blog_main.settings_prod
   ```

---

## 📦 Deployment Options

### Option 1: PythonAnywhere (Free Tier Available)

1. Sign up at [pythonanywhere.com](https://pythonanywhere.com)
2. Open Bash console and clone your repo:
   ```bash
   git clone https://github.com/yourusername/inkspire.git
   cd inkspire
   ```
3. Create virtualenv:
   ```bash
   python3.10 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Set `DJANGO_SETTINGS_MODULE=blog_main.settings_prod`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and all `POSTGRES_*` variables in the Web tab or WSGI configuration. Set `DJANGO_CSRF_TRUSTED_ORIGINS` when applicable.

5. Set up the database:
   ```bash
   python manage.py migrate --settings=blog_main.settings_prod
   python manage.py createsuperuser
   python manage.py collectstatic --settings=blog_main.settings_prod
   ```
6. Configure Web tab:
   - Source code: `/home/yourusername/inkspire`
   - Virtualenv: `/home/yourusername/inkspire/venv`
   - WSGI file: Point to `blog_main.wsgi`

7. Update WSGI file with environment variables:
   ```python
   import os
   os.environ['DJANGO_SETTINGS_MODULE'] = 'blog_main.settings_prod'
   os.environ['DJANGO_SECRET_KEY'] = 'your-secret-key'
   os.environ['DJANGO_ALLOWED_HOSTS'] = 'yourusername.pythonanywhere.com'
   
   from blog_main.wsgi import application
   ```

### Option 2: Railway / Render

1. Connect your GitHub repository
2. Set environment variables in dashboard
3. Set `DJANGO_SETTINGS_MODULE=blog_main.settings_prod`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and all required `POSTGRES_*` variables in the platform dashboard. Set `DJANGO_CSRF_TRUSTED_ORIGINS` for browser form submissions.
4. Set build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput --settings=blog_main.settings_prod && python manage.py migrate --settings=blog_main.settings_prod`
4. Set start command: `gunicorn blog_main.wsgi`

### Option 3: Heroku

1. Install Heroku CLI and login
2. Create a new Heroku app:
   ```bash
   heroku create inkspire-blog
   ```
3. Set environment variables:
   ```bash
   heroku config:set DJANGO_SECRET_KEY="your-secret-key"
   heroku config:set DJANGO_ALLOWED_HOSTS="inkspire-blog.herokuapp.com"
   heroku config:set DJANGO_CSRF_TRUSTED_ORIGINS="https://inkspire-blog.herokuapp.com"
   heroku config:set POSTGRES_DB="inkspire" POSTGRES_USER="inkspire_user" POSTGRES_PASSWORD="set-by-host" POSTGRES_HOST="database-host" POSTGRES_PORT="5432"
   heroku config:set DJANGO_SETTINGS_MODULE=blog_main.settings_prod
   ```
4. Deploy:
   ```bash
   git push heroku main
   heroku run python manage.py migrate
   heroku run python manage.py createsuperuser
   ```

### Option 4: DigitalOcean (VPS)

Use GitHub Student Pack for $200 free credits!

1. Create Ubuntu 22.04 Droplet ($6/month)
2. SSH into server and set up:
   ```bash
   apt update && apt upgrade -y
   apt install python3-pip python3-venv nginx supervisor -y
   ```
3. Clone repo, create venv, install requirements
4. Configure Gunicorn and Nginx
5. Set up SSL with Let's Encrypt

---

## 🔒 Security Checklist

- [ ] `DJANGO_SECRET_KEY` configured
- [ ] `DJANGO_ALLOWED_HOSTS` configured
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS` configured when required
- [ ] PostgreSQL credentials configured through the hosting platform
- [ ] HTTPS enabled (SSL certificate)
- [ ] Database credentials secured
- [ ] Static files served properly
- [ ] Admin URL secure

---

## 📁 Production Files

| File | Purpose |
|------|---------|
| `settings_prod.py` | Production settings |
| `Procfile` | Heroku/Railway command |
| `runtime.txt` | Python version |
| `.env.example` | Environment template |
| `requirements.txt` | Dependencies |

## Settings selection

- `manage.py` defaults to `blog_main.settings` for local development.
- WSGI and ASGI default to `blog_main.settings_prod`; an explicit `DJANGO_SETTINGS_MODULE` is respected.
- Production startup must use a process server such as Gunicorn, not `runserver`.
- Missing `DJANGO_SECRET_KEY` or `DJANGO_ALLOWED_HOSTS` intentionally stops production startup.
- The existing proxy configuration expects an HTTPS-terminating reverse proxy to send `X-Forwarded-Proto: https`.

## Database selection

- Local development continues to use SQLite at `db.sqlite3`; it does not require PostgreSQL credentials.
- Production requires PostgreSQL and never falls back to SQLite. Configure `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` through the hosting platform.
- `POSTGRES_CONN_MAX_AGE` defaults to `60`; `POSTGRES_SSLMODE` defaults to `require`. Managed databases normally require encrypted connections.
- Run migrations against the production database before startup: `python manage.py migrate --settings=blog_main.settings_prod`.
- Existing SQLite data is not transferred automatically. Do not upload `db.sqlite3` as a production database; plan any transfer separately.

## Local data and uploads

- `db.sqlite3` is local-development data and is not committed. Back it up before destructive local database work.
- Production uses PostgreSQL and deployments must run migrations; never deploy the repository SQLite database.
- User-uploaded files under `media/` are not committed. Production uploads require persistent mounted storage or object storage configured in a later task, with a separate backup policy.
- Application assets belong in `static/`. Git is not a database or media-backup system.

## Email selection

- Local development uses Django's console email backend; password-reset messages appear in the terminal without SMTP credentials.
- Production uses SMTP and requires `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL`. Missing values intentionally stop startup.
- `EMAIL_USE_TLS` defaults to `true`, `EMAIL_USE_SSL` defaults to `false`, and they cannot both be enabled. Common ports are `587` for STARTTLS and `465` for implicit SSL.
- `EMAIL_TIMEOUT` defaults to `10`; `SERVER_EMAIL` defaults to `DEFAULT_FROM_EMAIL`; `EMAIL_SUBJECT_PREFIX` defaults to `[InkSpire]`.
- Use hosting-platform or secret-manager credentials. This project does not select an email provider; test password-reset delivery in staging before release.

---

## 📞 Support

For issues, check Django deployment documentation:
https://docs.djangoproject.com/en/5.0/howto/deployment/
