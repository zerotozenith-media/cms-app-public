from django.db import models


class Service(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Testimony(models.Model):
    member_name = models.CharField(max_length=150, blank=True, default="")
    is_anonymous = models.BooleanField(default=False)
    date = models.DateField()
    service = models.ForeignKey("reports.Service", on_delete=models.PROTECT, related_name="testimonies")
    text = models.TextField()

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "Testimonies"

    def __str__(self):
        who = "Anonymous" if self.is_anonymous else (self.member_name or "Unknown")
        return f"{who} · {self.date}"


class WeeklyNote(models.Model):
    department = models.ForeignKey("reports.Department", on_delete=models.PROTECT, related_name="weekly_notes")
    week_label = models.CharField(max_length=50, help_text='Display label, e.g. "04-10 Aug 2026"')
    week_start = models.DateField(help_text="The real sortable/filterable date behind the label.")
    highlights = models.TextField(blank=True, default="")
    challenges = models.TextField(blank=True, default="")
    prayer_points = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-week_start"]

    def __str__(self):
        return f"{self.department} · {self.week_label}"


class Report(models.Model):
    """
    Real stored history (Batch 0.5, Finding 3) , the demo never saved a
    report anywhere; every export was one-time and forgotten.
    """
    class Kind(models.TextChoices):
        OVERSEER = "overseer", "Overseer report"
        ZONAL = "zonal", "Zonal monthly"

    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.OVERSEER)
    # The months covered, first to last. period_* is the last month.
    start_month = models.PositiveSmallIntegerField(null=True, blank=True)
    start_year = models.PositiveSmallIntegerField(null=True, blank=True)
    period_month = models.PositiveSmallIntegerField()
    period_year = models.PositiveSmallIntegerField()
    # One location's report, or the whole church's when blank.
    location = models.ForeignKey(
        "core.Location", on_delete=models.PROTECT, related_name="reports",
        null=True, blank=True,
    )
    generated_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="reports_generated")
    generated_at = models.DateTimeField(auto_now_add=True)
    other_additions = models.TextField(blank=True, default="")
    # Written by whoever generates an overseer report, and brought forward
    # into the next one so only what is new needs changing.
    summary = models.TextField(blank=True, default="")
    challenges = models.TextField(blank=True, default="")
    training = models.TextField(blank=True, default="")
    conclusion = models.TextField(blank=True, default="")
    pdf_file = models.FileField(
        upload_to="reports/%Y/%m/",
        help_text="Local storage for now , Batch 2.8 swaps the storage "
                   "backend to Azure Blob without changing this field.",
    )

    class Meta:
        ordering = ["-period_year", "-period_month", "-generated_at"]
        # Uniqueness per month and scope is checked when generating, since a
        # blank location (the whole church) is not treated as equal to
        # itself by a database constraint.

    def __str__(self):
        return f"{self.get_kind_display()} {self.period_month}/{self.period_year}"

    @property
    def first_month(self):
        return (self.start_year or self.period_year, self.start_month or self.period_month)
