"""
Men shepherd men, women shepherd women, and nobody shepherds themselves
(Kay, 17 October 2026). The live system had a woman shepherded by a man,
a man by a woman and a man shepherding himself, because older pairings
were never rechecked and no account was linked to its member record.
"""
import datetime
from io import StringIO

from django.core.management import call_command
from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User
from core.models import Location
from members.models import Member

D = datetime.date(2026, 7, 1)


class Base(APITestCase):
    def setUp(self):
        self.bh = Location.objects.create(id="bahrain", name="Bahrain HQ", is_core=True)
        self.qa = Location.objects.create(id="others", name="Qatar")
        role = Role.objects.create(name="Administrator")
        for mod in ["members", "admin", "newcomers"]:
            RolePermission.objects.create(role=role, module=mod, can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.role = role
        self.admin = User.objects.create_user(email="admin@t.com", password="x", role=role)
        self.client.force_authenticate(self.admin)
        mk = lambda f, s, g, **kw: Member.objects.create(first_name=f, surname=s, gender=g, location=self.bh, joined_date=D, **kw)
        # Members, as on the live system.
        self.gloria = mk("Gloria", "Afari", "Female", category="Worker")
        self.kwabena = mk("Kwabena", "Afari", "Male", category="Worker")
        self.chinedu = mk("Chinedu", "Uguru", "Male", category="Worker")
        self.joshua = mk("Joshua", "Afari", "Male")
        self.grace_m = mk("Grace", "Uguru", "Female")
        # Shepherd accounts, NOT linked to their member records.
        acct = lambda e, f, l, g: User.objects.create_user(email=e, password="x", role=role, first_name=f, last_name=l,
                                                           gender=g, can_shepherd=True, location=self.bh)
        self.u_kwabena = acct("k@t.com", "Kwabena", "Afari", "Male")
        self.u_gloria = acct("g@t.com", "Gloria", "Afari", "Female")
        self.u_chinedu = acct("c@t.com", "Chinedu", "Uguru", "Male")
        self.u_grace = acct("gt@t.com", "Grace", "Thomas", "Female")
        # The live pairings.
        Member.objects.filter(pk=self.gloria.pk).update(assigned_to=self.u_kwabena)
        Member.objects.filter(pk=self.kwabena.pk).update(assigned_to=self.u_kwabena)
        Member.objects.filter(pk=self.chinedu.pk).update(assigned_to=self.u_gloria)
        Member.objects.filter(pk=self.joshua.pk).update(assigned_to=self.u_chinedu)
        Member.objects.filter(pk=self.grace_m.pk).update(assigned_to=self.u_grace)


class Finding(Base):
    def test_rule_breaks_are_listed_for_the_members_page(self):
        r = self.client.get("/api/members/shepherd-problems/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual({p["name"]: p["tag"] for p in r.data["people"]},
                         {"Gloria Afari": "A man shepherds her", "Chinedu Uguru": "A woman shepherds him",
                          "Kwabena Afari": "Shepherds himself"})

    def test_each_row_carries_its_note(self):
        rows = {m["full_name"]: m["shepherd_problem"] for m in self.client.get("/api/members/?page_size=50").data["results"]}
        self.assertEqual(rows["Gloria Afari"], "A man shepherds her")
        self.assertEqual(rows["Joshua Afari"], "")

    def test_a_linked_account_counts_as_the_same_person_even_with_another_name(self):
        self.u_grace.member = self.grace_m
        self.u_grace.save()
        self.assertEqual(self.client.get(f"/api/members/{self.grace_m.id}/").data["shepherd_problem"], "Shepherds herself")

    def test_preflight_notes_them(self):
        out = StringIO()
        try:
            call_command("preflight", stdout=out)
        except SystemExit:      # other problems on a test server end it with 1
            pass
        self.assertIn("3 member(s) have a shepherd who breaks the rules", out.getvalue())


class Correcting(Base):
    def test_auto_assign_proposes_a_correct_shepherd_for_each(self):
        r = self.client.get("/api/members/assign-shepherds/")
        ch = {c["name"]: c for c in r.data["changes"] if c["kind"] == "member"}
        self.assertEqual(set(ch), {"Gloria Afari", "Chinedu Uguru", "Kwabena Afari"})
        self.assertEqual((ch["Gloria Afari"]["to_id"], ch["Gloria Afari"]["reason"]), (self.u_grace.id, "Her shepherd is a man"))
        self.assertEqual((ch["Chinedu Uguru"]["to_id"], ch["Chinedu Uguru"]["reason"]), (self.u_kwabena.id, "His shepherd is a woman"))
        self.assertEqual(ch["Kwabena Afari"]["reason"], "He shepherds himself")
        self.assertEqual(ch["Kwabena Afari"]["to_id"], self.u_chinedu.id)
        self.assertTrue(all(c["correction"] and c["warn"] for c in ch.values()))
        # Load: Kwabena carried 2 and keeps 1 (Chinedu arrives, both Afaris leave).
        load = {s["name"]: (s["now"], s["after"]) for s in r.data["load"]}
        self.assertEqual(load["Kwabena Afari"], (2, 1))
        self.assertEqual(load["Gloria Afari"], (1, 0))

    def test_apply_corrects_them_and_leave_as_it_is_skips(self):
        r = self.client.post("/api/members/assign-shepherds/", {"skips": [{"kind": "member", "id": self.chinedu.id}]}, format="json")
        self.assertEqual(r.data["applied_members"], 2)
        self.gloria.refresh_from_db(); self.kwabena.refresh_from_db(); self.chinedu.refresh_from_db()
        self.assertEqual((self.gloria.assigned_to, self.kwabena.assigned_to, self.chinedu.assigned_to),
                         (self.u_grace, self.u_chinedu, self.u_gloria))
        self.assertEqual(self.client.get("/api/members/shepherd-problems/").data["count"], 1)

    def test_a_hand_pick_of_themselves_is_ignored(self):
        self.client.post("/api/members/assign-shepherds/", {"overrides": [
            {"kind": "member", "id": self.kwabena.id, "to_id": self.u_kwabena.id}]}, format="json")
        self.kwabena.refresh_from_db()
        self.assertNotEqual(self.kwabena.assigned_to, self.u_kwabena)

    def test_nobody_suitable_is_listed_not_applied(self):
        User.objects.filter(pk=self.u_grace.pk).update(can_shepherd=False)
        ch = {c["name"]: c for c in self.client.get("/api/members/assign-shepherds/").data["changes"]}
        self.assertIsNone(ch["Gloria Afari"]["to_id"])
        self.assertIn("Her shepherd is a man.", ch["Gloria Afari"]["reason"])

    def test_nothing_to_correct_leaves_well_paired_people_alone(self):
        Member.objects.filter(pk=self.kwabena.pk).update(assigned_to=self.u_chinedu)
        Member.objects.filter(pk=self.chinedu.pk).update(assigned_to=self.u_kwabena)
        Member.objects.filter(pk=self.gloria.pk).update(assigned_to=self.u_grace)
        self.assertEqual(self.client.get("/api/members/assign-shepherds/").data["changes"], [])


class NeverThemselves(Base):
    def test_profile_list_leaves_them_out(self):
        names = [s["name"] for s in self.client.get(f"/api/members/eligible-shepherds/?location=bahrain&member={self.kwabena.id}").data]
        self.assertNotIn("Kwabena Afari", names)
        self.assertIn("Chinedu Uguru", names)

    def test_saving_themselves_is_refused(self):
        r = self.client.patch(f"/api/members/{self.chinedu.id}/", {"assigned_to": self.u_chinedu.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Nobody can shepherd themselves", str(r.data))

    def test_bulk_assign_refuses_themselves(self):
        r = self.client.post("/api/members/bulk-assign-shepherd/", {"member_ids": [self.joshua.id, self.kwabena.id],
                                                                    "shepherd_id": self.u_kwabena.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Kwabena Afari", r.data["detail"])


class MemberRecord(Base):
    def test_admin_links_an_account_and_it_is_logged(self):
        r = self.client.patch(f"/api/users/{self.u_grace.id}/", {"member": self.grace_m.id}, format="json")
        self.assertEqual((r.status_code, r.data["member"]), (200, self.grace_m.id))
        self.assertTrue(AuditLog.objects.filter(action="Linked member record", details="Grace Uguru").exists())
        r = self.client.patch(f"/api/users/{self.u_grace.id}/", {"member": None}, format="json")
        self.assertIsNone(r.data["member"])

    def test_one_member_record_per_account(self):
        self.client.patch(f"/api/users/{self.u_grace.id}/", {"member": self.grace_m.id}, format="json")
        r = self.client.patch(f"/api/users/{self.u_gloria.id}/", {"member": self.grace_m.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("already the member record of", str(r.data))

    def test_choices_list_members_and_who_has_them(self):
        self.client.patch(f"/api/users/{self.u_grace.id}/", {"member": self.grace_m.id}, format="json")
        rows = {m["name"]: m for m in self.client.get("/api/users/member-choices/").data}
        self.assertEqual(rows["Grace Uguru"]["linked_to"], self.u_grace.id)
        self.assertIsNone(rows["Joshua Afari"]["linked_to"])

    def test_a_new_account_is_linked_by_name(self):
        r = self.client.post("/api/users/", {"email": "j@t.com", "password": "Strong-pass-2026", "first_name": "Joshua",
                                             "last_name": "Afari", "location": "bahrain"}, format="json")
        self.assertEqual((r.status_code, r.data["member"]), (201, self.joshua.id))
        r = self.client.post("/api/users/", {"email": "n@t.com", "password": "Strong-pass-2026", "first_name": "Nobody",
                                             "last_name": "Here", "location": "bahrain"}, format="json")
        self.assertIsNone(r.data["member"])


class LinkingOnUpdate(Base):
    """The migration's rule: exactly one member with the same full name, not already taken."""
    def test_rule(self):
        from accounts.linking import find_member
        self.assertEqual(find_member(self.u_kwabena, Member, User), self.kwabena)
        self.assertIsNone(find_member(self.u_grace, Member, User))       # Grace Thomas is not a member
        twin = Member.objects.create(first_name="Chinedu", surname="Uguru", gender="Male", location=self.qa, joined_date=D)
        self.assertEqual(find_member(self.u_chinedu, Member, User), self.chinedu)   # two names, his location decides
        User.objects.filter(pk=self.u_chinedu.pk).update(location=None)
        self.u_chinedu.refresh_from_db()
        self.assertIsNone(find_member(self.u_chinedu, Member, User))      # two names, no location: left alone
        twin.delete()
        self.u_gloria.member = self.chinedu; self.u_gloria.save()
        self.assertIsNone(find_member(self.u_chinedu, Member, User))      # already someone else's record

    def test_migration_links_the_live_accounts(self):
        from importlib import import_module
        from django.apps import apps
        mig = import_module("accounts.migrations.0006_link_accounts_to_members")
        mig.link(apps, None)
        got = dict(User.objects.exclude(member=None).values_list("email", "member__first_name"))
        self.assertEqual(got, {"k@t.com": "Kwabena", "g@t.com": "Gloria", "c@t.com": "Chinedu"})
