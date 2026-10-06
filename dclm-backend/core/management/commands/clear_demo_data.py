"""
Clear the demo records before the church's real data is loaded.

Every record the app collects is removed: people, attendance, giving and
expenses, follow-ups, messages sent, testimonies, notes, reports and the
audit history. The app's setup is kept: accounts and roles, locations,
meetings and fellowships, funds and the other lists, goals, the message
bank and its plans. The demo advert campaigns and building project go too.

    python manage.py clear_demo_data            shows what would go, changes nothing
    python manage.py clear_demo_data --yes      clears, all at once or not at all
"""
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

# Children before parents, so nothing is held back by a link.
CLEAR = [
    "followup.StepDone", "followup.MessageLog", "followup.SavedMessage", "followup.Enrolment",
    "service.ServiceStanding",
    "attendance.AttendanceSessionMember", "attendance.AttendanceSession",
    "newcomers.NewcomerContactAttempt", "newcomers.NewcomerTask", "newcomers.NewcomerMilestone",
    "newcomers.NewcomerStatusHistory", "newcomers.PublicRegistrationAttempt",
    "enquiries.EnquiryTask", "enquiries.EnquiryStatusHistory",
    "members.MemberFollowUpTask", "members.MemberCategoryHistory",
    "enquiries.Enquiry", "enquiries.Campaign", "newcomers.Newcomer", "members.Member", "members.Household",
    "finance.RemittanceLine", "finance.Remittance", "finance.Giving", "finance.Expense", "finance.Project",
    "reports.Testimony", "reports.WeeklyNote", "reports.Report",
    "accounts.AuditLog", "accounts.LoginAttempt",
]
KEEP = [
    "accounts.User", "accounts.Role", "core.Location", "attendance.MeetingType", "attendance.Fellowship",
    "finance.Fund", "finance.PaymentMethod", "finance.ExpenseCategory",
    "enquiries.EnquirySource", "newcomers.NewcomerSource", "newcomers.MilestoneType",
    "goals.Goal", "reports.Service", "reports.Department", "followup.MessageTemplate", "followup.PlanStep",
]
SHOW_NAMES = []  # Kay confirmed the demo campaigns and project go too


class Command(BaseCommand):
    help = "Clear the demo records, keeping the app's setup. Shows what would go unless --yes is given."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Really clear. Without it, nothing changes.")

    def handle(self, *args, yes=False, **opts):
        out = self.stdout.write
        out("Will be cleared:" if yes else "Would be cleared (nothing changes without --yes):")
        total = 0
        for key in CLEAR:
            n = apps.get_model(key).objects.count()
            total += n
            if n:
                out(f"  {key:<40} {n}")
        out(f"  {'Total':<40} {total}")
        out("\nKept:")
        for key in KEEP:
            out(f"  {key:<40} {apps.get_model(key).objects.count()}")
        for key in SHOW_NAMES:
            names = [str(o) for o in apps.get_model(key).objects.all()[:10]]
            if names:
                out(f"  Check these are real, not demo: {key}: {', '.join(names)}")
        if not yes:
            out("\nNothing was changed. Run again with --yes to clear.")
            return
        with transaction.atomic():
            for key in CLEAR:
                apps.get_model(key).objects.all().delete()
        left = sum(apps.get_model(k).objects.count() for k in CLEAR)
        out(self.style.SUCCESS(f"\nCleared. Records left in the cleared areas: {left}. Setup kept as listed."))
