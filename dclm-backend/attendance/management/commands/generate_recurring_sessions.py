"""
Batch 0.2 approved decision: recurring session generation is fully
automatic, with no staff action required. This command IS that automation
, it creates the upcoming pending AttendanceSession for every weekly
MeetingType, at every Location, if one doesn't already exist.

Scheduling this to actually run on its own (cron, Azure Function timer
trigger, etc.) is Phase 5 deployment work , this command is the real,
tested logic that scheduling will invoke. Idempotent: safe to run daily,
multiple times a day, or after a missed run, without ever creating
duplicate sessions.
"""
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Location
from attendance.models import MeetingType, AttendanceSession

WEEKDAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


class Command(BaseCommand):
    help = "Creates the upcoming pending session for every weekly meeting type, at every location."

    def handle(self, *args, **options):
        today = timezone.localdate()
        weekly_types = MeetingType.objects.filter(frequency=MeetingType.Frequency.WEEKLY)
        locations = list(Location.objects.all())
        created_count = 0
        skipped_count = 0

        if not locations:
            self.stdout.write(self.style.WARNING("No locations exist yet , nothing to generate."))
            return

        for mt in weekly_types:
            weekday_num = WEEKDAY_MAP.get((mt.day or "").strip().lower())
            if weekday_num is None:
                self.stdout.write(self.style.WARNING(
                    f"Skipping '{mt.name}': day '{mt.day}' is not a recognized weekday."
                ))
                continue

            next_date = self._next_occurrence(today, weekday_num)

            for loc in locations:
                _, was_created = AttendanceSession.objects.get_or_create(
                    meeting_type=mt, location=loc, date=next_date,
                    defaults={
                        "mode": AttendanceSession.Mode.IN_PERSON,
                        "status": AttendanceSession.Status.PENDING,
                    },
                )
                if was_created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Created: {mt.name} @ {loc.name} on {next_date}"))
                else:
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created {created_count}, skipped {skipped_count} (already existed)."
        ))

    @staticmethod
    def _next_occurrence(from_date, weekday_num):
        """
        Days until the next occurrence of weekday_num, counting today as a
        valid match , if today IS that weekday, today's session is the
        upcoming one, not next week's. get_or_create's own existence check
        is what actually prevents duplicates on repeated same-day runs,
        not this calculation.
        """
        days_ahead = (weekday_num - from_date.weekday()) % 7
        return from_date + datetime.timedelta(days=days_ahead)
