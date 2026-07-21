"""
Production settings for blog_main project.
Import this in production by setting DJANGO_SETTINGS_MODULE=blog_main.settings_prod
"""

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email
from dotenv import load_dotenv

from .settings import (
    COMMENT_RATE_LIMIT,
    CONTACT_RATE_LIMIT,
    LOGIN_FAILURE_IDENTITY_RATE,
    LOGIN_FAILURE_IP_RATE,
    PASSWORD_RESET_RATE,
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def _required_environment_value(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise ImproperlyConfigured(f'{name} environment variable is required in production.')
    return value


def _comma_separated_environment_value(name, *, required=False):
    values = [
        value.strip()
        for value in os.environ.get(name, '').split(',')
        if value.strip() and value.strip() != '*'
    ]
    if required and not values:
        raise ImproperlyConfigured(f'{name} environment variable is required in production.')
    return values


def _csrf_trusted_origins():
    origins = _comma_separated_environment_value('DJANGO_CSRF_TRUSTED_ORIGINS')
    for origin in origins:
        parsed = urlparse(origin)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            raise ImproperlyConfigured(
                'DJANGO_CSRF_TRUSTED_ORIGINS entries must include http:// or https://.'
            )
    return origins


def _required_integer_environment_value(name, *, minimum, maximum):
    value = _required_environment_value(name)
    try:
        integer_value = int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f'{name} environment variable must be an integer.'
        ) from exc
    if not minimum <= integer_value <= maximum:
        raise ImproperlyConfigured(
            f'{name} environment variable must be between {minimum} and {maximum}.'
        )
    return integer_value


def _non_negative_integer_environment_value(name, *, default):
    value = os.environ.get(name, '').strip()
    if not value:
        return default
    try:
        integer_value = int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f'{name} environment variable must be a non-negative integer.'
        ) from exc
    if integer_value < 0:
        raise ImproperlyConfigured(
            f'{name} environment variable must be a non-negative integer.'
        )
    return integer_value


def _postgres_sslmode():
    sslmode = os.environ.get('POSTGRES_SSLMODE', '').strip() or 'require'
    allowed_ssl_modes = {
        'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full',
    }
    if sslmode not in allowed_ssl_modes:
        raise ImproperlyConfigured(
            'POSTGRES_SSLMODE environment variable must be a supported PostgreSQL SSL mode.'
        )
    return sslmode


def _boolean_environment_value(name, *, default):
    value = os.environ.get(name, '').strip().lower()
    if not value:
        return default
    values = {
        'true': True, '1': True, 'yes': True, 'on': True,
        'false': False, '0': False, 'no': False, 'off': False,
    }
    if value not in values:
        raise ImproperlyConfigured(
            f'{name} environment variable must be a boolean value.'
        )
    return values[value]


def _positive_integer_environment_value(name, *, default):
    value = os.environ.get(name, '').strip()
    if not value:
        return default
    try:
        integer_value = int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f'{name} environment variable must be a positive integer.'
        ) from exc
    if integer_value <= 0:
        raise ImproperlyConfigured(
            f'{name} environment variable must be a positive integer.'
        )
    return integer_value


def _email_environment_value(name, *, default=None):
    value = os.environ.get(name, '').strip() if default is None else (
        os.environ.get(name, '').strip() or default
    )
    if not value:
        raise ImproperlyConfigured(f'{name} environment variable is required in production.')
    try:
        validate_email(value)
    except ValidationError as exc:
        raise ImproperlyConfigured(
            f'{name} environment variable must be a valid email address.'
        ) from exc
    return value

# SECURITY: no production fallback secret is permitted.
SECRET_KEY = _required_environment_value('DJANGO_SECRET_KEY')

# SECURITY: Never run with debug in production
DEBUG = False

# SECURITY: Set allowed hosts from environment
ALLOWED_HOSTS = _comma_separated_environment_value(
    'DJANGO_ALLOWED_HOSTS', required=True
)
CSRF_TRUSTED_ORIGINS = _csrf_trusted_origins()

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'blogs',
    'crispy_forms',
    'crispy_bootstrap5',
    'dashboard',
    'django_ckeditor_5',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

CRISPY_TEMPLATE_PACK = 'bootstrap5'

# CKEditor 5 Configuration
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['heading', '|', 'bold', 'italic', 'link',
                    'bulletedList', 'numberedList', 'blockQuote', 'imageUpload'],
    },
    'extends': {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': ['heading', '|', 'outdent', 'indent', '|', 'bold', 'italic', 'link', 'underline', 'strikethrough',
                    'code', 'subscript', 'superscript', '|', 'codeBlock', 'insertImage',
                    'bulletedList', 'numberedList', '|', 'blockQuote', 'imageUpload', '|',
                    'removeFormat',
                    'insertTable',],
        'image': {
            'toolbar': ['imageTextAlternative', '|', 'imageStyle:alignLeft',
                        'imageStyle:alignRight', 'imageStyle:alignCenter', 'imageStyle:side', '|'],
            'styles': [
                'full',
                'side',
                'alignLeft',
                'alignRight',
                'alignCenter',
            ]
        },
        'table': {
            'contentToolbar': ['tableColumn', 'tableRow', 'mergeTableCells'],
        },
        'heading': {
            'options': [
                {'model': 'paragraph', 'title': 'Paragraph',
                    'class': 'ck-heading_paragraph'},
                {'model': 'heading1', 'view': 'h1', 'title': 'Heading 1',
                    'class': 'ck-heading_heading1'},
                {'model': 'heading2', 'view': 'h2', 'title': 'Heading 2',
                    'class': 'ck-heading_heading2'},
                {'model': 'heading3', 'view': 'h3',
                    'title': 'Heading 3', 'class': 'ck-heading_heading3'}
            ]
        }
    },
}
CKEDITOR_5_FILE_UPLOAD_PERMISSION = "authenticated"
CK_EDITOR_5_UPLOAD_FILE_VIEW_NAME = 'ck_editor_5_upload_file'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'blog_main.middleware.SecurityHeadersMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'blog_main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'blogs.context_processors.get_categories'
            ],
        },
    },
]

WSGI_APPLICATION = 'blog_main.wsgi.application'

# Database - PostgreSQL is required in production.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _required_environment_value('POSTGRES_DB'),
        'USER': _required_environment_value('POSTGRES_USER'),
        'PASSWORD': _required_environment_value('POSTGRES_PASSWORD'),
        'HOST': _required_environment_value('POSTGRES_HOST'),
        'PORT': _required_integer_environment_value(
            'POSTGRES_PORT', minimum=1, maximum=65535
        ),
        'CONN_MAX_AGE': _non_negative_integer_environment_value(
            'POSTGRES_CONN_MAX_AGE', default=60
        ),
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'sslmode': _postgres_sslmode(),
        },
    }
}

# Cache - Redis is required in production so every application worker shares it.
REDIS_URL = _required_environment_value('REDIS_URL')
if not REDIS_URL.startswith(('redis://', 'rediss://')):
    raise ImproperlyConfigured(
        'REDIS_URL environment variable must use redis:// or rediss://.'
    )
CACHE_DEFAULT_TIMEOUT = _positive_integer_environment_value(
    'CACHE_DEFAULT_TIMEOUT', default=300
)
CACHE_KEY_PREFIX = os.environ.get('CACHE_KEY_PREFIX', '').strip() or 'inkspire'
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'TIMEOUT': CACHE_DEFAULT_TIMEOUT,
        'KEY_PREFIX': CACHE_KEY_PREFIX,
    }
}

# Email - SMTP is required in production. Development retains the console backend.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = _required_environment_value('EMAIL_HOST')
EMAIL_PORT = _required_integer_environment_value(
    'EMAIL_PORT', minimum=1, maximum=65535
)
EMAIL_HOST_USER = _required_environment_value('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = _required_environment_value('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = _boolean_environment_value('EMAIL_USE_TLS', default=True)
EMAIL_USE_SSL = _boolean_environment_value('EMAIL_USE_SSL', default=False)
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured('EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be enabled.')
EMAIL_TIMEOUT = _positive_integer_environment_value('EMAIL_TIMEOUT', default=10)
DEFAULT_FROM_EMAIL = _email_environment_value('DEFAULT_FROM_EMAIL')
SERVER_EMAIL = _email_environment_value('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)
EMAIL_SUBJECT_PREFIX = os.environ.get('EMAIL_SUBJECT_PREFIX', '').strip() or '[InkSpire]'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = ['blog_main/static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': GOOGLE_CLIENT_ID,
            'secret': GOOGLE_CLIENT_SECRET,
            'key': '',
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

# ============ SECURITY SETTINGS FOR PRODUCTION ============

# HTTPS/SSL Settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Session security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 1209600  # 2 weeks

# CSRF security
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# XSS Protection
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_RESOURCE_POLICY = 'same-origin'

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Clickjacking protection
X_FRAME_OPTIONS = 'DENY'

# Self-hosted CKEditor and Bootstrap require local scripts. The public layout
# also loads Bootstrap, Google Fonts, and Font Awesome from the listed CDNs.
# Inline styles remain necessary for the existing 404 page and template styles.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
    "https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
    "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
    "img-src 'self' data: https:; "
    "connect-src 'self'; "
    "form-action 'self'"
)

# Logging for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django_errors.log',
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}
