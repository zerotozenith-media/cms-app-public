"""
Production settings , Azure App Service + Azure Database for PostgreSQL.
Every secret comes from environment variables (set via Azure Key Vault /
App Service configuration in Phase 5), never hardcoded here.
"""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

DATABASE_URL = env("DATABASE_URL")  # required in production , no local fallback
import dj_database_url  # noqa: E402
DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True)
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Azure Blob Storage (Batch 2.8) , real storage backend for receipts and
# generated report PDFs. A connection string is used (Azure's standard
# format, also what the Azurite local emulator expects) rather than
# separate account name/key settings, since it's what the Azure portal
# hands you directly and bundles authentication in one value.
#
# Deliberately fails loudly if unset in production, rather than silently
# falling back to local disk , Azure App Service's local filesystem
# isn't reliably persistent, so a silent fallback here risks silent data
# loss for receipts and reports, not just a config inconvenience.
AZURE_CONNECTION_STRING = env("AZURE_CONNECTION_STRING")
AZURE_CONTAINER = env("AZURE_STORAGE_CONTAINER", default="dclm-files")

STORAGES = {
    "default": {"BACKEND": "storages.backends.azure_storage.AzureStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


# ---- Email ----
# Any SMTP provider works. Resend and Brevo both have free tiers large
# enough for a church this size. Mailtrap's free tier is a testing inbox
# that never delivers to real people, so it is not suitable here.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp.resend.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="resend")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}