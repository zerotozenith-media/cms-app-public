"""
Checks a server is actually ready before the church starts using it.

Replaces the manual go-live checklist with something that tests each
item rather than asking someone to confirm it. Several of these fail
silently in ways that look like the software is broken: no scheduled
absence check means no follow-up tasks ever appear, and missing PDF
libraries only surface when someone tries to generate a monthly report.

Exits non-zero if anything important is wrong, so it can be used in a
deployment pipeline.
"""
import os
import shutil
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from accounts.models import User
from attendance.models import MeetingType


class Command(BaseCommand):
    help = "Check this server is ready for the church to use."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.problems = []
        self.warnings = []

    def ok(self, message):
        self.stdout.write(self.style.SUCCESS(f"  ok      {message}"))

    def warn(self, message, advice):
        self.warnings.append((message, advice))
        self.stdout.write(self.style.WARNING(f"  note    {message}"))

    def bad(self, message, advice):
        self.problems.append((message, advice))
        self.stdout.write(self.style.ERROR(f"  problem {message}"))

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\nChecking this server\n"))

        self.check_settings()
        self.check_database()
        self.check_pdf_libraries()
        self.check_accounts()
        self.check_scheduled_jobs()
        self.check_meeting_setup()
        self.check_version_11()
        self.check_email()
        self.check_backups()

        self.stdout.write("")
        if self.problems:
            self.stdout.write(self.style.ERROR(
                f"{len(self.problems)} problem(s) to fix before going live:\n"))
            for message, advice in self.problems:
                self.stdout.write(f"  {message}\n      {advice}\n")
        if self.warnings:
            self.stdout.write(self.style.WARNING(
                f"{len(self.warnings)} thing(s) worth knowing:\n"))
            for message, advice in self.warnings:
                self.stdout.write(f"  {message}\n      {advice}\n")
        if not self.problems and not self.warnings:
            self.stdout.write(self.style.SUCCESS("Everything checked out. Ready to go.\n"))
        elif not self.problems:
            self.stdout.write(self.style.SUCCESS("Nothing blocking. Ready to go.\n"))

        if self.problems:
            raise SystemExit(1)

    # ---------------------------------------------------------------- checks

    def check_settings(self):
        if settings.DEBUG:
            self.bad(
                "DEBUG is on",
                "Set DJANGO_SETTINGS_MODULE=config.settings.production in .env. "
                "With DEBUG on, an error page shows your settings to whoever triggered it.",
            )
        else:
            self.ok("DEBUG is off")

        key = settings.SECRET_KEY
        if not key or len(key) < 40 or "change" in key.lower() or "insecure" in key.lower():
            self.bad(
                "DJANGO_SECRET_KEY looks like a placeholder",
                'Generate one: python3 -c "import secrets; print(secrets.token_urlsafe(64))"',
            )
        else:
            self.ok("secret key is set")

        if not settings.ALLOWED_HOSTS or settings.ALLOWED_HOSTS == ["*"]:
            self.bad(
                "DJANGO_ALLOWED_HOSTS is not set to your domain",
                "Set it to the domain people actually type, e.g. cms.dclm-bh.org",
            )
        else:
            self.ok(f"allowed hosts: {', '.join(settings.ALLOWED_HOSTS)}")

        if getattr(settings, "SECURE_SSL_REDIRECT", False):
            self.ok("HTTPS is enforced")
        else:
            self.warn(
                "HTTPS is not enforced",
                "Expected on production settings. Run certbot if you have not yet.",
            )

        if not getattr(settings, "APP_BASE_URL", ""):
            self.warn(
                "APP_BASE_URL is empty",
                "Notification emails will send without a link back to the app. "
                "Set it to https://your-domain in .env.",
            )
        else:
            self.ok("app URL set for email links")

    def check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            engine = connection.settings_dict["ENGINE"]
            if "sqlite" in engine:
                self.bad(
                    "still using SQLite",
                    "Set DATABASE_URL to your PostgreSQL connection string. SQLite "
                    "will not cope with several people using the system at once.",
                )
            else:
                self.ok("database reachable, PostgreSQL")
        except Exception as exc:
            self.bad(f"cannot reach the database: {exc}", "Check DATABASE_URL in .env.")

    def check_pdf_libraries(self):
        """ReportLab is pure Python, so this should never fail once
        requirements are installed. Checked anyway because a broken
        report only surfaces when someone tries to generate one."""
        try:
            import reportlab  # noqa: F401
            self.ok("PDF generation available, monthly reports will work")
        except Exception:
            self.bad(
                "PDF generation will fail",
                "pip install -r requirements.txt",
            )

    def check_accounts(self):
        count = User.objects.filter(is_active=True).count()
        if count == 0:
            self.bad(
                "no user accounts exist",
                "Run: python manage.py bootstrap_admin --email you@church.org --password ...",
            )
        else:
            self.ok(f"{count} active account(s)")

    def check_scheduled_jobs(self):
        """
        The single most common reason the system looks broken while being
        entirely functional.

        Judged by evidence rather than by a crontab. On Azure App Service the
        jobs are started from outside, by GitHub Actions or an Azure Function
        calling /api/tasks/run/, and every such run is written to the audit
        log. This used to look only for a crontab, so a site whose jobs ran
        perfectly from GitHub was told they were not scheduled.
        """
        from datetime import timedelta
        from django.utils import timezone
        from accounts.models import AuditLog

        out = ""
        crontab = shutil.which("crontab")
        if crontab:
            try:
                out = subprocess.run([crontab, "-l"], capture_output=True, text=True, timeout=10).stdout
            except Exception:
                out = ""

        now = timezone.now()

        def age(ts):
            hours = (now - ts).total_seconds() / 3600
            return f"{int(hours * 60)} minutes" if hours < 1 else (
                f"{int(hours)} hours" if hours < 48 else f"{int(hours // 24)} days")

        jobs = [
            ("check_absences", "the absence check", "hourly", timedelta(hours=3),
             "Without it no follow-up task is ever created and the feature looks broken."),
            ("generate_recurring_sessions", "weekly session creation", "daily", timedelta(hours=50),
             "Without it no attendance sessions appear each week."),
        ]
        for command, label, how_often, allowed, consequence in jobs:
            if command in out:
                self.ok(f"{label} is scheduled on this server")
                continue
            runs = AuditLog.objects.filter(action="Scheduled task", entity_name=command)
            latest = runs.first()
            good = runs.exclude(details__startswith="Failed").first()
            if latest and latest.details.startswith("Failed"):
                self.bad(f"{label} failed the last time it ran, {age(latest.timestamp)} ago",
                         f"{latest.details[:200]} {consequence}")
            elif good and now - good.timestamp <= allowed:
                self.ok(f"{label} runs from an outside scheduler, last {age(good.timestamp)} ago")
            elif good:
                self.bad(f"{label} last ran {age(good.timestamp)} ago, but should run {how_often}",
                         "Check the scheduler that calls /api/tasks/run/: the GitHub Actions "
                         "workflow may be paused or disabled, or the Azure Function stopped. "
                         f"{consequence}")
            else:
                self.bad(f"{label} has never run",
                         "Nothing has called it. Set up one scheduler from deploy/: the GitHub "
                         "Actions workflow, the Azure Function, or crontab.example on a server. "
                         f"{consequence}")

        for command, label in [("send_followup_digests", "shepherd digests"),
                               ("send_leadership_summary", "the leadership summary")]:
            if command in out or AuditLog.objects.filter(action="Scheduled task", entity_name=command).exists():
                self.ok(f"{label} are scheduled" if command.endswith("s") else f"{label} is scheduled")

    def check_meeting_setup(self):
        tracked = MeetingType.objects.filter(counts_for_absence=True)
        if not tracked.exists():
            self.warn(
                "no meeting counts toward absence follow-up",
                "Until one does, no follow-up tasks will be created. Switch it on in "
                "Admin, Meeting Types, usually for the main Sunday or Friday service.",
            )
            return

        without_time = tracked.filter(start_time__isnull=True)
        if without_time.exists():
            names = ", ".join(m.name for m in without_time)
            self.bad(
                f"tracked meeting with no start time: {names}",
                "The absence check measures from the start time, so these are never "
                "checked. Set a start time in Admin, Meeting Types.",
            )
        else:
            self.ok(f"{tracked.count()} meeting(s) tracked for absence, all with start times")

    def check_version_11(self):
        """
        What the version 11 data steps could not settle on their own.

        Each is reported with what a person needs to do, rather than
        guessed at, because the right answer depends on the church.
        """
        from django.utils import timezone
        from attendance.models import AttendanceSession, Fellowship
        from members.models import Member
        from newcomers.models import Newcomer

        weekly = MeetingType.objects.filter(frequency="weekly")
        bad_days = [m for m in weekly if m.day not in MeetingType.WEEKDAYS]
        if bad_days:
            self.bad(
                "weekly meeting with a day the system cannot read: "
                + ", ".join(f"{m.name} ({m.day or 'blank'})" for m in bad_days),
                "No sessions are created for these. Choose the day in the Day column, "
                "in Admin, Meeting Types and Households.",
            )
        else:
            self.ok(f"every weekly meeting has a readable day ({weekly.count()})")

        unlinked = Fellowship.objects.filter(is_active=True, meeting_type__isnull=True)
        if unlinked.exists():
            self.bad(
                "house fellowship not linked to a meeting: "
                + ", ".join(f.name for f in unlinked),
                "It gets no weekly session of its own. Set its meeting in Django admin, "
                "or re-add it in Admin, Meeting Types and Households.",
            )
        elif Fellowship.objects.filter(is_active=True).exists():
            self.ok("house fellowships and where they meet: " + ", ".join(
                f"{f.name} ({f.location.name if f.location else 'every location'})"
                for f in Fellowship.objects.filter(is_active=True).select_related("location")
                .order_by("name")))

        collecting = MeetingType.objects.filter(collects_offering=True)
        if not collecting.exists():
            self.warn(
                "no meeting is set to collect an offering",
                "The session form will not ask for one anywhere. Tick the meetings that "
                "collect in Admin, Meeting Types and Households.",
            )
        else:
            self.ok("meetings collecting an offering: "
                    + ", ".join(m.name for m in collecting.order_by("name")))

        converted = Newcomer.objects.filter(stage=Newcomer.Stage.MEMBER)
        missing = [n for n in converted if not Member.objects.filter(from_newcomer=n).exists()]
        if missing:
            self.warn(
                f"{len(missing)} newcomer(s) shown as members have no member record",
                "Run: python manage.py reconcile_converted_members  to see what it would "
                "do, then again with --apply.",
            )
        elif converted.exists():
            self.ok("every newcomer at the Member stage has a member record")

        blank = Member.objects.filter(phone="").count()
        if blank:
            self.bad(
                f"{blank} member(s) stored with an empty phone number",
                "Run: python manage.py migrate  The version 11 migration converts these.",
            )

        # An upcoming session for a fellowship meeting, with no fellowship,
        # at a location that now has fellowships of its own, would sit
        # beside the per-fellowship sessions on the same evening.
        fellowship_meetings = Fellowship.objects.filter(
            is_active=True, meeting_type__isnull=False).values_list("meeting_type_id", flat=True)
        with_own = set(Fellowship.objects.filter(is_active=True, location__isnull=False)
                       .values_list("location_id", flat=True))
        stray = AttendanceSession.objects.filter(
            meeting_type_id__in=set(fellowship_meetings), fellowship__isnull=True,
            location_id__in=with_own, date__gte=timezone.localdate())
        if stray.exists():
            self.warn(
                f"{stray.count()} upcoming fellowship session(s) with no fellowship set: "
                + ", ".join(f"{s.date} at {s.location.name}" for s in stray.select_related("location")[:5]),
                "Each fellowship now gets its own session, so these would appear beside them. "
                "Open each in Attendance and delete it with the bin at the top right of the "
                "session card. Anything recorded on it should first be re-entered on the right "
                "fellowship's session.",
            )
        leftover = AttendanceSession.objects.filter(
            meeting_type_id__in=set(fellowship_meetings), fellowship__isnull=True,
            status="pending", date__lt=timezone.localdate()).count()
        if leftover:
            self.warn(
                f"{leftover} past fellowship session(s) with no fellowship, never filled in",
                "Left from version 10, which made one session per Friday. They count as "
                "not filled in on the dashboard. Delete them in Attendance if they will "
                "never be completed.",
            )

    def check_email(self):
        if not getattr(settings, "NOTIFICATIONS_ENABLED", False):
            self.warn(
                "email notifications are off",
                "Fine if the church does not want them. To switch on, set "
                "NOTIFICATIONS_ENABLED=True and the EMAIL_ settings in .env.",
            )
            return
        if not getattr(settings, "EMAIL_HOST_PASSWORD", ""):
            self.bad(
                "notifications are on but no email password is set",
                "Add your provider's API key as EMAIL_HOST_PASSWORD in .env.",
            )
        else:
            self.ok("email configured")

    def check_backups(self):
        """A managed Azure database is backed up by Azure, with nothing to
        schedule. This used to call that "no backup is scheduled"."""
        host = (connection.settings_dict.get("HOST") or "").lower()
        if host.endswith(".postgres.database.azure.com"):
            self.ok("the database is on Azure Database for PostgreSQL, which backs it up automatically")
            self.warn(
                "check how long Azure keeps the backups",
                "In the Azure portal, open the database server, then Backup and restore. "
                "Pastoral records span years, so keep them as long as the plan allows.",
            )
            return
        crontab = shutil.which("crontab")
        out = ""
        if crontab:
            try:
                out = subprocess.run([crontab, "-l"], capture_output=True, text=True, timeout=10).stdout
            except Exception:
                pass
        if "pg_dump" in out:
            self.ok("nightly database backup is scheduled")
            self.warn(
                "backups are on this server only",
                "Copy them elsewhere. A backup on the same machine does not survive "
                "that machine failing, and it holds years of pastoral records.",
            )
        else:
            self.bad(
                "no database backup is scheduled",
                "The database holds everything. See deploy/crontab.example.",
            )
