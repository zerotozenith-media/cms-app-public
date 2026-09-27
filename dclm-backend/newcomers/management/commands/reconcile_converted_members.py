"""
Give every newcomer at the Member stage their member record.

Before version 11, moving a newcomer's card to the Member column changed
the label only. The person showed as a member on the newcomer board and
was missing from the member roll. This finds each of them and puts it
right.

Somebody may already have typed them onto the roll by hand, with no link
to their newcomer record. Creating a second record for them would put the
same person on the roll twice, so each newcomer is first matched against
members who have no newcomer record of their own:

    by phone number, then by email, then by exact name, within the same
    location. One clear match is linked. More than one is reported and
    left for a person to decide. No match creates the record.

Nothing changes unless --apply is given. Run it without first and read
what it would do.
"""
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.audit import log_audit
from members.models import Member
from newcomers.models import Newcomer


def _digits(value):
    return re.sub(r"\D", "", value or "")[-8:]


def _split_name(name):
    parts = (name or "").strip().split()
    first = parts[0] if parts else (name or "")
    surname = " ".join(parts[1:]) if len(parts) > 1 else first
    return first, surname


def find_candidates(newcomer):
    """Members with no newcomer record who look like this person."""
    unlinked = Member.objects.filter(from_newcomer__isnull=True)
    pool = unlinked.filter(location=newcomer.location)

    # A phone number identifies the person wherever they are now, so it is
    # matched across every location. Somebody who relocated keeps it.
    phone = _digits(newcomer.phone)
    if len(phone) >= 7:
        by_phone = [m for m in unlinked.exclude(phone__isnull=True) if _digits(m.phone) == phone]
        if by_phone:
            return by_phone, "phone"

    if newcomer.email:
        by_email = list(pool.filter(email__iexact=newcomer.email.strip()))
        if by_email:
            return by_email, "email"

    first, surname = _split_name(newcomer.name)
    by_name = list(pool.filter(first_name__iexact=first, surname__iexact=surname))
    return by_name, "name" if by_name else ""


from newcomers.views import _shepherd_to_keep


class Command(BaseCommand):
    help = ("Give every newcomer at the Member stage a linked member record. "
            "Reports only, unless --apply is given.")

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true",
                            help="Make the changes. Without it, nothing is written.")

    def handle(self, *args, **options):
        apply = options["apply"]
        missing = [n for n in Newcomer.objects.filter(stage=Newcomer.Stage.MEMBER)
                   .select_related("location").order_by("name")
                   if not Member.objects.filter(from_newcomer=n).exists()]

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{len(missing)} newcomer(s) at the Member stage with no member record"
            f"{'' if apply else ' (report only, nothing will change)'}\n"))
        if not missing:
            self.stdout.write(self.style.SUCCESS("Nothing to do.\n"))
            return

        linked = created = ambiguous = 0
        for n in missing:
            candidates, how = find_candidates(n)
            if len(candidates) > 1:
                ambiguous += 1
                names = ", ".join(f"{m.full_name} (id {m.id})" for m in candidates)
                self.stdout.write(self.style.WARNING(
                    f"  decide  {n.name}: {len(candidates)} members match by {how}: {names}"))
                continue

            if candidates:
                m = candidates[0]
                self.stdout.write(f"  link    {n.name} to existing member {m.full_name} "
                                  f"(id {m.id}, matched by {how})")
                if apply:
                    with transaction.atomic():
                        Member.objects.filter(pk=m.pk).update(from_newcomer=n)
                        log_audit(None, "Linked to newcomer record", "Member", m.full_name,
                                  f"Reconciled at version 11, matched by {how}")
                linked += 1
            else:
                first, surname = _split_name(n.name)
                # Stored as nothing when blank: phone numbers are unique on the
                # roll, and an empty string would clash with the next one.
                phone = (n.phone or "").strip() or None
                if phone and Member.objects.filter(phone=phone).exists():
                    ambiguous += 1
                    owner = Member.objects.get(phone=phone)
                    self.stdout.write(self.style.WARNING(
                        f"  decide  {n.name}: phone {phone} already belongs to "
                        f"{owner.full_name} (id {owner.id}), who is linked to another "
                        f"newcomer record. Probably the same person registered twice."))
                    continue
                self.stdout.write(f"  create  {n.name}, joined {n.stage_since}")
                if apply:
                    with transaction.atomic():
                        Member.objects.create(
                            surname=surname, first_name=first,
                            phone=phone, email=n.email, location=n.location,
                            joined_date=n.stage_since,
                            category=Member.Category.GENERAL,
                            from_newcomer=n,
                            # Keep the shepherd they had as a newcomer, if
                            # they can shepherd members there.
                            assigned_to=_shepherd_to_keep(n),
                        )
                        log_audit(None, "Made a member", "Newcomer", n.name,
                                  "Member record created at version 11. The card had "
                                  "been moved to Member without one.")
                created += 1

        verb = "Done" if apply else "Would do"
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"{verb}: {linked} linked to an existing member, {created} created."))
        if ambiguous:
            self.stdout.write(self.style.WARNING(
                f"{ambiguous} left for a person to decide. Open each in Members, remove the "
                "duplicate, and run this again."))
        if not apply:
            self.stdout.write("Run again with --apply to make these changes.\n")
