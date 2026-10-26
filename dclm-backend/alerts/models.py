"""
Phone and computer alerts (Kay, October 2026): web push, so they arrive even
when the system is closed. Each person turns them on once per device, and
chooses which kinds they want.
"""
from django.conf import settings
from django.db import models


class PushSubscription(models.Model):
    """One device (a browser on a phone or computer) that accepts alerts."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.URLField(max_length=1000, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    device = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def info(self):
        return {"endpoint": self.endpoint, "keys": {"p256dh": self.p256dh, "auth": self.auth}}


class AlertSettings(models.Model):
    """Which kinds of alert a person wants. Every kind starts switched on."""
    KINDS = ("morning", "assigned", "arrivals", "weekly", "announcements", "followup")

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alert_settings")
    morning = models.BooleanField(default=True)
    assigned = models.BooleanField(default=True)
    arrivals = models.BooleanField(default=True)
    weekly = models.BooleanField(default=True)
    announcements = models.BooleanField(default=True)
    # Follow-up accountability: late tasks, reasons, the Review list,
    # repeated absences and reminders to tick names.
    followup = models.BooleanField(default=True)
    # So the morning and weekly alerts go once, however often the hourly
    # job runs.
    last_morning = models.DateField(null=True, blank=True)
    last_weekly = models.DateField(null=True, blank=True)

    @classmethod
    def for_user(cls, user):
        obj, _ = cls.objects.get_or_create(user=user)
        return obj

    def wants(self, kind):
        return bool(getattr(self, kind, False))


class Announcement(models.Model):
    """An alert an administrator sent, kept so others can see what went out."""
    title = models.CharField(max_length=80)
    body = models.CharField(max_length=300)
    audience = models.CharField(max_length=120)
    location = models.ForeignKey("core.Location", on_delete=models.SET_NULL, null=True, blank=True)
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    people = models.PositiveIntegerField(default=0)
    devices = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PushKeys(models.Model):
    """The server's own key pair that phones check alerts against. Made
    once, automatically, the first time it is needed, so nobody has to set
    anything up. Never sent anywhere except the public half."""
    # Only ever one row, even if two servers make it at the same moment.
    singleton = models.BooleanField(default=True, unique=True, editable=False)
    public_key = models.CharField(max_length=120)
    private_key = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)


class Notice(models.Model):
    """
    An alert kept in the app as well as sent to the phone (Kay, 26 October
    2026), so somebody without phone alerts still sees it, and nothing
    depends on a phone being on.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notices")
    kind = models.CharField(max_length=20, default="followup")
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=400, blank=True, default="")
    url = models.CharField(max_length=200, blank=True, default="/")
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
