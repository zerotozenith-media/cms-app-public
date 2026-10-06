"""The data switch: clearing the demo records and loading the church's own (Kay)."""
import csv, io, os, tempfile
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import CommandError

from attendance.models import AttendanceSession, MeetingType
from core.tests_upgrade import Base
from enquiries.models import Campaign, Enquiry
from finance.models import Expense, Fund, Giving, PaymentMethod
from followup.models import Enrolment, MessageTemplate
from members.models import Household, Member
from newcomers.models import Newcomer, NewcomerSource
from reports.models import Service, Testimony


def report_csv(path):
    """A made-up July report in the church's layout."""
    g = [[""] * 42 for _ in range(40)]
    g[2][17] = "July 2026 GCK - Bahrain - A Made Up Theme"
    g[5][1] = "FRIDAY WORSHIP SERVICE"
    g[5][2:11] = ["17-Jul", "10", "6", "1", "1", "1", "2", "3", "24"]
    g[5][14], g[5][15] = "1000.00", "200.50"
    g[6][2:11] = ["24-Jul", "8", "4", "0", "1", "1", "1", "1", "16"]
    g[6][15] = "90.00"
    g[8][1] = "MONDAY BIBLE STUDY"
    g[8][2:11] = ["20-Jul", "5", "3", "1", "1", "0", "0", "0", "10"]
    g[22][2:6] = ["18-Jul", "4", "2", "6"]
    g[24][12], g[24][16] = "Rent", "1000.00"
    g[25][12], g[25][16] = "Church Administration", "250.00"
    g[33][20] = "God answered our prayers."
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(g)


def simple_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


class DataSwitchTestCase(Base):
    def setUp(self):
        super().setUp()
        for mid, name, day, lvl in (("fri-worship", "Friday Worship Service", "Friday", "detailed"),
                                    ("mon-bs", "Monday Bible Study", "Monday", "detailed"),
                                    ("sat-workers", "Saturday Workers Meeting", "Saturday", "simple")):
            MeetingType.objects.get_or_create(id=mid, defaults={"name": name, "day": day, "frequency": "weekly", "detail_level": lvl})
        for n in ("Tithe", "Offering"):
            Fund.objects.get_or_create(name=n)
        PaymentMethod.objects.get_or_create(name="Cash")
        Service.objects.get_or_create(name="Friday Worship Service")
        NewcomerSource.objects.get_or_create(name="Invited by a member")
        self.dir = tempfile.mkdtemp()
        self.report = os.path.join(self.dir, "July.csv"); report_csv(self.report)
        self.people = os.path.join(self.dir, "people.csv")
        simple_csv(self.people, ["Name", "Status", "Phone", "Email", "Address", "Invited by", "Adults / Youth / Child"], [
            ["Ada Example", "Member", "97300000001", "", "Flat 1, Road 2", "Facebook Ad", "Adult Sis"],
            ["Ben Example", "Member", "97300000002", "", "Flat 1, Road 2", "Self", "Adult Bro"],
            ["Cy New", "Newcomer", "97300000003", "", "Bahrain", "Bro Henry", "Youth Bro"]])
        self.newcomers = os.path.join(self.dir, "newcomers.csv")
        simple_csv(self.newcomers, ["Name", "Phone", "Gender", "Invited by"], [["Dee", "97300000004", "Female", "Facebook"]])
        self.contacts = os.path.join(self.dir, "contacts.csv")
        simple_csv(self.contacts, ["Name", "Phone", "Gender", "Invited by"], [["Eve", "97300000005", "Female", "Facebook ad"], ["Fay", "97300000006", "Female", "Facebook ad"]])

    def run_cmd(self, *args):
        out = io.StringIO(); call_command(*args, stdout=out); return out.getvalue()

    def test_clear_lists_without_changing_then_keeps_the_setup(self):
        self.member("Demo", "Person")
        MessageTemplate.objects.create(journey="any", theme="Test", number=1, body="Hello")
        bank = MessageTemplate.objects.count()
        out = self.run_cmd("clear_demo_data")
        self.assertIn("Nothing was changed", out); self.assertEqual(Member.objects.count(), 1)
        self.run_cmd("clear_demo_data", "--yes")
        self.assertEqual(Member.objects.count(), 0)
        self.assertTrue(MeetingType.objects.exists() and Fund.objects.exists() and self.admin.__class__.objects.filter(pk=self.admin.pk).exists())
        self.assertEqual(MessageTemplate.objects.count(), bank)              # the message bank is kept

    def test_import_check_keeps_nothing_and_load_follows_the_decisions(self):
        out = self.run_cmd("import_church_data", "--reports", self.report)
        self.assertIn("Nothing was kept", out); self.assertFalse(Giving.objects.exists())
        self.run_cmd("import_church_data", "--reports", self.report, "--yes")
        self.assertEqual(sorted(Giving.objects.values_list("amount", flat=True)), [Decimal("9.000"), Decimal("20.050"), Decimal("100.000")])  # SAR divided by 10
        fri = AttendanceSession.objects.get(meeting_type_id="fri-worship", date="2026-07-17")
        self.assertEqual((fri.mode, fri.men, fri.online_men, fri.new_comers, fri.status), ("in-person-and-online", 10, 0, 3, "filled"))
        mon = AttendanceSession.objects.get(meeting_type_id="mon-bs")
        self.assertEqual((mon.mode, mon.men, mon.online_men), ("online", 0, 5))
        self.assertTrue(AttendanceSession.objects.filter(meeting_type_id="sat-workers", online_men=4, online_women=2).exists())
        self.assertEqual(sorted(Expense.objects.values_list("category__name", flat=True)), ["Administration", "Rent"])
        self.assertEqual(Testimony.objects.get().service.name, "Friday Worship Service")

    def test_a_month_is_never_loaded_twice(self):
        self.run_cmd("import_church_data", "--reports", self.report, "--yes")
        with self.assertRaises(CommandError):
            self.run_cmd("import_church_data", "--reports", self.report, "--yes")
        self.assertEqual(Giving.objects.count(), 3)

    def test_people_newcomers_and_contacts(self):
        self.run_cmd("import_church_data", "--people", self.people, "--newcomers", self.newcomers, "--contacts", self.contacts, "--yes")
        self.assertEqual(Household.objects.count(), 1)                       # the two members share an address
        self.assertEqual(Member.objects.filter(household__isnull=False, category="General Member").count(), 2)
        cy = Newcomer.objects.get(name="Cy New"); dee = Newcomer.objects.get(name="Dee")
        self.assertEqual((cy.source.name, cy.invited_by_name, cy.keep_in_touch, cy.age_group), ("Invited by a member", "Bro Henry", False, ""))
        self.assertEqual(dee.source.name, "Facebook advert")
        self.assertEqual(set(Enquiry.objects.values_list("campaign__name", flat=True)), {"Facebook advert"})
        self.assertEqual(Enrolment.objects.count(), 0)                       # nobody's messages start by themselves
        with self.assertRaises(CommandError):                                # a phone already in the app is refused
            self.run_cmd("import_church_data", "--contacts", self.contacts, "--yes")


class BundledDataTestCase(Base):
    """The church's records that travel with the update read as Kay approved."""
    def test_the_bundled_files_read_in_full(self):
        from core.importers.monthly_reports import parse
        from core.importers.people import read_people, read_simple
        from core.management.commands.load_church_data import DATA
        totals = {m: parse(os.path.join(DATA, f"report-2026-{m:02d}.csv"), m) for m in (7, 8, 9)}
        self.assertEqual([len(t["sessions"]) for t in totals.values()], [9, 24, 25])
        self.assertEqual([round(sum(g["sar"] for g in t["giving"]), 2) for t in totals.values()], [10130.9, 8291.4, 11422.57])
        self.assertEqual([round(sum(e["sar"] for e in t["expenses"]), 2) for t in totals.values()], [10059.06, 5100.0, 3450.0])
        people = read_people(os.path.join(DATA, "people.csv"))
        self.assertEqual((len(people), sum(p["status"] == "member" for p in people)), (17, 7))
        self.assertEqual(len(read_simple(os.path.join(DATA, "newcomers.csv"))), 19)
        self.assertEqual(len(read_simple(os.path.join(DATA, "contacts.csv"))), 59)
