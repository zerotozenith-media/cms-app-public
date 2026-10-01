"""
The service ladder (F21): six levels that encourage steady, faithful
follow-up. Points are worked out afresh from the last 90 days of records,
so nothing here can drift from what actually happened. Only each person's
current level is stored, because moving down waits for a 30-day notice.
"""
from django.conf import settings
from django.db import models


class ServiceStanding(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_standing")
    level = models.PositiveSmallIntegerField(default=0, help_text="0 Sower up to 5 Good and Faithful Servant.")
    since = models.DateField(help_text="When they reached this level.")
    grace_until = models.DateField(null=True, blank=True, help_text="Below their level: they keep it until this date.")
    moved_up_on = models.DateField(null=True, blank=True)
    note_dismissed_on = models.DateField(null=True, blank=True, help_text="When they last dismissed the dashboard note.")

    def __str__(self):
        return f"{self.user} at level {self.level}"
