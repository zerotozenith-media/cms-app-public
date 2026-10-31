"""
Month-end balance (Kay, 30 October 2026).

Each month the money held is balanced: what the records say should be
there (the opening balance, plus giving, less expenses, less remittance
sent) against what is actually there (cash counted, or the bank
statement). The Accounts person prepares it and sends it for approval, a
different person with Approve month-end approves it, and the month is then
closed: nothing dated in it can be added, changed or deleted until an
administrator reopens it, with a reason.
"""
import datetime
from decimal import Decimal

from django.db import models


class MoneySettings(models.Model):
    """How one location keeps its money, and where its balancing starts."""

    class KeptAs(models.TextChoices):
        CASH = "cash", "Cash"
        BANK = "bank", "Bank account"

    location = models.OneToOneField("core.Location", on_delete=models.CASCADE, related_name="money_settings")
    kept_as = models.CharField(max_length=10, choices=KeptAs.choices, default=KeptAs.CASH)
    start_month = models.DateField(
        default=datetime.date(2026, 7, 1),
        help_text="The first month balanced. Stored as its first day.")
    opening_balance = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0"),
        help_text="The money held on the first day of the start month.")
    updated_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="+")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Money settings for {self.location}"


class MonthEnd(models.Model):
    """One location's month, balanced."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        SENT = "sent", "Waiting for approval"
        CLOSED = "closed", "Closed"

    class Meta:
        ordering = ["-month"]
        unique_together = [("location", "month")]

    location = models.ForeignKey("core.Location", on_delete=models.PROTECT, related_name="month_ends")
    month = models.DateField(help_text="The first day of the month.")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    # What was counted, or read from the bank statement.
    counted_amount = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    counted_by_1 = models.CharField(max_length=100, blank=True, default="")
    counted_by_2 = models.CharField(max_length=100, blank=True, default="")
    difference_note = models.TextField(blank=True, default="")
    attachment = models.FileField(upload_to="monthend/%Y/", blank=True, null=True)

    # The figures as they stood when it was sent, so the approver and the
    # report see exactly what was balanced.
    opening = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    giving = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    expenses = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    remittance = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    expected = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)

    prepared_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="month_ends_prepared")
    sent_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="month_ends_approved")
    approved_at = models.DateTimeField(null=True, blank=True)
    sent_back_note = models.TextField(blank=True, default="")
    sent_back_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="+")
    sent_back_at = models.DateTimeField(null=True, blank=True)
    reopen_reason = models.TextField(blank=True, default="")
    reopened_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="+")
    reopened_at = models.DateTimeField(null=True, blank=True)

    @property
    def difference(self):
        if self.counted_amount is None or self.expected is None:
            return None
        return self.counted_amount - self.expected

    def __str__(self):
        return f"{self.location} {self.month:%B %Y}"
