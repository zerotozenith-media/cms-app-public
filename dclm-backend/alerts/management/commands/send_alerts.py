from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send the morning and weekly alerts that are due. The hourly scheduled job does this by itself."

    def handle(self, *args, **options):
        from alerts.scheduled import run
        self.stdout.write(run())
