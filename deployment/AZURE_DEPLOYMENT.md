# Azure App Service Deployment Guide (InkSpire / `blog_main`)

This guide covers the **first deployment** of InkSpire to Azure App Service
(Linux, Python 3.12). It intentionally keeps **SQLite** as the database and
uses the environment-variable-driven `blog_main.settings` module (not
`blog_main.settings_prod`, which requires PostgreSQL/Redis/SMTP). Migrating to
PostgreSQL, Redis, and SMTP is a separate, later task.

> This document is preparation only. No deployment or push has been performed
> as part of generating this guide.

---

## 1. Azure Web App creation settings

Create the Web App with these settings (Azure Portal, "Create Web App", or
equivalent CLI):

| Setting | Value |
|---|---|
| Publish | Code |
| Runtime stack | Python 3.12 |
| Operating System | Linux |
| Region | (closest to your users) |
| App Service Plan | Linux plan, B1 or higher (F1 free tier works for a first test but sleeps/limits CPU) |
| Startup Command | `bash startup.sh` |

Azure CLI equivalent:

```bash
az group create --name inkspire-rg --location eastus

az appservice plan create \
  --name inkspire-plan \
  --resource-group inkspire-rg \
  --is-linux \
  --sku B1

az webapp create \
  --name <your-unique-app-name> \
  --resource-group inkspire-rg \
  --plan inkspire-plan \
  --runtime "PYTHON:3.12"

az webapp config set \
  --name <your-unique-app-name> \
  --resource-group inkspire-rg \
  --startup-file "bash startup.sh"
```

Azure's Python image builds the app with Oryx (installs `requirements.txt`
automatically on deploy) and then runs the configured startup command.

---

## 2. Required environment variables (App Settings)

Set these under **Configuration > Application settings** in the Azure Portal,
or via `az webapp config appsettings set`. Required for the app to run
correctly with SQLite kept for this first deployment:

| Name | Example value | Notes |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `blog_main.settings` | Keeps SQLite; do **not** set to `blog_main.settings_prod` yet (that requires Postgres/Redis/SMTP) |
| `DJANGO_SECRET_KEY` | *(generate, see below)* | Required — do not reuse the insecure dev key |
| `DJANGO_DEBUG` | `False` | Must be `False` on any public deployment |
| `DJANGO_ALLOWED_HOSTS` | `<your-app-name>.azurewebsites.net` | Comma-separated if multiple hosts/custom domain |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://<your-app-name>.azurewebsites.net` | Comma-separated, must include scheme |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | Tells Oryx to run `pip install -r requirements.txt` on deploy |
| `WEBSITES_PORT` | *(usually not needed)* | Gunicorn binds to `$PORT`, which Azure sets automatically |

Optional, for Google OAuth (can be configured later — leave blank until you
have real credentials):

| Name | Notes |
|---|---|
| `GOOGLE_CLIENT_ID` | From Google Cloud Console OAuth client |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console OAuth client |

Generate a secret key locally before deploying:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Azure CLI equivalent for setting app settings:

```bash
az webapp config appsettings set \
  --name <your-unique-app-name> \
  --resource-group inkspire-rg \
  --settings \
    DJANGO_SETTINGS_MODULE=blog_main.settings \
    DJANGO_SECRET_KEY="<generated-key>" \
    DJANGO_DEBUG=False \
    DJANGO_ALLOWED_HOSTS="<your-app-name>.azurewebsites.net" \
    DJANGO_CSRF_TRUSTED_ORIGINS="https://<your-app-name>.azurewebsites.net" \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

### SQLite caveat (read before relying on this in real usage)

Azure App Service Linux's local filesystem is **not guaranteed persistent**
across restarts, scaling, or redeploys (it uses ephemeral/local storage by
default unless persistent storage is explicitly configured). This means
`db.sqlite3` — and anything under `media/` — can be reset. This is acceptable
for an initial smoke-test deployment but **not for real data**. Before
storing real content, either:

- Mount Azure Files/persistent storage for `db.sqlite3` and `media/`, or
- Migrate to Azure Database for PostgreSQL (the project's
  `blog_main.settings_prod` module and `DATABASE_URL` support in
  `blog_main.settings` are already prepared for this).

---

## 3. Startup command

```
bash startup.sh
```

`startup.sh` (repository root) runs, in order:

1. `python manage.py collectstatic --noinput` — gathers static files into
   `staticfiles/`, served by WhiteNoise.
2. `python manage.py migrate` — applies migrations to `db.sqlite3`.
3. `gunicorn blog_main.wsgi --bind=0.0.0.0:$PORT` — starts the app server on
   the port Azure assigns via the `$PORT` environment variable.

It also pins `DJANGO_SETTINGS_MODULE` to `blog_main.settings` if not already
set, since `blog_main/wsgi.py` defaults to `blog_main.settings_prod` when the
variable is absent.

---

## 4. GitHub Deployment Center steps

1. In the Azure Portal, open your Web App.
2. Go to **Deployment Center** (left sidebar, under Deployment).
3. Choose **Source: GitHub**, authorize/sign in to GitHub if prompted.
4. Select your **Organization**, **Repository**, and **Branch** (e.g. `main`
   or a dedicated `deploy/azure` branch — do not deploy directly from an
   unreviewed feature branch).
5. Build provider: choose **GitHub Actions** (recommended — Azure generates a
   workflow file for you) or **App Service build service (Kudu)**.
6. Save. Azure will:
   - For GitHub Actions: commit a `.github/workflows/*.yml` file to your repo
     that builds and deploys on every push to the selected branch.
   - For Kudu: trigger an immediate build/deploy using Oryx directly from the
     GitHub webhook.
7. Confirm `SCM_DO_BUILD_DURING_DEPLOYMENT=true` is set (see section 2) so
   Oryx installs `requirements.txt` during deployment.
8. Monitor the first deployment under **Deployment Center > Logs**.

**Do not click "Save" on the Deployment Center or push a branch that triggers
it until you're ready to actually deploy** — creating the connection can kick
off an immediate build/deploy.

---

## 5. Troubleshooting

**App shows "Application Error" / default Azure placeholder page**
- Check **Log stream** (Portal > Monitoring > Log stream) for the actual
  Gunicorn/Django traceback.
- Confirm the startup command is exactly `bash startup.sh` under
  Configuration > General settings.

**`DisallowedHost` errors**
- `DJANGO_ALLOWED_HOSTS` doesn't include the exact hostname being requested.
  Add `<app-name>.azurewebsites.net` (and any custom domain) exactly as it
  appears in the browser.

**CSRF verification failed on forms/login**
- `DJANGO_CSRF_TRUSTED_ORIGINS` must include the full origin with scheme,
  e.g. `https://<app-name>.azurewebsites.net` (not just the hostname).

**Static files return 404 or unstyled pages**
- Confirm `collectstatic` ran successfully in the deployment log (part of
  `startup.sh`).
- Confirm `whitenoise.middleware.WhiteNoiseMiddleware` is immediately after
  `SecurityMiddleware` in `MIDDLEWARE` (already configured).
- If you changed static file contents without redeploying, the manifest
  hash-named files may be stale — redeploy triggers a fresh `collectstatic`.

**Container fails to start / timeout binding to port**
- Gunicorn must bind to `0.0.0.0:$PORT`, not a hardcoded port. `startup.sh`
  already does this. Do not hardcode `--bind=0.0.0.0:8000`.

**Migrations not applied / `no such table` errors**
- Confirm `python manage.py migrate` in `startup.sh` actually completed (check
  Log stream). If the filesystem was reset (see SQLite caveat above), the
  database and any prior data will be gone and migrations start fresh.

**Google login button doesn't work / redirect URI mismatch**
- Google OAuth is not required for this deployment. If configuring it later,
  add the exact Azure callback URL
  (`https://<app-name>.azurewebsites.net/accounts/google/login/callback/`) to
  the Authorized redirect URIs in Google Cloud Console, and set
  `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` app settings.

**Changes not appearing after deploy**
- Check Deployment Center > Logs to confirm the latest commit actually built
  and deployed (GitHub Actions run must succeed, not just be triggered).
- Restart the Web App (Overview > Restart) to force a fresh Gunicorn start
  after a settings change.

**`ModuleNotFoundError` for a dependency**
- Confirm `SCM_DO_BUILD_DURING_DEPLOYMENT=true` is set so Oryx runs
  `pip install -r requirements.txt`. Without it, dependencies may not be
  installed.
