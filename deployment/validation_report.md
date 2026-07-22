# Azure Deployment Readiness — Validation Report

Generated while preparing InkSpire (Django package `blog_main`) for Azure App
Service (Linux, Python 3.12), using the local `venv` interpreter. No
deployment or push was performed.

## Command outputs

### `python manage.py check`

```
System check identified no issues (0 silenced).
```

Exit code: `0`

### `python manage.py collectstatic --noinput`

```
217 static files copied to '<repo>/staticfiles'.
```

Exit code: `0`

Ran with `blog_main.settings` (the default `DJANGO_SETTINGS_MODULE` for
`manage.py`), which now reads `DEBUG`, `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS`, and `SECRET_KEY` from environment variables with safe
local defaults, uses `whitenoise.storage.CompressedManifestStaticFilesStorage`,
and defaults the database to local SQLite via `dj_database_url` (no
`DATABASE_URL` set locally).

## Changes verified

- `WhiteNoiseMiddleware` is present immediately after `SecurityMiddleware` in
  `MIDDLEWARE` (`blog_main/settings.py`).
- `STATIC_URL = '/static/'`, `STATIC_ROOT = BASE_DIR / 'staticfiles'`,
  `STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'`.
- `MEDIA_URL = '/media/'`, `MEDIA_ROOT = BASE_DIR / 'media'`.
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` all read from
  environment variables (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`,
  `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`) with safe
  local-development defaults preserved.
- Database defaults to SQLite (`db.sqlite3`) via `dj_database_url.config()`,
  with an optional `DATABASE_URL` override for a later migration off SQLite.
- `gunicorn`, `whitenoise`, and `dj-database-url` are installed in the project
  `venv` and pinned in `requirements.txt`.
- `startup.sh` runs `collectstatic`, `migrate`, then starts Gunicorn bound to
  `0.0.0.0:$PORT`, and pins `DJANGO_SETTINGS_MODULE=blog_main.settings` unless
  already overridden (so it does not accidentally pick up
  `blog_main.settings_prod`'s PostgreSQL/Redis/SMTP requirements).
- `runtime.txt` contains `python-3.12`.
- Google OAuth (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) remains
  environment-variable-driven with no hardcoded credentials — unchanged, and
  already present in `.env.example` as blank placeholders.

## Known limitations (by design, per requirements)

- SQLite is kept for this first deployment. Azure App Service's local
  filesystem is not guaranteed persistent across restarts/scaling — this is
  flagged in `deployment/AZURE_DEPLOYMENT.md` and is expected to be addressed
  in a later migration to Azure Database for PostgreSQL.
- `blog_main.settings_prod` (PostgreSQL/Redis/SMTP-only) was left unmodified
  and unused for this deployment; it remains available for a future
  production-hardening pass.

## Readiness verdict

**Ready for a first Azure App Service deployment under the stated
constraints** (SQLite retained, package name unchanged, env-var-driven
config). Both required checks (`check`, `collectstatic`) pass with no errors.
Deployment itself was intentionally not performed.
