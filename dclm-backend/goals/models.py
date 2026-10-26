from django.db import models


class Goal(models.Model):
    class Horizon(models.TextChoices):
        SHORT = "Short-term", "Short-term"
        MEDIUM = "Medium-term", "Medium-term"
        LONG = "Long-term", "Long-term"
        SPIRITUAL = "Spiritual growth", "Spiritual growth"

    class Tracking(models.TextChoices):
        AUTO = "auto", "Auto-tracked"
        MANUAL = "manual", "Manual"

    class PeriodType(models.TextChoices):
        MONTH = "month", "This month"
        QUARTER = "quarter", "This quarter"
        YEAR = "year", "This year"
        NONE = "none", "Not time-boxed"

    class CalculationType(models.TextChoices):
        """
        New field, added in Batch 2.5. What an auto-tracked goal actually
        computes is identified structurally here, not by matching the
        goal's display name , renaming a goal in the real system must
        never silently break its tracking the way string-matching would.
        Blank/unused for manual goals.
        """
        LATEST_SESSION_TOTAL = "latest_session_total", "Latest filled session total"
        MONTHLY_AVERAGE = "monthly_average_attendance", "Average attendance this month"
        TASK_COMPLETION_RATE = "task_completion_rate", "Follow-up task completion rate"
        TESTIMONY_COUNT = "testimony_count", "Testimony count"
        MEMBER_CATEGORY_MOVES = "member_category_moves", "Members moved to a category"
        MILESTONE_COUNT = "milestone_count", "Milestone count"
        # Item 11 (Kay, 26 October 2026): goals that update themselves.
        SESSIONS_HELD = "sessions_held", "Sessions held"
        FUND_TOTAL = "fund_total", "Fund total"
        NET_GIVING = "net_giving", "Monthly giving less expenses"
        NAMED_CHECKINS = "named_checkins", "People checked in by name"

    horizon = models.CharField(max_length=30, choices=Horizon.choices)
    name = models.CharField(max_length=200)
    target = models.DecimalField(max_digits=10, decimal_places=2)
    current = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Only meaningful for manual goals , auto goals compute live instead.",
    )
    unit = models.CharField(max_length=10, blank=True, default="")
    tracking = models.CharField(max_length=10, choices=Tracking.choices)
    period_type = models.CharField(
        max_length=10, choices=PeriodType.choices, default=PeriodType.NONE,
        help_text="Batch 0.5, Finding 1: auto goals filter their underlying query to this window.",
    )
    source = models.CharField(max_length=300, help_text="Plain-language description shown to users.")
    # For the overseer report's goal tables. Free text, because a target is
    # often "From October 2026" or "31 October and 31 December 2026".
    target_date = models.CharField(max_length=80, blank=True, default="")
    measured_by = models.CharField(max_length=200, blank=True, default="")
    link_route = models.CharField(max_length=50, blank=True, default="")
    link_tab = models.CharField(max_length=50, blank=True, default="")

    calculation_type = models.CharField(max_length=30, choices=CalculationType.choices, blank=True, default="")
    calculation_meeting_type = models.ForeignKey(
        "attendance.MeetingType", on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Used by LATEST_SESSION_TOTAL.",
    )
    calculation_target_category = models.CharField(
        max_length=30, blank=True, default="",
        help_text="Used by MEMBER_CATEGORY_MOVES, e.g. 'Worker'.",
    )
    calculation_milestone_type = models.ForeignKey(
        "newcomers.MilestoneType", on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Used by MILESTONE_COUNT.",
    )
    # Item 11: one location, or blank for all locations; and the fund a
    # Fund total goal counts.
    calculation_location = models.ForeignKey(
        "core.Location", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    calculation_fund = models.ForeignKey(
        "finance.Fund", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["horizon", "name"]

    def __str__(self):
        return self.name

    # Auto-tracked goal *values* are computed in goals/calculations.py,
    # not here , read-time aggregation against Attendance/Members/
    # Newcomers/Reports data belongs in the API layer, not the model layer.
