"""
Build 2 of the follow-up plan (Kay, 26 October 2026): due times from the
6:00 pm clock, tasks that pile, newcomers followed up after missing a
service, the five results, one visit closing all, Away, Was present,
cancelling and changing a due time.
"""
import datetime

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User
from attendance.absence import create_tasks, plan
from attendance.models import AttendanceSession, AttendanceSessionMember, MeetingType
from core.followup_rules import at
from core.models import FollowUpRules, Location
from members.models import Member, MemberContactAttempt, MemberFollowUpTask
from newcomers.models import Newcomer, NewcomerSource, NewcomerTask

D = datetime.date
SIX = datetime.time(18, 0)


class Base(APITestCase):
    def setUp(self):
        self.bh = Location.objects.create(id="bahrain", name="Bahrain HQ", is_core=True)
        admin_role, _ = Role.objects.get_or_create(name="Administrator")
        fu_role, _ = Role.objects.get_or_create(name="Follow-up")
        RolePermission.objects.filter(role__in=[admin_role, fu_role]).delete()
        for mod in ["members", "newcomers", "attendance", "admin"]:
            RolePermission.objects.create(role=admin_role, module=mod, can_view=True, can_create=True,
                                          can_edit=True, can_delete=True)
        for mod in ["members", "newcomers", "attendance"]:
            RolePermission.objects.create(role=fu_role, module=mod, can_view=True, can_create=True,
                                          can_edit=True, can_delete=False)
        self.admin = User.objects.create_user(email="a@t.com", password="x", role=admin_role, first_name="Chinedu",
                                              last_name="Uguru")
        self.gloria = User.objects.create_user(email="g@t.com", password="x", role=fu_role, first_name="Gloria",
                                               last_name="Afari", gender="Female", can_shepherd=True, location=self.bh)
        self.grace = User.objects.create_user(email="gt@t.com", password="x", role=fu_role, first_name="Grace",
                                              last_name="Thomas", gender="Female", can_shepherd=True, location=self.bh)
        self.fri = MeetingType.objects.create(id="fri-worship", name="Friday Worship Service", day="Friday",
                                              frequency="weekly", detail_level="detailed", counts_for_absence=True,
                                              start_time=SIX)
        mk = lambda f, s, **kw: Member.objects.create(first_name=f, surname=s, gender="Female", location=self.bh,
                                                       joined_date=D(2026, 1, 1), **kw)
        self.chinwendu = mk("Chinwendu", "Uguru", assigned_to=self.gloria)
        self.came = mk("Grace", "Uguru", assigned_to=self.gloria)
        src = NewcomerSource.objects.create(name="Friend")
        self.peggy = Newcomer.objects.create(name="Peggy Dede Laryea", source=src, location=self.bh, gender="Female",
                                             stage="attending", created_at=D(2026, 10, 2), stage_since=D(2026, 10, 2),
                                             assigned_to=self.gloria)
        self.client.force_authenticate(self.admin)

    def service(self, day, tick=True):
        s = AttendanceSession.objects.create(meeting_type=self.fri, date=day, location=self.bh, mode="in-person")
        if tick:
            AttendanceSessionMember.objects.create(session=s, member=self.came)
        return s

    def check(self, s, now):
        p = plan(s)
        return create_tasks(s, p["to_follow_up"], p["newcomers"], now=now)


class Making(Base):
    def test_members_and_newcomers_get_tasks_due_6pm_next_day(self):
        day = D(2026, 10, 30)
        made = self.check(self.service(day), at(day, datetime.time(21, 17)))
        self.assertEqual(sorted(type(t).__name__ for t in made), ["MemberFollowUpTask", "NewcomerTask"])
        for t in made:
            self.assertEqual((t.kind, t.clock_start, t.due_at), ("absence", at(day, SIX), at(D(2026, 10, 31), SIX)))
            self.assertEqual(t.due_date, D(2026, 10, 31))

    def test_names_ticked_late_start_the_clock_when_the_task_is_made(self):
        day = D(2026, 10, 30)
        late = at(D(2026, 11, 1), datetime.time(10, 0))
        t = self.check(self.service(day), late)[0]
        self.assertEqual((t.clock_start, t.due_at), (late, late + datetime.timedelta(hours=24)))

    def test_tasks_pile_and_count_the_run(self):
        s1 = self.service(D(2026, 10, 16))
        self.check(s1, at(s1.date, datetime.time(21, 17)))
        AttendanceSession.objects.create(meeting_type=self.fri, date=D(2026, 10, 20), location=self.bh,
                                         mode="in-person", status="did-not-hold")  # skipped
        self.service(D(2026, 10, 21), tick=False)  # nobody ticked: says nothing, skipped
        s2 = self.service(D(2026, 10, 23))
        t = [x for x in self.check(s2, at(s2.date, datetime.time(21, 17))) if isinstance(x, MemberFollowUpTask)][0]
        self.assertEqual(t.missed_in_row, 2)
        self.assertEqual(MemberFollowUpTask.objects.filter(member=self.chinwendu, done=False).count(), 2)

    def test_who_is_not_expected(self):
        day = D(2026, 10, 30)
        Member.objects.filter(pk=self.chinwendu.pk).update(away_from=D(2026, 10, 25), away_to=D(2026, 11, 5))
        left = Member.objects.create(first_name="Ama", surname="Left", location=self.bh, joined_date=D(2025, 1, 1),
                                     status="left")
        new_today = Newcomer.objects.create(name="Joyce Josephine", source=self.peggy.source, location=self.bh,
                                            stage="new", created_at=day, stage_since=day)
        Newcomer.objects.filter(pk=self.peggy.pk).update(stage="not-interested")
        p = plan(self.service(day))
        self.assertEqual(p["to_follow_up"], [])
        self.assertEqual(p["newcomers"], [])

    def test_stages_come_from_the_rules(self):
        r = FollowUpRules.get(); r.newcomer_stages = "new,contacted"; r.save()
        self.assertEqual(plan(self.service(D(2026, 10, 30)))["newcomers"], [])

    def test_a_workers_meeting_does_not_chase_newcomers(self):
        self.fri.audience = "workers"
        self.fri.save()
        self.assertEqual(plan(self.service(D(2026, 10, 30)))["newcomers"], [])


class Results(Base):
    def setUp(self):
        super().setUp()
        today = timezone.localdate()
        self.s1 = self.service(today - datetime.timedelta(days=14))
        self.s2 = self.service(today - datetime.timedelta(days=7))
        self.t1 = [t for t in self.check(self.s1, at(self.s1.date, datetime.time(21, 17)))
                   if isinstance(t, MemberFollowUpTask)][0]
        self.t2 = [t for t in self.check(self.s2, at(self.s2.date, datetime.time(21, 17)))
                   if isinstance(t, MemberFollowUpTask)][0]

    def url(self, t, what="record-result"):
        return f"/api/member-followup-tasks/{t.id}/{what}/"

    REACHED = {"result": "reached", "contact_method": "Home visit", "contact_goal": "Encourage her",
               "contact_scripture": "Hebrews 10:25", "contact_root_cause": "Friday shifts",
               "contact_next_step": "Call on Thursday"}

    def test_the_four_boxes_are_required(self):
        r = self.client.post(self.url(self.t2), {"result": "reached", "contact_method": "Home visit"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.data), {"contact_goal", "contact_scripture", "contact_root_cause", "contact_next_step"})

    def test_one_visit_closes_all_and_makes_the_next_step(self):
        nxt = timezone.localdate() + datetime.timedelta(days=3)
        r = self.client.post(self.url(self.t2), dict(self.REACHED, next_step_date=str(nxt)), format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["closed_also"], [self.t1.id])
        self.t1.refresh_from_db()
        self.assertEqual((self.t1.done, self.t1.result, self.t1.covered_by_id), (True, "reached", self.t2.id))
        n = MemberFollowUpTask.objects.get(pk=r.data["next_task"])
        self.assertEqual((n.kind, n.due_date, n.text, n.assigned_to), ("next-step", nxt, "Call on Thursday", self.gloria))

    def test_the_old_complete_button_does_the_same(self):
        body = {k: v for k, v in self.REACHED.items() if k != "result"}
        r = self.client.post(self.url(self.t2, "complete"), body, format="json")
        self.assertEqual(r.data["closed_also"], [self.t1.id])

    def test_tried_logs_attempts_and_hands_over_after_three(self):
        for i in range(3):
            r = self.client.post(self.url(self.t2), {"result": "tried", "method": "Phone call", "note": "No answer"},
                                 format="json")
            self.assertEqual((r.data["attempt_count"], len(r.data["attempts"])), (i + 1, i + 1))
        self.t2.refresh_from_db()
        self.assertEqual((self.t2.done, self.t2.escalation), (False, "attempts"))
        self.assertEqual(MemberContactAttempt.objects.filter(task=self.t2).count(), 3)
        self.assertEqual(len(self.client.get(f"/api/member-followup-tasks/{self.t2.id}/").data["attempts"]), 3)

    def test_known_reason_can_mark_away(self):
        r = self.client.post(self.url(self.t2), {"result": "known-reason", "note": "Travelling",
                                                 "away_from": "2026-11-01", "away_to": "2026-11-15",
                                                 "away_reason": "travelling"}, format="json")
        self.assertEqual(r.data["result"], "known-reason")
        self.chinwendu.refresh_from_db()
        self.assertEqual((self.chinwendu.away_from, self.chinwendu.away_to), (D(2026, 11, 1), D(2026, 11, 15)))
        self.assertIn("Say what the reason is",
                      str(self.client.post(self.url(self.t1), {"result": "known-reason"}, format="json").data))

    def test_needs_the_coordinator_needs_a_note(self):
        self.assertEqual(self.client.post(self.url(self.t2), {"result": "needs-coordinator"}, format="json").status_code, 400)
        r = self.client.post(self.url(self.t2), {"result": "needs-coordinator", "note": "Family matter"}, format="json")
        self.assertEqual((r.data["escalation"], r.data["done"]), ("needs-coordinator", False))

    def test_moved_away_closes_everything_and_leaves_the_list(self):
        self.client.post(self.url(self.t2), {"result": "moved-away", "note": "Moved to Dubai"}, format="json")
        self.chinwendu.refresh_from_db()
        self.assertEqual(self.chinwendu.status, "moved-away")
        self.assertFalse(MemberFollowUpTask.objects.filter(member=self.chinwendu, done=False).exists())
        names = [m["full_name"] for m in self.client.get("/api/members/").data["results"]]
        self.assertNotIn("Chinwendu Uguru", names)
        names = [m["full_name"] for m in self.client.get("/api/members/?status=all").data["results"]]
        self.assertIn("Chinwendu Uguru", names)
        self.assertEqual(self.client.get("/api/members/stats/").data["inactive"], 1)

    def test_ticked_afterwards_closes_as_was_present(self):
        r = self.client.post(f"/api/attendance-sessions/{self.s2.id}/check_in/", {"member_id": self.chinwendu.id},
                             format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.t2.refresh_from_db()
        self.assertEqual((self.t2.done, self.t2.result), (True, "was-present"))
        self.t1.refresh_from_db()
        self.assertFalse(self.t1.done)

    def test_only_a_coordinator_or_administrator_cancels(self):
        self.client.force_authenticate(self.gloria)
        r = self.client.post(self.url(self.t2, "cancel"), {"reason": "was-at-service"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertIn("never reaches the shepherd's record", r.data["detail"])
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(self.url(self.t2, "cancel"), {"reason": "x"}, format="json").status_code, 400)
        r = self.client.post(self.url(self.t2, "cancel"), {"reason": "was-at-service", "note": "Overflow room"},
                             format="json")
        self.assertEqual((r.data["result"], r.data["result_note"]),
                         ("cancelled", "The person was at the service: Overflow room"))
        self.assertTrue(AuditLog.objects.filter(action="Cancelled follow-up task").exists())

    def test_changing_a_due_time(self):
        later = (timezone.localtime() + datetime.timedelta(days=2)).replace(microsecond=0)
        self.client.force_authenticate(self.gloria)
        self.assertEqual(self.client.post(self.url(self.t2, "change-due"), {"due_at": later.isoformat(),
                                                                             "why": "x"}, format="json").status_code, 403)
        self.client.force_authenticate(self.admin)
        r = self.client.post(self.url(self.t2, "change-due"), {"due_at": later.isoformat()}, format="json")
        self.assertIn("Say why", str(r.data))
        r = self.client.post(self.url(self.t2, "change-due"), {"due_at": later.isoformat(), "why": "Visit agreed"},
                             format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.due_at, later)


class Away(Base):
    def test_shepherd_coordinator_or_administrator_only(self):
        body = {"away_from": "2026-11-01", "away_to": "2026-11-15", "away_reason": "travelling", "away_note": "Lagos"}
        self.client.force_authenticate(self.grace)  # not her shepherd
        self.assertEqual(self.client.post(f"/api/members/{self.chinwendu.id}/away/", body, format="json").status_code, 403)
        self.client.force_authenticate(self.gloria)
        r = self.client.post(f"/api/members/{self.chinwendu.id}/away/", body, format="json")
        self.assertEqual((r.status_code, r.data["away_reason"]), (200, "travelling"))
        r = self.client.post(f"/api/newcomers/{self.peggy.id}/away/", dict(body, away_to="2026-10-01"), format="json")
        self.assertEqual(r.status_code, 400)
        self.client.force_authenticate(self.admin)
        self.client.delete(f"/api/members/{self.chinwendu.id}/away/")
        self.chinwendu.refresh_from_db()
        self.assertIsNone(self.chinwendu.away_from)


class Leaving(Base):
    def test_not_interested_needs_a_reason_and_stops_follow_up(self):
        t = self.check(self.service(D(2026, 10, 30)), at(D(2026, 10, 30), datetime.time(21, 17)))
        url = f"/api/newcomers/{self.peggy.id}/change-stage/"
        self.assertIn("Say why", str(self.client.post(url, {"to_stage": "not-interested"}, format="json").data))
        self.client.post(url, {"to_stage": "not-interested", "note": "Moved back home"}, format="json")
        self.assertFalse(NewcomerTask.objects.filter(newcomer=self.peggy, done=False).exists())

    def test_a_member_marked_left_stops_follow_up(self):
        self.check(self.service(D(2026, 10, 30)), at(D(2026, 10, 30), datetime.time(21, 17)))
        r = self.client.patch(f"/api/members/{self.chinwendu.id}/", {"status": "left", "status_note": "Joined family"},
                              format="json")
        self.assertEqual((r.status_code, r.data["status"]), (200, "left"))
        self.assertIsNotNone(r.data["status_date"])
        self.assertFalse(MemberFollowUpTask.objects.filter(member=self.chinwendu, done=False).exists())
