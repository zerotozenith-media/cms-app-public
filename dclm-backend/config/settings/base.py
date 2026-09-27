import os
"""
Base settings shared by every environment (local, staging, production).
Environment-specific files (local.py / production.py) import * from here
and override only what genuinely differs between environments.
"""
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-insecure-key-override-in-env")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "storages",

    # DCLM Bahrain CMS apps , one per Phase 0 module boundary
    "core",
    "accounts",
    "members",
    "attendance",
    "newcomers",
    "enquiries",
    "finance",
    "goals",
    "reports",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.CurrentUserMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

# Custom user model , extends Django's built-in auth User (Batch 0.6).
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
# Bahrain timezone , flagged explicitly per the roadmap's "get dates right by type" principle.
TIME_ZONE = "Asia/Bahrain"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Local filesystem storage for now. Batch 2.8 swaps the storage BACKEND to
# Azure Blob , Django's storage abstraction means the generation code in
# reports/pdf.py doesn't need to change when that happens, only this setting.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "core.authentication.AuditAwareJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    # A model refusing a save comes back as a message, not a server error.
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
}

from datetime import timedelta  # noqa: E402
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
}


# ---- Notifications ----
# Off unless explicitly switched on, so a fresh install or a staging copy
# of the real database cannot email the congregation by accident.
NOTIFICATIONS_ENABLED = env.bool("NOTIFICATIONS_ENABLED", default=False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="DCLM Bahrain <noreply@dclm-bh.org>")

# Used to build links in emails. Without it the emails still send, they
# just carry no "open your list" button.
APP_BASE_URL = env("APP_BASE_URL", default="")


# Shared secret for the scheduled-task endpoint, which exists because
# Azure App Service has no cron. Empty by default: the endpoint refuses
# everything when this is unset, so a deployment that forgets it fails
# loudly instead of quietly accepting anyone.
TASK_SECRET = os.environ.get("DCLM_TASK_SECRET", "")


# Lets the site read the file name a download is sent with, so a
# spreadsheet is named after the figures it holds. Without it the browser
# hides the header whenever the site and the server have different
# addresses, as they may in production.
CORS_EXPOSE_HEADERS = ["Content-Disposition"]
