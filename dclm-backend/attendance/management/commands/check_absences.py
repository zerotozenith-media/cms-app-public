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

from attendance.models import AttendanceSession
from members.models import Member, MemberFollowUpTask

HOURS_AFTER_START = 3
FOLLOWUP_DUE_IN_DAYS = 2


class Command(BaseCommand):
    help = "Finds sessions past their absence-check threshold and creates follow-up tasks for members not checked in."

    def handle(self, *args, **options):
        now = timezone.now()
        candidates = AttendanceSession.objects.filter(
            status=AttendanceSession.Status.PENDING,
            meeting_type__counts_for_absence=True,
            meeting_type__start_time__isnull=False,
        ).select_related("meeting_type", "location")

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
        roster = Member.objects.filter(location=session.location)
        checked_in_ids = set(session.attendees.values_list("member_id", flat=True))
        absentees = roster.exclude(id__in=checked_in_ids)

        created = 0
        for member in absentees:
            # Idempotency against re-running the command on the same
            # session , regardless of done status, this exact session's
            # absence for this exact member is only ever recorded once.
            already_processed = MemberFollowUpTask.objects.filter(
                member=member, missed_session=session,
            ).exists()
            if already_processed:
                continue

            # The confirmed "don't stack tasks" rule , a genuinely
            # different, still-open follow-up from an earlier absence
            # blocks a new one; a *resolved* earlier one does not.
            has_other_open_task = MemberFollowUpTask.objects.filter(
                member=member, done=False,
            ).exclude(missed_session=session).exists()
            if has_other_open_task:
                continue

            MemberFollowUpTask.objects.create(
                member=member,
                text=f"Missed {session.meeting_type.name} , check in",
                due_date=timezone.localdate() + datetime.timedelta(days=FOLLOWUP_DUE_IN_DAYS),
                assigned_to=member.assigned_to,
                missed_session=session,
                missed_meeting_name=session.meeting_type.name,
                missed_date=session.date,
            )
            created += 1

        return created
