"""
Confirmed design: no usher or leader ever clicks an "end service" button.
Some time after a tracked meeting's start time, anyone not checked in is
automatically treated as absent and gets a real follow-up task created
for their shepherd. This command IS that automation , scheduling it to
actually run on its own (cron, Azure Function timer trigger, etc.) is
Phase 5 deployment work, matching generate_recurring_sessions' existing
precedent; this command is the real, tested logic that scheduling will
invoke.

Idempotent two ways, deliberately: safe to run every few minutes without
ever double-processing the same session (a member already has a task
tied to that specific missed_session), while still correctly allowing a
genuinely new absence at a later session to create a new task even if an
earlier one was already resolved , only an *open* task on a *different*
session blocks a new one, matching the confirmed "don't stack tasks"
rule without also blocking real, separate follow-ups over time.

A meeting with counts_for_absence on but no start_time set is simply
never auto-checked , there's no reasonable threshold to compare against,
and guessing one would be worse than doing nothing until an admin sets it.
"""
import datetime

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from attendance.models import AttendanceSession, MeetingType
from members.models import Member, MemberFollowUpTask

from attendance.absence import AUTO_LOOKBACK_DAYS, FOLLOWUP_DUE_IN_DAYS  # noqa: F401

HOURS_AFTER_START = 3
# A session whose headcount was saved early is still checked, for this
# many days after it, so switching this on never reaches back to old
# services and floods shepherds with tasks for months ago.
FILLED_LOOKBACK_DAYS = AUTO_LOOKBACK_DAYS


class Command(BaseCommand):
    help = "Finds sessions past their absence-check threshold and creates follow-up tasks for members not checked in."

    def handle(self, *args, **options):
        now = timezone.now()
        # Pending sessions as before. A session whose headcount was saved
        # before the check ran was skipped for good, so nobody absent from
        # it was ever followed up (found 17 Oct 2026). It is checked too,
        # when at least one member was checked in by name, which shows the
        # names were taken; a headcount alone says nothing about who came.
        recent = timezone.localdate() - datetime.timedelta(days=FILLED_LOOKBACK_DAYS)
        candidates = AttendanceSession.objects.filter(
            Q(status=AttendanceSession.Status.PENDING)
            | Q(status=AttendanceSession.Status.FILLED, date__gte=recent,
                attendees__member__isnull=False),
            meeting_type__counts_for_absence=True,
            meeting_type__start_time__isnull=False,
        ).distinct().select_related("meeting_type", "location")

        sessions_checked = 0
        tasks_created = 0

        for session in candidates:
            session_start = timezone.make_aware(
                datetime.datetime.combine(session.date, session.meeting_type.start_time)
            )
            threshold = session_start + datetime.timedelta(hours=HOURS_AFTER_START)
            if now < threshold:
                continue  # not time yet , real service may still be in progress

            created = self._process_session(session)
            sessions_checked += 1
            tasks_created += created

        self.stdout.write(self.style.SUCCESS(
            f"Checked {sessions_checked} session(s) past threshold, created {tasks_created} follow-up task(s)."
        ))

    def _process_session(self, session):
        # Only the people expected at the meeting, once per service, and
        # never stacked on an open follow-up: the rules live in absence.py,
        # shared with "Follow up those not ticked".
        from attendance.absence import create_tasks, plan
        return create_tasks(session, plan(session)["to_follow_up"])
