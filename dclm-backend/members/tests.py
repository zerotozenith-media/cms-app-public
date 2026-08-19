import datetime

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User
from core.models import Location
from .models import Household, Member, MemberCategoryHistory, MemberFollowUpTask


class MembersAPITestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.others = Location.objects.create(id="others", name="Others", note="Qatar")

        self.admin_role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.admin_role, module="members",
            can_view=True, can_create=True, can_edit=True, can_delete=True)

        self.coord_role = Role.objects.create(name="Location Coordinator")
        RolePermission.objects.create(role=self.coord_role, module="members",
            can_view=True, can_create=True, can_edit=True, can_delete=False)

        self.viewer_role = Role.objects.create(name="Viewer")
        RolePermission.objects.create(role=self.viewer_role, module="members",
            can_view=True, can_create=False, can_edit=False, can_delete=False)

        self.admin = User.objects.create_user(email="admin@test.com", password="x", role=self.admin_role)
        self.coord = User.objects.create_user(email="coord@test.com", password="x", role=self.coord_role, location=self.bahrain)
        self.viewer = User.objects.create_user(email="viewer@test.com", password="x", role=self.viewer_role, location=self.bahrain)

        self.hh = Household.objects.create(name="Uguru Household")
        self.bahrain_member = Member.objects.create(
            surname="Uguru", first_name="Chinedu", location=self.bahrain,
            household=self.hh, joined_date=datetime.date(2019, 3, 10),
        )
        self.qatar_member = Member.objects.create(
            surname="Karim", first_name="Ali", location=self.others,
            joined_date=datetime.date(2023, 4, 19),
        )

    def auth(self, user):
        self.client.force_authenticate(user=user)

    # --- Authentication / permission enforcement ---

    def test_unauthenticated_request_denied(self):
        resp = self.client.get("/api/members/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_viewer_can_list_but_not_create(self):
        self.auth(self.viewer)
        resp = self.client.get("/api/members/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp2 = self.client.post("/api/members/", {
            "surname": "Test", "first_name": "New", "location": "bahrain",
            "joined_date": "2026-01-01",
        })
        self.assertEqual(resp2.status_code, status.HTTP_403_FORBIDDEN)

    def test_coordinator_can_create_but_not_delete(self):
        self.auth(self.coord)
        resp = self.client.post("/api/members/", {
            "surname": "Osei", "first_name": "Sarah", "location": "bahrain",
            "joined_date": "2017-05-06",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        resp2 = self.client.delete(f"/api/members/{self.bahrain_member.id}/")
        self.assertEqual(resp2.status_code, status.HTTP_403_FORBIDDEN)

    # --- Location scoping ---

    def test_coordinator_only_sees_own_location(self):
        self.auth(self.coord)
        resp = self.client.get("/api/members/")
        names = [m["surname"] for m in resp.data["results"]] if "results" in resp.data else [m["surname"] for m in resp.data]
        self.assertIn("Uguru", names)
        self.assertNotIn("Karim", names)

    # --- Category filtering (Batch 3.4 finding: the demo's filtering was
    # entirely client-side against a small mock array , added real
    # server-side filtering here, since a real member list won't stay small) ---

    def test_filter_by_category(self):
        self.auth(self.admin)
        Member.objects.create(surname="Osei", first_name="Sarah", location=self.bahrain,
            joined_date=datetime.date.today(), category="Worker")
        resp = self.client.get("/api/members/?category=Worker")
        results = resp.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["surname"], "Osei")

    def test_category_filter_composes_correctly_with_location_scoping(self):
        """
        The two filters must compose, not just work independently , a
        Coordinator filtering by category must still only see their own
        location's members, never another location's Workers leaking
        through because the category filter was applied without the
        location scope still in effect.
        """
        Member.objects.create(surname="Qatar", first_name="Worker", location=self.others,
            joined_date=datetime.date.today(), category="Worker")
        self.auth(self.coord)
        resp = self.client.get("/api/members/?category=Worker")
        surnames = [m["surname"] for m in resp.data["results"]]
        self.assertNotIn("Qatar", surnames, "Location scoping must still apply even when a category filter is also active.")

    def test_ordering_by_category(self):
        self.auth(self.admin)
        resp = self.client.get("/api/members/?ordering=category")
        self.assertEqual(resp.status_code, 200)

    def test_coordinator_cannot_fetch_other_location_member_directly(self):
        self.auth(self.coord)
        resp = self.client.get(f"/api/members/{self.qatar_member.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND,
            "A Bahrain coordinator must not be able to retrieve a Qatar member even by guessing the ID.")

    def test_administrator_sees_all_locations(self):
        self.auth(self.admin)
        resp = self.client.get("/api/members/")
        count = resp.data["count"] if "count" in resp.data else len(resp.data)
        self.assertEqual(count, 2)

    # --- move_category business logic ---

    def test_move_category_creates_history_and_updates_field_atomically(self):
        self.auth(self.admin)
        resp = self.client.post(
            f"/api/members/{self.bahrain_member.id}/move-category/",
            {"to_category": "Worker in Training"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.bahrain_member.refresh_from_db()
        self.assertEqual(self.bahrain_member.category, "Worker in Training")
        history = MemberCategoryHistory.objects.filter(member=self.bahrain_member)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().from_category, "General Member")
        self.assertEqual(history.first().to_category, "Worker in Training")

    def test_move_category_response_includes_the_new_history_entry(self):
        """
        Regression test for a real bug found while building Batch 2.3:
        prefetch_related caches category_history on the instance at
        get_object() time, so reusing that same instance to build the
        response after creating a new history entry returned a stale,
        empty list , the API response looked like nothing happened even
        though the database was correct. This checks the response
        payload directly, not just the database, so this class of bug
        can't slip through silently again.
        """
        self.auth(self.admin)
        resp = self.client.post(
            f"/api/members/{self.bahrain_member.id}/move-category/",
            {"to_category": "Worker in Training"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["category_history"]), 1,
            "API response must include the just-created history entry, not a stale empty list.")
        self.assertEqual(resp.data["category_history"][0]["to_category"], "Worker in Training")

    def test_move_to_same_category_rejected(self):
        self.auth(self.admin)
        resp = self.client.post(
            f"/api/members/{self.bahrain_member.id}/move-category/",
            {"to_category": "General Member"},  # already this category
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_category_field_is_read_only_on_plain_patch(self):
        self.auth(self.admin)
        original_category = self.bahrain_member.category
        resp = self.client.patch(f"/api/members/{self.bahrain_member.id}/", {"category": "Worker"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.bahrain_member.refresh_from_db()
        self.assertEqual(self.bahrain_member.category, original_category,
            "category must only change via move-category, never a plain PATCH.")

    # --- Uniqueness validation surfaces cleanly, not as a 500 ---

    def test_duplicate_phone_returns_clean_400_not_server_error(self):
        self.auth(self.admin)
        Member.objects.create(surname="First", first_name="A", location=self.bahrain,
            joined_date=datetime.date.today(), phone="+973 3900 0001")
        resp = self.client.post("/api/members/", {
            "surname": "Second", "first_name": "B", "location": "bahrain",
            "joined_date": "2026-01-01", "phone": "+973 3900 0001",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", resp.data)

    # --- Household ---

    def test_household_member_count(self):
        self.auth(self.admin)
        resp = self.client.get(f"/api/households/{self.hh.id}/")
        self.assertEqual(resp.data["member_count"], 1)

    def test_household_search(self):
        self.auth(self.admin)
        resp = self.client.get("/api/households/?search=Uguru")
        results = resp.data["results"] if "results" in resp.data else resp.data
        self.assertEqual(len(results), 1)

    # --- total_given: live aggregate, same pattern as Project.amount_raised ---

    def test_total_given_reflects_giving_immediately(self):
        from finance.models import Fund, PaymentMethod, Giving
        fund = Fund.objects.create(name="Tithe")
        method = PaymentMethod.objects.create(name="Cash")
        self.auth(self.admin)
        resp0 = self.client.get(f"/api/members/{self.bahrain_member.id}/")
        self.assertEqual(resp0.data["total_given"], 0)

        Giving.objects.create(date=datetime.date.today(), fund=fund, method=method,
            amount="850.000", location=self.bahrain, member=self.bahrain_member)
        resp1 = self.client.get(f"/api/members/{self.bahrain_member.id}/")
        self.assertEqual(float(resp1.data["total_given"]), 850.0,
            "total_given must reflect newly recorded giving immediately, not a stale value.")

    # --- Client-controlled page size (Batch 3.4 finding) ---

    def test_page_size_query_param_is_respected(self):
        self.auth(self.admin)
        for i in range(5):
            Member.objects.create(surname=f"Test{i}", first_name="X", location=self.bahrain,
                joined_date=datetime.date.today())
        resp = self.client.get("/api/members/?page_size=3")
        self.assertEqual(len(resp.data["results"]), 3)

    def test_page_size_cannot_exceed_max(self):
        self.auth(self.admin)
        resp = self.client.get("/api/members/?page_size=9999")
        self.assertLessEqual(len(resp.data["results"]), 100)

    # --- Stats endpoint: unfiltered counts, but still location-scoped ---

    def test_stats_returns_correct_counts_by_category(self):
        self.auth(self.admin)
        Member.objects.create(surname="A", first_name="X", location=self.bahrain,
            joined_date=datetime.date.today(), category="Worker")
        Member.objects.create(surname="B", first_name="Y", location=self.bahrain,
            joined_date=datetime.date.today(), category="Worker in Training")
        resp = self.client.get("/api/members/stats/")
        self.assertEqual(resp.data["workers"], 1)
        self.assertEqual(resp.data["workers_in_training"], 1)
        self.assertEqual(resp.data["general_members"], 2)  # bahrain_member + qatar_member from setUp

    def test_stats_respects_location_scoping(self):
        self.auth(self.coord)
        resp = self.client.get("/api/members/stats/")
        self.assertEqual(resp.data["total"], 1, "Stats must be location-scoped for a Coordinator, same as the list itself.")

    def test_stats_ignores_category_query_param_since_its_purpose_is_unfiltered_totals(self):
        """
        Confirms the explicit LocationScopedQuerySetMixin.get_queryset(self)
        call correctly bypasses MemberViewSet's own category-filtering
        override , a ?category= param on this endpoint must not
        accidentally zero out the other categories' counts.
        """
        self.auth(self.admin)
        resp = self.client.get("/api/members/stats/?category=Worker")
        self.assertGreaterEqual(resp.data["general_members"], 1,
            "The stats endpoint must return all-category counts regardless of any ?category= param.")

    # --- Household filtering (Batch 3.4: needed for the profile page's
    # "other household members" display) ---

    def test_filter_by_household(self):
        self.auth(self.admin)
        Member.objects.create(surname="Sibling", first_name="Test", location=self.bahrain,
            joined_date=datetime.date.today(), household=self.hh)
        resp = self.client.get(f"/api/members/?household={self.hh.id}")
        surnames = [m["surname"] for m in resp.data["results"]]
        self.assertIn("Uguru", surnames)  # bahrain_member is in self.hh per setUp
        self.assertIn("Sibling", surnames)

    # --- Audit logging integration ---

    def test_create_member_writes_audit_log(self):
        self.auth(self.admin)
        AuditLog.objects.all().delete()
        self.client.post("/api/members/", {
            "surname": "Noor", "first_name": "Fatima", "location": "bahrain",
            "joined_date": "2024-09-14",
        })
        entry = AuditLog.objects.filter(action="Created", entity_type="Member", entity_name="Fatima Noor")
        self.assertTrue(entry.exists())
        self.assertEqual(entry.first().user_name_snapshot, "admin@test.com")

    def test_move_category_produces_exactly_one_audit_entry(self):
        self.auth(self.admin)
        AuditLog.objects.all().delete()
        self.client.post(f"/api/members/{self.bahrain_member.id}/move-category/", {"to_category": "Worker"})
        entries = AuditLog.objects.filter(entity_name="Chinedu Uguru")
        self.assertEqual(entries.count(), 1,
            f"Expected exactly 1 audit entry (dedup working), got {entries.count()}")
        self.assertEqual(entries.first().action, "Moved")


class MemberFollowUpTaskTestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="members",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@test.com", password="x", role=self.role)
        self.shepherd = User.objects.create_user(email="shepherd@test.com", password="x", role=self.role,
            first_name="Grace", last_name="Thomas")
        self.member = Member.objects.create(surname="Noor", first_name="Fatima", location=self.bahrain,
            joined_date=datetime.date(2024, 1, 1), assigned_to=self.shepherd)
        self.task = MemberFollowUpTask.objects.create(
            member=self.member, text="Missed Friday Worship Service , check in",
            due_date=datetime.date(2026, 8, 16), assigned_to=self.shepherd,
            missed_meeting_name="Friday Worship Service", missed_date=datetime.date(2026, 8, 14),
        )

    def auth(self):
        self.client.force_authenticate(user=self.admin)

    def test_list_shows_real_data(self):
        self.auth()
        resp = self.client.get("/api/member-followup-tasks/")
        self.assertEqual(resp.status_code, 200)
        results = resp.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["member_name"], "Fatima Noor")
        self.assertEqual(results[0]["assigned_to_name"], "Grace Thomas")

    def test_complete_requires_method_and_sets_done(self):
        self.auth()
        resp = self.client.post(f"/api/member-followup-tasks/{self.task.id}/complete/", {
            "contact_method": "Home visit",
            "contact_goal": "Check why she missed and reconnect her",
            "contact_scripture": "Hebrews 10:25",
            "contact_root_cause": "New Friday work shift",
            "contact_next_step": "She will join Monday Bible Study; call again on the 25th",
        })
        self.assertEqual(resp.status_code, 200)
        self.task.refresh_from_db()
        self.assertTrue(self.task.done)
        self.assertEqual(self.task.contact_method, "Home visit")

    def test_complete_without_method_rejected(self):
        self.auth()
        resp = self.client.post(f"/api/member-followup-tasks/{self.task.id}/complete/", {"contact_goal": "x"})
        self.assertEqual(resp.status_code, 400)
        self.task.refresh_from_db()
        self.assertFalse(self.task.done)

    def test_plain_patch_cannot_mark_done_directly(self):
        self.auth()
        resp = self.client.patch(f"/api/member-followup-tasks/{self.task.id}/", {"done": True})
        self.assertEqual(resp.status_code, 200)
        self.task.refresh_from_db()
        self.assertFalse(self.task.done)

    def test_filter_by_member(self):
        other_member = Member.objects.create(surname="Karim", first_name="Ali", location=self.bahrain,
            joined_date=datetime.date(2023, 1, 1))
        MemberFollowUpTask.objects.create(member=other_member, text="Missed", due_date=datetime.date(2026, 8, 20),
            missed_meeting_name="Friday Worship Service", missed_date=datetime.date(2026, 8, 14))
        self.auth()
        resp = self.client.get(f"/api/member-followup-tasks/?member={self.member.id}")
        results = resp.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["member_name"], "Fatima Noor")

    def test_filter_by_done_status(self):
        self.task.done = True
        self.task.save()
        MemberFollowUpTask.objects.create(member=self.member, text="Another one",
            due_date=datetime.date(2026, 8, 25), missed_meeting_name="Friday Worship Service",
            missed_date=datetime.date(2026, 8, 21))
        self.auth()
        resp = self.client.get("/api/member-followup-tasks/?done=false")
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["text"], "Another one")

    def test_stats_endpoint(self):
        import datetime as dt
        from django.utils import timezone
        today = timezone.localdate()
        # setUp's self.task is due 2026-08-16 , deliberately not assumed
        # to be past or future here; only this test's own two tasks are
        # asserted on, using dates relative to today so the test can't
        # drift into a false failure the way a hardcoded date already did.
        MemberFollowUpTask.objects.filter(id=self.task.id).delete()
        not_overdue_member = Member.objects.create(surname="Yusuf", first_name="Amina", location=self.bahrain,
            joined_date=datetime.date(2022, 1, 1))
        MemberFollowUpTask.objects.create(member=not_overdue_member, text="Missed",
            due_date=today + dt.timedelta(days=3), assigned_to=self.shepherd,
            missed_meeting_name="Friday Worship Service", missed_date=today - dt.timedelta(days=2))
        overdue_member = Member.objects.create(surname="Osei", first_name="Sarah", location=self.bahrain,
            joined_date=datetime.date(2020, 1, 1))
        MemberFollowUpTask.objects.create(member=overdue_member, text="Missed",
            due_date=today - dt.timedelta(days=5),  # deliberately overdue, no assignee
            missed_meeting_name="Friday Worship Service", missed_date=today - dt.timedelta(days=7))
        self.auth()
        resp = self.client.get("/api/member-followup-tasks/stats/")
        self.assertEqual(resp.data["open_followups"], 2)
        self.assertEqual(resp.data["overdue"], 1)
        self.assertEqual(resp.data["unassigned"], 1)

    def test_query_count_does_not_grow_with_task_count(self):
        """Same class of N+1 already caught once in Phase 4.1 for
        Newcomers , proactively verified here rather than waiting for a
        slow endpoint to surface it."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        for i in range(10):
            MemberFollowUpTask.objects.create(member=self.member, text=f"Task {i}",
                due_date=datetime.date(2026, 8, 20), assigned_to=self.shepherd,
                missed_meeting_name="Friday Worship Service", missed_date=datetime.date(2026, 8, 14))
        self.auth()
        with CaptureQueriesContext(connection) as ctx:
            self.client.get("/api/member-followup-tasks/")
        self.assertLess(len(ctx.captured_queries), 10,
            f"Expected a small, constant query count, got {len(ctx.captured_queries)}")


class FollowUpStructuredFieldsTestCase(APITestCase):
    """
    The four outcome fields are required at the API layer. A tick with no
    record of what happened is not useful to whoever reads it months
    later, so this proves each field is genuinely enforced rather than
    just present on the model.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=role, module="members",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin_sf@test.com", password="x", role=role)
        self.member = Member.objects.create(surname="Noor", first_name="Fatima", location=self.bahrain,
            joined_date=datetime.date(2024, 1, 1))
        self.task = MemberFollowUpTask.objects.create(
            member=self.member, text="Missed service", due_date=datetime.date(2026, 8, 16),
            missed_meeting_name="Friday Worship Service", missed_date=datetime.date(2026, 8, 14),
        )
        self.full = {
            "contact_method": "Home visit",
            "contact_goal": "Reconnect her to the Friday service",
            "contact_scripture": "Hebrews 10:25",
            "contact_root_cause": "New Friday work shift",
            "contact_next_step": "Join Monday Bible Study, call on the 25th",
        }

    def _post(self, payload):
        self.client.force_authenticate(user=self.admin)
        return self.client.post(f"/api/member-followup-tasks/{self.task.id}/complete/", payload)

    def test_all_four_fields_are_saved(self):
        resp = self._post(self.full)
        self.assertEqual(resp.status_code, 200)
        self.task.refresh_from_db()
        self.assertTrue(self.task.done)
        self.assertEqual(self.task.contact_goal, "Reconnect her to the Friday service")
        self.assertEqual(self.task.contact_scripture, "Hebrews 10:25")
        self.assertEqual(self.task.contact_root_cause, "New Friday work shift")
        self.assertEqual(self.task.contact_next_step, "Join Monday Bible Study, call on the 25th")

    def test_each_field_is_individually_required(self):
        for field in ["contact_goal", "contact_scripture", "contact_root_cause", "contact_next_step"]:
            payload = dict(self.full)
            payload.pop(field)
            resp = self._post(payload)
            self.assertEqual(resp.status_code, 400, f"Omitting {field} should be rejected")
            self.task.refresh_from_db()
            self.assertFalse(self.task.done, f"Task must stay open when {field} is missing")

    def test_blank_and_whitespace_only_values_are_rejected(self):
        """Someone typing a space to get past the form defeats the point."""
        for value in ["", "   "]:
            payload = dict(self.full)
            payload["contact_root_cause"] = value
            resp = self._post(payload)
            self.assertEqual(resp.status_code, 400, f"Value {value!r} should be rejected")

    def test_none_this_time_is_accepted_for_scripture(self):
        """Deliberate: forcing a scripture would just teach people to
        invent one. An explicit 'None this time' is a real answer."""
        payload = dict(self.full)
        payload["contact_scripture"] = "None this time"
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.contact_scripture, "None this time")

    def test_audit_entry_records_the_goal(self):
        AuditLog.objects.all().delete()
        self._post(self.full)
        entry = AuditLog.objects.filter(entity_type="Member", entity_name="Fatima Noor").first()
        self.assertIsNotNone(entry)
        self.assertIn("Reconnect her", entry.details)
