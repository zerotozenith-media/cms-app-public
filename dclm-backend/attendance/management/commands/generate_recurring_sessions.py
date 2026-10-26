"""
Batch 0.2 approved decision: recurring session generation is fully
automatic, with no staff action required. This command IS that automation.

Item 20 (Kay, 26 October 2026): a session used to be made up to 6 days
ahead, at every location, and showed Pending, so next Friday looked the
same as a service whose names were never taken. Now each meeting makes its
session only at the locations that hold it (Admin, Meeting Types, Held at),
and only once the meeting is no more than its "Create each session" days
away. 0, the default, makes it at 2:07 am on the day itself.

Idempotent: safe to run daily, several times a day, or after a missed run,
without ever creating duplicate sessions.
"""
import datetime

from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone

from core.models import Location
from attendance.models import MeetingType, AttendanceSession

WEEKDAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


class Command(BaseCommand):
    help = "Creates each weekly meeting's session at the locations that hold it, on the day or the days ahead set for it."

    def handle(self, *args, **options):
        today = timezone.localdate()
        weekly_types = MeetingType.objects.filter(frequency=MeetingType.Frequency.WEEKLY)
        created_count = 0
        locations = list(Location.objects.all())
        skipped_count = 0

        if not locations:
            self.stdout.write(self.style.WARNING("No locations exist yet, so nothing to generate."))
            return

        for mt in weekly_types:
            weekday_num = WEEKDAY_MAP.get((mt.day or "").strip().lower())
            if weekday_num is None:
                self.stdout.write(self.style.WARNING(
                    f"Skipping '{mt.name}': day '{mt.day}' is not a recognized weekday."
                ))
                continue

            next_date = self._next_occurrence(today, weekday_num)
            if (next_date - today).days > (mt.create_days_ahead or 0):
                continue  # not yet: it appears nearer the day

            for loc in mt.held_locations():
                # A meeting type with fellowships needs one session per
                # fellowship. Two fellowships meet the same evening, so a
                # single session would leave the second one nowhere to be
                # recorded.
                # Only the fellowships that meet at this location. A location
                # with none of its own keeps the single session it had before
                # fellowships existed.
                fellowships = [None]
                if mt.has_fellowships:
                    here = list(mt.fellowship_set.filter(is_active=True).filter(
                        models.Q(location=loc) | models.Q(location__isnull=True)))
                    fellowships = here or [None]

                for fellowship in fellowships:
                    lookup = dict(meeting_type=mt, location=loc, date=next_date)
                    if fellowship is not None:
                        lookup["fellowship"] = fellowship
                    _, was_created = AttendanceSession.objects.get_or_create(
                        **lookup,
                        defaults={
                            "mode": mt.usual_mode,
                            "status": AttendanceSession.Status.PENDING,
                        },
                    )
                    if was_created:
                        created_count += 1
                        label = f" ({fellowship.name})" if fellowship else ""
                        self.stdout.write(self.style.SUCCESS(
                            f"Created: {mt.name}{label} @ {loc.name} on {next_date}"))
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
