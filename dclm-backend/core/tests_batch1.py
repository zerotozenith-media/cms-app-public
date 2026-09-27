"""
Batch 1: the offering tick, day validation, fellowship-aware session
generation, registration assignment, and monthly remittance.
"""
import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User
from attendance.models import AttendanceSession, Fellowship, MeetingType
from core.models import AppSetting, Location
from finance.models import Expense, ExpenseCategory, Fund, Giving, PaymentMethod, Remittance
from members.models import Member
from newcomers.models import Newcomer, NewcomerSource


class Base(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        role = Role.objects.create(name="Administrator")
        for module in ["members", "attendance", "newcomers", "finance",
                       "goals", "reports", "outreach", "admin"]:
            RolePermission.objects.create(
                role=role, module=module, can_view=True,
                can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="a@t.com", password="x", role=role)
        self.client.force_authenticate(user=self.admin)
        self.today = timezone.localdate()


class OfferingTickTestCase(Base):
    """
    Which meetings collect an offering is a church decision, so it lives
    on the meeting type rather than in a list inside the code.
    """
    def test_a_meeting_can_be_marked_as_collecting(self):
        mt = MeetingType.objects.create(
            id="fri-worship", name="Friday Worship Service", day="Friday",
            frequency="weekly", detail_level="detailed", collects_offering=True)
        self.assertTrue(mt.collects_offering)

    def test_it_defaults_to_off(self):
        """A new meeting does not ask for money until somebody says it
        should."""
        mt = MeetingType.objects.create(
            id="gck", name="Global Crusade", day="", frequency="occasional",
            detail_level="detailed")
        self.assertFalse(mt.collects_offering)

    def test_it_can_be_changed_over_the_api(self):
        mt = MeetingType.objects.create(
            id="mon-bs", name="Monday Bible Study", day="Monday",
            frequency="weekly", detail_level="detailed")
        resp = self.client.patch(f"/api/meeting-types/{mt.id}/",
                                 {"collects_offering": True}, format="json")
        self.assertEqual(resp.status_code, 200)
        mt.refresh_from_db()
        self.assertTrue(mt.collects_offering)


class MeetingDayTestCase(Base):
    """
    A day the generator cannot match means sessions silently stop
    appearing, and the only warning goes to a log nobody reads.
    """
    def test_a_shortened_day_is_refused(self):
        with self.assertRaises(ValidationError):
            MeetingType.objects.create(
                id="bad", name="Bad", day="Fri", frequency="weekly",
                detail_level="simple")

    def test_a_misspelled_day_is_refused(self):
        with self.assertRaises(ValidationError):
            MeetingType.objects.create(
                id="bad2", name="Bad", day="Freeday", frequency="weekly",
                detail_level="simple")

    def test_a_weekly_meeting_needs_a_day(self):
        with self.assertRaises(ValidationError):
            MeetingType.objects.create(
                id="bad3", name="Bad", day="", frequency="weekly",
                detail_level="simple")

    def test_an_occasional_meeting_needs_no_day(self):
        """GCK has no fixed day, and that is correct rather than broken."""
        mt = MeetingType.objects.create(
            id="gck", name="Global Crusade", day="", frequency="occasional",
            detail_level="detailed")
        self.assertFalse(mt.generates_sessions)

    def test_a_valid_weekly_meeting_reports_that_it_generates(self):
        mt = MeetingType.objects.create(
            id="fri", name="Friday Worship", day="Friday", frequency="weekly",
            detail_level="detailed")
        self.assertTrue(mt.generates_sessions)


class FellowshipSessionTestCase(Base):
    """
    Two fellowships meet the same evening, so one session per date leaves
    the second one nowhere to be recorded.
    """
    def setUp(self):
        super().setUp()
        self.house = MeetingType.objects.create(
            id="fri-house", name="Friday House Caring Fellowship", day="Friday",
            frequency="weekly", detail_level="detailed", collects_offering=True)
        self.women = Fellowship.objects.create(name="HCF Women", meeting_type=self.house)
        self.men = Fellowship.objects.create(name="HCF Men", meeting_type=self.house)

    def test_one_session_is_generated_per_fellowship(self):
        call_command("generate_recurring_sessions", verbosity=0)
        sessions = AttendanceSession.objects.filter(meeting_type=self.house)
        self.assertEqual(sessions.count(), 2)
        self.assertEqual({s.fellowship for s in sessions}, {self.women, self.men})

    def test_adding_a_third_fellowship_needs_no_code_change(self):
        youth = Fellowship.objects.create(name="HCF Youth", meeting_type=self.house)
        call_command("generate_recurring_sessions", verbosity=0)
        sessions = AttendanceSession.objects.filter(meeting_type=self.house)
        self.assertEqual(sessions.count(), 3)
        self.assertIn(youth, {s.fellowship for s in sessions})

    def test_an_inactive_fellowship_gets_no_session(self):
        self.men.is_active = False
        self.men.save()
        call_command("generate_recurring_sessions", verbosity=0)
        self.assertEqual(
            AttendanceSession.objects.filter(meeting_type=self.house).count(), 1)

    def test_running_twice_does_not_duplicate(self):
        call_command("generate_recurring_sessions", verbosity=0)
        call_command("generate_recurring_sessions", verbosity=0)
        self.assertEqual(
            AttendanceSession.objects.filter(meeting_type=self.house).count(), 2)

    def test_an_ordinary_meeting_still_gets_one_session(self):
        MeetingType.objects.create(
            id="fri-worship", name="Friday Worship", day="Friday",
            frequency="weekly", detail_level="detailed")
        call_command("generate_recurring_sessions", verbosity=0)
        self.assertEqual(
            AttendanceSession.objects.filter(meeting_type_id="fri-worship").count(), 1)


class RegistrationAssignmentTestCase(Base):
    """
    A task created with nobody's name on it is never picked up, because
    auto assign assigns people rather than tasks.
    """
    def setUp(self):
        super().setUp()
        self.source = NewcomerSource.objects.create(name="Walk-in")
        worker_role = Role.objects.create(name="Follow-up")
        RolePermission.objects.create(role=worker_role, module="newcomers",
                                      can_view=True, can_create=True, can_edit=True)
        self.shepherd = User.objects.create_user(
            email="s@t.com", password="x", role=worker_role, location=self.bahrain)
        m = Member.objects.create(surname="Osei", first_name="Sarah",
                                  location=self.bahrain, joined_date=self.today,
                                  category=Member.Category.WORKER)
        self.shepherd.member = m
        self.shepherd.save()

    def _register(self, **kw):
        from newcomers.intake import create_auto_tasks
        n = Newcomer.objects.create(
            name="Joy Mensah", source=self.source, location=self.bahrain,
            stage=Newcomer.Stage.NEW, created_at=self.today,
            stage_since=self.today, **kw)
        create_auto_tasks(n)
        n.refresh_from_db()
        return n

    def test_a_newcomer_is_given_a_shepherd_at_registration(self):
        n = self._register(wants_visit=True)
        self.assertIsNotNone(n.assigned_to)

    def test_the_task_inherits_that_shepherd(self):
        n = self._register(wants_visit=True)
        task = n.tasks.first()
        self.assertIsNotNone(task)
        self.assertEqual(task.assigned_to, n.assigned_to)

    def test_nothing_is_assigned_when_the_setting_is_off(self):
        """Turning it off means assign by hand, usually so whoever met
        the newcomer keeps them. That is a decision, not an oversight."""
        AppSetting.objects.update_or_create(
            key="auto_assign_newcomers", defaults={"value": "false"})
        n = self._register(wants_visit=True)
        self.assertIsNone(n.assigned_to)

    def test_an_existing_shepherd_is_not_overwritten(self):
        n = self._register(wants_visit=True, assigned_to=self.shepherd)
        self.assertEqual(n.assigned_to, self.shepherd)

    def test_open_tasks_follow_when_a_shepherd_is_set_later(self):
        AppSetting.objects.update_or_create(
            key="auto_assign_newcomers", defaults={"value": "false"})
        n = self._register(wants_visit=True)
        self.assertIsNone(n.tasks.first().assigned_to)

        from members.assignment import carry_tasks_to_shepherd
        n.assigned_to = self.shepherd
        n.save()
        moved = carry_tasks_to_shepherd(n)
        self.assertEqual(moved, 1)
        self.assertEqual(n.tasks.first().assigned_to, self.shepherd)


class RemittanceTestCase(Base):
    """
    Remittance is monthly, and the figure the system works out is a
    proposal rather than a rule.
    """
    def setUp(self):
        super().setUp()
        self.tithe = Fund.objects.create(name="Tithe")
        self.building = Fund.objects.create(name="Building")
        self.cash = PaymentMethod.objects.create(name="Cash")
        self.rent = ExpenseCategory.objects.create(name="Rent")
        d = self.today.replace(day=1)
        Giving.objects.create(date=d, fund=self.tithe, method=self.cash,
                              amount=Decimal("1000"), location=self.bahrain)
        Giving.objects.create(date=d, fund=self.building, method=self.cash,
                              amount=Decimal("500"), location=self.bahrain)
        Expense.objects.create(date=d, category=self.rent,
                               amount=Decimal("300"), location=self.bahrain)
        self.month = f"{d:%Y-%m}"

    def test_the_proposal_takes_expenses_off_first(self):
        resp = self.client.get(f"/api/remittances/proposed/?month={self.month}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Decimal(resp.data["collected"]), Decimal("1500"))
        self.assertEqual(Decimal(resp.data["expenses"]), Decimal("300"))
        self.assertEqual(Decimal(resp.data["due"]), Decimal("1200"))

    def test_each_fund_carries_its_share_of_the_expenses(self):
        resp = self.client.get(f"/api/remittances/proposed/?month={self.month}")
        by_fund = {l["fund_name"]: Decimal(l["amount_due"]) for l in resp.data["lines"]}
        # Tithe raised two thirds, so carries two thirds of the 300.
        self.assertEqual(by_fund["Tithe"], Decimal("800.000"))
        self.assertEqual(by_fund["Building"], Decimal("400.000"))

    def test_building_is_proposed_to_go_elsewhere(self):
        resp = self.client.get(f"/api/remittances/proposed/?month={self.month}")
        dest = {l["fund_name"]: l["destination"] for l in resp.data["lines"]}
        self.assertEqual(dest["Tithe"], "dubai")
        self.assertEqual(dest["Building"], "lagos")

    def test_a_remittance_can_be_recorded(self):
        resp = self.client.post("/api/remittances/", {
            "month": f"{self.month}-01", "sent_on": str(self.today),
            "reference": "TRF-1",
            "lines": [{"fund": self.tithe.id, "amount_due": "800.000",
                       "amount_sent": "800.000", "destination": "dubai"}],
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Remittance.objects.count(), 1)

    def test_an_override_without_a_reason_is_refused(self):
        """Otherwise the difference is silent, and six months later
        nobody can say why one month sent 300 more than it collected."""
        resp = self.client.post("/api/remittances/", {
            "month": f"{self.month}-01", "sent_on": str(self.today),
            "lines": [{"fund": self.tithe.id, "amount_due": "800.000",
                       "amount_sent": "1100.000", "destination": "dubai"}],
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("note", resp.data)

    def test_an_override_with_a_reason_is_accepted(self):
        resp = self.client.post("/api/remittances/", {
            "month": f"{self.month}-01", "sent_on": str(self.today),
            "note": "A member covered the rent",
            "lines": [{"fund": self.tithe.id, "amount_due": "800.000",
                       "amount_sent": "1100.000", "destination": "dubai"}],
        }, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        r = Remittance.objects.first()
        self.assertEqual(r.difference, Decimal("300.000"))

    def test_both_figures_are_kept(self):
        self.client.post("/api/remittances/", {
            "month": f"{self.month}-01", "sent_on": str(self.today),
            "note": "Member covered expenses",
            "lines": [{"fund": self.tithe.id, "amount_due": "800.000",
                       "amount_sent": "1100.000", "destination": "dubai"}],
        }, format="json")
        line = Remittance.objects.first().lines.first()
        self.assertEqual(line.amount_due, Decimal("800.000"))
        self.assertEqual(line.amount_sent, Decimal("1100.000"))

    def test_it_can_be_edited_afterwards(self):
        """A reference gets mistyped, and somebody has to fix it."""
        create = self.client.post("/api/remittances/", {
            "month": f"{self.month}-01", "sent_on": str(self.today),
            "reference": "WRONG",
            "lines": [{"fund": self.tithe.id, "amount_due": "800.000",
                       "amount_sent": "800.000", "destination": "dubai"}],
        }, format="json")
        rid = create.data["id"]
        resp = self.client.patch(f"/api/remittances/{rid}/",
                                 {"reference": "TRF-CORRECT"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Remittance.objects.get(id=rid).reference, "TRF-CORRECT")

    def test_giving_no_longer_carries_a_destination(self):
        """It was asking the wrong question in the wrong place."""
        self.assertFalse(hasattr(Giving(), "remitted_to"))


class RemittanceRoundingTestCase(Base):
    """The fund lines must add up to exactly the amount due, to the fils."""
    def setUp(self):
        super().setUp()
        cash = PaymentMethod.objects.create(name="Cash")
        rent = ExpenseCategory.objects.create(name="Rent")
        d = self.today.replace(day=1)
        # Figures that do not split evenly.
        for name, amount in [("Tithe", "1000.001"), ("Offering", "333.337"), ("Building", "212.119")]:
            Giving.objects.create(date=d, fund=Fund.objects.create(name=name), method=cash,
                                  amount=Decimal(amount), location=self.bahrain)
        Expense.objects.create(date=d, category=rent, amount=Decimal("100.001"),
                               location=self.bahrain)
        self.month = f"{d:%Y-%m}"

    def test_lines_sum_to_the_amount_due(self):
        r = self.client.get(f"/api/remittances/proposed/?month={self.month}")
        total = sum(Decimal(str(l["amount_due"])) for l in r.data["lines"])
        self.assertEqual(total, Decimal(str(r.data["due"])))
        self.assertEqual(Decimal(str(r.data["due"])), Decimal("1445.456"))


class OneTargetTestCase(Base):
    """
    The dashboard and the attendance chart used to read different target
    fields for the same meeting, 150 on one screen and 45 on the other.
    """
    def setUp(self):
        super().setUp()
        from goals.models import Goal
        self.mt = MeetingType.objects.create(
            id="fri-worship", name="Friday Worship", day="Friday",
            frequency="weekly", detail_level="detailed", monthly_target=45)
        self.goal = Goal.objects.create(
            name="Friday attendance", horizon=Goal.Horizon.SHORT, target=150,
            current=0, tracking="auto", calculation_meeting_type=self.mt)

    def test_the_goal_is_the_target(self):
        self.assertEqual(self.mt.effective_target, 150.0)

    def test_the_meeting_figure_is_used_without_a_goal(self):
        self.goal.delete()
        self.assertEqual(self.mt.effective_target, 45.0)

    def test_the_dashboard_and_the_meeting_agree(self):
        dash = self.client.get("/api/dashboard/summary/?meeting=fri-worship").data
        mt = self.client.get("/api/meeting-types/fri-worship/").data
        self.assertEqual(dash["attendance"]["target"], mt["effective_target"])
