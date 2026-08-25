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
        """The single most common reason the system looks broken while
        being entirely functional."""
        crontab = shutil.which("crontab")
        if not crontab:
            self.warn(
                "cannot check the schedule, crontab not found",
                "If you schedule jobs another way, confirm check_absences and "
                "generate_recurring_sessions both run.",
            )
            return
        try:
            out = subprocess.run([crontab, "-l"], capture_output=True, text=True, timeout=10).stdout
        except Exception:
            out = ""

        if "check_absences" in out:
            self.ok("absence check is scheduled")
        else:
            self.bad(
                "the absence check is not scheduled",
                "Without it no follow-up task is ever created and the feature looks "
                "broken. See deploy/crontab.example.",
            )

        if "generate_recurring_sessions" in out:
            self.ok("weekly session creation is scheduled")
        else:
            self.bad(
                "weekly session creation is not scheduled",
                "Without it no attendance sessions appear each week. "
                "See deploy/crontab.example.",
            )

        if "send_followup_digests" in out:
            self.ok("shepherd digests are scheduled")

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
