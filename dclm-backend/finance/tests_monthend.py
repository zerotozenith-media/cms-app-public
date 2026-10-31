"""Month-end balance (Kay, 30 October 2026)."""
import datetime
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User
from core.models import Location
from .models import Expense, ExpenseCategory, Fund, Giving, PaymentMethod
from .monthend_models import MoneySettings, MonthEnd
from .remittance_models import Remittance, RemittanceLine


def perm(role, module, view=True, create=False, edit=False, delete=False):
    RolePermission.objects.update_or_create(role=role, module=module, defaults=dict(
        can_view=view, can_create=create, can_edit=edit, can_delete=delete))


class MonthEndTests(APITestCase):
    def setUp(self):
        self.loc = Location.objects.get_or_create(id="bahrain", defaults={"name": "Bahrain HQ", "is_core": True})[0]
        acc = Role.objects.create(name="Accounts")
        perm(acc, "finance", create=True, edit=True, delete=True)
        appr = Role.objects.get_or_create(name="Finance Approver")[0]
        perm(appr, "finance")
        perm(appr, "monthend", edit=True)
        adm = Role.objects.get_or_create(name="Administrator")[0]
        for m in ("finance", "admin", "monthend"):
            perm(adm, m, create=True, edit=True, delete=True)
        self.acc = User.objects.create_user(email="acc@t.com", password="x", role=acc, location=self.loc,
                                            first_name="Grace", last_name="Thomas")
        self.appr = User.objects.create_user(email="appr@t.com", password="x", role=appr, location=self.loc)
        self.admin = User.objects.create_user(email="adm@t.com", password="x", role=adm)
        self.fund = Fund.objects.create(name="Tithe")
        self.cash = PaymentMethod.objects.get_or_create(name="Cash")[0]
        self.cat = ExpenseCategory.objects.create(name="Rent")
        MoneySettings.objects.update_or_create(location=self.loc, defaults=dict(
            start_month=datetime.date(2026, 7, 1), opening_balance=Decimal("0")))
        self.give(datetime.date(2026, 7, 3), "1200")
        self.spend(datetime.date(2026, 7, 10), "380")
        r = Remittance.objects.create(month=datetime.date(2026, 6, 1), location=self.loc,
                                      sent_on=datetime.date(2026, 7, 5))
        RemittanceLine.objects.create(remittance=r, fund=self.fund, amount_due=Decimal("600"),
                                      amount_sent=Decimal("600"), destination="dubai")

    def give(self, d, amt):
        return Giving.objects.create(date=d, fund=self.fund, method=self.cash, amount=Decimal(amt), location=self.loc)

    def spend(self, d, amt):
        return Expense.objects.create(date=d, category=self.cat, amount=Decimal(amt), location=self.loc)

    def as_(self, u):
        self.client.force_authenticate(u)

    def send(self, month="2026-07", amount="220.00", c2="Samuel Mensah", note=""):
        return self.client.post("/api/month-end/send/", {"location": "bahrain", "month": month,
                                                         "counted_amount": amount, "counted_by_1": "Grace Thomas",
                                                         "counted_by_2": c2, "difference_note": note})

    def test_defaults_and_figures(self):
        self.as_(self.acc)
        r = self.client.get("/api/month-end/?location=bahrain&month=2026-07")
        self.assertEqual(r.status_code, 200)
        f = r.data["figures"]
        self.assertEqual((f["opening"], f["giving"], f["expenses"], f["remittance"], f["expected"]),
                         ("0.000", "1200.000", "380.000", "600.000", "220.000"))
        self.assertEqual(r.data["settings"]["kept_as"], "cash")
        self.assertEqual(r.data["months"][-1]["month"], "2026-07")

    def test_send_rules(self):
        self.as_(self.acc)
        r = self.send(c2="grace thomas")
        self.assertIn("two different people", str(r.data["counted_by_2"]))
        r = self.send(amount="215")
        self.assertIn("difference of BHD 5.000", str(r.data["difference_note"]))
        r = self.send(month="2026-08")
        self.assertIn("July 2026 is not closed yet", str(r.data))
        nxt = (timezone.localdate().replace(day=1) + datetime.timedelta(days=40)).strftime("%Y-%m")
        r = self.client.post("/api/month-end/send/", {"location": "bahrain", "month": nxt, "counted_amount": "1",
                                                      "counted_by_1": "A", "counted_by_2": "B"})
        self.assertIn("has not ended yet", str(r.data))
        r = self.send(amount="215", note="Bank charge of BHD 5.00")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["record"]["status"], "sent")

    def test_locked_while_sent_and_closed(self):
        self.as_(self.acc)
        self.send()
        r = self.client.post("/api/expenses/", {"date": "2026-07-20", "category": self.cat.id, "amount": "5",
                                                "location": "bahrain"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("sent for approval", str(r.data))
        # The person who prepared it cannot approve it.
        self.as_(self.admin)
        MonthEnd.objects.filter(month=datetime.date(2026, 7, 1)).update(prepared_by=self.admin)
        r = self.client.post("/api/month-end/approve/", {"location": "bahrain", "month": "2026-07"})
        self.assertIn("a different person approves it", str(r.data))
        MonthEnd.objects.filter(month=datetime.date(2026, 7, 1)).update(prepared_by=self.acc)
        self.as_(self.acc)
        r = self.client.post("/api/month-end/approve/", {"location": "bahrain", "month": "2026-07"})
        self.assertEqual(r.status_code, 403)
        self.as_(self.appr)
        r = self.client.post("/api/month-end/approve/", {"location": "bahrain", "month": "2026-07"})
        self.assertEqual(r.data["record"]["status"], "closed")
        self.as_(self.acc)
        g = Giving.objects.first()
        for resp in (
            self.client.post("/api/giving/", {"date": "2026-07-20", "fund": self.fund.id, "method": self.cash.id,
                                              "amount": "5", "location": "bahrain"}),
            self.client.patch(f"/api/giving/{g.id}/", {"amount": "1"}),
            self.client.delete(f"/api/giving/{g.id}/"),
            self.client.delete(f"/api/expenses/{Expense.objects.first().id}/"),
        ):
            self.assertEqual(resp.status_code, 400, resp.data)
            self.assertIn("July 2026 is closed for Bahrain HQ", str(resp.data))
        # Moving an August entry into July is refused too.
        e = self.spend(datetime.date(2026, 8, 2), "9")
        r = self.client.patch(f"/api/expenses/{e.id}/", {"date": "2026-07-30"})
        self.assertEqual(r.status_code, 400)
        # August opens with July's counted balance.
        r = self.client.get("/api/month-end/?location=bahrain&month=2026-08")
        self.assertEqual(r.data["figures"]["opening"], "220.000")
        self.assertTrue(AuditLog.objects.filter(action="Approved and closed").exists())

    def test_send_back_and_reopen(self):
        self.as_(self.acc)
        self.send()
        self.as_(self.appr)
        r = self.client.post("/api/month-end/send-back/", {"location": "bahrain", "month": "2026-07"})
        self.assertIn("Say what needs correcting", str(r.data))
        r = self.client.post("/api/month-end/send-back/", {"location": "bahrain", "month": "2026-07",
                                                          "note": "The rent has no receipt"})
        self.assertEqual(r.data["record"]["status"], "open")
        self.as_(self.acc)
        self.assertEqual(self.client.post("/api/expenses/", {"date": "2026-07-21", "category": self.cat.id,
                                                             "amount": "0", "location": "bahrain"}).status_code, 201)
        self.send()
        self.as_(self.appr)
        self.client.post("/api/month-end/approve/", {"location": "bahrain", "month": "2026-07"})
        # August closed too: July cannot be reopened first.
        MonthEnd.objects.create(location=self.loc, month=datetime.date(2026, 8, 1), status="closed",
                                counted_amount=Decimal("220"))
        self.as_(self.acc)
        r = self.client.post("/api/month-end/reopen/", {"location": "bahrain", "month": "2026-07", "reason": "x"})
        self.assertEqual(r.status_code, 403)
        self.as_(self.admin)
        r = self.client.post("/api/month-end/reopen/", {"location": "bahrain", "month": "2026-07", "reason": "x"})
        self.assertIn("Reopen August 2026 first", str(r.data))
        MonthEnd.objects.filter(month=datetime.date(2026, 8, 1)).delete()
        r = self.client.post("/api/month-end/reopen/", {"location": "bahrain", "month": "2026-07"})
        self.assertIn("Say why", str(r.data))
        r = self.client.post("/api/month-end/reopen/", {"location": "bahrain", "month": "2026-07",
                                                       "reason": "Receipt handed in late"})
        self.assertEqual(r.data["record"]["status"], "open")
        self.assertTrue(AuditLog.objects.filter(action="Reopened", details="Receipt handed in late").exists())

    def test_settings(self):
        self.as_(self.acc)
        self.assertEqual(self.client.put("/api/money-settings/?location=bahrain", {"kept_as": "bank"}).status_code, 403)
        self.as_(self.admin)
        r = self.client.put("/api/money-settings/?location=bahrain",
                            {"kept_as": "cash", "start_month": "2030-01", "opening_balance": "0"})
        self.assertIn("cannot be in the future", str(r.data))
        r = self.client.put("/api/money-settings/?location=bahrain",
                            {"kept_as": "cash", "start_month": "2026-07", "opening_balance": "50"})
        self.assertEqual(r.data["opening_balance"], "50.000")
        self.as_(self.acc)
        self.send(amount="270.00")
        self.as_(self.admin)
        r = self.client.put("/api/money-settings/?location=bahrain", {"opening_balance": "10"})
        self.assertIn("can no longer change", str(r.data))
        # Cash or bank can still change.
        r = self.client.put("/api/money-settings/?location=bahrain", {"kept_as": "bank"})
        self.assertEqual(r.data["kept_as"], "bank")

    def test_offering_and_remittance_locked(self):
        """A closed month's offerings and remittances cannot change either."""
        from rest_framework.exceptions import ValidationError
        from attendance.models import AttendanceSession, MeetingType
        from attendance.views import AttendanceSessionViewSet as V
        mt = MeetingType.objects.create(id="friday-worship", name="Friday Worship Service", day="Friday",
                                        frequency="weekly", detail_level="detailed", collects_offering=True)
        s = AttendanceSession.objects.create(meeting_type=mt, date=datetime.date(2026, 7, 24), location=self.loc)
        V._record_offering(s, {"Tithe": "20"})
        MonthEnd.objects.create(location=self.loc, month=datetime.date(2026, 7, 1), status="closed",
                                counted_amount=Decimal("0"))
        V._record_offering(s, {"Tithe": "20"})          # unchanged: fine
        with self.assertRaises(ValidationError) as e:
            V._record_offering(s, {"Tithe": "25"})
        self.assertIn("the offering dated in July", str(e.exception.detail))
        self.as_(self.acc)
        r = self.client.delete(f"/api/remittances/{Remittance.objects.first().id}/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("a remittance dated in July", str(r.data))
