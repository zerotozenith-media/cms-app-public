import datetime

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User
from attendance.models import MeetingType, AttendanceSession
from core.models import Location
from members.models import Household, Member, MemberCategoryHistory
from newcomers.models import MilestoneType, Newcomer, NewcomerMilestone, NewcomerSource, NewcomerTask
from reports.models import Service, Testimony
from .calculations import period_bounds, compute_goal_value
from .models import Goal


class PeriodBoundsTestCase(TestCase):
    def test_month_bounds_cover_the_whole_current_month(self):
        start, end = period_bounds("month")
        today = timezone.localdate()
        self.assertEqual(start.month, today.month)
        self.assertEqual(end.month, today.month)
        self.assertEqual(start.day, 1)

    def test_quarter_bounds_are_three_months_wide(self):
        start, end = period_bounds("quarter")
        self.assertEqual((end.year - start.year) * 12 + (end.month - start.month), 2)

    def test_none_returns_no_bounds(self):
        self.assertEqual(period_bounds("none"), (None, None))


class GoalCalculationTestCase(TestCase):
    """
    Direct tests of the calculation engine against real underlying data ,
    this is the core of what Batch 2.5 exists to fix: auto-tracked goals
    that claim a time period must actually filter by it.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.mt = MeetingType.objects.create(id="fri-worship", name="Friday Worship", day="Friday",
            frequency="weekly", detail_level="detailed", monthly_target=150)
        self.member = Member.objects.create(surname="Uguru", first_name="Chinedu",
            location=self.bahrain, joined_date=datetime.date(2019, 3, 10))
        self.salvation = MilestoneType.objects.create(name="Salvation")
        self.source = NewcomerSource.objects.create(name="Test")
        self.today = timezone.localdate()

    def test_latest_session_total_sums_across_locations_on_the_same_date(self):
        qatar = Location.objects.create(id="others", name="Others")
        AttendanceSession.objects.create(meeting_type=self.mt, date=self.today, location=self.bahrain,
            mode="in-person", status="filled", men=38, women=52)
        AttendanceSession.objects.create(meeting_type=self.mt, date=self.today, location=qatar,
            mode="online", status="filled", men=5, women=7)
        goal = Goal.objects.create(horizon="Short-term", name="FW", target=150, tracking="auto",
            period_type="none", source="x", calculation_type="latest_session_total",
            calculation_meeting_type=self.mt)
        self.assertEqual(compute_goal_value(goal), 102)  # 38+52+5+7

    def test_testimony_count_excludes_outside_period_month(self):
        Testimony.objects.create(date=self.today, service=Service.objects.create(name="Sunday"), text="In period")
        Testimony.objects.create(
            date=self.today.replace(day=1) - datetime.timedelta(days=40),  # definitely last month or earlier
            service=Service.objects.get(name="Sunday"), text="Out of period",
        )
        goal = Goal.objects.create(horizon="Short-term", name="Testimonies", target=6, tracking="auto",
            period_type="month", source="x", calculation_type="testimony_count")
        self.assertEqual(compute_goal_value(goal), 1)

    def test_member_category_moves_respects_quarter_boundary(self):
        MemberCategoryHistory.objects.create(member=self.member, from_category="General Member",
            to_category="Worker in Training", changed_date=self.today)  # inside current quarter
        MemberCategoryHistory.objects.create(member=self.member, from_category="General Member",
            to_category="Worker in Training", changed_date=self.today.replace(year=self.today.year - 1))  # a year ago
        goal = Goal.objects.create(horizon="Medium-term", name="Moves", target=5, tracking="auto",
            period_type="quarter", source="x", calculation_type="member_category_moves",
            calculation_target_category="Worker in Training")
        self.assertEqual(compute_goal_value(goal), 1)

    def test_the_exact_bug_this_batch_fixes_quarter_and_year_goals_now_genuinely_differ(self):
        """
        Batch 0.5's core finding: 'Workers in Training moved to Worker
        (quarter)' and 'New workers raised and deployed (year)' ran the
        IDENTICAL all-time calculation in the demo, despite claiming
        different time windows. This proves they now genuinely differ
        when the data actually differs between the two windows.
        """
        # One move this quarter
        MemberCategoryHistory.objects.create(member=self.member, from_category="Worker in Training",
            to_category="Worker", changed_date=self.today)
        # One move last year (inside the YEAR-goal's window only if this
        # year, so use two years ago to be unambiguously outside both)
        old_member = Member.objects.create(surname="Old", first_name="Move", location=self.bahrain,
            joined_date=datetime.date(2015, 1, 1))
        two_years_ago = self.today.replace(year=self.today.year - 2)
        MemberCategoryHistory.objects.create(member=old_member, from_category="Worker in Training",
            to_category="Worker", changed_date=two_years_ago)

        quarter_goal = Goal.objects.create(horizon="Medium-term", name="Quarter goal", target=3,
            tracking="auto", period_type="quarter", source="x",
            calculation_type="member_category_moves", calculation_target_category="Worker")
        year_goal = Goal.objects.create(horizon="Long-term", name="Year goal", target=10,
            tracking="auto", period_type="year", source="x",
            calculation_type="member_category_moves", calculation_target_category="Worker")

        self.assertEqual(compute_goal_value(quarter_goal), 1, "Only this quarter's move should count.")
        self.assertEqual(compute_goal_value(year_goal), 1, "Only this year's move should count (the 2-year-old one shouldn't).")
        # Both happen to be 1 here by construction, so also prove they're
        # independently computed, not coincidentally sharing logic:
        MemberCategoryHistory.objects.create(member=self.member, from_category="Worker in Training",
            to_category="Worker", changed_date=self.today)  # a 2nd move, still this quarter AND this year
        self.assertEqual(compute_goal_value(quarter_goal), 2)
        self.assertEqual(compute_goal_value(year_goal), 2)
        # Now add one more move outside the current quarter but still this year
        # (only valid if we're not in Q1 , guard for test stability)
        if self.today.month > 3:
            earlier_this_year = self.today.replace(month=1, day=15)
            MemberCategoryHistory.objects.create(member=self.member, from_category="Worker in Training",
                to_category="Worker", changed_date=earlier_this_year)
            self.assertEqual(compute_goal_value(quarter_goal), 2, "Must not count a move from earlier this year, outside the current quarter.")
            self.assertEqual(compute_goal_value(year_goal), 3, "Must count it for the year-scoped goal though.")

    def test_milestone_count_only_counts_achieved_within_period(self):
        n = Newcomer.objects.create(name="Jane", source=self.source, location=self.bahrain,
            created_at=self.today, stage_since=self.today)
        NewcomerMilestone.objects.create(newcomer=n, milestone_type=self.salvation, achieved_date=self.today)
        goal = Goal.objects.create(horizon="Spiritual growth", name="Salvations", target=10, tracking="auto",
            period_type="month", source="x", calculation_type="milestone_count",
            calculation_milestone_type=self.salvation)
        self.assertEqual(compute_goal_value(goal), 1)

    def test_task_completion_rate(self):
        n = Newcomer.objects.create(name="Jane", source=self.source, location=self.bahrain,
            created_at=self.today, stage_since=self.today)
        NewcomerTask.objects.create(newcomer=n, text="A", due_date=self.today, done=True)
        NewcomerTask.objects.create(newcomer=n, text="B", due_date=self.today, done=False)
        goal = Goal.objects.create(horizon="Short-term", name="Tasks", target=100, tracking="auto",
            period_type="none", source="x", calculation_type="task_completion_rate")
        self.assertEqual(compute_goal_value(goal), 50)

    def test_manual_goal_computation_returns_none(self):
        goal = Goal.objects.create(horizon="Long-term", name="Manual", target=15, tracking="manual",
            period_type="none", source="x", current=9)
        self.assertIsNone(compute_goal_value(goal))


class GoalAPITestCase(APITestCase):
    def setUp(self):
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="goals",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@test.com", password="x", role=self.role)

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_manual_goal_current_value_is_the_stored_current_field(self):
        goal = Goal.objects.create(horizon="Long-term", name="Manual Goal", target=15,
            tracking="manual", period_type="none", source="x", current=9)
        self.auth(self.admin)
        resp = self.client.get(f"/api/goals/{goal.id}/")
        self.assertEqual(resp.data["current_value"], 9)
        self.assertIsNone(resp.data["calculation_error"])

    def test_auto_goal_missing_calculation_type_surfaces_a_real_error(self):
        goal = Goal.objects.create(horizon="Short-term", name="Misconfigured", target=10,
            tracking="auto", period_type="none", source="x")  # no calculation_type set
        self.auth(self.admin)
        resp = self.client.get(f"/api/goals/{goal.id}/")
        self.assertIsNotNone(resp.data["calculation_error"],
            "A misconfigured auto goal must surface a real error, not silently show 0.")

    def test_updating_manual_goal_progress_writes_audit_log(self):
        from accounts.models import AuditLog
        goal = Goal.objects.create(horizon="Long-term", name="Manual", target=15,
            tracking="manual", period_type="none", source="x", current=9)
        self.auth(self.admin)
        AuditLog.objects.all().delete()
        self.client.patch(f"/api/goals/{goal.id}/", {"current": 11})
        self.assertTrue(AuditLog.objects.filter(action="Updated progress", entity_name="Manual").exists())


class SeedGoalsCommandTestCase(TestCase):
    def setUp(self):
        MeetingType.objects.create(id="fri-worship", name="Friday Worship Service", day="Friday",
            frequency="weekly", detail_level="detailed", monthly_target=150)
        MeetingType.objects.create(id="mon-bs", name="Monday Bible Study", day="Monday",
            frequency="weekly", detail_level="detailed", monthly_target=60)
        MilestoneType.objects.create(name="Salvation")
        MilestoneType.objects.create(name="Water Baptism")

    def test_seeds_exactly_fourteen_goals(self):
        call_command("seed_default_goals")
        self.assertEqual(Goal.objects.count(), 14)

    def test_idempotent(self):
        call_command("seed_default_goals")
        call_command("seed_default_goals")
        self.assertEqual(Goal.objects.count(), 14)

    def test_correct_mix_of_auto_and_manual(self):
        call_command("seed_default_goals")
        self.assertEqual(Goal.objects.filter(tracking="auto").count(), 9)
        self.assertEqual(Goal.objects.filter(tracking="manual").count(), 5)


class AutomaticGoalsTestCase(APITestCase):
    """Item 11 (Kay, 26 October 2026): goals that update themselves from the records."""

    def setUp(self):
        import datetime
        from django.utils import timezone
        from accounts.models import Role, RolePermission, User
        from attendance.models import AttendanceSession, MeetingType
        from core.models import Location
        from finance.models import Expense, ExpenseCategory, Fund, Giving, PaymentMethod
        self.bh = Location.objects.get_or_create(id="bahrain", defaults={"name": "Bahrain HQ", "is_core": True})[0]
        self.qa = Location.objects.get_or_create(id="others", defaults={"name": "Qatar"})[0]
        self.asia = MeetingType.objects.create(id="asia", name="Asia Fellowship", day="Saturday", frequency="weekly",
                                              detail_level="simple")
        today = timezone.localdate()
        for loc, total in ((self.bh, 8), (self.bh, 12), (self.qa, 30)):
            s = AttendanceSession.objects.create(meeting_type=self.asia, date=today - datetime.timedelta(days=len(
                AttendanceSession.objects.all())), location=loc, mode="in-person", status="filled")
            AttendanceSession.objects.filter(pk=s.pk).update(men=total)
        self.tithe = Fund.objects.get_or_create(name="Tithe")[0]
        cash = PaymentMethod.objects.get_or_create(name="Cash")[0]
        Giving.objects.create(date=today, fund=self.tithe, method=cash, amount=100, location=self.bh)
        Giving.objects.create(date=today, fund=self.tithe, method=cash, amount=50, location=self.qa)
        cat = ExpenseCategory.objects.get_or_create(name="Rent")[0]
        Expense.objects.create(date=today, category=cat, amount=30, location=self.bh)
        role = Role.objects.get_or_create(name="Administrator")[0]
        RolePermission.objects.update_or_create(role=role, module="goals", defaults=dict(can_view=True, can_create=True, can_edit=True))
        self.client.force_authenticate(User.objects.create_user(email="a@t.com", password="x", role=role))

    def make(self, **kw):
        body = dict(name="Goal", horizon="Short-term", target=10, tracking="auto", source="Auto")
        body.setdefault("period_type", "month")
        body.update(kw)
        return self.client.post("/api/goals/", body, format="json")

    def test_measures_and_location(self):
        r = self.make(calculation_type="sessions_held", calculation_meeting_type="asia", calculation_location="bahrain",
                      period_type="none")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["current_value"], 2)
        self.assertEqual(r.data["measure_note"], "Asia Fellowship sessions held at Bahrain HQ")
        r = self.make(calculation_type="fund_total", calculation_fund=self.tithe.id)
        self.assertEqual(float(r.data["current_value"]), 150)
        r = self.make(calculation_type="net_giving", calculation_location="bahrain")
        self.assertEqual(float(r.data["current_value"]), 70)

    def test_a_measure_needs_its_meeting(self):
        r = self.make(calculation_type="sessions_held")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["calculation_meeting_type"], ["Choose the meeting."])
