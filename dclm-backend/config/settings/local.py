"""
Local development settings.
Uses SQLite by default so a developer can run the project with zero setup.
Switch DATABASE_URL in .env to point at a real Postgres instance if preferred.
"""
from .base import *  # noqa: F401,F403
from .base import BASE_DIR, env

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASE_URL = env("DATABASE_URL", default="") or f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
import dj_database_url  # noqa: E402
DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}

CORS_ALLOW_ALL_ORIGINS = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Defaults to local filesystem (MEDIA_ROOT, from base.py). Setting
# AZURE_CONNECTION_STRING in .env switches to real Azure Blob storage ,
# same mechanism whether pointed at real Azure or, for testing, a local
# Azurite emulator. Not required for normal local development.
AZURE_CONNECTION_STRING = env("AZURE_CONNECTION_STRING", default="")
AZURE_CONTAINER = env("AZURE_STORAGE_CONTAINER", default="dclm-files")

if AZURE_CONNECTION_STRING:
    STORAGES = {
        "default": {"BACKEND": "storages.backends.azure_storage.AzureStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

# Print notifications to the console instead of sending them. Combined
# with the console EMAIL_BACKEND above, this makes the digests visible
# in development without any provider account.
NOTIFICATIONS_ENABLED = True
APP_BASE_URL = "http://localhost:5173"
