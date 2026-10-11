"""Kay, 10 October 2026: men follow up men, women follow up women.
A person whose gender is not known may go to anyone, with a warning."""
from accounts.models import Role, RolePermission, User
from core.tests_upgrade import Base
from enquiries.models import Enquiry, EnquirySource
from members.assignment import assign_on_registration, build_assignment_preview
from members.models import Household, Member
from newcomers.models import Newcomer
from newcomers.views import convert_to_member


class GenderMatchTestCase(Base):
    def setUp(self):
        super().setUp()
        fu, _ = Role.objects.get_or_create(name="Contact helpers")
        RolePermission.objects.update_or_create(role=fu, module="newcomers", defaults=dict(can_view=True, can_create=True, can_edit=True))
        RolePermission.objects.update_or_create(role=fu, module="members", defaults=dict(can_view=True, can_create=True, can_edit=True))
        mk = lambda e, f, l, g: User.objects.create_user(email=e, password="x", role=fu, location=self.bahrain,
                                                          first_name=f, last_name=l, can_shepherd=True, gender=g)
        self.gloria = mk("g@t.com", "Gloria", "Afari", "Female")
        self.henry = mk("h@t.com", "Henry", "Ashu", "Male")
        self.nogender = mk("n@t.com", "Noel", "Unset", "")
        self.src = EnquirySource.objects.create(name="Facebook")

    def contact(self, name, gender="", **kw):
        return Enquiry.objects.create(name=name, source=self.src, phone="97300000000", stage="contacted", gender=gender, **kw)

    # Contacts -------------------------------------------------------------

    def test_auto_assign_matches_gender_and_warns_when_not_known(self):
        w, m, u = self.contact("Ada", "Female"), self.contact("Ben", "Male"), self.contact("Cy")
        p = self.client.get("/api/enquiries/auto-assign/").data
        rows = {r["enquiry"]: r for r in p["rows"]}
        self.assertEqual(rows[w.id]["proposed"], self.gloria.id)
        self.assertEqual(rows[m.id]["proposed"], self.henry.id)
        self.assertFalse(rows[w.id]["warn"])
        self.assertIn(rows[u.id]["proposed"], {self.gloria.id, self.henry.id})   # anyone with a gender set
        self.assertTrue(rows[u.id]["warn"]); self.assertIn("Gender not known", rows[u.id]["reason"])
        self.assertNotIn(self.nogender.id, [r["proposed"] for r in p["rows"]])  # no gender, given nobody
        self.assertIn("Noel Unset", p["notice"])
        genders = {x["id"]: x["gender"] for x in p["people"]}
        self.assertEqual(genders[self.gloria.id], "Female")

    def test_no_shepherd_of_that_gender_leaves_them_unassigned_or_as_they_are(self):
        self.gloria.gender = ""; self.gloria.save()
        a = self.contact("Ada", "Female")
        b = self.contact("Bea", "Female", assigned_to=self.gloria)
        p = self.client.get("/api/enquiries/auto-assign/").data
        self.assertIsNone(next(r for r in p["rows"] if r["enquiry"] == a.id)["proposed"])
        p = self.client.get("/api/enquiries/auto-assign/?everyone=1").data
        row = next(r for r in p["rows"] if r["enquiry"] == b.id)
        self.assertEqual(row["proposed"], self.gloria.id)                     # never stripped
        self.assertIn("Left as it is", row["reason"])

    def test_by_hand_a_woman_cannot_go_to_a_man(self):
        w = self.contact("Ada", "Female")
        r = self.client.patch(f"/api/enquiries/{w.id}/", {"assigned_to": self.henry.id}, format="json")
        self.assertEqual(r.status_code, 400); self.assertIn("a woman", str(r.data))
        r = self.client.patch(f"/api/enquiries/{w.id}/", {"assigned_to": self.nogender.id}, format="json")
        self.assertEqual(r.status_code, 400)                                   # no gender set, cannot take a woman
        self.assertEqual(self.client.patch(f"/api/enquiries/{w.id}/", {"assigned_to": self.gloria.id}, format="json").status_code, 200)

    def test_not_known_can_go_to_anyone_and_keeps_the_tag(self):
        u = self.contact("Cy")
        r = self.client.patch(f"/api/enquiries/{u.id}/", {"assigned_to": self.henry.id}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["gender"], "")                                 # still not known
        self.assertEqual(r.data["assigned_to_gender"], "Male")

    def test_setting_a_gender_that_no_longer_matches_is_allowed_and_shown(self):
        u = self.contact("Cy", assigned_to=self.henry)
        r = self.client.patch(f"/api/enquiries/{u.id}/", {"gender": "Female"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data["gender"], r.data["assigned_to_gender"]), ("Female", "Male"))   # the page warns

    def test_several_at_once_refuses_a_mismatch_and_saves_nothing(self):
        a, b = self.contact("Ada", "Female"), self.contact("Ben", "Male")
        r = self.client.post("/api/enquiries/bulk-assign/", {"enquiries": [a.id, b.id], "assigned_to": self.henry.id}, format="json")
        self.assertEqual(r.status_code, 400); self.assertIn("Ada (a woman)", r.data["detail"])
        self.assertFalse(Enquiry.objects.filter(assigned_to=self.henry).exists())

    def test_auto_assign_apply_refuses_a_mismatch(self):
        a = self.contact("Ada", "Female")
        r = self.client.post("/api/enquiries/auto-assign/", {"changes": [{"enquiry": a.id, "assigned_to": self.henry.id}]}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_gender_carries_to_newcomer_and_a_mismatched_handler_is_not_kept(self):
        u = self.contact("Cy", assigned_to=self.henry)
        u.gender = "Female"; u.save()
        self.assertEqual(self.client.post(f"/api/enquiries/{u.id}/convert/", {"location": "bahrain"}, format="json").status_code, 200)
        n = Newcomer.objects.get(name="Cy")
        self.assertEqual(n.gender, "Female")
        self.assertNotEqual(n.assigned_to_id, self.henry.id)
        self.assertIn(n.assigned_to_id, {self.gloria.id, None})

    # Members and newcomers -------------------------------------------------

    def test_household_only_stays_together_where_gender_matches(self):
        hh = Household.objects.create(name="Okafor")
        self.member("Kalu", "Okafor", household=hh, gender="Male", assigned_to=self.henry)
        ada = self.member("Ada", "Okafor", household=hh, gender="Female")
        son = self.member("Samuel", "Okafor", household=hh, gender="Male")
        changes, err = build_assignment_preview()
        self.assertIsNone(err)
        by = {c["id"]: c for c in changes if c["kind"] == "member"}
        self.assertEqual(by[ada.id]["to_id"], self.gloria.id)
        self.assertEqual((by[son.id]["to_id"], by[son.id]["reason"]), (self.henry.id, "Household, same gender"))

    def test_member_preview_endpoint_and_apply_respect_gender(self):
        ada = self.member("Ada", "Eze", gender="Female")
        pete = self.member("Pete", "Lim")
        d = self.client.get("/api/members/assign-shepherds/").data
        by = {c["id"]: c for c in d["changes"] if c["kind"] == "member"}
        self.assertEqual(by[ada.id]["to_id"], self.gloria.id)
        self.assertTrue(by[pete.id]["warn"])
        self.assertIn("Noel Unset", d["notice"])
        # A hand pick that breaks the rule is ignored on apply.
        self.client.post("/api/members/assign-shepherds/", {"overrides": [{"kind": "member", "id": ada.id, "to_id": self.henry.id}]}, format="json")
        ada.refresh_from_db(); self.assertEqual(ada.assigned_to_id, self.gloria.id)

    def test_member_by_hand_and_bulk_respect_gender(self):
        ada = self.member("Ada", "Eze", gender="Female")
        r = self.client.patch(f"/api/members/{ada.id}/", {"assigned_to": self.henry.id}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/members/bulk-assign-shepherd/", {"member_ids": [ada.id], "shepherd_id": self.henry.id}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/members/bulk-assign-shepherd/", {"member_ids": [ada.id], "shepherd_id": self.gloria.id}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_shepherd_list_carries_gender_for_the_screens(self):
        rows = {r["id"]: r["gender"] for r in self.client.get("/api/members/eligible-shepherds/").data}
        self.assertEqual((rows[self.gloria.id], rows[self.henry.id], rows[self.nogender.id]), ("Female", "Male", ""))

    def test_a_woman_registering_gets_a_woman(self):
        n = Newcomer.objects.create(name="Mary", source=self.source, location=self.bahrain, stage="new",
                                    created_at=self.today, stage_since=self.today, gender="Female")
        self.assertEqual(assign_on_registration(n), self.gloria)

    def test_joining_the_roll_carries_gender_and_keeps_a_matching_shepherd(self):
        n = Newcomer.objects.create(name="Mary Ann", source=self.source, location=self.bahrain, stage="integrated",
                                    created_at=self.today, stage_since=self.today, gender="Female",
                                    phone="97311112222", assigned_to=self.gloria)
        m = convert_to_member(n, self.admin)
        m = Member.objects.get(id=getattr(m, "id", None) or Member.objects.get(from_newcomer=n).id)
        self.assertEqual((m.gender, m.assigned_to_id), ("Female", self.gloria.id))

    def test_admin_sets_a_users_gender(self):
        r = self.client.patch(f"/api/users/{self.nogender.id}/", {"gender": "Male"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.nogender.refresh_from_db(); self.assertEqual(self.nogender.gender, "Male")
