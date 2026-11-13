"""
Fewer follow-up tasks (13 November 2026): one open task per person, Lapsed
after the misses in a row set in Follow-up Rules, the Follow-up
Coordinator's choice, and the one-off cleanup.
"""
import datetime

from accounts.models import Role, User
from alerts.models import Notice
from attendance.models import AttendanceSessionMember
from core.followup_rules import at
from core.models import FollowUpRules
from core.tests_task_results import Base, D
from members.models import Member, MemberFollowUpTask
from newcomers.models import Newcomer, NewcomerTask

NIGHT = datetime.time(21, 17)


class FewerBase(Base):
    def setUp(self):
        super().setUp()
        FollowUpRules.objects.filter(pk=1).update(one_open_task=True, lapsed_after_misses=3)
        coord_role, _ = Role.objects.get_or_create(name="Follow-up Coordinator role")
        self.coord = User.objects.create_user(email="fc@t.com", password="x", role=coord_role, first_name="Ruth",
                                              last_name="Okon", is_followup_coordinator=True)
        self.fridays = [D(2026, 10, 2), D(2026, 10, 9), D(2026, 10, 16), D(2026, 10, 23), D(2026, 10, 30)]

    def miss(self, day):
        s = self.service(day)
        self.check(s, at(day, NIGHT))
        return s

    def open_tasks(self, member=None):
        return MemberFollowUpTask.objects.filter(member=member or self.chinwendu, done=False, kind="absence")


class OneOpenTask(FewerBase):
    def test_a_second_miss_joins_the_open_task(self):
        s1 = self.miss(self.fridays[0])
        s2 = self.miss(self.fridays[1])
        self.assertEqual(self.open_tasks().count(), 1)
        first = self.open_tasks().get()
        self.assertEqual(first.missed_session, s1)
        joined = MemberFollowUpTask.objects.get(member=self.chinwendu, missed_session=s2)
        self.assertEqual((joined.done, joined.result, joined.covered_by_id), (True, "joined", first.id))
        self.assertIn("Missed 2 services, latest Friday Worship Service on 9 October", first.text)
        self.assertEqual(first.missed_in_row, 2)
        self.assertTrue(Notice.objects.filter(user=self.gloria, title__contains="again").exists())

    def test_the_check_running_again_adds_nothing(self):
        s1 = self.miss(self.fridays[0])
        s2 = self.miss(self.fridays[1])
        self.check(s2, at(s2.date, datetime.time(22, 0)))
        self.assertEqual(MemberFollowUpTask.objects.filter(member=self.chinwendu).count(), 2)

    def test_switch_off_keeps_tasks_piling(self):
        FollowUpRules.objects.filter(pk=1).update(one_open_task=False, lapsed_after_misses=0)
        for d in self.fridays[:3]:
            self.miss(d)
        self.assertEqual(self.open_tasks().count(), 3)

    def test_ticked_late_for_a_joined_miss(self):
        self.miss(self.fridays[0])
        s2 = self.miss(self.fridays[1])
        AttendanceSessionMember.objects.create(session=s2, member=self.chinwendu)
        from attendance.absence import close_was_present
        close_was_present(s2, member_ids=[self.chinwendu.id])
        first = self.open_tasks().get()
        self.assertEqual(MemberFollowUpTask.objects.get(missed_session=s2, member=self.chinwendu).result, "was-present")
        self.assertEqual(first.text, "Missed Friday Worship Service, check in with them")

    def test_ticked_late_for_the_first_miss_leaves_the_later_one_open(self):
        s1 = self.miss(self.fridays[0])
        s2 = self.miss(self.fridays[1])
        AttendanceSessionMember.objects.create(session=s1, member=self.chinwendu)
        from attendance.absence import close_was_present
        close_was_present(s1, member_ids=[self.chinwendu.id])
        still = self.open_tasks().get()
        self.assertEqual(still.missed_session, s2)

    def test_joined_misses_are_left_out_of_the_measures(self):
        from core.followup_overview import _tasks
        self.miss(self.fridays[0])
        self.miss(self.fridays[1])
        tasks = [t for t in _tasks(None, at(D(2026, 10, 1), datetime.time(0)), at(D(2026, 10, 31), NIGHT))
                 if getattr(t, "member_id", None) == self.chinwendu.id]
        self.assertEqual(len(tasks), 1)


class Lapsed(FewerBase):
    def test_the_third_miss_in_a_row_makes_them_lapsed(self):
        for d in self.fridays[:3]:
            self.miss(d)
        self.chinwendu.refresh_from_db()
        self.assertEqual((self.chinwendu.lapsed_since, self.chinwendu.lapsed_meeting),
                         (self.fridays[2], "Friday Worship Service"))
        self.assertEqual(self.open_tasks().count(), 0)
        self.assertEqual(MemberFollowUpTask.objects.filter(member=self.chinwendu, result="lapsed").count(), 1)
        self.assertTrue(Notice.objects.filter(user=self.coord, title__contains="is now Lapsed").exists())
        self.assertTrue(Notice.objects.filter(user=self.gloria, title__contains="is now Lapsed").exists())
        self.assertTrue(Newcomer.objects.get(pk=self.peggy.pk).lapsed_since)

    def test_no_more_tasks_while_lapsed(self):
        for d in self.fridays[:4]:
            self.miss(d)
        self.assertEqual(MemberFollowUpTask.objects.filter(member=self.chinwendu).count(), 2)
        self.assertEqual(self.open_tasks().count(), 0)

    def test_ticked_present_ends_lapsed(self):
        for d in self.fridays[:3]:
            self.miss(d)
        s = self.service(self.fridays[3])
        AttendanceSessionMember.objects.create(session=s, member=self.chinwendu)
        from attendance.absence import close_was_present
        close_was_present(s, member_ids=[self.chinwendu.id])
        self.chinwendu.refresh_from_db()
        self.assertIsNone(self.chinwendu.lapsed_since)
        self.assertTrue(Notice.objects.filter(user=self.coord, body__contains="No longer Lapsed").exists())

    def test_the_list_and_follow_up_again(self):
        for d in self.fridays[:3]:
            self.miss(d)
        self.client.force_authenticate(self.coord)
        rows = self.client.get("/api/followup/lapsed/").data["results"]
        self.assertEqual(sorted(r["name"] for r in rows), ["Chinwendu Uguru", "Peggy Dede Laryea"])
        r = self.client.post("/api/followup/lapsed/decide/",
                             {"kind": "member", "id": self.chinwendu.id, "choice": "again"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.chinwendu.refresh_from_db()
        self.assertIsNone(self.chinwendu.lapsed_since)
        # Misses before Follow up again no longer count: the next miss is the
        # first of a new run, not the fourth.
        Member.objects.filter(pk=self.chinwendu.pk).update(follow_up_from=self.fridays[3])
        self.miss(self.fridays[3])
        t = self.open_tasks().get()
        self.assertEqual(t.missed_in_row, 1)

    def test_left_and_not_interested(self):
        for d in self.fridays[:3]:
            self.miss(d)
        self.client.force_authenticate(self.coord)
        self.client.post("/api/followup/lapsed/decide/", {"kind": "member", "id": self.chinwendu.id, "choice": "left"},
                         format="json")
        self.client.post("/api/followup/lapsed/decide/", {"kind": "newcomer", "id": self.peggy.id, "choice": "left"},
                         format="json")
        self.chinwendu.refresh_from_db(); self.peggy.refresh_from_db()
        self.assertEqual((self.chinwendu.status, self.peggy.stage), ("left", "not-interested"))
        self.assertEqual(self.client.get("/api/followup/lapsed/").data["results"], [])

    def test_a_shepherd_cannot_decide(self):
        for d in self.fridays[:3]:
            self.miss(d)
        self.client.force_authenticate(self.gloria)
        r = self.client.post("/api/followup/lapsed/decide/",
                             {"kind": "member", "id": self.chinwendu.id, "choice": "again"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertIn("Follow-up Coordinator", str(r.data))

    def test_off_means_never_lapsed(self):
        FollowUpRules.objects.filter(pk=1).update(lapsed_after_misses=0)
        for d in self.fridays:
            self.miss(d)
        self.chinwendu.refresh_from_db()
        self.assertIsNone(self.chinwendu.lapsed_since)
        self.assertEqual(self.open_tasks().count(), 1)

    def test_the_setting_has_limits(self):
        r = self.client.patch("/api/followup-rules/", {"lapsed_after_misses": 21}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.patch("/api/followup-rules/", {"lapsed_after_misses": 4, "one_open_task": False},
                              format="json")
        self.assertEqual(r.status_code, 200, r.data)


class Cleanup(FewerBase):
    def setUp(self):
        super().setUp()
        # The old rules made these: three open tasks for one person.
        FollowUpRules.objects.filter(pk=1).update(one_open_task=False, lapsed_after_misses=0)
        for d in self.fridays[:3]:
            self.miss(d)
        FollowUpRules.objects.filter(pk=1).update(one_open_task=True, lapsed_after_misses=3)

    def test_preview_changes_nothing(self):
        r = self.client.get("/api/followup/cleanup/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["lapsed"], 2)
        self.assertEqual(self.open_tasks().count(), 3)
        self.chinwendu.refresh_from_db()
        self.assertIsNone(self.chinwendu.lapsed_since)

    def test_apply(self):
        FollowUpRules.objects.filter(pk=1).update(lapsed_after_misses=4)
        r = self.client.post("/api/followup/cleanup/")
        self.assertEqual((r.data["tasks_joined"], r.data["people_with_extra_tasks"], r.data["lapsed"]), (3, 2, 0))
        self.assertEqual(self.open_tasks().count(), 1)
        self.assertEqual(NewcomerTask.objects.filter(newcomer=self.peggy, done=False, kind="absence").count(), 1)

    def test_apply_lapses(self):
        self.client.post("/api/followup/cleanup/")
        self.chinwendu.refresh_from_db()
        self.assertTrue(self.chinwendu.lapsed_since)
        self.assertEqual(MemberFollowUpTask.objects.filter(member=self.chinwendu, done=False).count(), 0)

    def test_only_an_administrator_for_all_locations(self):
        self.client.force_authenticate(self.gloria)
        r = self.client.get("/api/followup/cleanup/")
        self.assertEqual(r.status_code, 403)
        self.assertIn("All locations", str(r.data))
