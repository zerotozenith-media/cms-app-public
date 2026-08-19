"""
Weekly church-level follow-up summary for leadership.

Unlike the shepherd digest, this sends even when the numbers are good:
"nothing outstanding" is worth knowing once a week, and it confirms the
notifications are still working.

Goes to every active user whose role can view the admin module, which is
the closest thing the system has to "leadership" without inventing a new
flag for it.
"""
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from accounts.permissions import user_can_view_module
from core.digests import build_leadership_summary
from core.notifications import send_notification
from members.models import MemberFollowUpTask


class Command(BaseCommand):
    help = "Email leadership a weekly follow-up summary."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Show what would be sent, without sending.")

    def handle(self, *args, **options):
        today = timezone.localdate()
        week_ago = today - datetime.timedelta(days=7)

        open_qs = MemberFollowUpTask.objects.filter(done=False)
        stats = {
            "open": open_qs.count(),
            "overdue": open_qs.filter(due_date__lt=today).count(),
            "unassigned": open_qs.filter(assigned_to__isnull=True).count(),
            "completed_this_week": MemberFollowUpTask.objects.filter(
                done=True, contact_date__gte=week_ago,
            ).count(),
        }

        subject, text, html = build_leadership_summary(stats, today=today)

        recipients = [
            u for u in User.objects.filter(is_active=True).select_related("role", "member")
            if u.email and user_can_view_module(u, "admin")
        ]

        sent = 0
        for user in recipients:
            if options["dry_run"]:
                self.stdout.write(f"  would email {user.email}: {subject}")
                sent += 1
                continue
            if send_notification(to=user.email, subject=subject, text_body=text, html_body=html):
                sent += 1

        verb = "Would have emailed" if options["dry_run"] else "Emailed"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {sent} of {len(recipients)} leadership recipient(s). "
            f"Open: {stats['open']}, overdue: {stats['overdue']}, unassigned: {stats['unassigned']}."
        ))
