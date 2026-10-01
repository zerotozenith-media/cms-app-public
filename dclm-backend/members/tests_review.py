"""
Editing the auto-assign review before applying it.

Apply recomputes from fresh data rather than trusting the browser, so a
preview left open cannot write against data that has changed. These
tests make sure it still honours what the reviewer chose, and cannot be
tricked into assigning somebody who is not a shepherd.
"""
import datetime

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User
from core.models import Location
from members.models import Member


class ReviewEditsTestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        admin_role = Role.objects.create(name="Administrator")
        for m in ["members", "attendance", "newcomers", "finance",
                  "goals", "reports", "outreach", "admin"]:
            RolePermission.objects.create(role=admin_role, module=m, can_view=True,
                                          can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="a@t.com", password="x", role=admin_role)
        self.client.force_authenticate(user=self.admin)
        today = timezone.localdate()

        # Two shepherds, each a Worker with a linked account.
        self.shepherds = []
        for name in ["Grace", "Sarah"]:
            m = Member.objects.create(surname="T", first_name=name, location=self.bahrain,
                                      joined_date=today, category=Member.Category.WORKER)
            u = User.objects.create_user(can_shepherd=True, email=f"{name}@t.com", password="x",
                                         role=admin_role, member=m, location=self.bahrain)
            self.shepherds.append(u)

        # Three members nobody shepherds yet.
        self.people = [Member.objects.create(
            surname="P", first_name=f"Person{i}", location=self.bahrain,
            joined_date=today, category=Member.Category.GENERAL) for i in range(3)]

        # Somebody with an account who is not a shepherd.
        self.outsider = User.objects.create_user(email="x@t.com", password="x", role=admin_role)

    def preview(self):
        return self.client.get("/api/members/assign-shepherds/").data["changes"]

    def apply(self, **body):
        return self.client.post("/api/members/assign-shepherds/", body, format="json")

    def test_a_shepherd_chosen_by_hand_is_saved(self):
        """The whole point: without this the system's pick replaced the
        reviewer's when Apply was pressed."""
        first = self.preview()[0]
        other = next(s for s in self.shepherds if s.id != first["to_id"])
        self.apply(overrides=[{"kind": "member", "id": first["id"], "to_id": other.id}])
        self.assertEqual(Member.objects.get(id=first["id"]).assigned_to_id, other.id)

    def test_untouched_rows_keep_the_systems_pick(self):
        changes = self.preview()
        first, second = changes[0], changes[1]
        other = next(s for s in self.shepherds if s.id != first["to_id"])
        self.apply(overrides=[{"kind": "member", "id": first["id"], "to_id": other.id}])
        self.assertEqual(Member.objects.get(id=second["id"]).assigned_to_id, second["to_id"])

    def test_a_skipped_row_is_left_unassigned(self):
        first = self.preview()[0]
        self.apply(skips=[{"kind": "member", "id": first["id"]}])
        self.assertIsNone(Member.objects.get(id=first["id"]).assigned_to_id)

    def test_skipping_everything_assigns_nothing(self):
        changes = self.preview()
        resp = self.apply(skips=[{"kind": c["kind"], "id": c["id"]} for c in changes])
        self.assertEqual(resp.data["applied_members"], 0)
        self.assertFalse(Member.objects.filter(assigned_to__isnull=False,
                                               category=Member.Category.GENERAL).exists())

    def test_an_override_naming_a_non_shepherd_is_ignored(self):
        """The list comes from the browser, so a crafted request must not
        make anybody a shepherd."""
        first = self.preview()[0]
        self.apply(overrides=[{"kind": "member", "id": first["id"], "to_id": self.outsider.id}])
        self.assertNotEqual(Member.objects.get(id=first["id"]).assigned_to_id, self.outsider.id)

    def test_a_malformed_override_does_not_break_apply(self):
        resp = self.apply(overrides=[{"kind": "member"}, {"id": "x", "to_id": "y"}, "junk"])
        self.assertEqual(resp.status_code, 200)

    def test_a_person_assigned_since_the_preview_is_not_overwritten(self):
        """A preview left open in a tab must not undo a newer decision."""
        first = self.preview()[0]
        # Somebody assigns them in another tab.
        Member.objects.filter(id=first["id"]).update(assigned_to_id=self.shepherds[0].id)
        other = self.shepherds[1]
        self.apply(overrides=[{"kind": "member", "id": first["id"], "to_id": other.id}])
        self.assertEqual(Member.objects.get(id=first["id"]).assigned_to_id,
                         self.shepherds[0].id)

    def test_the_preview_shows_each_shepherds_load_before_and_after(self):
        """Without it, a batch sent to one worker reads as a fault."""
        data = self.client.get("/api/members/assign-shepherds/").data
        self.assertIn("load", data)
        total_after = sum(s["after"] for s in data["load"])
        total_now = sum(s["now"] for s in data["load"])
        self.assertEqual(total_after - total_now, len(data["changes"]))

    def test_a_hand_pick_is_recorded_in_the_audit_log(self):
        from accounts.models import AuditLog
        first = self.preview()[0]
        other = next(s for s in self.shepherds if s.id != first["to_id"])
        self.apply(overrides=[{"kind": "member", "id": first["id"], "to_id": other.id}])
        entry = AuditLog.objects.filter(action="Auto-assigned shepherds").first()
        self.assertIn("chosen by hand", entry.details)
