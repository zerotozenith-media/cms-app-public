"""
Tests for shepherd assignment. This decides who is responsible for whom
across the whole church, so each confirmed rule gets its own test rather
than relying on one happy-path check.
"""
import datetime

from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User, AuditLog
from core.models import Location, AppSetting
from newcomers.models import Newcomer, NewcomerSource
from .models import Member, Household, MemberFollowUpTask
from .assignment import build_assignment_preview, apply_assignment_changes


class AssignmentEngineTestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        role = Role.objects.create(name="Administrator")
        for mod in ["members", "newcomers"]:
            RolePermission.objects.create(role=role, module=mod,
                can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin_as@test.com", password="x", role=role, is_superuser=True)
        self.role = role

        # A shepherd is a User account linked to a Member in the Worker
        # category, since tasks are assigned to whoever logs in.
        self.m1 = Member.objects.create(surname="Thomas", first_name="Grace", location=self.bahrain,
            joined_date=datetime.date(2018, 1, 1), category=Member.Category.WORKER)
        self.m2 = Member.objects.create(surname="Osei", first_name="Sarah", location=self.bahrain,
            joined_date=datetime.date(2017, 1, 1), category=Member.Category.WORKER)
        self.w1 = User.objects.create_user(email="grace@test.com", password="x", role=role,
            first_name="Grace", last_name="Thomas", member=self.m1)
        self.w2 = User.objects.create_user(email="sarah@test.com", password="x", role=role,
            first_name="Sarah", last_name="Osei", member=self.m2)
        self.source = NewcomerSource.objects.create(name="Church website")

    def auth(self):
        self.client.force_authenticate(user=self.admin)

    def _member(self, surname, **kw):
        return Member.objects.create(surname=surname, first_name="Test", location=self.bahrain,
            joined_date=datetime.date(2024, 1, 1), **kw)

    # --- Core rules ---

    def test_household_takes_priority_over_load_balancing(self):
        hh = Household.objects.create(name="Adeyinka Household")
        self._member("Adeyinka", household=hh, assigned_to=self.w1)
        target = self._member("Adeyinka2", household=hh)
        changes, err = build_assignment_preview()
        self.assertIsNone(err)
        change = next(c for c in changes if c["id"] == target.id)
        self.assertEqual(change["to_id"], self.w1.id)
        self.assertEqual(change["reason"], "Household")

    def test_load_balancing_spreads_people_across_workers(self):
        for i in range(4):
            self._member(f"Person{i}")
        changes, _ = build_assignment_preview()
        assigned = [c["to_id"] for c in changes if c["kind"] == "member"]
        self.assertGreater(len(set(assigned)), 1, "Should not pile everyone onto one worker")

    def test_only_workers_can_be_shepherds(self):
        self._member("General", category=Member.Category.GENERAL)
        self._member("InTraining", category=Member.Category.IN_TRAINING)
        changes, _ = build_assignment_preview()
        worker_ids = {self.w1.id, self.w2.id}  # User ids
        for c in changes:
            self.assertIn(c["to_id"], worker_ids)

    def test_error_when_no_workers_exist(self):
        Member.objects.filter(category=Member.Category.WORKER).delete()
        self._member("Somebody")
        changes, err = build_assignment_preview()
        self.assertEqual(changes, [])
        self.assertIn("No Workers available", err)

    # --- Only-unassigned vs reassign-everyone ---

    def test_default_leaves_existing_pairings_alone(self):
        deliberate = self._member("Paired", assigned_to=self.w2)
        changes, _ = build_assignment_preview(reassign_everyone=False)
        self.assertFalse(any(c["id"] == deliberate.id and c["kind"] == "member" for c in changes),
            "A deliberate pairing must not be touched by default")

    def test_reassign_everyone_includes_already_assigned_people(self):
        for i in range(4):
            self._member(f"Loaded{i}", assigned_to=self.w1)
        changes, _ = build_assignment_preview(reassign_everyone=True)
        self.assertTrue(any(c["kind"] == "member" for c in changes),
            "Reassign everyone should propose moving people off an overloaded worker")

    # --- Preview never writes ---

    def test_preview_does_not_save_anything(self):
        m = self._member("Untouched")
        build_assignment_preview()
        m.refresh_from_db()
        self.assertIsNone(m.assigned_to, "Preview must never write")

    def test_apply_commits_the_changes(self):
        m = self._member("ToAssign")
        changes, _ = build_assignment_preview()
        apply_assignment_changes(changes)
        m.refresh_from_db()
        self.assertIsNotNone(m.assigned_to)

    # --- Newcomer toggle ---

    def test_newcomers_included_by_default(self):
        Newcomer.objects.create(name="New Person", source=self.source, location=self.bahrain,
            stage="new", created_at=datetime.date.today(), stage_since=datetime.date.today())
        changes, _ = build_assignment_preview()
        self.assertTrue(any(c["kind"] == "newcomer" for c in changes))

    def test_newcomers_excluded_when_setting_is_off(self):
        AppSetting.set_bool("auto_assign_newcomers", False)
        Newcomer.objects.create(name="New Person", source=self.source, location=self.bahrain,
            stage="new", created_at=datetime.date.today(), stage_since=datetime.date.today())
        changes, _ = build_assignment_preview()
        self.assertFalse(any(c["kind"] == "newcomer" for c in changes))

    def test_not_interested_newcomers_are_skipped(self):
        Newcomer.objects.create(name="Gone Away", source=self.source, location=self.bahrain,
            stage="not-interested", created_at=datetime.date.today(), stage_since=datetime.date.today())
        changes, _ = build_assignment_preview()
        self.assertFalse(any(c["kind"] == "newcomer" for c in changes))

    # --- API ---

    def test_preview_endpoint_returns_changes_without_saving(self):
        m = self._member("ApiPreview")
        self.auth()
        resp = self.client.get("/api/members/assign-shepherds/")
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(resp.data["count"], 0)
        m.refresh_from_db()
        self.assertIsNone(m.assigned_to)

    def test_apply_endpoint_saves_and_audits(self):
        self._member("ApiApply")
        AuditLog.objects.all().delete()
        self.auth()
        resp = self.client.post("/api/members/assign-shepherds/", {})
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(resp.data["applied_members"], 0)
        self.assertTrue(AuditLog.objects.filter(action="Auto-assigned shepherds").exists())

    def test_apply_twice_reports_nothing_left(self):
        self._member("Once")
        self.auth()
        self.client.post("/api/members/assign-shepherds/", {})
        resp = self.client.post("/api/members/assign-shepherds/", {})
        self.assertEqual(resp.data["applied_members"], 0)
        self.assertIn("Nothing to assign", resp.data["detail"])

    def test_bulk_assign_sets_shepherd_on_all_selected(self):
        a = self._member("BulkA")
        b = self._member("BulkB")
        self.auth()
        resp = self.client.post("/api/members/bulk-assign-shepherd/",
            {"member_ids": [a.id, b.id], "shepherd_id": self.w1.id}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["updated"], 2)
        a.refresh_from_db(); b.refresh_from_db()
        self.assertEqual(a.assigned_to, self.w1)
        self.assertEqual(b.assigned_to, self.w1)

    def test_bulk_assign_rejects_a_non_worker_shepherd(self):
        general_member = self._member("NotAWorker", category=Member.Category.GENERAL)
        general_user = User.objects.create_user(email="general@test.com", password="x",
            role=self.role, member=general_member)
        target = self._member("Target")
        self.auth()
        resp = self.client.post("/api/members/bulk-assign-shepherd/",
            {"member_ids": [target.id], "shepherd_id": general_user.id}, format="json")
        self.assertEqual(resp.status_code, 400)
        target.refresh_from_db()
        self.assertIsNone(target.assigned_to)

    # --- Regressions found by end-to-end testing, not unit tests ---

    def test_a_worker_is_never_their_own_shepherd(self):
        """Found live: the only unassigned worker was proposed as her own
        shepherd, because she was also the least loaded candidate."""
        # w1's member record has no shepherd yet, so it is in scope
        changes, _ = build_assignment_preview()
        for c in changes:
            if c["kind"] == "member" and c["id"] == self.m1.id:
                self.assertNotEqual(c["to_id"], self.w1.id,
                    "A worker must never be assigned as their own shepherd")

    def test_household_pairs_even_when_nobody_is_assigned_yet(self):
        """Found live: a household where neither person had a shepherd
        never paired up, because the rule only looked at saved data."""
        hh = Household.objects.create(name="Fresh Household")
        a = self._member("FreshA", household=hh)
        b = self._member("FreshB", household=hh)
        changes, _ = build_assignment_preview()
        ca = next(c for c in changes if c["id"] == a.id and c["kind"] == "member")
        cb = next(c for c in changes if c["id"] == b.id and c["kind"] == "member")
        self.assertEqual(ca["to_id"], cb["to_id"],
            "Both members of a household should get the same shepherd in one run")
        self.assertEqual(cb["reason"], "Household")

    def test_preview_shows_real_names_not_email_addresses(self):
        """
        Found while testing the live endpoint rather than in unit tests:
        the preview showed "grace@dclm-bh.org" where a reviewer expects
        "Grace Thomas". User.first_name/last_name are often blank when
        accounts are created quickly, and the old helper fell straight
        through to email. The linked member record always has a real
        name, so it is preferred now.
        """
        User.objects.filter(id=self.w2.id).update(first_name="", last_name="")
        self._member("Someone", category=Member.Category.GENERAL)
        changes, err = build_assignment_preview()
        self.assertIsNone(err)
        self.assertTrue(changes, "Expected at least one proposed change")
        for c in changes:
            self.assertNotIn("@", c["to_name"],
                f"Shepherd name should be a person's name, got {c['to_name']!r}")


class EligibleShepherdsEndpointTestCase(APITestCase):
    """
    The bulk-assign dropdown must offer exactly who the engine accepts.
    If it listed anyone else, an admin could pick a person and get a
    rejection with no obvious reason.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=role, module="members",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@t.com", password="x", role=role)

        worker = Member.objects.create(surname="Osei", first_name="Sarah", location=self.bahrain,
            joined_date=datetime.date(2020, 1, 1), category=Member.Category.WORKER)
        self.worker_user = User.objects.create_user(email="sarah@t.com", password="x", role=role)
        self.worker_user.member = worker
        self.worker_user.save()

        general = Member.objects.create(surname="Noor", first_name="Fatima", location=self.bahrain,
            joined_date=datetime.date(2024, 1, 1), category=Member.Category.GENERAL)
        self.general_user = User.objects.create_user(email="fatima@t.com", password="x", role=role)
        self.general_user.member = general
        self.general_user.save()

    def test_lists_only_workers(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/members/eligible-shepherds/")
        self.assertEqual(resp.status_code, 200)
        ids = [s["id"] for s in resp.data]
        self.assertIn(self.worker_user.id, ids)
        self.assertNotIn(self.general_user.id, ids,
            "A General Member must never be offered as a shepherd.")

    def test_uses_real_names_not_emails(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/members/eligible-shepherds/")
        names = [s["name"] for s in resp.data]
        self.assertIn("Sarah Osei", names)
        self.assertFalse(any("@" in n for n in names))

    def test_requires_authentication(self):
        resp = self.client.get("/api/members/eligible-shepherds/")
        self.assertIn(resp.status_code, (401, 403))
