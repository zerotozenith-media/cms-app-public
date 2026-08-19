from django.db import models


class Fund(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PaymentMethod(models.Model):
    """Admin-configurable , Batch 0.4 decision (was hardcoded to Cash/Online Transfer)."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Expense categories"

    def __str__(self):
        return self.name


class Project(models.Model):
    """Fields beyond target_amount (description, target_date, status) are
    Batch 0.4 best-practice additions, not from the original demo."""
    class Status(models.TextChoices):
        ACTIVE = "Active", "Active"
        COMPLETED = "Completed", "Completed"
        ARCHIVED = "Archived", "Archived"

    id = models.SlugField(primary_key=True, max_length=60)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    location = models.ForeignKey("core.Location", on_delete=models.PROTECT, related_name="projects")
    target_amount = models.DecimalField(max_digits=12, decimal_places=3)
    target_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["-status", "name"]

    def __str__(self):
        return self.name

    @property
    def amount_raised(self):
        # Always computed live from Giving, never a stored running total (Batch 0.4).
        return self.giving_entries.aggregate(total=models.Sum("amount"))["total"] or 0


class Giving(models.Model):
    date = models.DateField()
    fund = models.ForeignKey("finance.Fund", on_delete=models.PROTECT, related_name="giving_entries")
    method = models.ForeignKey("finance.PaymentMethod", on_delete=models.PROTECT, related_name="giving_entries")
    amount = models.DecimalField(max_digits=12, decimal_places=3)  # BHD uses 3 decimal places
    location = models.ForeignKey("core.Location", on_delete=models.PROTECT, related_name="giving_entries")
    project = models.ForeignKey(
        "finance.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="giving_entries"
    )
    member = models.ForeignKey(
        "members.Member", on_delete=models.SET_NULL, null=True, blank=True, related_name="giving_entries"
    )

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "Giving"

    def __str__(self):
        return f"{self.fund} , {self.amount} ({self.date})"


class Expense(models.Model):
    date = models.DateField()
    category = models.ForeignKey("finance.ExpenseCategory", on_delete=models.PROTECT, related_name="expenses")
    amount = models.DecimalField(max_digits=12, decimal_places=3)
    location = models.ForeignKey("core.Location", on_delete=models.PROTECT, related_name="expenses")
    description = models.CharField(max_length=300, blank=True, default="")
    # Real uploaded file (Azure Blob, wired up in Batch 2.8) , URL reference
    # only, never inline file data (Batch 0.4 technical note).
    receipt_file = models.FileField(
        upload_to="receipts/%Y/%m/", blank=True, null=True,
        help_text="Real uploaded file (Batch 2.8) , was a placeholder URL field until now.",
    )
    project = models.ForeignKey(
        "finance.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses"
    )

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.category} , {self.amount} ({self.date})"
