import datetime
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User, AuditLog
from attendance.models import MeetingType, AttendanceSession
from finance.models import Fund, PaymentMethod, ExpenseCategory, Giving, Expense
from goals.models import Goal
from newcomers.models import Newcomer, NewcomerSource, NewcomerTask
from .models import Location, AppSetting


class DashboardSummaryTestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.others = Location.objects.create(id="others", name="Others", note="Qatar")

        self.admin = User.objects.create_user(email="admin@test.com", password="x", is_superuser=True)
        coord_role = Role.objects.create(name="Location Coordinator")
        # Phase 4.3: dashboard sections are now gated by real per-module
        # view permission , this fixture grants exactly what these
        # existing tests exercise (attendance/finance/newcomers/goals),
        # so they keep testing location-scoping, a different concern
        # from permission-gating, which gets its own dedicated tests below.
        for module in ["attendance", "finance", "newcomers", "goals"]:
            RolePermission.objects.create(role=coord_role, module=module, can_view=True)
        self.coord = User.objects.create_user(email="coord@test.com", password="x", role=coord_role, location=self.bahrain)

        self.mt = MeetingType.objects.create(id="fri-worship", name="Friday Worship Service",
            day="Friday", frequency="weekly", detail_level="detailed", monthly_target=150)

        # Two locations, two dates, so the "latest date, summed across scope" logic is real
        AttendanceSession.objects.create(meeting_type=self.mt, date=datetime.date(2026, 8, 7),
            location=self.bahrain, mode="in-person", status="filled", men=38, women=52)
        AttendanceSession.objects.create(meeting_type=self.mt, date=datetime.date(2026, 8, 7),
            location=self.others, mode="online", status="filled", men=5, women=7)
        AttendanceSession.objects.create(meeting_type=self.mt, date=datetime.date(2026, 7, 31),
            location=self.bahrain, mode="in-person", status="filled", men=30, women=44)

        self.fund = Fund.objects.create(name="Tithe")
        self.method = PaymentMethod.objects.create(name="Cash")
        self.category = ExpenseCategory.objects.create(name="Rent")
        Giving.objects.create(date=datetime.date(2026, 8, 7), fund=self.fund, method=self.method,
            amount=Decimal("850.000"), location=self.bahrain)
        Giving.objects.create(date=datetime.date(2026, 8, 7), fund=self.fund, method=self.method,
            amount=Decimal("300.000"), location=self.others)
        Expense.objects.create(date=datetime.date(2026, 8, 5), category=self.category,
            amount=Decimal("200.000"), location=self.bahrain)

        source = NewcomerSource.objects.create(name="Website")
        self.n1 = Newcomer.objects.create(name="Bahrain Newcomer", source=source, location=self.bahrain,
            stage="new", created_at=datetime.date.today(), stage_since=datetime.date.today())
        self.n2 = Newcomer.objects.create(name="Qatar Newcomer", source=source, location=self.others,
            stage="new", created_at=datetime.date.today(), stage_since=datetime.date.today())
        NewcomerTask.objects.create(newcomer=self.n1, text="Call back", due_date=datetime.date.today(), done=False)
        NewcomerTask.objects.create(newcomer=self.n2, text="Home visit", due_date=datetime.date.today(), done=False)

        Goal.objects.create(horizon="Short-term", name="Friday Worship attendance (monthly avg)",
            target=150, tracking="auto", period_type="none", source="x",
            calculation_type="latest_session_total", calculation_meeting_type=self.mt)

    def auth(self, user):
        self.client.force_authenticate(user=user)

    # --- Friday Worship: latest date, summed correctly ---

    def test_admin_sees_fw_total_summed_across_all_locations_on_latest_date(self):
        self.auth(self.admin)
        resp = self.client.get("/api/dashboard/summary/")
        self.assertEqual(resp.data["friday_worship"]["total"], 102)  # 38+52+5+7, the LATEST date (Aug 7), both locations
        self.assertEqual(resp.data["friday_worship"]["target"], 150)

    def test_coordinator_sees_fw_total_only_for_their_own_location(self):
        self.auth(self.coord)
        resp = self.client.get("/api/dashboard/summary/")
        self.assertEqual(resp.data["friday_worship"]["total"], 90)  # 38+52 only , Bahrain's Aug 7 session

    def test_fw_trend_excludes_dates_outside_scope_correctly(self):
        self.auth(self.coord)
        resp = self.client.get("/api/dashboard/summary/")
        trend_dates = [t["date"] for t in resp.data["friday_worship"]["trend"]]
        self.assertIn("2026-08-07", trend_dates)
        self.assertIn("2026-07-31", trend_dates)

    # --- Finance: location-scoped totals ---

    def test_admin_sees_giving_total_across_all_locations(self):
        self.auth(self.admin)
        resp = self.client.get("/api/dashboard/summary/")
        self.assertEqual(resp.data["giving_total"], 1150.0)  # 850 + 300

    def test_coordinator_sees_giving_total_only_for_bahrain(self):
        self.auth(self.coord)
        resp = self.client.get("/api/dashboard/summary/")
        self.assertEqual(resp.data["giving_total"], 850.0)

    def test_net_total_computed_correctly(self):
        self.auth(self.coord)
        resp = self.client.get("/api/dashboard/summary/")
        self.assertEqual(resp.data["net_total"], 650.0)  # 850 giving - 200 expense, Bahrain only

    # --- Newcomers: location-scoped pipeline and follow-ups ---

    def test_coordinator_sees_only_their_location_newcomers_and_tasks(self):
        self.auth(self.coord)
        resp = self.client.get("/api/dashboard/summary/")
        self.assertEqual(resp.data["newcomers_in_pipeline"], 1)
        self.assertEqual(len(resp.data["follow_ups_due"]), 1)
        self.assertEqual(resp.data["follow_ups_due"][0]["newcomer_name"], "Bahrain Newcomer")

    def test_admin_sees_all_locations_newcomers(self):
        self.auth(self.admin)
        resp = self.client.get("/api/dashboard/summary/")
        self.assertEqual(resp.data["newcomers_in_pipeline"], 2)

    # --- The important distinction: Goals stay church-wide, NEVER location-filtered ---

    def test_goals_are_not_location_filtered_even_for_a_scoped_coordinator(self):
        """
        Goals have no location field in the approved schema , a
        Coordinator's dashboard must still show the real church-wide
        goal progress, not a location-scoped subset, unlike every other
        stat on this same endpoint.
        """
        self.auth(self.coord)
        resp = self.client.get("/api/dashboard/summary/")
        fw_goal = next(g for g in resp.data["short_term_goals"] if "Friday Worship" in g["name"])
        # The goal's own calculation is church-wide (all-time, all-location
        # latest session), so it must equal the ADMIN's fw total (102),
        # not the coordinator's own location-scoped fw total (90).
        self.assertEqual(fw_goal["current"], 102.0,
            "Goal progress must stay church-wide even on a location-scoped user's dashboard.")

    # --- Auth ---

    def test_unauthenticated_request_denied(self):
        resp = self.client.get("/api/dashboard/summary/")
        self.assertEqual(resp.status_code, 401)

    # --- Phase 4.3: sections are gated by real per-module permission ---

    def test_user_without_finance_permission_does_not_see_finance_data(self):
        members_only_role = Role.objects.create(name="Members Only")
        RolePermission.objects.create(role=members_only_role, module="members", can_view=True)
        user = User.objects.create_user(email="members_only@test.com", password="x",
            role=members_only_role, location=self.bahrain)
        self.auth(user)
        resp = self.client.get("/api/dashboard/summary/")
        self.assertEqual(resp.status_code, 200, "The Dashboard itself stays open to any authenticated user.")
        self.assertFalse(resp.data["finance_access"])
        self.assertNotIn("giving_total", resp.data,
            "A restricted section must be entirely omitted, not present with a zero or null value.")
        self.assertNotIn("giving_by_fund", resp.data)

    def test_user_without_any_of_the_four_gated_modules_sees_only_access_flags(self):
        bare_role = Role.objects.create(name="Bare Role")
        user = User.objects.create_user(email="bare@test.com", password="x", role=bare_role, location=self.bahrain)
        self.auth(user)
        resp = self.client.get("/api/dashboard/summary/")
        self.assertEqual(resp.status_code, 200)
        for flag in ["attendance_access", "finance_access", "newcomers_access", "goals_access"]:
            self.assertFalse(resp.data[flag])
        for real_data_key in ["friday_worship", "giving_total", "newcomers_in_pipeline", "short_term_goals"]:
            self.assertNotIn(real_data_key, resp.data)

    def test_user_with_only_finance_permission_sees_only_that_section(self):
        finance_only_role = Role.objects.create(name="Finance Only")
        RolePermission.objects.create(role=finance_only_role, module="finance", can_view=True)
        user = User.objects.create_user(email="finance_only@test.com", password="x",
            role=finance_only_role, location=self.bahrain)
        self.auth(user)
        resp = self.client.get("/api/dashboard/summary/")
        self.assertTrue(resp.data["finance_access"])
        self.assertIn("giving_total", resp.data)
        self.assertFalse(resp.data["attendance_access"])
        self.assertNotIn("friday_worship", resp.data)

    def test_superuser_sees_every_section_regardless_of_role(self):
        """A superuser bypasses role checks entirely , same rule every
        other permission check in the app already follows."""
        self.auth(self.admin)
        resp = self.client.get("/api/dashboard/summary/")
        for flag in ["attendance_access", "finance_access", "newcomers_access", "goals_access"]:
            self.assertTrue(resp.data[flag])


class AppSettingsAPITestCase(APITestCase):
    """
    Church-wide switches. Any authenticated user may read them (the
    assignment screen needs the current state to label itself), but only
    administrators may change them.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)

        admin_role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=admin_role, module="admin",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@t.com", password="x", role=admin_role)

        plain_role = Role.objects.create(name="Recorder")
        RolePermission.objects.create(role=plain_role, module="attendance", can_view=True)
        self.plain = User.objects.create_user(email="plain@t.com", password="x", role=plain_role)

    def test_defaults_when_nothing_has_been_set(self):
        self.client.force_authenticate(user=self.plain)
        resp = self.client.get("/api/settings/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["auto_assign_newcomers"],
            "Newcomers should be included in auto-assign unless switched off.")

    def test_admin_can_change_a_setting(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch("/api/settings/", {"auto_assign_newcomers": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["auto_assign_newcomers"])
        self.assertFalse(AppSetting.get_bool("auto_assign_newcomers", True))

    def test_non_admin_cannot_change_a_setting(self):
        self.client.force_authenticate(user=self.plain)
        resp = self.client.patch("/api/settings/", {"auto_assign_newcomers": False}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(AppSetting.get_bool("auto_assign_newcomers", True),
            "A rejected request must not have changed anything.")

    def test_unauthenticated_cannot_read(self):
        resp = self.client.get("/api/settings/")
        self.assertIn(resp.status_code, (401, 403))

    def test_unknown_key_is_rejected(self):
        """Silently ignoring an unknown key would let a typo look like it
        saved. Better to fail loudly."""
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch("/api/settings/", {"nonexistent_switch": True}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_non_boolean_value_is_rejected(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch("/api/settings/", {"auto_assign_newcomers": "yes"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_change_is_audited(self):
        from accounts.models import AuditLog
        self.client.force_authenticate(user=self.admin)
        self.client.patch("/api/settings/", {"auto_assign_newcomers": False}, format="json")
        self.assertTrue(
            AuditLog.objects.filter(entity_type="Setting", entity_name="auto_assign_newcomers").exists(),
            "Changing a church-wide setting should be traceable.",
        )


class DemoRolePermissionsTestCase(TestCase):
    """
    The two demo roles must genuinely differ in which modules they can
    see, not only in what they may edit.

    Found in acceptance testing: a Location Coordinator could open Admin,
    Finance and Outreach, because can_view was set True for every module
    on both roles. That is wrong on its own, and it also made the
    permission tests impossible to run, since no role existed that lacked
    finance or outreach to test against.
    """
    def test_the_coordinator_cannot_see_admin_finance_or_outreach(self):
        call_command("seed_demo_data", verbosity=0)
        coord = Role.objects.get(name="Location Coordinator")
        modules = set(RolePermission.objects.filter(
            role=coord, can_view=True).values_list("module", flat=True))
        for forbidden in ("admin", "finance", "outreach"):
            self.assertNotIn(forbidden, modules,
                             f"A Location Coordinator should not be able to view {forbidden}")

    def test_the_administrator_can_see_everything(self):
        call_command("seed_demo_data", verbosity=0)
        admin = Role.objects.get(name="Administrator")
        modules = set(RolePermission.objects.filter(
            role=admin, can_view=True).values_list("module", flat=True))
        for expected in ("admin", "finance", "outreach", "members",
                         "attendance", "newcomers", "goals", "reports"):
            self.assertIn(expected, modules)

    def test_the_two_roles_are_not_identical(self):
        """The whole point of a second demo role is having something to
        test permission rules against."""
        call_command("seed_demo_data", verbosity=0)
        def mods(name):
            return set(RolePermission.objects.filter(
                role__name=name, can_view=True).values_list("module", flat=True))
        self.assertNotEqual(mods("Administrator"), mods("Location Coordinator"))


class AuditNoDuplicateEntriesTestCase(APITestCase):
    """
    One action, one audit entry, attributed to the person who did it.

    Found through a test failing on a developer's machine and not on
    mine. Creating a member wrote two entries: post_save fires during
    the save, but a view calls log_audit() with the instance after it, so
    the suppression check always came too late for a creation. One entry
    named the real user, the other said "System", which reads as though
    the software acted on its own.

    The test that caught it asserted on .first(), and the two rows were
    milliseconds apart. On Linux they sorted predictably; on Windows,
    with coarser timestamps, they did not, so the test passed here and
    failed there. The flakiness was the symptom; the duplicate was the
    fault.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        role = Role.objects.create(name="Administrator")
        for module in ["members", "attendance", "newcomers", "finance",
                       "goals", "reports", "outreach", "admin"]:
            RolePermission.objects.create(
                role=role, module=module,
                can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(
            email="auditor@test.com", password="x", role=role)
        self.client.force_authenticate(user=self.admin)

    def test_creating_a_member_writes_exactly_one_entry(self):
        AuditLog.objects.all().delete()
        resp = self.client.post("/api/members/", {
            "surname": "Noor", "first_name": "Fatima", "location": "bahrain",
            "joined_date": "2024-09-14"})
        self.assertEqual(resp.status_code, 201)
        entries = AuditLog.objects.filter(entity_type="Member", entity_name="Fatima Noor")
        self.assertEqual(entries.count(), 1,
                         "One action should produce one entry, not a generic one alongside a specific one")

    def test_the_entry_names_the_person_not_the_system(self):
        AuditLog.objects.all().delete()
        self.client.post("/api/members/", {
            "surname": "Noor", "first_name": "Fatima", "location": "bahrain",
            "joined_date": "2024-09-14"})
        entry = AuditLog.objects.get(entity_type="Member", entity_name="Fatima Noor")
        self.assertNotEqual(entry.user_name_snapshot, "System",
                            'An action taken by a signed-in user must not be credited to "System"')
        self.assertEqual(entry.user_name_snapshot, "auditor@test.com")

    def test_result_does_not_depend_on_row_ordering(self):
        """The original test only passed because the rows happened to sort
        the right way. With one row there is nothing to sort."""
        AuditLog.objects.all().delete()
        self.client.post("/api/members/", {
            "surname": "Bello", "first_name": "Peace", "location": "bahrain",
            "joined_date": "2024-09-14"})
        rows = AuditLog.objects.filter(entity_name="Peace Bello")
        self.assertEqual(rows.count(), 1)
        for ordering in ("timestamp", "-timestamp", "id", "-id"):
            self.assertEqual(rows.order_by(ordering).first().user_name_snapshot,
                             "auditor@test.com")

    def test_an_action_with_no_signed_in_user_still_records_as_system(self):
        """The System label is correct when nobody was signed in, for
        example a scheduled job. It should not disappear entirely."""
        from accounts.audit import log_audit
        AuditLog.objects.all().delete()
        log_audit(None, "Created", "Member", "Someone")
        self.assertEqual(AuditLog.objects.get().user_name_snapshot, "System")
