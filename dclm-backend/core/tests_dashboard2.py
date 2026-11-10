"""
Dashboard redesign (approved 10 November 2026): periods and what each is
compared with, the figures for each kind of dashboard, the summary tables,
the export, the "no receipt" flag, the settings behind them, and a guard
that the number of database queries does not grow with the records.
"""
import datetime
from decimal import Decimal
from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User
from attendance.models import AttendanceSession, AttendanceSessionMember, MeetingType
from core import dash_period as dp
from core import settings_store
from core.models import AppSetting, Location
from finance.models import Expense, ExpenseCategory, Fund, Giving, PaymentMethod
from newcomers.models import MilestoneType, Newcomer, NewcomerMilestone, NewcomerSource, NewcomerTask

TODAY = datetime.date(2026, 11, 10)


def d(y, m, day):
    return datetime.date(y, m, day)


class PeriodTests(TestCase):
    def test_this_month_is_compared_with_the_same_days_of_the_month_before(self):
        p = dp.resolve({"period": "this_month"}, TODAY)
        self.assertEqual((p["start"], p["end"]), (d(2026, 11, 1), TODAY))
        c = dp.comparison(p)
        self.assertEqual(c[:2], (d(2026, 10, 1), d(2026, 10, 10)))
        self.assertEqual((c[2], c[3]), ("1 to 10 October 2026", "before"))

    def test_last_month_is_compared_with_the_whole_month_before(self):
        p = dp.resolve({"period": "last_month"}, TODAY)
        self.assertEqual(dp.comparison(p)[:3], (d(2026, 9, 1), d(2026, 9, 30), "September 2026"))

    def test_the_quarter_is_compared_with_the_quarter_before_to_the_same_day(self):
        p = dp.resolve({"period": "this_quarter"}, TODAY)
        self.assertEqual(p["start"], d(2026, 10, 1))
        self.assertEqual(dp.comparison(p)[:2], (d(2026, 7, 1), d(2026, 8, 10)))

    def test_nothing_before_records_start_is_compared(self):
        # Year to date 2026: January to June 2025 and 2026 have no records.
        self.assertIsNone(dp.comparison(dp.resolve({"period": "this_year"}, TODAY)))
        self.assertIsNone(dp.comparison(dp.resolve({"period": "last_year"}, TODAY)))

    def test_a_year_later_the_same_days_a_year_earlier_are_used(self):
        c = dp.comparison(dp.resolve({"period": "this_month"}, d(2027, 8, 10)))
        self.assertEqual((c[0], c[1], c[3]), (d(2026, 8, 1), d(2026, 8, 10), "year"))
        # July 2027 to date: a year earlier is July 2026, the first month with records.
        self.assertEqual(dp.comparison(dp.resolve({"period": "this_month"}, d(2027, 7, 3)))[3], "year")
        # Year to date 2027 still has nothing to compare with: January to June 2026 had no records.
        self.assertIsNone(dp.comparison(dp.resolve({"period": "this_year"}, d(2027, 8, 10))))

    def test_records_start_comes_from_settings(self):
        settings_store.set_value("records_start", "2026-10")
        self.assertIsNone(dp.comparison(dp.resolve({"period": "this_quarter"}, TODAY)))

    def test_the_financial_year_moves_year_to_date_and_the_quarters(self):
        settings_store.set_value("finance_year_end_month", 3)
        p = dp.resolve({"period": "this_year"}, TODAY)
        self.assertEqual(p["start"], d(2026, 4, 1))
        self.assertEqual(dp.resolve({"period": "this_quarter"}, TODAY)["start"], d(2026, 10, 1))
        self.assertEqual(dp.resolve({"period": "last_year"}, TODAY)["start"], d(2025, 4, 1))
        self.assertEqual(dp.resolve({"period": "last_year"}, TODAY)["end"], d(2026, 3, 31))

    def test_the_opening_period_comes_from_settings(self):
        self.assertEqual(dp.resolve({}, TODAY)["key"], "this_month")
        settings_store.set_value("dashboard_opens_on", "this_year")
        self.assertEqual(dp.resolve({}, TODAY)["key"], "this_year")

    def test_a_range_and_a_year_are_checked_and_explained(self):
        from rest_framework.exceptions import ValidationError
        for bad in ({"period": "range", "from": "2026-10", "to": "2026-08"},
                    {"period": "range", "from": "2026-01", "to": "2026-08"},
                    {"period": "range", "from": "2026-8", "to": "2026-09"},
                    {"period": "year", "year": "2024"}, {"period": "fortnight"}):
            with self.assertRaises(ValidationError):
                dp.resolve(bad, TODAY)
        p = dp.resolve({"period": "range", "from": "2026-09", "to": "2026-10"}, TODAY)
        self.assertEqual((p["label"], dp.comparison(p)[:2]), ("September to October 2026", (d(2026, 7, 1), d(2026, 8, 31))))
        # August to September would be compared with June to July, and June has no records.
        self.assertIsNone(dp.comparison(dp.resolve({"period": "range", "from": "2026-08", "to": "2026-09"}, TODAY)))

    def test_short_periods_draw_up_to_twelve_months_but_never_before_records(self):
        months = dp.chart_months(dp.resolve({"period": "this_month"}, TODAY))
        self.assertEqual((months[0], months[-1]), (d(2026, 7, 1), d(2026, 11, 1)))


class Base(APITestCase):
    def setUp(self):
        self.bh = Location.objects.create(id="bahrain", name="Bahrain HQ", is_core=True)
        self.qa = Location.objects.create(id="others", name="Qatar")
        self.fw = MeetingType.objects.create(id="fri-worship", name="Friday Worship Service", day="Friday",
                                             frequency="weekly", detail_level="detailed", collects_offering=True)
        self.mon = MeetingType.objects.create(id="mon-bs", name="Monday Bible Study", day="Monday",
                                              frequency="weekly", detail_level="detailed", collects_offering=False)
        self.fund = Fund.objects.create(name="Tithe")
        self.method = PaymentMethod.objects.create(name="Cash")
        self.cat = ExpenseCategory.objects.create(name="Utilities")
        self.src = NewcomerSource.objects.create(name="Walk-in")
        self.salv = MilestoneType.objects.create(name="Salvation")
        self.admin = self.user("admin@t.com", "Administrator", ["members", "attendance", "newcomers", "finance", "goals",
                                                               "reports", "admin"], full=True)
        self.coord = self.user("coord@t.com", "Location Coordinator", ["members", "attendance", "newcomers", "finance",
                                                                      "reports", "admin"], location=self.bh)
        self.accounts = self.user("acc@t.com", "Accounts", ["finance", "monthend", "reports"], full=True)
        self.shep = self.user("shep@t.com", "Follow-up", ["attendance", "members", "newcomers"], location=self.bh)
        self.p = mock.patch("django.utils.timezone.localdate", return_value=TODAY)
        self.p.start()
        self.addCleanup(self.p.stop)

    def user(self, email, role, modules, full=False, location=None):
        r, _ = Role.objects.get_or_create(name=role)
        for m in modules:
            RolePermission.objects.get_or_create(role=r, module=m, defaults=dict(
                can_view=True, can_create=True, can_edit=full or m in ("attendance", "newcomers", "members"),
                can_delete=full))
        return User.objects.create_user(email=email, password="x", role=r, location=location, first_name=email[:4])

    def session(self, date, loc, total, mt=None, status="filled"):
        return AttendanceSession.objects.create(meeting_type=mt or self.fw, date=date, location=loc, mode="in-person",
                                                status=status, men=total)

    def give(self, date, amount, loc=None, session=None):
        return Giving.objects.create(date=date, fund=self.fund, method=self.method, amount=Decimal(amount),
                                     location=loc or self.bh, session=session)

    def spend(self, date, amount, loc=None, receipt=""):
        return Expense.objects.create(date=date, category=self.cat, amount=Decimal(amount), location=loc or self.bh,
                                      receipt_file=receipt)

    def get(self, user, **params):
        self.client.force_authenticate(user)
        r = self.client.get("/api/dashboard/", params)
        self.assertEqual(r.status_code, 200, r.content)
        return r.data


class FiguresTests(Base):
    def test_cards_compare_with_the_same_days_of_october(self):
        self.give(d(2026, 11, 5), "150")
        self.give(d(2026, 10, 5), "100")
        self.give(d(2026, 10, 20), "999")          # after 10 October: not in the comparison
        self.spend(d(2026, 11, 2), "40")
        self.session(d(2026, 11, 6), self.bh, 50)
        self.session(d(2026, 11, 6), self.qa, 10)  # the same Friday at Qatar: one service of 60
        self.session(d(2026, 10, 2), self.bh, 40)
        data = self.get(self.admin)
        c = data["cards"]
        self.assertEqual((c["giving"]["value"], c["giving"]["before"]), ("150.00", "100.00"))
        self.assertEqual(c["net"]["value"], "110.00")
        self.assertEqual((c["attendance"]["value"], c["attendance"]["before"]), (60, 40))
        self.assertEqual(data["compare"], {"label": "1 to 10 October 2026", "kind": "before"})

    def test_a_month_with_nothing_recorded_is_a_gap_not_zero(self):
        self.session(d(2026, 7, 3), self.bh, 40)
        self.session(d(2026, 9, 4), self.bh, 50)
        self.session(d(2026, 9, 11), self.bh, 70)
        months = self.get(self.admin)["charts"]["attendance_by_month"]["months"]
        self.assertEqual([m["attendance"] for m in months], [40, None, 60, None, None])

    def test_on_track_and_ready_follow_the_membership_rule(self):
        def person(name, first_came, fridays_attended, saved):
            n = Newcomer.objects.create(name=name, source=self.src, location=self.bh, stage="attending",
                                        created_at=first_came, stage_since=first_came)
            for f in fridays_attended:
                s = AttendanceSession.objects.filter(date=f, location=self.bh, meeting_type=self.fw).first()
                AttendanceSessionMember.objects.create(session=s, newcomer=n)
            if saved:
                NewcomerMilestone.objects.create(newcomer=n, milestone_type=self.salv, achieved_date=first_came)
            return n
        fridays = [d(2026, 4, 3) + datetime.timedelta(weeks=i) for i in range(32)]
        for f in fridays:
            self.session(f, self.bh, 40)
        people = [person("Ready", d(2026, 4, 3), fridays[::2], True),          # 7 months, 50%, saved
                  person("On track", d(2026, 9, 4), [f for f in fridays if f >= d(2026, 9, 4)], True),
                  person("Not saved", d(2026, 9, 4), [f for f in fridays if f >= d(2026, 9, 4)], False),
                  person("Seldom", d(2026, 4, 3), fridays[:3], True)]
        m = self.get(self.admin)["cards"]["membership"]
        self.assertEqual((m["on_track"], m["ready"], m["pipeline"]), (1, 1, 4))
        from newcomers.membership import readiness
        self.assertEqual([readiness(p, TODAY)["ready"] for p in people], [True, False, False, False])

    def test_each_kind_of_dashboard_gets_its_own_parts(self):
        admin, coord, acc, shep = (self.get(u) for u in (self.admin, self.coord, self.accounts, self.shep))
        self.assertEqual((admin["kind"], admin["table"]["by"]), ("leader", "location"))
        self.assertEqual((coord["kind"], coord["table"]["by"], coord["scope"]["name"]), ("leader", "meeting", "Bahrain HQ"))
        self.assertEqual((acc["kind"], acc["table"]["by"]), ("accounts", "month"))
        self.assertNotIn("attendance", acc["cards"])
        self.assertIn("cash", acc["cards"])
        self.assertEqual(shep["kind"], "worker")
        self.assertNotIn("table", shep)
        self.assertNotIn("giving", shep["cards"])
        self.assertIn("my_tasks", shep["cards"])

    def test_an_administrator_viewing_one_location_gets_the_table_by_meeting(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get("/api/dashboard/", HTTP_X_VIEWING_LOCATION="others")
        self.assertEqual((r.data["table"]["by"], r.data["scope"]["name"]), ("meeting", "Qatar"))

    def test_the_table_by_location_adds_up(self):
        self.give(d(2026, 11, 3), "30", self.bh)
        self.give(d(2026, 11, 3), "20", self.qa)
        self.spend(d(2026, 11, 3), "5", self.qa)
        t = self.get(self.admin)["table"]
        rows = {r["name"]: r for r in t["rows"]}
        self.assertEqual((rows["Qatar"]["giving"], rows["Qatar"]["net"]), ("20.00", "15.00"))
        self.assertEqual((t["total"]["giving"], t["total"]["net"]), ("50.00", "45.00"))
        self.assertEqual(rows["Qatar"]["month_end"], "Open")

    def test_the_table_by_meeting_counts_sessions_not_filled_in(self):
        self.session(d(2026, 11, 6), self.bh, 50)
        self.session(d(2026, 11, 2), self.bh, 0, mt=self.mon, status="pending")
        rows = {r["name"]: r for r in self.get(self.coord)["table"]["rows"]}
        self.assertEqual(rows["Monday Bible Study"]["not_filled"], 1)
        self.assertIsNone(rows["Monday Bible Study"]["offering"])       # does not collect an offering
        self.assertEqual(rows["Friday Worship Service"]["attendance"], 50)

    def test_the_table_by_month_carries_cash_from_month_to_month(self):
        from finance.monthend_models import MonthEnd, MoneySettings
        MoneySettings.objects.create(location=self.bh, start_month=d(2026, 9, 1), opening_balance=Decimal("100"))
        self.give(d(2026, 9, 5), "50")
        self.spend(d(2026, 10, 5), "30")
        MonthEnd.objects.create(location=self.bh, month=d(2026, 9, 1), status="closed", counted_amount=Decimal("149"))
        locs = {l["name"]: l for l in self.get(self.accounts)["table"]["locations"]}
        rows = {r["month"]: r for r in locs["Bahrain HQ"]["rows"]}
        self.assertEqual((rows["2026-09"]["cash"], rows["2026-09"]["status_label"]), ("149.00", "Closed"))
        self.assertEqual((rows["2026-10"]["start"], rows["2026-10"]["cash"]), ("149.00", "119.00"))
        self.assertTrue(rows["2026-11"]["so_far"])


class ReceiptFlagTests(Base):
    def keys(self, user):
        from core.outstanding import outstanding
        return {i["key"]: i for i in outstanding(user)}

    def test_expenses_with_no_receipt_follow_the_setting(self):
        self.spend(d(2026, 11, 2), "40")
        self.spend(d(2026, 10, 2), "12.5")
        self.spend(d(2026, 9, 2), "500")                      # before last month: not counted
        self.spend(d(2026, 11, 3), "90", receipt="receipts/2026/11/a.pdf")
        self.assertEqual(self.keys(self.admin)["no-receipt"]["count"], 1)
        settings_store.set_value("receipt_flag_over", "10")
        self.assertEqual(self.keys(self.admin)["no-receipt"]["count"], 2)
        self.assertIn("over BHD 10.00", self.keys(self.admin)["no-receipt"]["label"])

    def test_only_people_who_can_edit_money_are_told(self):
        self.spend(d(2026, 11, 2), "40")
        self.assertNotIn("no-receipt", self.keys(self.shep))
        self.assertNotIn("no-receipt", self.keys(self.coord))   # can view money, not edit it
        self.assertIn("no-receipt", self.keys(self.accounts))


class SettingsTests(Base):
    def test_an_administrator_changes_the_settings_and_it_is_logged(self):
        self.client.force_authenticate(self.admin)
        r = self.client.patch("/api/settings/", {"finance_year_end_month": 3, "receipt_flag_over": "40",
                                                 "two_step_roles": {str(self.shep.role_id): "choose"}}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.data["finance_year_end_month"], r.data["receipt_flag_over"]), (3, "40.00"))
        self.assertEqual(Role.objects.get(id=self.shep.role_id).two_step, "choose")
        from accounts.models import AuditLog
        self.assertTrue(AuditLog.objects.filter(entity_name="Financial year ends in").exists())

    def test_a_wrong_value_saves_nothing_and_says_why(self):
        self.client.force_authenticate(self.admin)
        r = self.client.patch("/api/settings/", {"finance_year_end_month": 13, "receipt_flag_over": "40"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("January to December", r.data["finance_year_end_month"])
        self.assertFalse(AppSetting.objects.filter(key="receipt_flag_over").exists())

    def test_others_cannot_change_them(self):
        self.client.force_authenticate(self.coord)
        r = self.client.patch("/api/settings/", {"receipt_flag_over": "0"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertIn("Only administrators", r.data["detail"])


class ExportTests(Base):
    def test_excel_and_pdf(self):
        self.give(d(2026, 11, 3), "30")
        self.client.force_authenticate(self.admin)
        x = self.client.get("/api/dashboard/export/", {"output": "excel"})
        self.assertEqual(x.status_code, 200)
        self.assertIn("spreadsheetml", x["Content-Type"])
        p = self.client.get("/api/dashboard/export/", {"output": "pdf"})
        self.assertEqual((p.status_code, p.content[:4]), (200, b"%PDF"))
        self.client.force_authenticate(self.accounts)
        self.assertEqual(self.client.get("/api/dashboard/export/", {"output": "excel", "location": "others"}).status_code, 200)

    def test_a_dashboard_with_no_table_explains_why(self):
        self.client.force_authenticate(self.shep)
        r = self.client.get("/api/dashboard/export/", {"output": "pdf"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("no table", r.data["detail"])
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/dashboard/export/", {"output": "word"}).status_code, 400)


class QueryCountTests(Base):
    """The number of database queries must not grow with the records, so
    the dashboard stays quick as the years of records build up."""

    def add_records(self, n):
        for i in range(n):
            day = d(2026, 7, 3) + datetime.timedelta(weeks=i % 18)
            for loc in (self.bh, self.qa):
                s = self.session(day, loc, 30 + i)
                self.give(day, "10", loc, session=s)
                self.spend(day, "4", loc)
                nc = Newcomer.objects.create(name=f"N{i}{loc.id}", source=self.src, location=loc, stage="attending",
                                             created_at=day, stage_since=day, assigned_to=self.shep)
                AttendanceSessionMember.objects.create(session=s, newcomer=nc)
                NewcomerMilestone.objects.create(newcomer=nc, milestone_type=self.salv, achieved_date=day)
                NewcomerTask.objects.create(newcomer=nc, text="Call", due_date=day, assigned_to=self.shep)

    def queries(self, user):
        self.client.force_authenticate(user)
        with CaptureQueriesContext(connection) as q:
            r = self.client.get("/api/dashboard/", {"period": "this_year"})
        self.assertEqual(r.status_code, 200)
        return len(q.captured_queries)

    def test_queries_stay_the_same_as_records_grow(self):
        self.add_records(2)
        small = {u.email: self.queries(u) for u in (self.admin, self.coord, self.accounts, self.shep)}
        self.add_records(30)
        big = {u.email: self.queries(u) for u in (self.admin, self.coord, self.accounts, self.shep)}
        self.assertEqual(small, big)
