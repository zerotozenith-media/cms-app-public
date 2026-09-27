"""
Monthly remittance.

Remittance happens once a month, not each time money is received, so
asking "where did this go" on every giving entry was the wrong question
in the wrong place.

The system works out what is due, which is what was collected less what
was spent. The person recording it can override that figure, because a
member sometimes covers the expenses and more is sent than the
arithmetic suggests. Both numbers are kept, so the monthly report can
say what was actually sent rather than what was expected.
"""
from decimal import Decimal

from django.db import models
from django.utils import timezone


class Remittance(models.Model):
    """One month's transfer, recorded after it was made."""

    class Meta:
        ordering = ["-month"]
        # Each location sends its own money, so each records its own month.
        unique_together = [("month", "location")]

    # Stored as the first day of the month so it sorts and filters
    # normally; only the year and month are meaningful.
    month = models.DateField()
    # Whose money this is. Without it the figures added up every
    # location, and once one location recorded a month the other could not.
    location = models.ForeignKey(
        "core.Location", on_delete=models.PROTECT, related_name="remittances",
        null=True, blank=True,
    )
    sent_on = models.DateField(default=timezone.localdate)
    reference = models.CharField(
        max_length=80, blank=True, default="",
        help_text="Bank or transfer reference, so the record can be matched "
                  "against a statement.",
    )
    note = models.TextField(
        blank=True, default="",
        help_text="Required when the amount sent differs from the amount due.",
    )
    recorded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="remittances_recorded",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_due(self):
        return sum((l.amount_due for l in self.lines.all()), Decimal("0"))

    @property
    def total_sent(self):
        return sum((l.amount_sent for l in self.lines.all()), Decimal("0"))

    @property
    def difference(self):
        return self.total_sent - self.total_due

    def __str__(self):
        return f"Remittance for {self.month:%B %Y}"


class RemittanceLine(models.Model):
    """
    One fund's share of a month's remittance.

    Separate lines because the funds do not all go to the same place:
    building goes elsewhere from tithe and offering.
    """

    class Destination(models.TextChoices):
        DUBAI = "dubai", "Dubai"
        LAGOS = "lagos", "Lagos"
        QATAR = "qatar", "Qatar"
        KEPT = "kept", "Kept here"

    remittance = models.ForeignKey(
        Remittance, on_delete=models.CASCADE, related_name="lines")
    fund = models.ForeignKey(
        "finance.Fund", on_delete=models.PROTECT, related_name="remittance_lines")

    # What the system worked out, kept alongside what was actually sent so
    # the difference stays visible rather than being quietly overwritten.
    amount_due = models.DecimalField(max_digits=12, decimal_places=3)
    amount_sent = models.DecimalField(max_digits=12, decimal_places=3)
    destination = models.CharField(
        max_length=20, choices=Destination.choices, default=Destination.DUBAI)

    class Meta:
        unique_together = [("remittance", "fund")]
        ordering = ["fund__name"]

    @property
    def difference(self):
        return self.amount_sent - self.amount_due

    def __str__(self):
        return f"{self.fund} {self.amount_sent} to {self.get_destination_display()}"
