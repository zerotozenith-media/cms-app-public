"""
Version 11 upgrade: the reconciliation command, the new preflight
checks, meeting day handling, blank phone numbers, and fellowship
locations. Several of these guard bugs the upgrade rehearsal found on a
copy of a version 10 database.
"""
import datetime
from io import StringIO

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User
from attendance.models import AttendanceSession, Fellowship, MeetingType
from core.models import Location
from members.models import Member
from newcomers.models import Newcomer, NewcomerSource


class Base(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.others = Location.objects.create(id="others", name="Others")
        role = Role.objects.create(name="Administrator")
        for m in ["members", "attendance", "newcomers", "finance",
                  "goals", "reports", "outreach", "admin"]:
            RolePermission.objects.create(role=role, module=m, can_view=True,
                                          can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="u@t.com", password="x", role=role)
        self.client.force_authenticate(user=self.admin)
        self.today = timezone.localdate()
        self.source = NewcomerSource.objects.create(name="Walk-in")

    def newcomer(self, name, stage="member", phone="", email="", location=None):
        return Newcomer.objects.create(
            name=name, source=self.source, location=location or self.bahrain, stage=stage,
            created_at=self.today, stage_since=self.today - datetime.timedelta(days=40),
            phone=phone, email=email)

    def member(self, first, surname, phone=None, location=None, **kw):
        return Member.objects.create(first_name=first, surname=surname, phone=phone,
                                     location=location or self.bahrain,
                                     joined_date=self.today, category="general", **kw)

    def run_command(self, *args):
        out = StringIO()
        call_command("reconcile_converted_members", *args, stdout=out)
        return out.getvalue()


class ReconcileTestCase(Base):
    """Newcomers moved to Member before version 11 had no member record."""

    def test_a_dry_run_changes_nothing(self):
        self.newcomer("Joy Mensah")
        before = Member.objects.count()
        out = self.run_command()
        self.assertEqual(Member.objects.count(), before)
        self.assertIn("create  Joy Mensah", out)
        self.assertIn("--apply", out)

    def test_apply_creates_the_record(self):
        n = self.newcomer("Joy Mensah")
        self.run_command("--apply")
        m = Member.objects.get(from_newcomer=n)
        self.assertEqual((m.first_name, m.surname), ("Joy", "Mensah"))

    def test_the_join_date_is_when_they_reached_member(self):
        n = self.newcomer("Joy Mensah")
        self.run_command("--apply")
        self.assertEqual(Member.objects.get(from_newcomer=n).joined_date, n.stage_since)

    def test_a_phone_match_in_another_location_is_linked_not_duplicated(self):
        """They relocated and were typed onto the roll by hand there."""
        n = self.newcomer("Yusuf Chukwu", phone="+973 3999 1111")
        typed = self.member("Typed", "Elsewhere", phone="+97339991111", location=self.others)
        self.run_command("--apply")
        typed.refresh_from_db()
        self.assertEqual(typed.from_newcomer, n)
        self.assertEqual(Member.objects.filter(from_newcomer=n).count(), 1)

    def test_an_email_match_is_linked(self):
        n = self.newcomer("Ada Obi", email="ada@example.com")
        typed = self.member("Ada", "Obi", email="ADA@example.com")
        self.run_command("--apply")
        typed.refresh_from_db()
        self.assertEqual(typed.from_newcomer, n)

    def test_two_name_matches_are_left_for_a_person(self):
        n = self.newcomer("Grace Twice")
        self.member("Grace", "Twice", phone="+97330000001")
        self.member("Grace", "Twice", phone="+97330000002")
        out = self.run_command("--apply")
        self.assertIn("decide  Grace Twice", out)
        self.assertFalse(Member.objects.filter(from_newcomer=n).exists())

    def test_no_phone_is_stored_as_nothing(self):
        self.newcomer("First Nophone")
        self.newcomer("Second Nophone")
        self.run_command("--apply")
        self.assertEqual(Member.objects.filter(from_newcomer__isnull=False, phone__isnull=True).count(), 2)

    def test_running_again_changes_nothing(self):
        self.newcomer("Joy Mensah")
        self.run_command("--apply")
        before = Member.objects.count()
        out = self.run_command("--apply")
        self.assertEqual(Member.objects.count(), before)
        self.assertIn("Nothing to do", out)


class BlankPhoneTestCase(Base):
    """Once one member had no phone, adding a second failed with a server error."""

    def test_several_members_without_a_phone_can_be_added(self):
        for i in range(3):
            r = self.client.post("/api/members/", {
                "surname": f"Person{i}", "first_name": "No", "phone": "",
                "location": "bahrain", "joined_date": str(self.today), "category": "general",
            }, format="json")
            self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Member.objects.filter(phone__isnull=True).count(), 3)

    def test_make_member_twice_without_a_phone(self):
        for i in range(2):
            n = self.newcomer(f"No Phone{i}", stage="attending")
            r = self.client.post(f"/api/newcomers/{n.id}/make-member/")
            self.assertEqual(r.status_code, 201, r.data)

    def test_a_phone_already_on_the_roll_is_explained(self):
        self.member("Existing", "Person", phone="+97333333333")
        n = self.newcomer("Same Person", stage="attending", phone="+97333333333")
        r = self.client.post(f"/api/newcomers/{n.id}/make-member/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("already on the member roll", r.data["detail"])


class MeetingDayApiTestCase(Base):
    """A refused day used to reach the person as a server error."""

    def test_a_short_day_is_written_in_full(self):
        r = self.client.post("/api/meeting-types/", {
            "id": "fri", "name": "Friday Service", "day": "Fri",
            "frequency": "weekly", "detail_level": "simple"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["day"], "Friday")

    def test_a_nonsense_day_is_a_message_not_a_crash(self):
        r = self.client.post("/api/meeting-types/", {
            "id": "bad", "name": "Bad", "day": "Freeday",
            "frequency": "weekly", "detail_level": "simple"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("not a day of the week", str(r.data["day"]))

    def test_a_meeting_with_a_bad_day_says_what_to_fix(self):
        MeetingType.objects.create(id="ok", name="Ok", day="Friday",
                                   frequency="weekly", detail_level="simple")
        MeetingType.objects.filter(id="ok").update(day="Someday")   # as a v10 row might be
        r = self.client.patch("/api/meeting-types/ok/", {"collects_offering": True}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Someday", str(r.data["day"]))
        r = self.client.patch("/api/meeting-types/ok/", {"day": "friday"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["day"], "Friday")


class FellowshipLocationTestCase(Base):
    """Qatar was given every Bahrain fellowship's session each Friday."""

    def setUp(self):
        super().setUp()
        self.house = MeetingType.objects.create(
            id="fri-house", name="Friday House Caring Fellowship", day="Friday",
            frequency="weekly", detail_level="detailed", collects_offering=True)
        Fellowship.objects.create(name="HCF Women", meeting_type=self.house, location=self.bahrain)
        Fellowship.objects.create(name="HCF Men", meeting_type=self.house, location=self.bahrain)

    def sessions_at(self, loc):
        return AttendanceSession.objects.filter(meeting_type=self.house, location=loc)

    def test_fellowships_only_get_sessions_where_they_meet(self):
        call_command("generate_recurring_sessions", verbosity=0)
        self.assertEqual(self.sessions_at(self.bahrain).count(), 2)
        self.assertFalse(self.sessions_at(self.others).filter(fellowship__isnull=False).exists())

    def test_a_location_with_no_fellowships_keeps_one_session(self):
        """As it had before fellowships existed."""
        call_command("generate_recurring_sessions", verbosity=0)
        others = self.sessions_at(self.others)
        self.assertEqual(others.count(), 1)
        self.assertIsNone(others.first().fellowship)

    def test_a_fellowship_with_no_location_meets_everywhere(self):
        Fellowship.objects.create(name="HCF Online", meeting_type=self.house, location=None)
        call_command("generate_recurring_sessions", verbosity=0)
        self.assertEqual(self.sessions_at(self.others).count(), 1)
        self.assertEqual(self.sessions_at(self.others).first().fellowship.name, "HCF Online")
        self.assertEqual(self.sessions_at(self.bahrain).count(), 3)

    def test_a_fellowship_added_in_admin_is_scheduled(self):
        """It used to be created with no meeting and never get a session."""
        r = self.client.post("/api/fellowships/", {"name": "HCF Youth", "area": "Isa Town",
                                                    "location": "bahrain"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["meeting_type"], "fri-house")
        call_command("generate_recurring_sessions", verbosity=0)
        self.assertTrue(self.sessions_at(self.bahrain).filter(fellowship__name="HCF Youth").exists())


class PreflightUpgradeTestCase(Base):
    """What the data steps leave for a person is reported plainly."""

    def run_preflight(self):
        out = StringIO()
        try:
            call_command("preflight", stdout=out)
        except SystemExit:
            pass
        return out.getvalue()

    def test_an_unreadable_day_is_a_problem(self):
        MeetingType.objects.create(id="x", name="Odd Meeting", day="Friday",
                                   frequency="weekly", detail_level="simple")
        MeetingType.objects.filter(id="x").update(day="Someday")
        self.assertIn("Odd Meeting (Someday)", self.run_preflight())

    def test_an_unlinked_fellowship_is_a_problem(self):
        Fellowship.objects.create(name="HCF Loose")
        self.assertIn("not linked to a meeting: HCF Loose", self.run_preflight())

    def test_unreconciled_members_are_reported_with_the_command(self):
        self.newcomer("Joy Mensah")
        out = self.run_preflight()
        self.assertIn("1 newcomer(s) shown as members have no member record", out)
        self.assertIn("reconcile_converted_members", out)

    def test_fellowship_locations_are_listed(self):
        house = MeetingType.objects.create(id="fri-house", name="House", day="Friday",
                                           frequency="weekly", detail_level="detailed")
        Fellowship.objects.create(name="HCF Men", meeting_type=house, location=self.bahrain)
        self.assertIn("HCF Men (Bahrain)", self.run_preflight())


class RemovingThingsInUseTestCase(Base):
    """
    Removing something still in use is refused with a reason. Before, a
    fund gave a server error and a campaign was deleted, silently wiping
    the campaign from its enquiries.
    """

    def test_a_fund_in_use_is_refused_with_a_reason(self):
        from finance.models import Fund, Giving, PaymentMethod
        fund = Fund.objects.create(name="Tithe")
        Giving.objects.create(date=self.today, fund=fund, amount=10,
                              method=PaymentMethod.objects.create(name="Cash"),
                              location=self.bahrain)
        r = self.client.delete(f"/api/funds/{fund.id}/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("still used by 1 record", r.data["detail"])
        self.assertTrue(Fund.objects.filter(id=fund.id).exists())

    def test_an_unused_fund_can_be_removed(self):
        from finance.models import Fund
        fund = Fund.objects.create(name="Unused")
        self.assertEqual(self.client.delete(f"/api/funds/{fund.id}/").status_code, 204)

    def test_a_campaign_with_enquiries_is_kept(self):
        from enquiries.models import Campaign, Enquiry, EnquirySource
        camp = Campaign.objects.create(name="Easter")
        Enquiry.objects.create(name="Asked", campaign=camp,
                               source=EnquirySource.objects.create(name="Instagram"))
        r = self.client.delete(f"/api/campaigns/{camp.id}/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Easter", r.data["detail"])
        self.assertTrue(Campaign.objects.filter(id=camp.id).exists())

    def test_an_unused_campaign_can_be_removed(self):
        from enquiries.models import Campaign
        camp = Campaign.objects.create(name="Unused")
        self.assertEqual(self.client.delete(f"/api/campaigns/{camp.id}/").status_code, 204)

    def test_a_location_in_use_says_so_plainly(self):
        self.member("Someone", "Here", location=self.others)
        r = self.client.delete("/api/locations/others/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Others still has", r.data["detail"])
        self.assertNotIn("protected foreign keys", r.data["detail"])


class ProjectsFromAdminTestCase(Base):
    """The Projects card sent fields the server did not have, so adding
    one always failed and the list showed NaN."""

    def test_a_project_needs_only_a_name_target_and_location(self):
        r = self.client.post("/api/projects/", {"name": "New Hall Fund",
                             "target_amount": "5000", "location": "bahrain"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["id"], "new-hall-fund")
        self.assertEqual(r.data["location_name"], "Bahrain")

    def test_two_projects_with_one_name_get_different_ids(self):
        for _ in range(2):
            r = self.client.post("/api/projects/", {"name": "Hall",
                                 "target_amount": "10", "location": "bahrain"}, format="json")
            self.assertEqual(r.status_code, 201, r.data)
        from finance.models import Project
        self.assertEqual(sorted(Project.objects.values_list("id", flat=True)), ["hall", "hall-2"])


class AuditOncePerActionTestCase(Base):
    """
    The automatic entry fired during the save and the view's fuller entry
    came after, so creates and deletes were logged twice.
    """
    def entries(self, **kw):
        from accounts.models import AuditLog
        return AuditLog.objects.filter(**kw)

    def test_creating_a_project_is_logged_once(self):
        r = self.client.post("/api/projects/", {"name": "Hall Fund", "target_amount": "100",
                                                 "location": "bahrain"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.entries(action="Created", entity_type__iexact="project").count(), 1)

    def test_deleting_a_project_is_logged_once(self):
        r = self.client.post("/api/projects/", {"name": "Hall Fund", "target_amount": "100",
                                                 "location": "bahrain"}, format="json")
        self.client.delete(f"/api/projects/{r.data['id']}/")
        self.assertEqual(self.entries(action="Deleted", entity_type__iexact="project").count(), 1)

    def test_the_fuller_entry_wins(self):
        """The one kept is the view's, with its user, not the bare automatic one."""
        self.client.post("/api/projects/", {"name": "Hall Fund", "target_amount": "100",
                                             "location": "bahrain"}, format="json")
        e = self.entries(action="Created", entity_type__iexact="project").get()
        self.assertEqual(e.user, self.admin)

    def test_a_save_with_no_hand_written_entry_is_still_logged(self):
        r = self.client.post("/api/members/", {"surname": "Solo", "first_name": "Only",
            "location": "bahrain", "joined_date": str(self.today), "category": "general"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertGreaterEqual(self.entries(entity_type__iexact="member", entity_name__icontains="Solo").count(), 1)

    def test_recording_a_remittance_is_one_entry(self):
        from decimal import Decimal
        from finance.models import Fund
        fund = Fund.objects.create(name="Tithe")
        self.client.post("/api/remittances/", {"month": f"{self.today:%Y-%m}-01", "sent_on": str(self.today),
            "lines": [{"fund": fund.id, "amount_due": "10.000", "amount_sent": "10.000",
                       "destination": "dubai"}]}, format="json")
        self.assertEqual(self.entries(entity_type="Remittance").count(), 1)
        self.assertFalse(self.entries(entity_type__icontains="remittance line").exists())


class UserManagementReachTestCase(Base):
    """
    A location coordinator could create a new all-locations Administrator,
    then sign in as it and see everything.
    """
    def setUp(self):
        super().setUp()
        self.admin_role = Role.objects.get(name="Administrator")
        self.coord_role = Role.objects.create(name="Location Coordinator")
        for m in ["members", "attendance", "newcomers", "finance", "goals", "reports", "outreach"]:
            RolePermission.objects.create(role=self.coord_role, module=m, can_view=True,
                                          can_create=True, can_edit=True, can_delete=True)
        RolePermission.objects.create(role=self.coord_role, module="admin", can_view=True,
                                      can_create=True, can_edit=False, can_delete=False)
        self.coord = User.objects.create_user(email="c@t.com", password="x", role=self.coord_role,
                                              location=self.bahrain)
        self.qatar_user = User.objects.create_user(email="q@t.com", password="x",
                                                   role=self.coord_role, location=self.others)

    def as_coord(self):
        self.client.force_authenticate(user=self.coord)

    def new_user(self, **kw):
        body = {"email": "n@t.com", "password": "Secret123!x", "first_name": "N", "last_name": "U",
                "role": self.coord_role.id, "location": "bahrain"}
        body.update(kw)
        return self.client.post("/api/users/", body, format="json")

    def test_a_coordinator_cannot_create_an_all_locations_account(self):
        self.as_coord()
        r = self.new_user(location=None)
        self.assertEqual(r.status_code, 403)

    def test_a_coordinator_cannot_create_an_account_elsewhere(self):
        self.as_coord()
        self.assertEqual(self.new_user(location="others").status_code, 403)

    def test_a_coordinator_cannot_grant_a_more_powerful_role(self):
        self.as_coord()
        r = self.new_user(role=self.admin_role.id)
        self.assertEqual(r.status_code, 403)
        self.assertIn("your own role cannot", str(r.data))

    def test_a_coordinator_can_add_someone_at_their_own_location(self):
        self.as_coord()
        r = self.new_user()
        self.assertEqual(r.status_code, 201, r.data)

    def test_a_coordinator_only_sees_their_own_locations_accounts(self):
        self.as_coord()
        emails = [u["email"] for u in self.client.get("/api/users/").data["results"]]
        self.assertIn("c@t.com", emails)
        self.assertNotIn("q@t.com", emails)
        self.assertNotIn("u@t.com", emails)   # the all-locations administrator

    def test_the_administrator_can_still_assign_any_role(self):
        r = self.new_user(role=self.admin_role.id, location=None, email="a2@t.com")
        self.assertEqual(r.status_code, 201, r.data)

    def test_the_audit_log_is_limited_to_their_location(self):
        from accounts.models import AuditLog
        AuditLog.objects.create(user=self.qatar_user, user_name_snapshot="Q", action="Created",
                                entity_type="Member", entity_name="Qatar person")
        self.as_coord()
        names = [e["entity_name"] for e in self.client.get("/api/audit-log/").data["results"]]
        self.assertNotIn("Qatar person", names)


class FutureSessionTestCase(Base):
    """Attendance for next Friday stood as the latest service on the dashboard."""
    def setUp(self):
        super().setUp()
        self.mt = MeetingType.objects.create(id="fri-worship", name="Friday Worship", day="Friday",
                                             frequency="weekly", detail_level="detailed")
        self.future = AttendanceSession.objects.create(
            meeting_type=self.mt, location=self.bahrain, mode="in-person", status="pending",
            date=self.today + datetime.timedelta(days=5))
        self.today_s = AttendanceSession.objects.create(
            meeting_type=self.mt, location=self.bahrain, mode="in-person", status="pending",
            date=self.today)

    def test_a_future_service_cannot_be_recorded(self):
        r = self.client.post(f"/api/attendance-sessions/{self.future.id}/record/", {"men": 1}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("on the day or after", r.data["detail"])

    def test_todays_service_can_be_recorded(self):
        r = self.client.post(f"/api/attendance-sessions/{self.today_s.id}/record/", {"men": 1}, format="json")
        self.assertEqual(r.status_code, 200, r.data)

    def test_nobody_can_be_checked_in_to_a_future_service(self):
        m = self.member("Early", "Bird")
        r = self.client.post(f"/api/attendance-sessions/{self.future.id}/check_in/", {"member_id": m.id}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_a_future_figure_is_never_the_latest(self):
        AttendanceSession.objects.filter(id=self.future.id).update(status="filled", men=99)
        d = self.client.get("/api/dashboard/summary/").data
        self.assertNotEqual(d["attendance"]["latest"], 99)


class FollowUpScopingTestCase(Base):
    """A Bahrain coordinator could see and act on Qatar's follow-ups."""
    def setUp(self):
        super().setUp()
        from members.models import MemberFollowUpTask
        from newcomers.models import NewcomerTask
        coord_role = Role.objects.create(name="Coordinator")
        for m in ["members", "newcomers"]:
            RolePermission.objects.create(role=coord_role, module=m, can_view=True,
                                          can_create=True, can_edit=True, can_delete=True)
        self.coord = User.objects.create_user(email="c@t.com", password="x", role=coord_role,
                                              location=self.bahrain)
        self.qatar_member = self.member("Far", "Away", location=self.others)
        self.qatar_newcomer = self.newcomer("Qatar Visitor", stage="attending", location=self.others)
        self.m_task = MemberFollowUpTask.objects.create(
            member=self.qatar_member, text="Call", due_date=self.today,
            missed_meeting_name="Friday Worship", missed_date=self.today)
        self.n_task = NewcomerTask.objects.create(newcomer=self.qatar_newcomer, text="Visit",
                                                  due_date=self.today)
        self.client.force_authenticate(user=self.coord)

    def ids(self, url):
        d = self.client.get(url).data
        return [x["id"] for x in d.get("results", d)]

    def test_member_follow_ups_elsewhere_are_hidden(self):
        self.assertNotIn(self.m_task.id, self.ids("/api/member-followup-tasks/"))

    def test_newcomer_tasks_elsewhere_are_hidden(self):
        self.assertNotIn(self.n_task.id, self.ids("/api/newcomer-tasks/"))

    def test_a_task_elsewhere_cannot_be_opened(self):
        self.assertEqual(self.client.get(f"/api/newcomer-tasks/{self.n_task.id}/").status_code, 404)

    def test_a_task_cannot_be_pinned_on_someone_elsewhere(self):
        from newcomers.models import NewcomerTask
        r = self.client.post("/api/newcomer-tasks/", {"newcomer": self.qatar_newcomer.id,
                             "text": "Sneaky", "due_date": str(self.today)}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(NewcomerTask.objects.filter(text="Sneaky").exists())


class FellowshipScopingTestCase(Base):
    def test_another_locations_fellowships_are_hidden(self):
        house = MeetingType.objects.create(id="fri-house", name="House", day="Friday",
                                           frequency="weekly", detail_level="detailed")
        Fellowship.objects.create(name="HCF Men", meeting_type=house, location=self.bahrain)
        Fellowship.objects.create(name="HCF Online", meeting_type=house, location=None)
        role = Role.objects.create(name="Qatar Coordinator")
        RolePermission.objects.create(role=role, module="attendance", can_view=True)
        self.client.force_authenticate(user=User.objects.create_user(
            email="q@t.com", password="x", role=role, location=self.others))
        d = self.client.get("/api/fellowships/").data
        names = [f["name"] for f in d.get("results", d)]
        self.assertEqual(names, ["HCF Online"])


class LocationNamesTestCase(Base):
    def test_anyone_signed_in_can_read_location_names(self):
        role = Role.objects.create(name="Usher only")
        RolePermission.objects.create(role=role, module="attendance", can_view=True)
        self.client.force_authenticate(user=User.objects.create_user(
            email="us@t.com", password="x", role=role, location=self.bahrain))
        d = self.client.get("/api/locations/").data
        self.assertIn("Bahrain", [l["name"] for l in d.get("results", d)])

    def test_changing_a_location_still_needs_admin(self):
        role = Role.objects.create(name="Usher only 2")
        RolePermission.objects.create(role=role, module="attendance", can_view=True)
        self.client.force_authenticate(user=User.objects.create_user(
            email="us2@t.com", password="x", role=role, location=self.bahrain))
        self.assertEqual(self.client.post("/api/locations/", {"id": "x", "name": "X"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete("/api/locations/others/").status_code, 403)


class AutoAssignWithNewcomersTestCase(Base):
    """
    Applying a batch that included a newcomer crashed, after saving the
    members before it. Tasks never followed the new shepherd either.
    """
    def setUp(self):
        super().setUp()
        # Newcomers are included by default.
        worker = Member.objects.create(first_name="Grace", surname="Shepherd",
                                       location=self.bahrain, joined_date=self.today,
                                       category=Member.Category.WORKER)
        self.shepherd = User.objects.create_user(email="s@t.com", password="x",
                                                 role=Role.objects.get(name="Administrator"),
                                                 member=worker, location=self.bahrain)
        self.person = self.member("Plain", "Member")
        self.visitor = self.newcomer("New Visitor", stage="attending")
        from newcomers.models import NewcomerTask
        self.task = NewcomerTask.objects.create(newcomer=self.visitor, text="Visit", due_date=self.today)

    def test_a_batch_with_a_newcomer_applies(self):
        preview = self.client.get("/api/members/assign-shepherds/").data["changes"]
        self.assertTrue(any(c["kind"] == "newcomer" for c in preview), preview)
        r = self.client.post("/api/members/assign-shepherds/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.visitor.refresh_from_db(); self.person.refresh_from_db()
        self.assertEqual(self.visitor.assigned_to, self.shepherd)
        self.assertEqual(self.person.assigned_to, self.shepherd)

    def test_the_newcomers_tasks_follow_them(self):
        self.client.post("/api/members/assign-shepherds/", {}, format="json")
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_to, self.shepherd)


class AttendanceRosterTestCase(Base):
    """An usher could not see any names to tick off."""
    def setUp(self):
        super().setUp()
        role = Role.objects.create(name="Usher")
        RolePermission.objects.create(role=role, module="attendance", can_view=True,
                                      can_create=True, can_edit=True)
        self.usher = User.objects.create_user(email="us@t.com", password="x", role=role,
                                              location=self.bahrain)
        self.here = self.member("Ada", "Here", phone="+97333330001", email="ada@x.com")
        self.there = self.member("Ben", "There", location=self.others)
        self.client.force_authenticate(user=self.usher)

    def test_an_usher_gets_names_to_tick_off(self):
        r = self.client.get("/api/attendance-roster/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Ada Here", [m["full_name"] for m in r.data["results"]])

    def test_only_what_attendance_needs_is_sent(self):
        row = self.client.get("/api/attendance-roster/").data["results"][0]
        self.assertNotIn("phone", row)
        self.assertNotIn("email", row)

    def test_it_is_limited_to_their_location(self):
        names = [m["full_name"] for m in self.client.get("/api/attendance-roster/").data["results"]]
        self.assertNotIn("Ben There", names)

    def test_search_finds_by_name(self):
        r = self.client.get("/api/attendance-roster/?search=ada")
        self.assertEqual([m["full_name"] for m in r.data["results"]], ["Ada Here"])

    def test_it_still_needs_attendance_permission(self):
        role = Role.objects.create(name="Finance only")
        RolePermission.objects.create(role=role, module="finance", can_view=True)
        self.client.force_authenticate(user=User.objects.create_user(
            email="f@t.com", password="x", role=role, location=self.bahrain))
        self.assertEqual(self.client.get("/api/attendance-roster/").status_code, 403)


class FellowshipDefaultLocationTestCase(Base):
    def setUp(self):
        super().setUp()
        MeetingType.objects.create(id="fri-house", name="House", day="Friday",
                                   frequency="weekly", detail_level="detailed")

    def test_added_without_a_location_it_meets_at_the_main_one(self):
        r = self.client.post("/api/fellowships/", {"name": "HCF New", "area": "Riffa"}, format="json")
        self.assertEqual(r.data["location"], "bahrain")

    def test_a_coordinator_adds_it_at_their_own_location(self):
        role = Role.objects.create(name="Qatar coord")
        RolePermission.objects.create(role=role, module="attendance", can_view=True, can_create=True)
        self.client.force_authenticate(user=User.objects.create_user(
            email="qc@t.com", password="x", role=role, location=self.others))
        r = self.client.post("/api/fellowships/", {"name": "HCF Doha"}, format="json")
        self.assertEqual(r.data["location"], "others")

    def test_every_location_can_still_be_chosen_on_purpose(self):
        r = self.client.post("/api/fellowships/", {"name": "HCF Online", "location": None}, format="json")
        self.assertIsNone(r.data["location"])


class ActionMeaningTestCase(Base):
    """
    Actions were judged by request type: a role that could only add
    records could move stages and put people on the member roll.
    """
    def setUp(self):
        super().setUp()
        role = Role.objects.create(name="Adds only")
        for m in ["newcomers", "members", "attendance"]:
            RolePermission.objects.create(role=role, module=m, can_view=True, can_create=True)
        self.client.force_authenticate(user=User.objects.create_user(
            email="add@t.com", password="x", role=role, location=self.bahrain))
        self.n = self.newcomer("Joy Mensah", stage="attending")

    def test_cannot_move_a_stage(self):
        r = self.client.post(f"/api/newcomers/{self.n.id}/change-stage/", {"to_stage": "contacted"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_cannot_make_a_member(self):
        self.assertEqual(self.client.post(f"/api/newcomers/{self.n.id}/make-member/").status_code, 403)
        self.assertFalse(Member.objects.filter(from_newcomer=self.n).exists())

    def test_cannot_move_a_members_category(self):
        m = self.member("Some", "One")
        r = self.client.post(f"/api/members/{m.id}/move-category/", {"to_category": "Worker"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_cannot_record_a_session(self):
        mt = MeetingType.objects.create(id="fri-worship", name="Friday", day="Friday",
                                        frequency="weekly", detail_level="detailed")
        s = AttendanceSession.objects.create(meeting_type=mt, location=self.bahrain, date=self.today,
                                             mode="in-person", status="pending")
        self.assertEqual(self.client.post(f"/api/attendance-sessions/{s.id}/record/", {"men": 1}, format="json").status_code, 403)

    def test_can_still_log_an_attempt(self):
        r = self.client.post(f"/api/newcomers/{self.n.id}/log-attempt/", {"method": "Phone call"}, format="json")
        self.assertNotEqual(r.status_code, 403)


class EnquiryConversionShepherdTestCase(Base):
    """A converted enquiry used to arrive on the board with no shepherd."""
    def setUp(self):
        super().setUp()
        from enquiries.models import Enquiry, EnquirySource
        worker = Member.objects.create(first_name="Grace", surname="Shepherd", location=self.bahrain,
                                       joined_date=self.today, category=Member.Category.WORKER)
        self.shepherd = User.objects.create_user(email="s@t.com", password="x",
                                                 role=Role.objects.get(name="Administrator"),
                                                 member=worker, location=self.bahrain)
        self.qatar_handler = User.objects.create_user(email="qh@t.com", password="x",
                                                      role=Role.objects.get(name="Administrator"),
                                                      location=self.others)
        src = EnquirySource.objects.create(name="Instagram")
        self.unassigned = Enquiry.objects.create(name="Joy", source=src, phone="+97330000011")
        self.handled_elsewhere = Enquiry.objects.create(name="Ben", source=src, phone="+97330000012",
                                                        assigned_to=self.qatar_handler)

    def convert(self, e):
        return self.client.post(f"/api/enquiries/{e.id}/convert/", {"location": "bahrain"}, format="json")

    def test_an_unassigned_enquiry_gets_a_shepherd(self):
        self.assertEqual(self.convert(self.unassigned).status_code, 200)
        self.unassigned.refresh_from_db()
        self.assertEqual(self.unassigned.converted_newcomer.assigned_to, self.shepherd)

    def test_a_handler_who_is_not_a_shepherd_there_is_replaced(self):
        self.convert(self.handled_elsewhere)
        self.handled_elsewhere.refresh_from_db()
        self.assertEqual(self.handled_elsewhere.converted_newcomer.assigned_to, self.shepherd)


class EnquiryTaskCompletionTestCase(Base):
    """Replying to a message should not need a scripture and a root cause."""
    def setUp(self):
        super().setUp()
        from enquiries.models import Enquiry, EnquirySource, EnquiryTask
        e = Enquiry.objects.create(name="Joy", source=EnquirySource.objects.create(name="Instagram"),
                                   phone="+97330000021")
        self.task = EnquiryTask.objects.create(enquiry=e, text="Reply", due_date=self.today)
        self.method = EnquiryTask.Method.choices[0][0]

    def test_how_they_were_reached_is_enough(self):
        r = self.client.post(f"/api/enquiry-tasks/{self.task.id}/complete/",
                             {"contact_method": self.method}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.task.refresh_from_db()
        self.assertTrue(self.task.done)

    def test_how_they_were_reached_is_still_required(self):
        r = self.client.post(f"/api/enquiry-tasks/{self.task.id}/complete/", {}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_pastoral_follow_ups_still_require_the_questions(self):
        from members.models import MemberFollowUpTask
        m = self.member("Some", "One")
        t = MemberFollowUpTask.objects.create(member=m, text="Visit", due_date=self.today,
                                              missed_meeting_name="Friday", missed_date=self.today)
        r = self.client.post(f"/api/member-followup-tasks/{t.id}/complete/",
                             {"contact_method": "Phone call"}, format="json")
        self.assertEqual(r.status_code, 400)


class OwnLocationOnlyTestCase(Base):
    """A Bahrain coordinator could create records of every kind for Qatar."""
    def setUp(self):
        super().setUp()
        from finance.models import Fund, PaymentMethod, ExpenseCategory
        role = Role.objects.create(name="Bahrain coordinator")
        for m in ["members", "attendance", "newcomers", "finance"]:
            RolePermission.objects.create(role=role, module=m, can_view=True,
                                          can_create=True, can_edit=True, can_delete=True)
        self.client.force_authenticate(user=User.objects.create_user(
            email="bc@t.com", password="x", role=role, location=self.bahrain))
        self.fund = Fund.objects.create(name="Tithe")
        self.method = PaymentMethod.objects.create(name="Cash")
        self.cat = ExpenseCategory.objects.create(name="Rent")

    def giving(self, loc):
        return self.client.post("/api/giving/", {"date": str(self.today), "fund": self.fund.id,
                                "method": self.method.id, "amount": "5", "location": loc}, format="json")

    def test_giving_for_another_location_is_refused(self):
        r = self.giving("others")
        self.assertEqual(r.status_code, 403)
        self.assertIn("your own location", str(r.data))

    def test_giving_for_their_own_location_is_fine(self):
        self.assertEqual(self.giving("bahrain").status_code, 201)

    def test_an_expense_for_another_location_is_refused(self):
        r = self.client.post("/api/expenses/", {"date": str(self.today), "category": self.cat.id,
                             "amount": "5", "location": "others", "description": "x"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_a_member_for_another_location_is_refused(self):
        r = self.client.post("/api/members/", {"surname": "X", "first_name": "Y", "location": "others",
                             "joined_date": str(self.today), "category": "General Member"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_moving_a_record_to_another_location_is_refused(self):
        m = self.member("Stay", "Here")
        r = self.client.patch(f"/api/members/{m.id}/", {"location": "others"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_an_all_locations_administrator_is_unaffected(self):
        self.client.force_authenticate(user=self.admin)
        self.assertEqual(self.giving("others").status_code, 201)


class FinanceRosterTestCase(Base):
    def test_a_finance_officer_gets_names_without_contact_details(self):
        role = Role.objects.create(name="Finance officer")
        RolePermission.objects.create(role=role, module="finance", can_view=True, can_create=True)
        self.client.force_authenticate(user=User.objects.create_user(
            email="fo@t.com", password="x", role=role, location=self.bahrain))
        self.member("Ada", "Giver", phone="+97333330009")
        r = self.client.get("/api/finance-roster/")
        self.assertEqual(r.status_code, 200)
        row = [m for m in r.data["results"] if m["full_name"] == "Ada Giver"][0]
        self.assertNotIn("phone", row)


class RemittancePerLocationTestCase(Base):
    """
    Remittance added up every location's money, and once one location
    recorded a month the other could not record its own.
    """
    def setUp(self):
        super().setUp()
        from decimal import Decimal
        from finance.models import Fund, PaymentMethod, Giving
        tithe = Fund.objects.create(name="Tithe"); cash = PaymentMethod.objects.create(name="Cash")
        d = self.today.replace(day=1); self.month = f"{d:%Y-%m}"
        Giving.objects.create(date=d, fund=tithe, method=cash, amount=Decimal("100"), location=self.bahrain)
        Giving.objects.create(date=d, fund=tithe, method=cash, amount=Decimal("40"), location=self.others)
        self.tithe = tithe
        role = Role.objects.create(name="Qatar finance")
        RolePermission.objects.create(role=role, module="finance", can_view=True, can_create=True, can_edit=True)
        self.qatar = User.objects.create_user(email="qf@t.com", password="x", role=role, location=self.others)

    def record(self, amount):
        return self.client.post("/api/remittances/", {"month": f"{self.month}-01", "sent_on": str(self.today),
            "lines": [{"fund": self.tithe.id, "amount_due": amount, "amount_sent": amount, "destination": "dubai"}]},
            format="json")

    def test_a_location_sees_only_its_own_money(self):
        self.client.force_authenticate(user=self.qatar)
        r = self.client.get(f"/api/remittances/proposed/?month={self.month}")
        self.assertEqual(float(r.data["collected"]), 40.0)

    def test_the_administrator_chooses_the_location(self):
        r = self.client.get(f"/api/remittances/proposed/?month={self.month}&location=bahrain")
        self.assertEqual(float(r.data["collected"]), 100.0)

    def test_both_locations_can_record_the_same_month(self):
        self.assertEqual(self.record("100.000").status_code, 201)
        self.client.force_authenticate(user=self.qatar)
        self.assertEqual(self.record("40.000").status_code, 201)

    def test_the_same_month_twice_for_one_location_is_explained(self):
        self.record("100.000")
        r = self.record("100.000")
        self.assertEqual(r.status_code, 400)
        self.assertIn("already recorded", str(r.data))

    def test_a_location_does_not_see_the_others_remittances(self):
        self.record("100.000")
        self.client.force_authenticate(user=self.qatar)
        d = self.client.get("/api/remittances/").data
        self.assertEqual(len(d.get("results", d)), 0)


class MonthlyAverageGoalTestCase(Base):
    """A goal named as a monthly average showed the latest single service."""
    def test_it_averages_this_months_services(self):
        from goals.models import Goal
        from goals.calculations import compute_goal_value
        mt = MeetingType.objects.create(id="fri-worship", name="Friday", day="Friday",
                                        frequency="weekly", detail_level="detailed")
        first = self.today.replace(day=1)
        for d, men in [(first, 60), (first, 40), (min(first.replace(day=2), self.today), 120)]:
            AttendanceSession.objects.create(meeting_type=mt, location=self.bahrain if men != 40 else self.others,
                                             date=d, mode="in-person", status="filled", men=men)
        g = Goal.objects.create(name="Friday (monthly avg)", horizon=Goal.Horizon.SHORT, target=150,
                                tracking="auto", calculation_type="monthly_average_attendance",
                                calculation_meeting_type=mt)
        value = compute_goal_value(g)
        if first == self.today:
            self.assertEqual(value, 220)          # one date: 60 + 40 + 120
        else:
            self.assertEqual(value, 110)          # (60 + 40) and 120, averaged


class ReportScopeTestCase(Base):
    """A location coordinator's report showed every location's figures."""
    def setUp(self):
        super().setUp()
        from decimal import Decimal
        from finance.models import Fund, PaymentMethod, Giving
        f = Fund.objects.create(name="Tithe"); m = PaymentMethod.objects.create(name="Cash")
        d = self.today.replace(day=1)
        Giving.objects.create(date=d, fund=f, method=m, amount=Decimal("100"), location=self.bahrain)
        Giving.objects.create(date=d, fund=f, method=m, amount=Decimal("40"), location=self.others)
        role = Role.objects.create(name="Qatar reports")
        RolePermission.objects.create(role=role, module="reports", can_view=True, can_create=True)
        self.qatar = User.objects.create_user(email="qr@t.com", password="x", role=role, location=self.others)

    def test_the_data_is_limited_to_one_location(self):
        from reports.pdf import gather_report_data
        whole = gather_report_data(self.today.year, self.today.month, "", self.admin)
        qatar = gather_report_data(self.today.year, self.today.month, "", self.admin, self.others)
        self.assertEqual(float(whole["income_total"]), 140.0)
        self.assertEqual(float(qatar["income_total"]), 40.0)
        self.assertEqual(qatar["scope_label"], "Others only")

    def test_a_coordinator_generates_their_own_locations_report(self):
        self.client.force_authenticate(user=self.qatar)
        r = self.client.post("/api/reports/generate/", {"period_month": self.today.month,
                             "period_year": self.today.year, "other_additions": ""}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["location"], "others")

    def test_the_whole_church_and_a_location_can_both_have_a_month(self):
        body = {"period_month": self.today.month, "period_year": self.today.year, "other_additions": ""}
        self.assertEqual(self.client.post("/api/reports/generate/", body, format="json").status_code, 201)
        self.client.force_authenticate(user=self.qatar)
        self.assertEqual(self.client.post("/api/reports/generate/", body, format="json").status_code, 201)

    def test_a_coordinator_does_not_see_the_whole_church_report(self):
        body = {"period_month": self.today.month, "period_year": self.today.year, "other_additions": ""}
        self.client.post("/api/reports/generate/", body, format="json")
        self.client.force_authenticate(user=self.qatar)
        d = self.client.get("/api/reports/").data
        self.assertEqual(len(d.get("results", d)), 0)


class ChurchWideSettingsTestCase(Base):
    """
    A location coordinator could add roles and meeting types, which affect
    every location, and anyone able to view Admin could flip church-wide
    switches.
    """
    def setUp(self):
        super().setUp()
        role = Role.objects.create(name="Coordinator")
        RolePermission.objects.create(role=role, module="admin", can_view=True, can_create=True)
        RolePermission.objects.create(role=role, module="attendance", can_view=True, can_create=True)
        self.coord = User.objects.create_user(email="co@t.com", password="x", role=role, location=self.bahrain)

    def test_a_coordinator_cannot_add_a_meeting_type(self):
        self.client.force_authenticate(user=self.coord)
        r = self.client.post("/api/meeting-types/", {"id": "x", "name": "X", "day": "Friday",
                             "frequency": "weekly", "detail_level": "simple"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertIn("every location", str(r.data))

    def test_a_coordinator_cannot_add_a_role(self):
        self.client.force_authenticate(user=self.coord)
        self.assertEqual(self.client.post("/api/roles/", {"name": "Mine"}, format="json").status_code, 403)

    def test_a_coordinator_can_still_read_them(self):
        self.client.force_authenticate(user=self.coord)
        self.assertEqual(self.client.get("/api/meeting-types/").status_code, 200)

    def test_viewing_admin_is_not_enough_to_change_a_setting(self):
        self.client.force_authenticate(user=self.coord)
        r = self.client.patch("/api/settings/", {"auto_assign_newcomers": False}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_the_administrator_still_can(self):
        r = self.client.post("/api/meeting-types/", {"id": "y", "name": "Y", "day": "Friday",
                             "frequency": "weekly", "detail_level": "simple"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)


class PublicRegistrationLocationTestCase(Base):
    """Every QR registration was filed under the main location."""
    def register(self, **extra):
        self.client.force_authenticate(user=None)
        body = {"name": f"Qr Visitor{len(extra)}", "phone": "+97339990000", **extra}
        return self.client.post("/api/public/newcomer-registration/", body, format="json")

    def test_the_qr_codes_location_is_used(self):
        r = self.register(location="others")
        self.assertIn(r.status_code, (200, 201), r.data)
        self.assertEqual(Newcomer.objects.get(name__endswith="Visitor1").location_id, "others")

    def test_without_one_it_goes_to_the_main_location(self):
        self.register()
        self.assertEqual(Newcomer.objects.get(name__endswith="Visitor0").location_id, "bahrain")

    def test_an_unknown_code_goes_to_the_main_location(self):
        self.register(location="nowhere")
        self.assertEqual(Newcomer.objects.get(name__endswith="Visitor1").location_id, "bahrain")


class LocationRenameTestCase(Base):
    def test_the_main_location_can_be_renamed(self):
        r = self.client.patch("/api/locations/bahrain/", {"name": "Bahrain HQ"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(Location.objects.get(id="bahrain").name, "Bahrain HQ")
        self.assertTrue(Location.objects.get(id="bahrain").is_core)

    def test_two_locations_cannot_share_a_name(self):
        r = self.client.patch("/api/locations/others/", {"name": "bahrain"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_the_short_code_cannot_change(self):
        r = self.client.patch("/api/locations/others/", {"id": "qatar"}, format="json")
        self.assertEqual(r.status_code, 400)


class MemberShepherdTestCase(Base):
    """A member's shepherd could be set to any account, not only a shepherd."""
    def setUp(self):
        super().setUp()
        worker = Member.objects.create(first_name="Grace", surname="Worker", location=self.bahrain,
                                       joined_date=self.today, category=Member.Category.WORKER)
        self.shepherd = User.objects.create_user(email="sh@t.com", password="x",
                                                 role=Role.objects.get(name="Administrator"),
                                                 member=worker, location=self.bahrain)
        self.not_a_shepherd = User.objects.create_user(email="fo@t.com", password="x",
                                                       role=Role.objects.get(name="Administrator"))
        self.person = self.member("Some", "One")

    def test_a_shepherd_can_be_set_on_the_profile(self):
        r = self.client.patch(f"/api/members/{self.person.id}/", {"assigned_to": self.shepherd.id}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["assigned_to_name"].split()[0], "Grace")

    def test_an_account_that_is_not_a_shepherd_is_refused(self):
        r = self.client.patch(f"/api/members/{self.person.id}/", {"assigned_to": self.not_a_shepherd.id}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_the_shepherd_can_be_cleared(self):
        self.client.patch(f"/api/members/{self.person.id}/", {"assigned_to": self.shepherd.id}, format="json")
        r = self.client.patch(f"/api/members/{self.person.id}/", {"assigned_to": None}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.data["assigned_to"])


class LockedMessageTestCase(Base):
    """After a lockout the right password still said "Invalid email or password"."""
    def attempt(self, email, password):
        self.client.force_authenticate(user=None)
        return self.client.post("/api/auth/login/", {"email": email, "password": password}, format="json")

    def test_a_locked_account_says_so(self):
        for _ in range(5):
            self.attempt(self.admin.email, "wrong")
        r = self.attempt(self.admin.email, "whatever the password")
        self.assertEqual(r.status_code, 429)
        self.assertIn("Too many attempts", r.data["detail"])

    def test_it_reveals_nothing_about_whether_an_account_exists(self):
        for _ in range(5):
            self.attempt("nobody@nowhere.org", "wrong")
        self.assertIn("Too many attempts", self.attempt("nobody@nowhere.org", "x").data["detail"])

    def test_a_wrong_password_is_still_generic(self):
        self.assertEqual(self.attempt(self.admin.email, "wrong").data["detail"], "Invalid email or password.")


class ReadinessPerLocationTestCase(Base):
    """Every location's Friday service counted, so full attendance scored 50%."""
    def test_full_attendance_at_their_location_is_100_percent(self):
        import datetime
        from attendance.models import AttendanceSessionMember
        from newcomers.membership import readiness
        mt = MeetingType.objects.create(id="fri-worship", name="Friday Worship", day="Friday",
                                        frequency="weekly", detail_level="detailed")
        n = self.newcomer("Faithful Visitor", stage="attending")
        start = self.today - datetime.timedelta(days=7 * 12)
        for week in range(12):
            d = start + datetime.timedelta(days=7 * week)
            here = AttendanceSession.objects.create(meeting_type=mt, location=self.bahrain, date=d,
                                                    mode="in-person", status="filled", men=10)
            AttendanceSession.objects.create(meeting_type=mt, location=self.others, date=d,
                                             mode="in-person", status="filled", men=5)
            AttendanceSessionMember.objects.create(session=here, newcomer=n)
        r = readiness(n, today=self.today)
        self.assertEqual(r["services_held"], 12)
        self.assertEqual(r["attendance_percent"], 100)

    def test_a_friday_attended_elsewhere_counts_without_passing_100_percent(self):
        import datetime
        from attendance.models import AttendanceSessionMember
        from newcomers.membership import readiness
        mt = MeetingType.objects.create(id="fri-worship", name="Friday Worship", day="Friday",
                                        frequency="weekly", detail_level="detailed")
        n = self.newcomer("Travelling Visitor", stage="attending")
        start = self.today - datetime.timedelta(days=7 * 4)
        for week in range(4):
            d = start + datetime.timedelta(days=7 * week)
            AttendanceSession.objects.create(meeting_type=mt, location=self.bahrain, date=d,
                                             mode="in-person", status="filled", men=10)
        away = AttendanceSession.objects.create(meeting_type=mt, location=self.others,
                                                date=start + datetime.timedelta(days=3),
                                                mode="in-person", status="filled", men=5)
        AttendanceSessionMember.objects.create(session=away, newcomer=n)
        for s in AttendanceSession.objects.filter(location=self.bahrain).order_by("date")[:2]:
            AttendanceSessionMember.objects.create(session=s, newcomer=n)
        r = readiness(n, today=self.today)
        self.assertEqual((r["services_attended"], r["services_held"]), (3, 5))
        self.assertLessEqual(r["attendance_percent"], 100)


class MemberKeepsShepherdTestCase(Base):
    """A newcomer made a member arrived on the roll with no shepherd."""
    def test_the_newcomers_shepherd_stays_with_them(self):
        worker = Member.objects.create(first_name="Grace", surname="Worker", location=self.bahrain,
                                       joined_date=self.today, category=Member.Category.WORKER)
        shepherd = User.objects.create_user(email="ks@t.com", password="x",
                                            role=Role.objects.get(name="Administrator"),
                                            member=worker, location=self.bahrain)
        n = self.newcomer("Joy Mensah", stage="attending")
        Newcomer.objects.filter(id=n.id).update(assigned_to=shepherd)
        self.assertIn(self.client.post(f"/api/newcomers/{n.id}/make-member/").status_code, (200, 201))
        self.assertEqual(Member.objects.get(from_newcomer=n).assigned_to, shepherd)

    def test_a_shepherd_from_another_location_is_not_carried_over(self):
        worker = Member.objects.create(first_name="Far", surname="Worker", location=self.others,
                                       joined_date=self.today, category=Member.Category.WORKER)
        elsewhere = User.objects.create_user(email="fw@t.com", password="x",
                                             role=Role.objects.get(name="Administrator"),
                                             member=worker, location=self.others)
        n = self.newcomer("Near Visitor", stage="attending")
        Newcomer.objects.filter(id=n.id).update(assigned_to=elsewhere)
        self.client.post(f"/api/newcomers/{n.id}/make-member/")
        self.assertIsNone(Member.objects.get(from_newcomer=n).assigned_to)


class NewFellowshipSessionTestCase(Base):
    """A new fellowship had no session until the scheduled job next ran."""
    def setUp(self):
        super().setUp()
        self.mt = MeetingType.objects.create(id="fri-house", name="House Fellowship", day="Friday",
                                             frequency="weekly", detail_level="detailed")

    def next_friday(self):
        import datetime
        return self.today + datetime.timedelta(days=(4 - self.today.weekday()) % 7)

    def test_it_gets_its_coming_session_at_once(self):
        r = self.client.post("/api/fellowships/", {"name": "HCF New", "location": "bahrain"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        s = AttendanceSession.objects.filter(fellowship_id=r.data["id"])
        self.assertEqual([x.date for x in s], [self.next_friday()])

    def test_an_untouched_plain_session_for_that_evening_is_replaced(self):
        AttendanceSession.objects.create(meeting_type=self.mt, location=self.bahrain, date=self.next_friday(),
                                         mode="in-person", status="pending")
        self.client.post("/api/fellowships/", {"name": "HCF First", "location": "bahrain"}, format="json")
        self.assertFalse(AttendanceSession.objects.filter(meeting_type=self.mt, location=self.bahrain,
                                                          fellowship__isnull=True).exists())

    def test_a_plain_session_already_filled_in_is_kept(self):
        AttendanceSession.objects.create(meeting_type=self.mt, location=self.bahrain, date=self.next_friday(),
                                         mode="in-person", status="pending", men=4)
        self.client.post("/api/fellowships/", {"name": "HCF Second", "location": "bahrain"}, format="json")
        self.assertTrue(AttendanceSession.objects.filter(meeting_type=self.mt, location=self.bahrain,
                                                         fellowship__isnull=True).exists())


class NewcomerMovedTestCase(Base):
    """Moving a newcomer left them with a shepherd at the old location."""
    def test_moving_gives_them_a_shepherd_at_the_new_location(self):
        def shepherd(email, loc):
            w = Member.objects.create(first_name=email[:3], surname="Worker", location=loc,
                                      joined_date=self.today, category=Member.Category.WORKER)
            return User.objects.create_user(email=email, password="x", member=w, location=loc,
                                            role=Role.objects.get(name="Administrator"))
        here, there = shepherd("bh@t.com", self.bahrain), shepherd("qa@t.com", self.others)
        n = self.newcomer("Moving Visitor", stage="new")
        Newcomer.objects.filter(id=n.id).update(assigned_to=here)
        from newcomers.models import NewcomerTask
        task = NewcomerTask.objects.create(newcomer=n, text="Visit", due_date=self.today, assigned_to=here)
        r = self.client.patch(f"/api/newcomers/{n.id}/", {"location": "others", "phone": "+97430000001"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        n.refresh_from_db(); task.refresh_from_db()
        self.assertEqual((n.assigned_to, task.assigned_to, n.phone), (there, there, "+97430000001"))


class WorkerLeavesTestCase(Base):
    """Part 12: when a worker leaves, Reassign everyone moves their people."""
    def test_reassign_everyone_moves_people_off_a_former_worker(self):
        def shepherd(email, first):
            w = Member.objects.create(first_name=first, surname="Worker", location=self.bahrain,
                                      joined_date=self.today, category=Member.Category.WORKER)
            return User.objects.create_user(email=email, password="x", member=w, location=self.bahrain,
                                            role=Role.objects.get(name="Administrator")), w
        leaving, leaving_member = shepherd("lv@t.com", "Leaving")
        staying, _ = shepherd("st@t.com", "Staying")
        people = [self.member(f"P{i}", "Person") for i in range(3)]
        Member.objects.filter(id__in=[p.id for p in people]).update(assigned_to=leaving)
        Member.objects.filter(id=leaving_member.id).update(category=Member.Category.GENERAL)
        r = self.client.post("/api/members/assign-shepherds/", {"reassign_everyone": True}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertFalse(Member.objects.filter(assigned_to=leaving).exists())
        self.assertTrue(all(Member.objects.get(id=p.id).assigned_to == staying for p in people))


class PreflightSchedulingTestCase(Base):
    """
    Preflight looked only for a crontab, so a site whose jobs ran from
    GitHub Actions was told they were not scheduled, and a managed Azure
    database was told it had no backup.
    """
    def preflight(self):
        import io
        from unittest import mock
        from django.core.management import call_command
        out = io.StringIO()
        with mock.patch("shutil.which", return_value=None):
            try:
                call_command("preflight", stdout=out)
            except SystemExit:
                pass
        return out.getvalue()

    def ran(self, command, hours_ago, details="Completed"):
        import datetime
        from django.utils import timezone
        from accounts.models import AuditLog
        e = AuditLog.objects.create(user=None, user_name_snapshot="System", action="Scheduled task",
                                    entity_type="System", entity_name=command, details=details)
        AuditLog.objects.filter(id=e.id).update(timestamp=timezone.now() - datetime.timedelta(hours=hours_ago))

    def test_recent_runs_from_an_outside_scheduler_are_fine(self):
        self.ran("check_absences", 1); self.ran("generate_recurring_sessions", 20)
        out = self.preflight()
        self.assertIn("the absence check runs from an outside scheduler", out)
        self.assertIn("weekly session creation runs from an outside scheduler", out)
        self.assertNotIn("not scheduled", out)

    def test_a_stale_job_is_reported_with_where_to_look(self):
        self.ran("check_absences", 30)
        out = self.preflight()
        self.assertIn("the absence check last ran 30 hours ago, but should run hourly", out)
        self.assertIn("GitHub Actions", out)

    def test_a_failed_run_is_reported(self):
        self.ran("check_absences", 2); self.ran("check_absences", 1, "Failed: database locked")
        self.assertIn("the absence check failed the last time it ran", self.preflight())

    def test_no_run_at_all_is_reported(self):
        self.assertIn("weekly session creation has never run", self.preflight())

    def test_an_azure_database_is_backed_up_by_azure(self):
        from unittest import mock
        from django.db import connection
        with mock.patch.dict(connection.settings_dict, {"HOST": "dclm.postgres.database.azure.com"}):
            out = self.preflight()
        self.assertIn("backs it up automatically", out)
        self.assertNotIn("no database backup is scheduled", out)
