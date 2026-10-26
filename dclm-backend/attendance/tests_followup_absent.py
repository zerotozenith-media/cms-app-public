"""'Follow up those not ticked' on a service ticked off afterwards, and
follow-up tasks added by hand on a member's profile (Kay, 17 Oct 2026)."""
import datetime

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User
from attendance.models import AttendanceSession, AttendanceSessionMember, MeetingType
from core.models import Location
from members.models import Member, MemberFollowUpTask

D = datetime.date


class Base(APITestCase):
    def setUp(self):
        self.bh = Location.objects.create(id="bahrain", name="Bahrain HQ", is_core=True)
        self.qa = Location.objects.create(id="others", name="Qatar")
        usher = Role.objects.create(name="Usher")
        RolePermission.objects.create(role=usher, module="attendance", can_view=True, can_edit=True)
        RolePermission.objects.create(role=usher, module="members", can_view=True, can_create=True)
        self.usher = User.objects.create_user(email="u@t.com", password="x", role=usher)
        viewer = Role.objects.create(name="Viewer")
        RolePermission.objects.create(role=viewer, module="attendance", can_view=True)
        RolePermission.objects.create(role=viewer, module="members", can_view=True)
        self.viewer = User.objects.create_user(email="v@t.com", password="x", role=viewer)
        self.shepherd = User.objects.create_user(email="s@t.com", password="x", role=usher, can_shepherd=True, gender="Male")
        self.other = User.objects.create_user(email="o@t.com", password="x", role=usher, can_shepherd=True, gender="Male")
        self.client.force_authenticate(self.usher)
        self.today = timezone.localdate()
        self.fri = MeetingType.objects.create(id="fri-worship", name="Friday Worship Service", day="Friday", frequency="weekly",
                                              detail_level="detailed", counts_for_absence=True, start_time=datetime.time(18, 0))
        self.mon = MeetingType.objects.create(id="mon-bs", name="Monday Bible Study", day="Monday", frequency="weekly",
                                              detail_level="detailed")
        self.sat = MeetingType.objects.create(id="sat-workers", name="Saturday Workers Meeting", day="Saturday",
                                              frequency="weekly", detail_level="simple", audience="workers")
        mk = lambda s, f, **kw: Member.objects.create(surname=s, first_name=f, location=self.bh, joined_date=D(2026, 7, 1),
                                                       assigned_to=self.shepherd, gender="Male", **kw)
        self.came = mk("Afari", "Joshua")
        self.a = mk("Ashu", "Henry", category="Worker")
        self.b = mk("Uguru", "Chinedu")
        self.c = mk("Eze", "Ifeanyi")
        Member.objects.create(surname="Q", first_name="Qatar", location=self.qa, joined_date=D(2026, 7, 1))

    def session(self, mt=None, days_ago=10, status="filled"):
        return AttendanceSession.objects.create(meeting_type=mt or self.fri, date=self.today - datetime.timedelta(days=days_ago),
                                                location=self.bh, mode="in-person", status=status, men=10)

    def url(self, s):
        return f"/api/attendance-sessions/{s.id}/follow-up-absent/"

    def tick(self, s, *members):
        for m in members:
            AttendanceSessionMember.objects.create(session=s, member=m)


class FollowUpThoseNotTicked(Base):
    def test_preview_then_create_for_an_old_service(self):
        s = self.session()
        self.tick(s, self.came)
        # Henry already has an open follow-up from another service.
        MemberFollowUpTask.objects.create(member=self.a, text="x", due_date=self.today, missed_meeting_name="Earlier", missed_date=self.today)
        r = self.client.get(self.url(s))
        self.assertEqual(r.status_code, 200, r.data)
        # Tasks pile (Kay, 26 October 2026): Henry's open task elsewhere no
        # longer stops a task for this service.
        self.assertEqual((r.data["to_follow_up"], r.data["ticked"], r.data["open_elsewhere"], r.data["already"]),
                         (3, ["Joshua Afari"], 1, 0))
        self.assertEqual(sorted(r.data["names"]), ["Chinedu Uguru", "Henry Ashu", "Ifeanyi Eze"])
        r = self.client.post(self.url(s))
        self.assertEqual((r.status_code, r.data["created"]), (201, 3))
        made = MemberFollowUpTask.objects.filter(missed_session=s)
        self.assertEqual(sorted(t.member.first_name for t in made), ["Chinedu", "Henry", "Ifeanyi"])
        t = made.get(member__first_name="Chinedu")
        # An old service followed up on request: the clock starts when the
        # task is made, and it is due 24 hours later.
        self.assertEqual((t.assigned_to, t.missed_meeting_name, t.missed_date, t.kind),
                         (self.shepherd, "Friday Worship Service", s.date, "absence"))
        self.assertEqual(t.due_at - t.clock_start, datetime.timedelta(hours=24))
        self.assertEqual(t.clock_start, t.created_at)
        self.assertTrue(AuditLog.objects.filter(action="Followed up absentees").exists())
        # Pressing it again makes nothing new.
        self.assertEqual(self.client.get(self.url(s)).data["to_follow_up"], 0)
        self.assertEqual(self.client.post(self.url(s)).data["created"], 0)
        self.assertEqual(self.client.get(self.url(s)).data["already"], 3)

    def test_a_meeting_not_followed_up_automatically_can_be_done_any_day(self):
        s = self.session(mt=self.mon, days_ago=3)
        self.tick(s, self.came)
        self.assertEqual(self.client.get(self.url(s)).data["to_follow_up"], 3)

    def test_only_those_expected_at_the_meeting(self):
        s = self.session(mt=self.sat, days_ago=3)
        self.tick(s, self.came)            # a general member ticked at a workers' meeting
        r = self.client.get(self.url(s)).data
        self.assertEqual(r["names"], ["Henry Ashu"])

    def test_refused_where_it_would_be_wrong(self):
        recent = self.session(days_ago=2)          # followed up automatically
        self.tick(recent, self.came)
        self.assertIn("automatically", str(self.client.get(self.url(recent)).data))
        today = self.session(days_ago=0, status="pending")
        self.tick(today, self.came)
        self.assertEqual(self.client.post(self.url(today)).status_code, 400)
        nobody = self.session()
        r = self.client.post(self.url(nobody))
        self.assertEqual(r.status_code, 400)
        self.assertIn("Tick who came first", str(r.data))
        # Asking first is not an error: the card just says so.
        r = self.client.get(self.url(nobody))
        self.assertEqual((r.status_code, r.data["to_follow_up"]), (200, 0))
        self.assertIn("Tick who came first", r.data["blocked"])
        self.assertEqual(MemberFollowUpTask.objects.count(), 0)
        old = self.session()
        self.tick(old, self.came)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(self.url(old)).status_code, 403)


class AddTaskByHand(Base):
    def test_goes_to_the_shepherd_unless_someone_else_is_chosen(self):
        r = self.client.post("/api/member-followup-tasks/", {"member": self.b.id, "text": "Call to check on him",
                                                              "due_date": "2026-10-19"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["assigned_to"], r.data["missed_meeting_name"], r.data["missed_date"]), (self.shepherd.id, "", None))
        r = self.client.post("/api/member-followup-tasks/", {"member": self.c.id, "text": "Visit", "due_date": "2026-10-20",
                                                              "assigned_to": self.other.id}, format="json")
        self.assertEqual(r.data["assigned_to"], self.other.id)
        log = AuditLog.objects.filter(action="Created follow-up task").order_by("-id").first()
        self.assertEqual(log.details, "Visit")

    def test_checks(self):
        r = self.client.post("/api/member-followup-tasks/", {"member": self.b.id, "text": "  ", "due_date": "2026-10-19"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/member-followup-tasks/", {"member": self.b.id, "text": "Call", "due_date": "2026-10-19",
                                                              "assigned_to": self.usher.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("shepherd", str(r.data))
        self.client.force_authenticate(self.viewer)
        r = self.client.post("/api/member-followup-tasks/", {"member": self.b.id, "text": "Call", "due_date": "2026-10-19"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_shepherd_email_lists_it_in_words(self):
        from core.digests import build_shepherd_digest
        MemberFollowUpTask.objects.create(member=self.b, text="Call to check on him", due_date=self.today, assigned_to=self.shepherd)
        MemberFollowUpTask.objects.create(member=self.c, text="x", due_date=self.today, assigned_to=self.shepherd,
                                          missed_meeting_name="Friday Worship Service", missed_date=self.today)
        subject, text, html = build_shepherd_digest("Shepherd", list(MemberFollowUpTask.objects.all()), self.today)
        self.assertIn("Chinedu Uguru, Call to check on him", text)
        self.assertIn("Ifeanyi Eze, missed Friday Worship Service", text)
        self.assertIn("Call to check on him", html)
