"""
Load the church's real records: the monthly reports and the people list.

    python manage.py import_church_data --reports July.csv August.csv September.csv --people DCLMBH.csv
        checks everything and shows what would be loaded, then undoes it all
    ... --yes
        loads it, all at once or not at all

Decisions taken with Kay: amounts in the reports are SAR and are divided by
10 to record BHD. Friday Worship numbers are in person, every other
meeting's are online. Giving is Cash, one entry per fund per service.
Expenses and testimonies are dated the last day of their month. Newcomers
start at Attending from July 2026, with messages not started, and came
through the Facebook advert unless Invited By names another person. Members are
General Members from July 2026, and each address becomes a household.
A month already loaded is refused, so nothing is loaded twice.
"""
import datetime
from collections import OrderedDict
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.importers.monthly_reports import parse
from core.importers.people import read_people, read_simple

START = datetime.date(2026, 7, 1)
CATEGORY = {"church administration": "Administration", "rent": "Rent", "transportation": "Transportation",
            "refreshments": "Refreshments", "charity": "Charity"}
ONLINE = {"men": "online_men", "women": "online_women", "youth_boys": "online_youth_boys", "youth_girls": "online_youth_girls",
          "children_boys": "online_children_boys", "children_girls": "online_children_girls"}


class Rollback(Exception):
    pass


def bhd(sar):
    return (Decimal(str(sar)) / 10).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


class Command(BaseCommand):
    help = "Load the monthly reports and the people list. Checks and undoes unless --yes is given."

    def add_arguments(self, p):
        p.add_argument("--reports", nargs="*", default=[], help="The monthly report CSV files.")
        p.add_argument("--people", help="The people CSV file.")
        p.add_argument("--newcomers", help="The newcomers list: Name, Phone, Gender, Invited by.")
        p.add_argument("--contacts", help="The Facebook advert contacts: Name, Phone, Gender, Invited by.")
        p.add_argument("--location", default="bahrain", help="Location id, Bahrain HQ by default.")
        p.add_argument("--yes", action="store_true", help="Really load. Without it, nothing is kept.")

    def handle(self, *a, reports, people, location, yes, newcomers=None, contacts=None, **o):
        from core.models import Location
        loc = Location.objects.filter(id=location).first()
        if not loc:
            raise CommandError(f"No location with id {location!r}.")
        self.out = self.stdout.write
        self.out(f"{'Loading' if yes else 'Checking (nothing will be kept)'} for {loc.name}\n")
        try:
            with transaction.atomic():
                for path in reports:
                    self.load_month(path, loc)
                if people:
                    self.load_people(people, loc)
                if newcomers:
                    self.load_newcomers(newcomers, loc)
                if contacts:
                    self.load_contacts(contacts, loc)
                if not yes:
                    raise Rollback
        except Rollback:
            self.out("\nChecked. Nothing was kept. Run again with --yes to load.")
            return
        self.out(self.style.SUCCESS("\nLoaded."))

    # ----------------------------------------------------------------- months
    def load_month(self, path, loc):
        from attendance.models import AttendanceSession, MeetingType
        from finance.models import Expense, ExpenseCategory, Fund, Giving, PaymentMethod
        from reports.models import Service, Testimony
        dates = []
        import csv
        from core.importers.monthly_reports import d
        for r in csv.reader(open(path, newline="")):
            for c in r:
                x = d(c)
                if x:
                    dates.append(x)
        month = max(set(m for m in (x.month for x in dates)), key=[x.month for x in dates].count)
        rec = parse(path, month)
        name = datetime.date(2026, month, 1).strftime("%B %Y")
        if Giving.objects.filter(location=loc, date__year=2026, date__month=month).exists() or \
           AttendanceSession.objects.filter(location=loc, date__year=2026, date__month=month, status="filled").exists():
            raise CommandError(f"{name} already has records at {loc.name}. Nothing was loaded.")
        meetings = {m.name: m for m in MeetingType.objects.all()}
        missing = sorted({s["meeting"] for s in rec["sessions"]} - set(meetings))
        if missing:
            raise CommandError(f"{name}: these meetings are not set up in Admin: {', '.join(missing)}")
        people = 0
        for s in rec["sessions"]:
            mt = meetings[s["meeting"]]
            counts = {k: int(s[k]) for k in ONLINE}
            fields = {"status": "filled", "mode": s["mode"], "new_comers": int(s["newcomers"]), "new_converts": int(s["new_converts"]),
                      "edition_name": s["edition_name"], "edition_place": s["edition_place"]}
            if s["mode"] == "online":
                fields.update({ONLINE[k]: v for k, v in counts.items()})
                fields.update({k: 0 for k in ONLINE})
            else:
                fields.update(counts)
            AttendanceSession.objects.update_or_create(meeting_type=mt, location=loc, date=s["date"], fellowship=None, defaults=fields)
            people += sum(counts.values()) + int(s["newcomers"]) + int(s["new_converts"])
        cash = PaymentMethod.objects.get(name__iexact="Cash")
        funds = {f.name.lower(): f for f in Fund.objects.all()}
        gtotal = Decimal("0")
        for g in rec["giving"]:
            fund = funds.get(g["fund"].lower())
            if not fund:
                raise CommandError(f"{name}: the fund {g['fund']!r} is not set up in Admin.")
            amt = bhd(g["sar"]); gtotal += amt
            Giving.objects.create(date=g["date"], fund=fund, method=cash, amount=amt, location=loc)
        etotal = Decimal("0")
        for e in rec["expenses"]:
            low = e["category"].lower()
            label = next((v for k, v in CATEGORY.items() if k in low), e["category"].strip().title())
            cat, made = ExpenseCategory.objects.get_or_create(name=label)
            if made:
                self.out(f"  New expense category: {label}")
            amt = bhd(e["sar"]); etotal += amt
            Expense.objects.create(date=e["date"], category=cat, amount=amt, location=loc, description=e["category"])
        svc = Service.objects.filter(name__icontains="Friday Worship").first() or Service.objects.first()
        for t in rec["testimonies"]:
            Testimony.objects.create(date=t["date"], service=svc, text=t["text"])
        self.out(f"{name}: {len(rec['sessions'])} sessions ({people} attendance), giving BHD {gtotal:,.3f}, "
                 f"expenses BHD {etotal:,.3f}, net BHD {gtotal - etotal:,.3f}, testimonies {len(rec['testimonies'])}")

    # ----------------------------------------------------------------- people
    def load_people(self, path, loc):
        from members.models import Household, Member
        from newcomers.models import Newcomer, NewcomerSource
        rows = read_people(path)
        phones = [p["phone"] for p in rows if p["phone"]]
        if len(phones) != len(set(phones)):
            raise CommandError("The people list has the same phone number twice. Nothing was loaded.")
        taken = set(Member.objects.exclude(phone="").values_list("phone", flat=True)) | set(Newcomer.objects.exclude(phone="").values_list("phone", flat=True))
        clash = [p["name"] for p in rows if p["phone"] in taken]
        if clash:
            raise CommandError(f"Already in the app, by phone: {', '.join(clash)}. Nothing was loaded.")
        # Kay: every newcomer came through the Facebook advert, except those
        # whose Invited By names another person.
        fb, _ = NewcomerSource.objects.get_or_create(name="Facebook advert")
        invited = NewcomerSource.objects.filter(name__iexact="Invited by a member").first() or \
            NewcomerSource.objects.create(name="Invited by a member")
        def source(inv):
            v = inv.lower().strip()
            if v in ("", "self", "na", "n/a") or "facebook" in v or v.startswith("fb"):
                return fb, ""
            return invited, inv
        homes = OrderedDict()
        for p in rows:
            if p["status"] == "member":
                homes.setdefault(p["address"].lower() or p["name"].lower(), []).append(p)
        members = newcomers = 0
        for key, group in homes.items():
            surname = group[0]["name"].split()[-1]
            hh = Household.objects.create(name=f"{surname} Household", address=group[0]["address"])
            for p in group:
                parts = p["name"].split()
                Member.objects.create(first_name=parts[0], surname=parts[-1] if len(parts) > 1 else "", other_names=" ".join(parts[1:-1]),
                                      gender=p["gender"], phone=p["phone"], email=p["email"], category="General Member",
                                      location=loc, joined_date=START, household=hh)
                members += 1
        for p in rows:
            if p["status"] != "newcomer":
                continue
            s, inv = source(p["invited_by"])
            n = Newcomer.objects.create(name=p["name"], source=s, stage="attending", location=loc, stage_since=START,
                                        address=p["address"], phone=p["phone"], email=p["email"], gender=p["gender"],
                                        age_group="20_and_above" if p["adult"] else "", keep_in_touch=False, invited_by_name=inv,
                                        created_at=datetime.datetime(2026, 7, 1, 9, 0, tzinfo=datetime.timezone.utc))
            newcomers += 1
        self.out(f"People: {members} members in {len(homes)} households, {newcomers} newcomers (messages not started)")

    # ------------------------------------------------------------ shared rules
    def _taken(self):
        from enquiries.models import Enquiry
        from members.models import Member
        from newcomers.models import Newcomer
        return (set(Member.objects.exclude(phone="").values_list("phone", flat=True))
                | set(Newcomer.objects.exclude(phone="").values_list("phone", flat=True))
                | set(Enquiry.objects.exclude(phone="").values_list("phone", flat=True)))

    def _check(self, rows, what):
        phones = [p["phone"] for p in rows if p["phone"]]
        if len(phones) != len(set(phones)):
            raise CommandError(f"The {what} list has the same phone number twice. Nothing was loaded.")
        clash = [p["name"] for p in rows if p["phone"] and p["phone"] in self._taken()]
        if clash:
            raise CommandError(f"Already in the app, by phone ({what}): {', '.join(clash)}. Nothing was loaded.")

    # -------------------------------------------------------------- newcomers
    def load_newcomers(self, path, loc):
        from newcomers.models import Newcomer, NewcomerSource
        rows = read_simple(path)
        self._check(rows, "newcomers")
        fb, _ = NewcomerSource.objects.get_or_create(name="Facebook advert")
        invited = NewcomerSource.objects.filter(name__iexact="Invited by a member").first() or NewcomerSource.objects.create(name="Invited by a member")
        n = 0
        for p in rows:
            v = p["invited_by"].lower()
            by_person = v not in ("", "self", "na", "n/a") and "facebook" not in v and not v.startswith("fb")
            Newcomer.objects.create(name=p["name"], source=invited if by_person else fb, stage="attending", location=loc, stage_since=START,
                                    phone=p["phone"], gender=p["gender"] if p["gender"] in ("Male", "Female") else "",
                                    keep_in_touch=False, invited_by_name=p["invited_by"] if by_person else "",
                                    created_at=datetime.datetime(2026, 7, 1, 9, 0, tzinfo=datetime.timezone.utc))
            n += 1
        self.out(f"Newcomers list: {n} newcomers (messages not started)")

    # --------------------------------------------------------------- contacts
    def load_contacts(self, path, loc):
        """Kay: people reached through the Facebook advert who have not visited
        yet are online contacts, under the Facebook advert campaign."""
        from enquiries.models import Campaign, Enquiry, EnquirySource
        from followup.models import Enrolment
        rows = read_simple(path)
        self._check(rows, "contacts")
        src = EnquirySource.objects.filter(name__iexact="Facebook").first() or EnquirySource.objects.create(name="Facebook")
        camp, _ = Campaign.objects.get_or_create(name="Facebook advert", defaults={"source": src})
        when = datetime.datetime(2026, 7, 1, 9, 0, tzinfo=datetime.timezone.utc)
        n = 0
        for p in rows:
            e = Enquiry.objects.create(name=p["name"], source=src, phone=p["phone"], campaign=camp, stage="contacted",
                                       stage_since=START, received_at=when)
            # A new enquiry starts its message journey by itself. Loading 59 at
            # once would flood Today's messages, so they start not started.
            Enrolment.objects.filter(enquiry=e).delete()
            n += 1
        self.out(f"Contacts: {n} online contacts under the Facebook advert campaign (messages not started)")
