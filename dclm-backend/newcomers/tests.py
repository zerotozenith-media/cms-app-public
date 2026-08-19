import datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User
from attendance.models import MeetingType
from core.models import Location
from members.models import Member
from .models import (
    NewcomerSource, MilestoneType, Newcomer, NewcomerStatusHistory,
    NewcomerTask, FollowUpUrgencySetting,
)


class NewcomerAPITestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.others = Location.objects.create(id="others", name="Others", note="Qatar")

        self.admin_role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.admin_role, module="newcomers",
            can_view=True, can_create=True, can_edit=True, can_delete=True)

        self.admin = User.objects.create_user(email="admin@test.com", password="x", role=self.admin_role)
        self.coord = User.objects.create_user(email="coord@test.com", password="x",
            role=self.admin_role, location=self.bahrain)
        self.leader = User.objects.create_user(email="sarah@test.com", password="x", role=self.admin_role)
        self.other_leader = User.objects.create_user(email="grace@test.com", password="x", role=self.admin_role)

        self.source = NewcomerSource.objects.create(name="Church website")
        self.milestone_salvation = MilestoneType.objects.create(name="Salvation")
        self.milestone_baptism = MilestoneType.objects.create(name="Water Baptism")

        FollowUpUrgencySetting.objects.create(stage="new", amber_days=3, red_days=6)
        FollowUpUrgencySetting.objects.create(stage="contacted", amber_days=5, red_days=10)

        self.bahrain_newcomer = Newcomer.objects.create(
            name="Jane Dosumu", source=self.source, stage="new",
            assigned_to=self.leader, location=self.bahrain,
            created_at=datetime.date.today(), stage_since=datetime.date.today(),
        )
        self.qatar_newcomer = Newcomer.objects.create(
            name="Ali Karim", source=self.source, stage="new",
            location=self.others,
            created_at=datetime.date.today(), stage_since=datetime.date.today(),
        )

    def auth(self, user):
        self.client.force_authenticate(user=user)

    # --- Location scoping ---

    def test_coordinator_only_sees_own_location(self):
        self.auth(self.coord)
        resp = self.client.get("/api/newcomers/")
        names = [n["name"] for n in resp.data["results"]]
        self.assertIn("Jane Dosumu", names)
        self.assertNotIn("Ali Karim", names)

    # --- change_stage: unified action covering all transitions ---

    def test_normal_stage_progression_creates_history_entry(self):
        self.auth(self.admin)
        resp = self.client.post(f"/api/newcomers/{self.bahrain_newcomer.id}/change-stage/", {"to_stage": "contacted"})
        self.assertEqual(resp.status_code, 200)
        self.bahrain_newcomer.refresh_from_db()
        self.assertEqual(self.bahrain_newcomer.stage, "contacted")
        history = NewcomerStatusHistory.objects.filter(newcomer=self.bahrain_newcomer)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().stage, "contacted")

    def test_mark_not_interested_with_note(self):
        self.auth(self.admin)
        resp = self.client.post(f"/api/newcomers/{self.bahrain_newcomer.id}/change-stage/", {
            "to_stage": "not-interested", "note": "Just curious, not looking for a church.",
        })
        self.assertEqual(resp.status_code, 200)
        self.bahrain_newcomer.refresh_from_db()
        self.assertEqual(self.bahrain_newcomer.stage, "not-interested")
        self.assertEqual(self.bahrain_newcomer.not_interested_note, "Just curious, not looking for a church.")
        history = NewcomerStatusHistory.objects.get(newcomer=self.bahrain_newcomer)
        self.assertEqual(history.note, "Just curious, not looking for a church.")

    def test_reactivate_clears_current_note_but_history_survives(self):
        self.auth(self.admin)
        self.client.post(f"/api/newcomers/{self.bahrain_newcomer.id}/change-stage/", {
            "to_stage": "not-interested", "note": "Not now.",
        })
        self.client.post(f"/api/newcomers/{self.bahrain_newcomer.id}/change-stage/", {"to_stage": "contacted"})
        self.bahrain_newcomer.refresh_from_db()
        self.assertEqual(self.bahrain_newcomer.stage, "contacted")
        self.assertEqual(self.bahrain_newcomer.not_interested_note, "",
            "Current note should clear on reactivation.")
        # But the episode itself must still be visible in history
        history = NewcomerStatusHistory.objects.filter(newcomer=self.bahrain_newcomer, stage="not-interested")
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().note, "Not now.",
            "The not-interested episode must remain visible in history even after reactivation.")

    def test_moving_to_same_stage_rejected(self):
        self.auth(self.admin)
        resp = self.client.post(f"/api/newcomers/{self.bahrain_newcomer.id}/change-stage/", {"to_stage": "new"})
        self.assertEqual(resp.status_code, 400)

    def test_stage_field_read_only_on_plain_patch(self):
        self.auth(self.admin)
        self.client.patch(f"/api/newcomers/{self.bahrain_newcomer.id}/", {"stage": "integrated"})
        self.bahrain_newcomer.refresh_from_db()
        self.assertEqual(self.bahrain_newcomer.stage, "new")

    def test_change_stage_produces_exactly_one_newcomer_level_audit_entry(self):
        self.auth(self.admin)
        AuditLog.objects.all().delete()
        self.client.post(f"/api/newcomers/{self.bahrain_newcomer.id}/change-stage/", {"to_stage": "contacted"})
        newcomer_entries = AuditLog.objects.filter(entity_type="Newcomer", entity_name="Jane Dosumu")
        self.assertEqual(newcomer_entries.count(), 1, f"Expected 1, got {newcomer_entries.count()}")

    # --- Urgency calculation (admin-adjustable thresholds, Batch 0.3 Finding 4) ---

    def test_urgency_uses_configured_thresholds(self):
        stale = Newcomer.objects.create(
            name="Stale Newcomer", source=self.source, stage="new", location=self.bahrain,
            created_at=datetime.date.today() - datetime.timedelta(days=7),
            stage_since=datetime.date.today() - datetime.timedelta(days=7),  # amber=3, red=6 for 'new' -> should be red
        )
        self.auth(self.admin)
        resp = self.client.get(f"/api/newcomers/{stale.id}/")
        self.assertEqual(resp.data["days_in_stage"], 7)
        self.assertEqual(resp.data["urgency"], "red")

    def test_fresh_newcomer_is_green(self):
        self.auth(self.admin)
        resp = self.client.get(f"/api/newcomers/{self.bahrain_newcomer.id}/")
        self.assertEqual(resp.data["urgency"], "green")

    # --- Dynamic milestone checklist ---

    def test_milestones_list_shows_all_types_even_unachieved(self):
        self.auth(self.admin)
        resp = self.client.get(f"/api/newcomers/{self.bahrain_newcomer.id}/")
        self.assertEqual(len(resp.data["milestones"]), 2)  # Salvation + Water Baptism
        self.assertTrue(all(m["achieved_date"] is None for m in resp.data["milestones"]))

    def test_new_milestone_type_automatically_appears_for_existing_newcomers(self):
        MilestoneType.objects.create(name="Holy Ghost Baptism")  # added AFTER newcomer existed
        self.auth(self.admin)
        resp = self.client.get(f"/api/newcomers/{self.bahrain_newcomer.id}/")
        names = [m["name"] for m in resp.data["milestones"]]
        self.assertIn("Holy Ghost Baptism", names, "New milestone types must appear without any backfill step.")

    def test_set_milestone_achieved(self):
        self.auth(self.admin)
        resp = self.client.post(f"/api/newcomers/{self.bahrain_newcomer.id}/set-milestone/", {
            "milestone_type": self.milestone_salvation.id, "achieved": True, "achieved_date": "2026-06-14",
        })
        self.assertEqual(resp.status_code, 200)
        milestone = next(m for m in resp.data["milestones"] if m["name"] == "Salvation")
        self.assertEqual(milestone["achieved_date"], datetime.date(2026, 6, 14))

    def test_unset_milestone(self):
        self.auth(self.admin)
        self.client.post(f"/api/newcomers/{self.bahrain_newcomer.id}/set-milestone/", {
            "milestone_type": self.milestone_salvation.id, "achieved": True,
        })
        resp = self.client.post(f"/api/newcomers/{self.bahrain_newcomer.id}/set-milestone/", {
            "milestone_type": self.milestone_salvation.id, "achieved": False,
        })
        milestone = next(m for m in resp.data["milestones"] if m["name"] == "Salvation")
        self.assertIsNone(milestone["achieved_date"])

    # --- Task assignment defaulting (Batch 0.3, Finding 3) ---

    def test_task_defaults_to_newcomer_primary_leader_when_unassigned(self):
        self.auth(self.admin)
        resp = self.client.post("/api/newcomer-tasks/", {
            "newcomer": self.bahrain_newcomer.id, "text": "Call back", "due_date": "2026-09-01",
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["assigned_to"], self.leader.id)

    def test_task_can_be_assigned_to_someone_other_than_primary_leader(self):
        self.auth(self.admin)
        resp = self.client.post("/api/newcomer-tasks/", {
            "newcomer": self.bahrain_newcomer.id, "text": "Home visit", "due_date": "2026-09-01",
            "assigned_to": self.other_leader.id,
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["assigned_to"], self.other_leader.id,
            "A task must be reassignable independently of the newcomer's primary leader.")

    def test_filter_tasks_by_newcomer(self):
        """Needed for the profile page's task list (Batch 3.6)."""
        other_newcomer = Newcomer.objects.create(name="Someone Else", source=self.source, location=self.bahrain,
            created_at=datetime.date.today(), stage_since=datetime.date.today())
        NewcomerTask.objects.create(newcomer=self.bahrain_newcomer, text="Task A", due_date=datetime.date.today())
        NewcomerTask.objects.create(newcomer=other_newcomer, text="Task B", due_date=datetime.date.today())
        self.auth(self.admin)
        resp = self.client.get(f"/api/newcomer-tasks/?newcomer={self.bahrain_newcomer.id}")
        results = resp.data["results"] if "results" in resp.data else resp.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "Task A")

    def test_open_tasks_count(self):
        NewcomerTask.objects.create(newcomer=self.bahrain_newcomer, text="Task 1",
            due_date=datetime.date.today(), done=False)
        NewcomerTask.objects.create(newcomer=self.bahrain_newcomer, text="Task 2",
            due_date=datetime.date.today(), done=True)
        self.auth(self.admin)
        resp = self.client.get(f"/api/newcomers/{self.bahrain_newcomer.id}/")
        self.assertEqual(resp.data["open_tasks_count"], 1)


class NewcomerIntakeSlipTestCase(APITestCase):
    """
    Real DCLM Bahrain intake slip fields (both the paper form used for
    manual entry and the QR self-registration form capture the same
    set) , added after the demo/original schema, following a real slip
    the user shared. Covers the three confirmed decisions: invited_by
    links to a Member when unambiguous, First Timer / New Resident are
    independent flags, and the three request checkboxes create real
    follow-up tasks with no automated sending.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="newcomers",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@test.com", password="x", role=self.role)
        self.source = NewcomerSource.objects.create(name="Walk-in")
        self.mt = MeetingType.objects.create(id="fri-worship", name="Friday Worship Service",
            day="Friday", frequency="weekly", detail_level="detailed", monthly_target=150)

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def base_payload(self, **overrides):
        payload = {
            "name": "Jane Dosumu", "source": self.source.id, "location": "bahrain",
            "address": "Building 12, Road 3401", "city_governorate": "Manama",
            "phone": "+973 3900 1234", "email": "jane@example.com",
            "gender": "Female", "age_group": "20_and_above",
            "prayer_request": "Healing for my mother", "meeting_attended": self.mt.id,
            "is_first_timer": True, "is_new_resident": False,
        }
        payload.update(overrides)
        return payload

    # --- Basic intake fields persist correctly ---

    def test_all_intake_fields_saved_correctly(self):
        self.auth(self.admin)
        resp = self.client.post("/api/newcomers/", self.base_payload())
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["address"], "Building 12, Road 3401")
        self.assertEqual(resp.data["city_governorate"], "Manama")
        self.assertEqual(resp.data["gender"], "Female")
        self.assertEqual(resp.data["age_group"], "20_and_above")
        self.assertEqual(resp.data["prayer_request"], "Healing for my mother")
        self.assertEqual(resp.data["meeting_attended_name"], "Friday Worship Service")

    # --- First Timer / New Resident: independent, can both be true ---

    def test_first_timer_and_new_resident_can_both_be_true(self):
        self.auth(self.admin)
        resp = self.client.post("/api/newcomers/", self.base_payload(is_first_timer=True, is_new_resident=True))
        self.assertTrue(resp.data["is_first_timer"])
        self.assertTrue(resp.data["is_new_resident"])

    # --- invited_by: links to Member when unambiguous, free text otherwise ---

    def test_invited_by_links_to_matching_member(self):
        m = Member.objects.create(surname="Thomas", first_name="Grace", location=self.bahrain,
            joined_date=datetime.date.today())
        self.auth(self.admin)
        resp = self.client.post("/api/newcomers/", self.base_payload(invited_by_name="Grace Thomas"))
        self.assertEqual(resp.data["invited_by_member"], m.id)
        self.assertEqual(resp.data["invited_by_member_name"], "Grace Thomas")
        self.assertEqual(resp.data["invited_by_name"], "Grace Thomas")

    def test_invited_by_stays_free_text_when_no_member_matches(self):
        self.auth(self.admin)
        resp = self.client.post("/api/newcomers/", self.base_payload(invited_by_name="A Family Friend"))
        self.assertIsNone(resp.data["invited_by_member"])
        self.assertEqual(resp.data["invited_by_name"], "A Family Friend")

    def test_invited_by_stays_free_text_when_name_is_ambiguous(self):
        """Two members share the exact name , must not guess which one."""
        Member.objects.create(surname="Thomas", first_name="Grace", location=self.bahrain,
            joined_date=datetime.date.today())
        Member.objects.create(surname="Thomas", first_name="Grace", location=self.bahrain,
            joined_date=datetime.date.today())
        self.auth(self.admin)
        resp = self.client.post("/api/newcomers/", self.base_payload(invited_by_name="Grace Thomas"))
        self.assertIsNone(resp.data["invited_by_member"],
            "An ambiguous name match must not guess , stay free text only.")
        self.assertEqual(resp.data["invited_by_name"], "Grace Thomas")

    def test_invited_by_member_is_read_only_cannot_be_set_directly(self):
        m = Member.objects.create(surname="Someone", first_name="Else", location=self.bahrain,
            joined_date=datetime.date.today())
        other = Member.objects.create(surname="Wrong", first_name="Person", location=self.bahrain,
            joined_date=datetime.date.today())
        self.auth(self.admin)
        resp = self.client.post("/api/newcomers/", self.base_payload(
            invited_by_name="Else Someone", invited_by_member=other.id,
        ))
        # invited_by_member is read-only , only the matching logic sets it,
        # a client can't misattribute a referral by passing the FK directly.
        self.assertNotEqual(resp.data["invited_by_member"], other.id)

    # --- Auto-created follow-up tasks, no automated sending ---

    def test_wants_visit_creates_a_real_task(self):
        self.auth(self.admin)
        resp = self.client.post("/api/newcomers/", self.base_payload(wants_visit=True))
        tasks = NewcomerTask.objects.filter(newcomer_id=resp.data["id"])
        self.assertEqual(tasks.count(), 1)
        self.assertEqual(tasks.first().text, "Schedule a home visit")

    def test_all_three_checkboxes_create_three_separate_tasks(self):
        self.auth(self.admin)
        resp = self.client.post("/api/newcomers/", self.base_payload(
            wants_visit=True, wants_to_know_more=True, wants_salvation_info=True,
        ))
        tasks = list(NewcomerTask.objects.filter(newcomer_id=resp.data["id"]).values_list("text", flat=True))
        self.assertEqual(len(tasks), 3)
        self.assertIn("Schedule a home visit", tasks)
        self.assertIn("Share more about the church", tasks)
        self.assertIn("Have a salvation conversation", tasks)

    def test_salvation_task_is_due_sooner_than_the_others(self):
        self.auth(self.admin)
        resp = self.client.post("/api/newcomers/", self.base_payload(
            wants_visit=True, wants_salvation_info=True,
        ))
        tasks = {t.text: t.due_date for t in NewcomerTask.objects.filter(newcomer_id=resp.data["id"])}
        self.assertLess(tasks["Have a salvation conversation"], tasks["Schedule a home visit"],
            "The salvation-interest task should be due sooner, reflecting real pastoral urgency.")

    def test_no_checkboxes_creates_no_tasks(self):
        self.auth(self.admin)
        resp = self.client.post("/api/newcomers/", self.base_payload())
        self.assertEqual(NewcomerTask.objects.filter(newcomer_id=resp.data["id"]).count(), 0)

    def test_auto_created_tasks_default_to_the_newcomers_assigned_leader(self):
        leader = User.objects.create_user(email="leader@test.com", password="x", role=self.role)
        self.auth(self.admin)
        resp = self.client.post("/api/newcomers/", self.base_payload(wants_visit=True, assigned_to=leader.id))
        task = NewcomerTask.objects.get(newcomer_id=resp.data["id"])
        self.assertEqual(task.assigned_to_id, leader.id)


class NewcomerListQueryCountTestCase(APITestCase):
    """
    Phase 4.1 regression test: a real N+1 was caught by testing against
    realistic data volume (55 seeded newcomers), not the 2-3 records
    used everywhere else in this suite , get_urgency() and
    get_milestones() were re-querying two tiny static tables on every
    single newcomer, and get_open_tasks_count() bypassed the viewset's
    prefetch entirely by calling .filter() instead of .all(). Confirmed
    empirically: 171 queries for 55 rows before the fix, 8 after.
    This locks in the invariant that actually matters , the query count
    must not grow with the number of newcomers , rather than a specific
    number that would need updating every time an unrelated field is added.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="newcomers",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin_qc@test.com", password="x", role=self.role)
        self.source = NewcomerSource.objects.create(name="Church website")
        MilestoneType.objects.create(name="Salvation")
        MilestoneType.objects.create(name="Water Baptism")
        for stage, amber, red in [("new", 3, 6), ("contacted", 5, 10), ("visiting", 15, 30)]:
            FollowUpUrgencySetting.objects.create(stage=stage, amber_days=amber, red_days=red)

    def _create_newcomers(self, count):
        for i in range(count):
            Newcomer.objects.create(
                name=f"Test Newcomer {i}", source=self.source, location=self.bahrain,
                stage="contacted", created_at=datetime.date.today(), stage_since=datetime.date.today(),
            )

    def test_query_count_does_not_grow_with_newcomer_count(self):
        self.auth = lambda: self.client.force_authenticate(user=self.admin)
        self.auth()

        self._create_newcomers(5)
        with self.assertNumQueries(7):
            resp_small = self.client.get("/api/newcomers/?page_size=100")
        self.assertEqual(len(resp_small.data["results"]), 5)

        self._create_newcomers(45)  # 50 total now
        with self.assertNumQueries(7):
            resp_large = self.client.get("/api/newcomers/?page_size=100")
        self.assertEqual(len(resp_large.data["results"]), 50)


class NewcomerTaskCompletionTestCase(APITestCase):
    """
    Phase 4.3: a checked box with no record of what was discussed isn't
    useful to a leader reviewing history later , done is now read-only,
    the only correct way to complete a task is the complete() action,
    which requires the real visitation outcome.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="newcomers",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@test.com", password="x", role=self.role)
        source = NewcomerSource.objects.create(name="Church website")
        self.newcomer = Newcomer.objects.create(name="Jane Dosumu", source=source, location=self.bahrain,
            stage="contacted", created_at=datetime.date.today(), stage_since=datetime.date.today())
        self.task = NewcomerTask.objects.create(newcomer=self.newcomer, text="Call back",
            due_date=datetime.date.today())

    def auth(self):
        self.client.force_authenticate(user=self.admin)

    def test_complete_requires_method_and_sets_done(self):
        self.auth()
        resp = self.client.post(f"/api/newcomer-tasks/{self.task.id}/complete/", {
            "contact_method": "Phone call",
            "contact_goal": "Welcome her and answer questions",
            "contact_scripture": "None this time",
            "contact_root_cause": "Still finding her way around",
            "contact_next_step": "Invite her to Bible study next week",
        })
        self.assertEqual(resp.status_code, 200)
        self.task.refresh_from_db()
        self.assertTrue(self.task.done)
        self.assertEqual(self.task.contact_method, "Phone call")
        self.assertEqual(self.task.contact_goal, "Welcome her and answer questions")
        self.assertEqual(self.task.contact_scripture, "None this time")
        self.assertEqual(self.task.contact_date, datetime.date.today())

    def test_complete_without_method_is_rejected(self):
        """The whole point , completion requires knowing HOW contact was made."""
        self.auth()
        resp = self.client.post(f"/api/newcomer-tasks/{self.task.id}/complete/", {
            "contact_goal": "Talked to her.",
        })
        self.assertEqual(resp.status_code, 400)
        self.task.refresh_from_db()
        self.assertFalse(self.task.done)

    def test_plain_patch_cannot_mark_done_directly(self):
        """done is read-only on the serializer , this is the regression
        this whole fix exists to prevent: bypassing the log requirement."""
        self.auth()
        resp = self.client.patch(f"/api/newcomer-tasks/{self.task.id}/", {"done": True})
        self.assertEqual(resp.status_code, 200)  # PATCH succeeds, but silently ignores done
        self.task.refresh_from_db()
        self.assertFalse(self.task.done, "done must not be settable via plain PATCH.")

    def test_explicit_contact_date_is_respected(self):
        self.auth()
        resp = self.client.post(f"/api/newcomer-tasks/{self.task.id}/complete/", {
            "contact_method": "Home visit", "contact_date": "2026-08-10",
            "contact_goal": "Check in after absence",
            "contact_scripture": "Psalm 23",
            "contact_root_cause": "Travelling for work",
            "contact_next_step": "Call on return",
        })
        self.assertEqual(resp.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.contact_date, datetime.date(2026, 8, 10))


class NewcomerTaskFilterTestCase(APITestCase):
    """
    The aggregate Follow-up tab relies on filtering by done server-side.
    Without it the request still returns 200 with every task, so the
    Open/Completed filter looks broken rather than erroring.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=role, module="newcomers",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@t.com", password="x", role=role)
        source = NewcomerSource.objects.create(name="Church website")
        today = datetime.date.today()
        n1 = Newcomer.objects.create(name="Open Person", source=source, location=self.bahrain,
            stage="contacted", created_at=today, stage_since=today)
        n2 = Newcomer.objects.create(name="Done Person", source=source, location=self.bahrain,
            stage="contacted", created_at=today, stage_since=today)
        NewcomerTask.objects.create(newcomer=n1, text="Call back", due_date=today)
        NewcomerTask.objects.create(newcomer=n2, text="Home visit", due_date=today, done=True)

    def test_filter_open_only(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/newcomer-tasks/?done=false")
        names = [t["text"] for t in resp.data["results"]]
        self.assertEqual(names, ["Call back"])

    def test_filter_completed_only(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/newcomer-tasks/?done=true")
        names = [t["text"] for t in resp.data["results"]]
        self.assertEqual(names, ["Home visit"])

    def test_no_filter_returns_both(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/newcomer-tasks/")
        self.assertEqual(len(resp.data["results"]), 2)
