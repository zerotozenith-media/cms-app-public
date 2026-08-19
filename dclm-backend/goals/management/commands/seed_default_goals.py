"""
Seeds the 14 goals approved in Batch 0.5, wired to their correct
calculation_type. Safe to re-run , uses get_or_create keyed on name.
Requires the relevant MeetingType/MilestoneType records to already
exist for the auto-tracked goals that reference them; skips with a
warning (never crashes) if a reference is missing.
"""
from django.core.management.base import BaseCommand

from attendance.models import MeetingType
from newcomers.models import MilestoneType
from goals.models import Goal


class Command(BaseCommand):
    help = "Seeds the 14 approved default goals, idempotent."

    def handle(self, *args, **options):
        fri_worship = MeetingType.objects.filter(id="fri-worship").first()
        mon_bs = MeetingType.objects.filter(id="mon-bs").first()
        salvation = MilestoneType.objects.filter(name="Salvation").first()
        baptism = MilestoneType.objects.filter(name="Water Baptism").first()

        goals = [
            dict(horizon="Short-term", name="Friday Worship attendance (monthly avg)",
                 target=150, unit="", tracking="auto", period_type="none",
                 source="From the latest filled Friday Worship attendance session.",
                 link_route="attendance", calculation_type="latest_session_total",
                 calculation_meeting_type=fri_worship),
            dict(horizon="Short-term", name="Monday Bible Study attendance (monthly avg)",
                 target=60, unit="", tracking="auto", period_type="none",
                 source="From the latest filled Monday Bible Study session.",
                 link_route="attendance", calculation_type="latest_session_total",
                 calculation_meeting_type=mon_bs),
            dict(horizon="Short-term", name="Newcomers contacted within 48 hours",
                 target=90, unit="%", tracking="manual", period_type="none",
                 source="Manually reviewed weekly by the Follow-up / Care Team."),
            dict(horizon="Short-term", name="Follow-up tasks closed vs opened",
                 target=100, unit="%", tracking="auto", period_type="none",
                 source="From follow-up tasks marked done across all newcomers.",
                 link_route="newcomers", calculation_type="task_completion_rate"),
            dict(horizon="Short-term", name="Testimonies recorded this month",
                 target=6, unit="", tracking="auto", period_type="month",
                 source="From testimonies submitted in Reports.",
                 link_route="reports", calculation_type="testimony_count"),
            dict(horizon="Medium-term", name="General Members moved to Worker in Training (quarter)",
                 target=5, unit="", tracking="auto", period_type="quarter",
                 source="From member category movement history.",
                 link_route="members", calculation_type="member_category_moves",
                 calculation_target_category="Worker in Training"),
            dict(horizon="Medium-term", name="Workers in Training moved to Worker (quarter)",
                 target=3, unit="", tracking="auto", period_type="quarter",
                 source="From member category movement history.",
                 link_route="members", calculation_type="member_category_moves",
                 calculation_target_category="Worker"),
            dict(horizon="Medium-term", name="Newcomer-to-member conversion rate (3 months)",
                 target=40, unit="%", tracking="manual", period_type="none",
                 source="Manually reviewed quarterly by the Pastoral team."),
            dict(horizon="Medium-term", name="Online attendance retention",
                 target=25, unit="%", tracking="manual", period_type="none",
                 source="Manually estimated from online attendee follow-up."),
            dict(horizon="Long-term", name="Total membership growth (year)",
                 target=15, unit="%", tracking="manual", period_type="none",
                 source="Manually reviewed at year end from membership records."),
            dict(horizon="Long-term", name="New workers raised and deployed (year)",
                 target=10, unit="", tracking="auto", period_type="year",
                 source="From member category movement history (moved to Worker).",
                 link_route="members", calculation_type="member_category_moves",
                 calculation_target_category="Worker"),
            dict(horizon="Long-term", name="Outreach reach converted to newcomers (year)",
                 target=120, unit="", tracking="manual", period_type="none",
                 source="Manually compiled from outreach and crusade records."),
            dict(horizon="Spiritual growth", name="Salvations recorded this month",
                 target=10, unit="", tracking="auto", period_type="month",
                 source="From the Salvation milestone on newcomer profiles.",
                 link_route="newcomers", calculation_type="milestone_count",
                 calculation_milestone_type=salvation),
            dict(horizon="Spiritual growth", name="Water baptisms this month",
                 target=5, unit="", tracking="auto", period_type="month",
                 source="From the Water Baptism milestone on newcomer profiles.",
                 link_route="newcomers", calculation_type="milestone_count",
                 calculation_milestone_type=baptism),
        ]

        created, skipped = 0, 0
        for g in goals:
            name = g["name"]
            if g.get("tracking") == "auto" and g.get("calculation_type") in (
                "latest_session_total", "milestone_count"
            ) and not g.get("calculation_meeting_type") and not g.get("calculation_milestone_type"):
                self.stdout.write(self.style.WARNING(
                    f"Skipping '{name}': required reference (meeting type or milestone type) not found yet."
                ))
                skipped += 1
                continue
            _, was_created = Goal.objects.get_or_create(name=name, defaults=g)
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {name}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created}, skipped {skipped}."))
