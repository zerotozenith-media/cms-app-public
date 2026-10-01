from django.apps import AppConfig


class FollowupConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "followup"
    verbose_name = "Follow-up journeys"

    def ready(self):
        from . import signals  # noqa: F401  starts and hands over journeys automatically
