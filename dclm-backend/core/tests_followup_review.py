"""
Build 3 of the follow-up plan (Kay, 26 October 2026): the Follow-up
Coordinator, late reasons, the Review list and its four choices, alerts,
the follow-up clock, attendance falling, and the account rules that go
with them.
"""
import datetime
from unittest import mock

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User
from alerts.models import Notice
from attendance.absence import create_tasks, plan
from attendance.models import AttendanceSession, AttendanceSessionMember, MeetingType
from core.followup_access import coordinators_for, coordinates
from core.followup_clock import attendance_falling, reminders, task_alerts
from core.followup_rules import at, rules
from core.models import FollowUpRules, FollowUpReview, Location
from members.models import Member, MemberFollowUpTask
from newcomers.models import Newcomer, NewcomerSource

D = datetime.date
SIX = datetime.time(18, 0)
H = datetime.timedelta(hours=1)


class Base(APITestCase):
    def setUp(self):
        self.bh = Location.objects.create(id="bahrain", name="Bahrain HQ", is_core=True)
        self.qa = Location.objects.create(id="others", name="Qatar")
        self.admin_role, _ = Role.objects.get_or_create(name="Administrator")
        self.fu_role, _ = Role.objects.get_or_create(name="Follow-up")
        RolePermission.objects.filter(role__in=[self.admin_role, self.fu_role]).delete()
        for mod in ["members", "newcomers", "attendance", "admin", "followup-review"]:
            RolePermission.objects.create(role=self.admin_role, module=mod, can_view=True, can_create=True,
                                          can_edit=True, can_delete=True)
        for mod in ["members", "newcomers", "attendance"]:
            RolePermission.objects.create(role=self.fu_role, module=mod, can_view=True, can_create=True,
                                          can_edit=True, can_delete=False)
        self.admin = User.objects.create_user(email="a@t.com", password="x", role=self.admin_role,
                                              first_name="Admin", last_name="One")
        mk = lambda e, f, l, g, **kw: User.objects.create_user(email=e, password="x", role=self.fu_role, first_name=f,
                                                                last_name=l, gender=g, can_shepherd=True,
                                                                location=self.bh, **kw)
        self.gloria = mk("g@t.com", "Gloria", "Afari", "Female")
        self.grace = mk("gt@t.com", "Grace", "Thomas", "Female")
        self.henry = mk("h@t.com", "Henry", "Ashu", "Male")
        self.coord = User.objects.create_user(email="c@t.com", password="x", role=self.fu_role, first_name="Chinedu",
                                              last_name="Uguru", is_followup_coordinator=True,
                                              coordinates_location=self.bh)
        self.fri = MeetingType.objects.create(id="fri-worship", name="Friday Worship Service", day="Friday",
                                              frequency="weekly", detail_level="detailed", counts_for_absence=True,
                                              start_time=SIX)
        m = lambda f, s, **kw: Member.objects.create(first_name=f, surname=s, gender="Female", location=self.bh,
                                                      joined_date=D(2026, 1, 1), **kw)
        self.chinwendu = m("Chinwendu", "Uguru", assigned_to=self.gloria)
        self.came = m("Grace", "Uguru", assigned_to=self.gloria)
        self.today = timezone.localdate()

    def service(self, day, tick=True):
        s = AttendanceSession.objects.create(meeting_type=self.fri, date=day, location=self.bh, mode="in-person")
        if tick:
            AttendanceSessionMember.objects.create(session=s, member=self.came)
        return s

    def missed(self, day, now=None):
        s = self.service(day)
        p = plan(s)
        made = create_tasks(s, p["to_follow_up"], p["newcomers"], now=now or at(day, datetime.time(21, 17)))
        return [t for t in made if isinstance(t, MemberFollowUpTask) and t.member_id == self.chinwendu.id][0]

    def notices(self, user):
        return list(Notice.objects.filter(user=user).values_list("title", flat=True))


class WhoCoordinates(Base):
    def test_tick_location_then_all_locations_then_administrators(self):
        self.assertTrue(coordinates(self.coord, "bahrain"))
        self.assertFalse(coordinates(self.coord, "others"))
        self.assertEqual(coordinators_for("bahrain"), [self.coord])
        self.assertEqual(coordinators_for("others"), [self.admin])
        everywhere = User.objects.create_user(email="e@t.com", password="x", is_followup_coordinator=True)
        self.assertEqual(coordinators_for("others"), [everywhere])

    def test_a_location_account_coordinates_its_own_location_only(self):
        self.client.force_authenticate(self.admin)
        r = self.client.patch(f"/api/users/{self.grace.id}/", {"is_followup_coordinator": True,
                                                               "coordinates_location": "others"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Bahrain HQ only", str(r.data))
        r = self.client.patch(f"/api/users/{self.grace.id}/", {"is_followup_coordinator": True}, format="json")
        self.assertEqual((r.data["coordinates_location"], r.data["coordinates_location_name"]), ("bahrain", "Bahrain HQ"))


class Routing(Base):
    def test_no_shepherd_goes_to_the_coordinator(self):
        Member.objects.filter(pk=self.chinwendu.pk).update(assigned_to=None)
        self.chinwendu.refresh_from_db()
        t = self.missed(self.today - datetime.timedelta(days=1))
        t.refresh_from_db()
        self.assertEqual((t.assigned_to, t.escalation), (self.coord, "no-shepherd"))
        self.assertIn("Chinwendu Uguru has no shepherd", self.notices(self.coord))

    def test_runs_alert_and_the_visit_task_comes_once(self):
        base = self.today - datetime.timedelta(days=28)
        for i in range(4):
            self.missed(base + datetime.timedelta(days=7 * i))
        titles = self.notices(self.coord)
        self.assertEqual(sorted(t for t in titles if "in a row" in t),
                         ["Chinwendu Uguru missed a 2nd Friday Worship Service in a row",
                          "Chinwendu Uguru missed a 3rd Friday Worship Service in a row",
                          "Chinwendu Uguru missed a 4th Friday Worship Service in a row"])
        visits = MemberFollowUpTask.objects.filter(kind="coordinator-visit")
        self.assertEqual((visits.count(), visits.first().assigned_to), (1, self.coord))
        self.assertIn("1 person to follow up", self.notices(self.gloria))

    def test_every_second_miss(self):
        r = FollowUpRules.get(); r.alert_repeat = "every-second"; r.save()
        base = self.today - datetime.timedelta(days=28)
        for i in range(4):
            self.missed(base + datetime.timedelta(days=7 * i))
        self.assertEqual(len([t for t in self.notices(self.coord) if "in a row" in t]), 2)


class Reasons(Base):
    def setUp(self):
        super().setUp()
        self.day = self.today - datetime.timedelta(days=3)
        self.t = self.missed(self.day)
        self.url = f"/api/member-followup-tasks/{self.t.id}/"

    def test_needs_a_reason_from_48_hours_and_blocks_other_results(self):
        from core.followup_review import needs_reason
        self.assertFalse(needs_reason(self.t, at(self.day, SIX) + 47 * H))
        self.assertTrue(needs_reason(self.t, at(self.day, SIX) + 49 * H))
        self.client.force_authenticate(self.gloria)
        self.assertTrue(self.client.get(self.url).data["needs_reason"])
        r = self.client.post(self.url + "record-result/", {"result": "tried", "method": "Phone call"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("needs a reason first", r.data["detail"])

    def test_giving_a_reason(self):
        self.client.force_authenticate(self.gloria)
        far = self.today + datetime.timedelta(days=9)
        r = self.client.post(self.url + "give-reason/", {"reason": "tried", "new_date": str(far)}, format="json")
        self.assertIn("7 days ahead", str(r.data))
        ok = self.today + datetime.timedelta(days=2)
        r = self.client.post(self.url + "give-reason/", {"reason": "tried", "note": "Phone off", "new_date": str(ok)},
                             format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertFalse(r.data["needs_reason"])
        self.assertEqual(r.data["reviews"][0]["reason"], "Tried but could not reach")
        self.assertTrue(any("reason given" in n for n in self.notices(self.coord)))
        r = self.client.post(self.url + "record-result/", {"result": "tried", "method": "Phone call"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_not_late_needs_no_reason(self):
        fresh = self.missed(self.today, now=timezone.now())
        self.client.force_authenticate(self.gloria)
        r = self.client.post(f"/api/member-followup-tasks/{fresh.id}/give-reason/",
                             {"reason": "tried", "new_date": str(self.today)}, format="json")
        self.assertIn("not late yet", str(r.data))


class Review(Base):
    def setUp(self):
        super().setUp()
        self.day = self.today - datetime.timedelta(days=4)
        self.t = self.missed(self.day)

    def decide(self, choice, **kw):
        return self.client.post("/api/followup/review/decide/", dict(type="member", id=self.t.id, choice=choice, **kw),
                                format="json")

    def test_only_reviewers_see_the_list(self):
        self.client.force_authenticate(self.gloria)
        self.assertEqual(self.client.get("/api/followup/review/").status_code, 403)
        self.client.force_authenticate(self.coord)
        rows = self.client.get("/api/followup/review/").data["results"]
        self.assertEqual([r["person"] for r in rows], ["Chinwendu Uguru"])
        self.assertEqual(rows[0]["shepherd"], "Gloria Afari")

    def test_accept_moves_the_date_and_takes_it_off_the_list(self):
        from core.followup_review import give_reason, on_review
        give_reason(self.t, self.gloria, "person-away", "Travelling", self.today + datetime.timedelta(days=2))
        self.client.force_authenticate(self.coord)
        r = self.decide("accept")
        self.assertEqual(r.status_code, 200, r.data)
        self.t.refresh_from_db()
        self.assertEqual(self.t.due_at, at(self.today + datetime.timedelta(days=2), SIX))
        self.assertFalse(on_review(self.t))
        self.assertIn("Chinwendu Uguru: Accept", self.notices(self.gloria))

    def test_hand_on_this_task_only(self):
        self.client.force_authenticate(self.coord)
        r = self.decide("hand-on", handed_to=self.henry.id)
        self.assertIn("same gender", str(r.data))
        r = self.client.get(f"/api/followup/review/eligible/?type=member&id={self.t.id}")
        self.assertEqual([x["name"] for x in r.data["results"]], ["Grace Thomas"])
        self.assertIn("Only women at Bahrain HQ", r.data["why"])
        r = self.decide("hand-on", handed_to=self.grace.id)
        self.t.refresh_from_db()
        self.chinwendu.refresh_from_db()
        self.assertEqual((self.t.assigned_to, self.t.handed_from, self.chinwendu.assigned_to),
                         (self.grace, self.gloria, self.gloria))
        self.assertIn("Task handed to you: Chinwendu Uguru", self.notices(self.grace))
        # Her shepherd changes for good later: the handed task stays with Grace.
        from core.task_actions import move_open_tasks
        move_open_tasks(self.chinwendu, self.henry.id)
        self.t.refresh_from_db()
        self.assertEqual(self.t.assigned_to, self.grace)

    def test_take_and_ask(self):
        self.client.force_authenticate(self.coord)
        self.assertIn("Write the question", str(self.decide("ask").data))
        self.decide("ask", note="Did you try her husband's number?")
        self.assertTrue(any("asks: Did you try" in n for n in
                            Notice.objects.filter(user=self.gloria).values_list("body", flat=True)))
        self.decide("take")
        self.t.refresh_from_db()
        self.assertEqual(self.t.assigned_to, self.coord)
        self.assertEqual(FollowUpReview.objects.filter(member_task=self.t).count(), 2)
        self.assertTrue(AuditLog.objects.filter(action="Follow-up review decision").exists())

    def test_late_decisions_go_to_the_administrators_once(self):
        late = at(self.day, SIX) + datetime.timedelta(days=5, hours=1)
        task_alerts(late, rules())
        task_alerts(late + H, rules())
        self.assertEqual(self.notices(self.admin).count("Late decision: Chinwendu Uguru"), 1)
        self.assertTrue(any("on your Review list" in n for n in self.notices(self.coord)))

    def test_overview_and_shepherd_people(self):
        self.client.force_authenticate(self.coord)
        r = self.client.get("/api/followup/review/overview/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["stats"]["review"], 1)
        row = [s for s in r.data["shepherds"] if s["name"] == "Gloria Afari"][0]
        self.assertEqual((row["people"], row["limit"], row["open"]), (2, 6, 1))
        people = self.client.get(f"/api/followup/review/shepherd/{self.gloria.id}/").data["results"]
        self.assertEqual({p["person"] for p in people}, {"Chinwendu Uguru", "Grace Uguru"})
        self.assertEqual(self.client.get("/api/followup/review/overview/?location=others").status_code, 403)


class Clock(Base):
    def test_reminder_then_names_alert_each_once(self):
        day = self.today - datetime.timedelta(days=1)
        s = self.service(day, tick=False)
        reminders(at(day, datetime.time(21, 20)), rules())
        reminders(at(day, datetime.time(21, 50)), rules())
        self.assertEqual(len([n for n in self.notices(self.admin) if "please tick names" in n]), 1)
        reminders(at(day + datetime.timedelta(days=1), datetime.time(18, 20)), rules())
        self.assertTrue(any("Names still not taken" in n for n in self.notices(self.coord)))

    def test_no_reminder_once_names_are_ticked(self):
        day = self.today - datetime.timedelta(days=1)
        self.service(day)
        reminders(at(day, datetime.time(21, 20)), rules())
        self.assertEqual(Notice.objects.count(), 0)

    def test_attendance_falling(self):
        start = self.today - datetime.timedelta(days=7 * 8)
        for i in range(8):
            s = self.service(start + datetime.timedelta(days=7 * i))
            if i in (0, 1, 2):
                AttendanceSessionMember.objects.create(session=s, member=self.chinwendu)
        now = at(self.today, datetime.time(8, 0))
        self.assertEqual(attendance_falling(now, rules()), 1)
        t = MemberFollowUpTask.objects.get(kind="attendance-falling")
        self.assertEqual((t.member, t.text), (self.chinwendu, "Attendance falling: came to 3 of the last 8 services"))
        self.assertEqual(attendance_falling(now + H, rules()), 0)   # once a day


class Accounts(Base):
    def test_switching_off_a_shepherd_hands_tasks_on(self):
        t = self.missed(self.today - datetime.timedelta(days=1))
        self.client.force_authenticate(self.admin)
        r = self.client.patch(f"/api/users/{self.gloria.id}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        t.refresh_from_db()
        self.assertEqual((t.assigned_to, t.escalation), (self.coord, "no-shepherd"))
        self.assertTrue(AuditLog.objects.filter(action="Changed account", details__icontains="switched on").exists())

    def test_the_last_full_administrator_is_kept(self):
        self.client.force_authenticate(self.admin)
        r = self.client.patch(f"/api/users/{self.admin.id}/", {"location": "bahrain"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("full Admin rights", str(r.data))
        perm = RolePermission.objects.get(role=self.admin_role, module="admin")
        r = self.client.patch(f"/api/role-permissions/{perm.id}/", {"can_edit": False}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_reset_link_and_add_to_roll(self):
        self.client.force_authenticate(self.admin)
        with mock.patch("accounts.password_reset._send") as send:
            r = self.client.post(f"/api/users/{self.henry.id}/send-reset/")
        self.assertEqual(r.status_code, 200, r.data)
        send.assert_called_once()
        r = self.client.post(f"/api/users/{self.henry.id}/add-to-roll/", {"category": "Worker"}, format="json")
        self.assertEqual((r.status_code, r.data["member_name"]), (200, "Henry Ashu"))
        self.henry.refresh_from_db()
        self.assertEqual((self.henry.member.location_id, self.henry.member.gender), ("bahrain", "Male"))


class Notices(Base):
    def test_list_and_mark_read(self):
        from alerts.events import notify
        notify([self.gloria.id], "Hello", "World", "/follow-up")
        self.client.force_authenticate(self.gloria)
        r = self.client.get("/api/alerts/notices/")
        self.assertEqual((r.data["unread"], r.data["results"][0]["title"]), (1, "Hello"))
        self.client.post("/api/alerts/notices/", {}, format="json")
        self.assertEqual(self.client.get("/api/alerts/notices/").data["unread"], 0)


class LocationRemoval(Base):
    def test_a_location_with_accounts_is_not_removed(self):
        self.client.force_authenticate(self.admin)
        qa_user = User.objects.create_user(email="q@t.com", password="x", location=self.qa)
        r = self.client.delete("/api/locations/others/")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["detail"], "Qatar still has 1 account (q@t.com). Move these to another location in Admin "
                                           "first, then remove Qatar.")
        qa_user.delete()
        self.assertEqual(self.client.delete("/api/locations/others/").status_code, 204)


class ReasonsTogether(Base):
    def test_all_or_nothing_and_one_alert(self):
        day = self.today - datetime.timedelta(days=10)
        a = self.missed(day)
        b = self.missed(day + datetime.timedelta(days=7))
        self.client.force_authenticate(self.gloria)
        ok = str(self.today + datetime.timedelta(days=2))
        r = self.client.post("/api/followup/reasons/", {"items": [
            {"type": "member", "id": a.id, "reason": "tried", "new_date": ok},
            {"type": "member", "id": b.id, "reason": "", "new_date": ok}]}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(FollowUpReview.objects.count(), 0)
        r = self.client.post("/api/followup/reasons/", {"items": [
            {"type": "member", "id": a.id, "reason": "tried", "new_date": ok},
            {"type": "member", "id": b.id, "reason": "forgot", "new_date": ok}]}, format="json")
        self.assertEqual((r.status_code, r.data["saved"]), (200, 2))
        self.assertEqual([t for t in self.notices(self.coord) if "gave reasons" in t], ["Gloria Afari gave reasons for 2 late tasks"])
