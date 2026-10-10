"""Kay, 10 October 2026: a named follow-up person for every online contact."""
from accounts.models import Role, RolePermission, User
from core.tests_upgrade import Base
from enquiries.models import Enquiry, EnquirySource
from followup.models import Enrolment


class ContactFollowUpTestCase(Base):
    def setUp(self):
        super().setUp()
        fu, _ = Role.objects.get_or_create(name="Contact helpers")
        RolePermission.objects.update_or_create(role=fu, module="newcomers", defaults=dict(can_view=True, can_create=True, can_edit=True))
        viewer = Role.objects.create(name="Contact viewer")
        RolePermission.objects.create(role=viewer, module="newcomers", can_view=True)
        self.gloria = User.objects.create_user(email="g@t.com", password="x", role=fu, location=self.bahrain, first_name="Gloria", last_name="Afari", can_shepherd=True)
        self.henry = User.objects.create_user(email="h@t.com", password="x", role=fu, location=self.bahrain, first_name="Henry", last_name="Ashu", can_shepherd=True)
        self.not_ticked = User.objects.create_user(email="n@t.com", password="x", role=fu, location=self.bahrain, first_name="Nat", last_name="Ticked")
        self.viewer = User.objects.create_user(email="v@t.com", password="x", role=viewer, location=self.bahrain, first_name="Vi", last_name="Ewer", can_shepherd=True)
        src = EnquirySource.objects.create(name="Facebook")
        self.contacts = [Enquiry.objects.create(name=f"Contact {i}", source=src, phone=f"9730000{i:04d}", stage="contacted") for i in range(7)]
        Enrolment.objects.all().delete()                       # loaded with messages not started, as on live
        self.gone = Enquiry.objects.create(name="Already came", source=src, phone="97399999999", stage="attended")

    def test_only_ticked_people_who_can_work_on_contacts_are_offered(self):
        names = [p["name"] for p in self.client.get("/api/enquiries/followup-people/").data["results"]]
        self.assertIn("Gloria Afari", names); self.assertIn("Henry Ashu", names)
        self.assertNotIn("Nat Ticked", names)                  # not ticked Can shepherd others
        self.assertNotIn("Vi Ewer", names)                     # can only view contacts

    def test_one_contact_can_be_given_a_person_and_a_bad_choice_is_refused(self):
        c = self.contacts[0]
        self.assertEqual(self.client.patch(f"/api/enquiries/{c.id}/", {"assigned_to": self.gloria.id}, format="json").status_code, 200)
        c.refresh_from_db(); self.assertEqual(c.assigned_to, self.gloria)
        self.assertEqual(self.client.patch(f"/api/enquiries/{c.id}/", {"assigned_to": self.not_ticked.id}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/enquiries/{c.id}/", {"assigned_to": None}, format="json").status_code, 200)

    def test_several_at_once(self):
        ids = [c.id for c in self.contacts[:3]]
        r = self.client.post("/api/enquiries/bulk-assign/", {"enquiries": ids, "assigned_to": self.henry.id}, format="json")
        self.assertEqual(r.data["changed"], 3)
        self.assertEqual(Enquiry.objects.filter(assigned_to=self.henry).count(), 3)
        bad = self.client.post("/api/enquiries/bulk-assign/", {"enquiries": ids, "assigned_to": self.viewer.id}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(Enquiry.objects.filter(assigned_to=self.henry).count(), 3)   # nothing changed

    def test_auto_assign_shares_evenly_and_saves_only_on_apply(self):
        self.contacts[0].assigned_to = self.gloria; self.contacts[0].save()
        p = self.client.get("/api/enquiries/auto-assign/").data
        self.assertEqual(len(p["rows"]), 6)                    # the attended contact and the assigned one are left out
        self.assertEqual(sorted(x["after"] for x in p["people"]), [3, 4])
        self.assertEqual(Enquiry.objects.filter(assigned_to__isnull=True).count(), 7)   # preview saves nothing
        changes = [{"enquiry": r["enquiry"], "assigned_to": r["proposed"]} for r in p["rows"]]
        changes[-1]["assigned_to"] = None                      # leave one unassigned
        self.client.post("/api/enquiries/auto-assign/", {"changes": changes}, format="json")
        self.assertEqual(Enquiry.objects.exclude(stage="attended").filter(assigned_to__isnull=True).count(), 1)

    def test_a_view_only_role_cannot_assign(self):
        self.client.force_authenticate(user=self.viewer)
        self.assertEqual(self.client.post("/api/enquiries/bulk-assign/", {"enquiries": [self.contacts[0].id], "assigned_to": self.gloria.id}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/enquiries/auto-assign/").status_code, 403)

    def test_start_messages_for_contacts_goes_to_their_follow_up_person(self):
        c = self.contacts[0]; c.assigned_to = self.gloria; c.save()
        rows = self.client.get("/api/followup/start-many/?kind=contacts").data["results"]
        self.assertEqual(len(rows), 7)
        self.assertEqual(next(r for r in rows if r["id"] == c.id)["shepherd"], "Gloria Afari")
        self.assertEqual(self.client.post("/api/followup/start-many/", {"enquiries": [c.id, self.gone.id]}, format="json").data["started"], 1)
        self.assertTrue(Enrolment.objects.filter(enquiry=c, status="active").exists())
        self.client.force_authenticate(user=self.gloria)
        self.assertIn(c.name, [x["person"]["name"] for x in self.client.get("/api/followup/today/").data["results"]])
