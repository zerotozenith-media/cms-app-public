"""
Emails each shepherd their outstanding follow-ups.

Scheduled to run the morning after a tracked service rather than every
day, because that is when absences actually appear. A daily email that
is usually empty teaches people to ignore it.

Deliberately sends nothing to a shepherd with no open tasks.
"""
import datetime

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from accounts.models import User
from accounts.names import display_name
from attendance.models import AttendanceSession
from core.digests import build_shepherd_digest
from core.notifications import send_notification
from members.models import MemberFollowUpTask


class Command(BaseCommand):
    help = "Email each shepherd their open follow-ups. Run the morning after a tracked service."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true",
            help="Send even if no tracked service happened yesterday.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show who would be emailed and what, without sending.",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()

        if not options["force"] and not self._tracked_service_recently(today):
            self.stdout.write(
                "No tracked service in the last day, so there is nothing new to report. "
                "Use --force to send anyway."
            )
            return

        open_tasks = (
            MemberFollowUpTask.objects
            .filter(done=False, assigned_to__isnull=False)
            .select_related("member", "assigned_to", "assigned_to__member")
        )

        by_shepherd = {}
        for task in open_tasks:
            by_shepherd.setdefault(task.assigned_to, []).append(task)

        sent = skipped = 0
        for shepherd, tasks in by_shepherd.items():
            if not shepherd.email:
                skipped += 1
                continue

            built = build_shepherd_digest(display_name(shepherd), tasks, today=today)
            if not built:
                continue
            subject, text, html = built

            if options["dry_run"]:
                self.stdout.write(f"  would email {shepherd.email}: {subject}")
                sent += 1
                continue

            if send_notification(to=shepherd.email, subject=subject, text_body=text, html_body=html):
                sent += 1
            else:
                skipped += 1

        unassigned = MemberFollowUpTask.objects.filter(done=False, assigned_to__isnull=True).count()

        verb = "Would have emailed" if options["dry_run"] else "Emailed"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {sent} shepherd(s). {skipped} skipped."
        ))
        if unassigned:
            self.stdout.write(self.style.WARNING(
                f"{unassigned} open follow-up(s) have nobody assigned, so nobody was told about them."
            ))

    def _tracked_service_recently(self, today):
        """Did a meeting that counts toward absence follow-up happen in
        the last day? That is what makes a digest worth sending."""
        return AttendanceSession.objects.filter(
            meeting_type__counts_for_absence=True,
            date__gte=today - datetime.timedelta(days=1),
            date__lte=today,
        ).exists()
