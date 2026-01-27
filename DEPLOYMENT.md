# InkSpire - Deployment Guide

## 🚀 Quick Deployment Checklist

### Before Deployment:

1. **Generate a new SECRET_KEY:**
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

2. **Set environment variables:**
   ```bash
   export SECRET_KEY="your-generated-secret-key"
   export DEBUG=False
   export ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"
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
4. Set up the database:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py collectstatic
   ```
5. Configure Web tab:
   - Source code: `/home/yourusername/inkspire`
   - Virtualenv: `/home/yourusername/inkspire/venv`
   - WSGI file: Point to `blog_main.wsgi`

6. Update WSGI file with environment variables:
   ```python
   import os
   os.environ['SECRET_KEY'] = 'your-secret-key'
   os.environ['DEBUG'] = 'False'
   os.environ['ALLOWED_HOSTS'] = 'yourusername.pythonanywhere.com'
   
   from blog_main.wsgi import application
   ```

### Option 2: Railway / Render

1. Connect your GitHub repository
2. Set environment variables in dashboard
3. Set build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
4. Set start command: `gunicorn blog_main.wsgi`

### Option 3: Heroku

1. Install Heroku CLI and login
2. Create a new Heroku app:
   ```bash
   heroku create inkspire-blog
   ```
3. Set environment variables:
   ```bash
   heroku config:set SECRET_KEY="your-secret-key"
   heroku config:set DEBUG=False
   heroku config:set ALLOWED_HOSTS="inkspire-blog.herokuapp.com"
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

- [ ] DEBUG = False
- [ ] New SECRET_KEY generated
- [ ] ALLOWED_HOSTS configured
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

---

## 📞 Support

For issues, check Django deployment documentation:
https://docs.djangoproject.com/en/5.0/howto/deployment/
