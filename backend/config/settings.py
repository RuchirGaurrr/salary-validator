'''settings.py — Django project configuration'''''


import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file so we can read environment variables
load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
# BASE_DIR points to the backend/ folder
BASE_DIR = Path(__file__).resolve().parent.parent


# ── Security ───────────────────────────────────────────────────────────────────
# SECRET_KEY must come from .env — never hardcode this
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-env-file")

# DEBUG = True locally, False on Render
DEBUG = os.environ.get("DEBUG", "True") == "True"

# ALLOWED_HOSTS — comma-separated in .env, e.g. "localhost,yourdomain.onrender.com"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")


# ── Installed Apps ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",       # Django REST Framework — lets us build APIs easily
    "corsheaders",          # Allows React frontend to call our API
    # Our app
    "validation",
]


# ── Middleware ─────────────────────────────────────────────────────────────────
# Middleware = code that runs on every request/response
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",            # CORS must be FIRST
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",        # Serves static files on Render
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Allow React frontend (on any origin during hackathon) to call our API
CORS_ALLOW_ALL_ORIGINS = True


# ── URL & WSGI Config ──────────────────────────────────────────────────────────
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"


# ── Templates ─────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ── Database ───────────────────────────────────────────────────────────────────
# SQLite — simple file-based database, perfect for hackathon
# BASE_DIR / 'db.sqlite3' gives an absolute path (required for Render)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ── Django REST Framework ──────────────────────────────────────────────────────
REST_FRAMEWORK = {
    # Return JSON by default (not HTML)
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # No authentication required for hackathon
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
}


# ── Static Files ───────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"   # Where collectstatic puts files for Render
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# ── Misc ───────────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True
