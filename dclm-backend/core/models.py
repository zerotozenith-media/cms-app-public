from django.db import models


class Location(models.Model):
    """
    Per Batch 0.1/0.7: Bahrain is a protected core location and cannot
    be deleted. Every other location is fully Admin-manageable.
    id is a slug (not an auto integer) to match the approved schema and
    keep it human-readable in every other table that references it.
    """
    id = models.SlugField(primary_key=True, max_length=50)
    name = models.CharField(max_length=100)
    note = models.CharField(max_length=200, blank=True, default="")
    is_core = models.BooleanField(
        default=False,
        help_text="True only for Bahrain. Prevents deletion.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.note})" if self.note else self.name

    def delete(self, *args, **kwargs):
        if self.is_core:
            raise models.ProtectedError(
                f"'{self.name}' is a core location and cannot be deleted.", [self]
            )
        return super().delete(*args, **kwargs)


class AppSetting(models.Model):
    """
    Small key/value store for church-wide switches an administrator can
    change from the UI. Deliberately not a settings.py constant: these
    are operational choices the church owns, not deployment config.
    """
    key = models.CharField(max_length=100, primary_key=True)
    value = models.CharField(max_length=255)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return f"{self.key}={self.value}"

    @classmethod
    def get_bool(cls, key, default=False):
        row = cls.objects.filter(key=key).first()
        if not row:
            return default
        return row.value.lower() in ("true", "1", "yes")

    @classmethod
    def set_bool(cls, key, value):
        cls.objects.update_or_create(key=key, defaults={"value": "true" if value else "false"})
