"""
Creates the first administrator, plus the location and role it needs.

Exists so deploy/install.sh can do it without a human pasting a shell
snippet. Idempotent: if the account already exists it says so and
changes nothing, which matters because the installer is safe to re-run.

Reads the email and password from the environment rather than command
arguments, so the password does not end up in shell history or show in
the process list.
"""
import os

from django.core.management.base import BaseCommand

from accounts.models import Role, RolePermission, User
from core.models import Location

MODULES = [
    "members", "attendance", "newcomers", "finance",
    "goals", "reports", "outreach", "admin",
]


class Command(BaseCommand):
    help = "Create the first administrator account, with the location and role it needs."

    def add_arguments(self, parser):
        parser.add_argument("--email", default=os.environ.get("DJANGO_ADMIN_EMAIL", ""))
        parser.add_argument("--password", default=os.environ.get("DJANGO_ADMIN_PASSWORD", ""))

    def handle(self, *args, **options):
        email = options["email"].strip()
        password = options["password"]

        if not email or not password:
            self.stderr.write(
                "Set DJANGO_ADMIN_EMAIL and DJANGO_ADMIN_PASSWORD, or pass "
                "--email and --password."
            )
            return

        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(self.style.WARNING(
                f"    note {email} already exists, leaving it alone."
            ))
            return

        # Bahrain is the core location and cannot be deleted later.
        location, created = Location.objects.get_or_create(
            id="bahrain", defaults={"name": "Bahrain", "is_core": True},
        )
        if created:
            self.stdout.write("    ok Bahrain location created")

        role, created = Role.objects.get_or_create(name="Administrator")
        if created:
            self.stdout.write("    ok Administrator role created")

        for module in MODULES:
            RolePermission.objects.get_or_create(
                role=role, module=module,
                defaults=dict(can_view=True, can_create=True, can_edit=True, can_delete=True),
            )

        User.objects.create_user(email=email, password=password, role=role)
        self.stdout.write(self.style.SUCCESS(f"    ok administrator {email} created"))
        self.stdout.write("    note tell them to change that password after first login")
