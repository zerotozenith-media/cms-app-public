"""
Add the church records that were missing after the data load (Kay, 6 October 2026):

  - the July GCK, "The Season of Divine Turnaround", 29 July to 2 August 2026;
  - September's Ministers' Renewal, 28 September 2026;
  - the workers and the worker in training.

    python manage.py add_missing_church_data          checks and lists, keeps nothing
    python manage.py add_missing_church_data --yes    applies it, all at once or not at all

Anything already in the app is left alone, so it is safe to run after some
sessions were added by hand, or to run twice.
"""
import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

THEME = "The Season of Divine Turnaround"
# GCK days sent by Kay: brothers, sisters, boys and girls (children).
JULY_GCK = [("2026-07-29", 8, 4, 4, 2), ("2026-07-30", 6, 4, 3, 1), ("2026-07-31", 9, 4, 3, 2),
            ("2026-08-01", 5, 3, 3, 1), ("2026-08-02", 6, 4, 4, 2)]
RENEWAL = ("2026-09-28", 4, 2)
WORKERS = [("Chinedu", "Uguru"), ("Chinwendu", "Uguru"), ("Gloria", "Afari"), ("Kwabena", "Afari")]
TRAINEES = [("Henry", "Ashu")]


class Rollback(Exception):
    pass


class Command(BaseCommand):
    help = "Add the July GCK, September's Ministers' Renewal and the workers' categories."

    def add_arguments(self, p):
        p.add_argument("--location", default="bahrain", help="Location id, Bahrain HQ by default.")
        p.add_argument("--yes", action="store_true", help="Really apply. Without it, nothing is kept.")

    def handle(self, *a, location, yes, **o):
        from attendance.models import AttendanceSession, MeetingType
        from core.models import Location
        from members.models import Member, MemberCategoryHistory
        loc = Location.objects.filter(id=location).first()
        gck = MeetingType.objects.filter(id="gck").first() or MeetingType.objects.filter(name__icontains="Global Crusade").first()
        mrc = MeetingType.objects.filter(id="min-renewal").first() or MeetingType.objects.filter(name__icontains="Renewal").first()
        if not (loc and gck and mrc):
            raise CommandError("The location, GCK or Ministerial Renewal is not set up. Nothing was changed.")
        out = self.stdout.write
        out(f"{'Applying' if yes else 'Checking (nothing will be kept)'} for {loc.name}\n")
        try:
            with transaction.atomic():
                def session(mt, date, edition, **counts):
                    s = AttendanceSession.objects.filter(meeting_type=mt, location=loc, date=date, fellowship=None).first()
                    if s and s.status == "filled":
                        out(f"  Already there, left alone: {mt.name}, {date}")
                        return
                    fields = {"mode": "online", "status": "filled", "edition_name": edition, **counts}
                    if s:
                        for k, v in fields.items():
                            setattr(s, k, v)
                        s.save()
                    else:
                        AttendanceSession.objects.create(meeting_type=mt, location=loc, date=date, **fields)
                    out(f"  Added: {mt.name}, {date}, {sum(counts.values())} people")
                for date, men, women, boys, girls in JULY_GCK:
                    session(gck, date, THEME, online_men=men, online_women=women, online_children_boys=boys, online_children_girls=girls)
                date, men, women = RENEWAL
                session(mrc, date, "", online_men=men, online_women=women)
                for names, category in ((WORKERS, "Worker"), (TRAINEES, "Worker in Training")):
                    for first, surname in names:
                        m = Member.objects.filter(location=loc, first_name__iexact=first, surname__iexact=surname).first()
                        if not m:
                            raise CommandError(f"No member {first} {surname} at {loc.name}. Nothing was changed.")
                        if m.category == category:
                            out(f"  Already {category}, left alone: {first} {surname}")
                            continue
                        MemberCategoryHistory.objects.create(member=m, from_category=m.category, to_category=category,
                                                             changed_date=timezone.localdate())
                        old, m.category = m.category, category
                        m.save(update_fields=["category"])
                        out(f"  Moved: {first} {surname}, {old} to {category}")
                if not yes:
                    raise Rollback
        except Rollback:
            out("\nChecked. Nothing was kept. Run again with --yes to apply.")
            return
        out(self.style.SUCCESS("\nApplied."))
