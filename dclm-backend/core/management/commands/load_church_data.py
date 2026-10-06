"""
Load the church's own records, which travel inside this update: the July to
September 2026 monthly reports, the members, the newcomers and the Facebook
advert contacts, with every correction Kay approved already applied.

    python manage.py load_church_data          checks everything, keeps nothing
    python manage.py load_church_data --yes    loads it, all at once or not at all

Run clear_demo_data --yes first. A month already loaded, or a phone number
already in the app, is refused, so nothing can be loaded twice.
"""
import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "importers", "data")


class Command(BaseCommand):
    help = "Load the church's July to September 2026 records that come with this update."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Really load. Without it, nothing is kept.")

    def handle(self, *args, yes=False, **opts):
        f = lambda name: os.path.join(DATA, name)
        args = ["import_church_data",
                "--reports", f("report-2026-07.csv"), f("report-2026-08.csv"), f("report-2026-09.csv"),
                "--people", f("people.csv"), "--newcomers", f("newcomers.csv"), "--contacts", f("contacts.csv")]
        if yes:
            args.append("--yes")
        call_command(*args, stdout=self.stdout, stderr=self.stderr)
