import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

# -----------------------------------------------------------------------------
# CORE SETTINGS
# -----------------------------------------------------------------------------
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-fallback-key-replace-in-prod')

# Set DEBUG=False in production via environment variable
DEBUG = os.environ.get('DEBUG', 'True').strip().lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [
    'https://*.azurewebsites.net',
    'https://*.onrender.com',
]

# -----------------------------------------------------------------------------
# INSTALLED APPS & MIDDLEWARE
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_ckeditor_5',
    # Your Apps
    'blogs',
    'dashboard',
]
SITE_ID = 1
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'blog_main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'blogs.context_processors.get_categories',
                'blogs.context_processors.get_user_bookmarks',
            ],
        },
    },
]

WSGI_APPLICATION = 'blog_main.wsgi.application'

# -----------------------------------------------------------------------------
# DATABASE
# -----------------------------------------------------------------------------
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# -----------------------------------------------------------------------------
# CACHE (In-Memory)
# -----------------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'inkspire-cache',
    }
}

# -----------------------------------------------------------------------------
# PASSWORD VALIDATORS
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -----------------------------------------------------------------------------
# INTERNATIONALIZATION
# -----------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# STATIC & MEDIA FILES
# -----------------------------------------------------------------------------
# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# -----------------------------------------------------------------------------
# CLOUDINARY (media uploads)
# -----------------------------------------------------------------------------
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -----------------------------------------------------------------------------
# AUTHENTICATION (django-allauth)
# -----------------------------------------------------------------------------
LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_LOGIN_ON_GET = True

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APPS': [
            {
                'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
                'secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
            },
        ],
    },
}

# -----------------------------------------------------------------------------
# CRISPY FORMS
# -----------------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# -----------------------------------------------------------------------------
# RATE LIMITING
# -----------------------------------------------------------------------------
COMMENT_RATE_LIMIT = '10/m'
PASSWORD_RESET_RATE = '5/h'
LOGIN_FAILURE_IP_RATE = '20/h'
LOGIN_FAILURE_IDENTITY_RATE = '10/h'

# -----------------------------------------------------------------------------
# CKEDITOR 5
# -----------------------------------------------------------------------------
CKEDITOR_5_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
CK_EDITOR_5_UPLOAD_FILE_VIEW_NAME = "ck_editor_5_upload_file"
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['heading', '|', 'bold', 'italic', 'link',
                    'bulletedList', 'numberedList', 'blockQuote', 'imageUpload'],
    },
    'extends': {
        'toolbar': ['heading', '|', 'bold', 'italic', 'link',
                    'underline', 'strikethrough', '|',
                    'bulletedList', 'numberedList', 'todoList', '|',
                    'blockQuote', 'codeBlock', '|',
                    'imageUpload', 'mediaEmbed', '|',
                    'insertTable', '|', 'undo', 'redo'],
        'image': {
            'toolbar': ['imageTextAlternative', 'imageStyle:alignLeft',
                        'imageStyle:alignRight', 'imageStyle:alignCenter',
                        'imageStyle:side'],
        },
        'table': {
            'contentToolbar': ['tableColumn', 'tableRow', 'mergeTableCells'],
        },
    },
}