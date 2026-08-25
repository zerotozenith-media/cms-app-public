"""
Creates the platforms a church is likely to be contacted through.

Without this an administrator opens the add-enquiry form to an empty
dropdown and cannot record anyone until they have worked out that
sources are configured elsewhere. Idempotent, so running it again after
someone has added their own does nothing.
"""
from django.core.management.base import BaseCommand

from enquiries.models import EnquirySource

DEFAULTS = [
    "Instagram",
    "WhatsApp",
    "Facebook",
    "TikTok",
    "Website contact form",
    "Phone call",
    "Referred by a member",
]


class Command(BaseCommand):
    help = "Create the default set of online enquiry sources."

    def handle(self, *args, **options):
        created = skipped = 0
        for name in DEFAULTS:
            _, was_created = EnquirySource.objects.get_or_create(name=name)
            if was_created:
                created += 1
                self.stdout.write(f"  Created: {name}")
            else:
                skipped += 1
        self.stdout.write(self.style.SUCCESS(
            f"Done. Created {created}, already present {skipped}."
        ))
