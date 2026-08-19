from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Signal handlers must be connected in ready(), not at module import
        # time, to avoid Django app-loading-order issues.
        import core.signals  # noqa: F401
