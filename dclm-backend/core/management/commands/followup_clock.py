from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Runs the follow-up clock once: reminders, reasons, the Review list, late decisions, attendance falling."

    def handle(self, *args, **options):
        from core.followup_clock import run
        self.stdout.write(run())
