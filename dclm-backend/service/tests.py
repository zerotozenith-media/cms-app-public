"""F21: the service ladder's points, levels, notice period and next steps."""
import datetime

from attendance.models import AttendanceSession, AttendanceSessionMember, MeetingType
from core.tests_upgrade import Base
from followup.models import Enrolment, MessageLog, StepDone
from members.models import MemberFollowUpTask
from newcomers.models import MilestoneType, NewcomerMilestone, NewcomerTask

from . import engine
from .models import ServiceStanding

D = datetime.timedelta


class PointsTestCase(Base):
    def setUp(self):
        super().setUp()
        self.u = self.admin
        self.n = self.newcomer("Followed Person", stage="attending")
        self.n.assigned_to = self.u; self.n.save()

    def task(self, due, contact):
        return NewcomerTask.objects.create(newcomer=self.n, text="Visit", due_date=due, assigned_to=self.u, done=True, contact_date=contact)

    def test_follow_ups_on_time_late_and_outside_the_window(self):
        self.task(self.today, self.today - D(days=1))           # on time
        self.task(self.today - D(days=5), self.today)           # late
        self.task(self.today - D(days=100), self.today - D(days=95))  # outside 90 days
        total, got = engine.points(self.u, self.today)
        self.assertEqual((got["followup_on_time"], got["followup_late"], total), (1, 1, 15))

    def test_messages_replies_and_skips(self):
        e = Enrolment.objects.get(newcomer=self.n)
        for kind in ("planned", "own", "reply", "skipped"):
            MessageLog.objects.create(enrolment=e, day=1, kind=kind, text="x", sent_by=self.u, on_date=self.today)
        total, got = engine.points(self.u, self.today)
        self.assertEqual((got["message"], got["reply"], total), (2, 1, 7))

    def test_discipler_step(self):
        e = Enrolment.objects.create(journey="converts", newcomer=self.n, started=self.today)
        StepDone.objects.create(enrolment=e, step=0, done_on=self.today, by=self.u)
        self.assertEqual(engine.points(self.u, self.today)[0], 8)

    def test_results_return_visits_baptism_and_returning_member(self):
        MeetingType.objects.create(id="fri-worship", name="Friday Worship", day="Friday", frequency="weekly", detail_level="detailed")
        for k in range(3):
            s = AttendanceSession.objects.create(meeting_type_id="fri-worship", location=self.bahrain, date=self.today - D(days=7 * (2 - k)), mode="in-person", status="filled")
            AttendanceSessionMember.objects.create(session=s, newcomer=self.n)
        wb = MilestoneType.objects.create(name="Water Baptism")
        NewcomerMilestone.objects.create(newcomer=self.n, milestone_type=wb, achieved_date=self.today)
        m = self.member("Absent", "Member")
        MemberFollowUpTask.objects.create(member=m, text="Missed", due_date=self.today, assigned_to=self.u, done=True, contact_date=self.today - D(days=10),
                                          missed_date=self.today - D(days=12), missed_meeting_name="Friday Worship")
        AttendanceSessionMember.objects.create(session=AttendanceSession.objects.order_by("-date").first(), member=m)
        total, got = engine.points(self.u, self.today)
        self.assertEqual((got["return_visit"], got["baptised"], got["member_returned"]), (2, 1, 1))

    def test_level_boundaries(self):
        self.assertEqual([engine.level_for(p) for p in (0, 99, 100, 249, 250, 450, 699, 700, 1000, 5000)], [0, 0, 1, 1, 2, 3, 3, 4, 5, 5])


class LevelChangesTestCase(Base):
    def setUp(self):
        super().setUp()
        self.n = self.newcomer("Ladder Person", stage="attending"); self.n.assigned_to = self.admin; self.n.save()

    def give(self, count, day):
        for _ in range(count):
            NewcomerTask.objects.create(newcomer=self.n, text="Visit", due_date=day, assigned_to=self.admin, done=True, contact_date=day)

    def test_moving_up_is_immediate(self):
        engine.refresh(self.admin, self.today)
        self.give(25, self.today)                       # 250 points: Labourer
        s, total, _ = engine.refresh(self.admin, self.today)
        self.assertEqual((s.level, s.moved_up_on, total), (2, self.today, 250))

    def test_dropping_waits_30_days_then_goes_one_level(self):
        start = self.today - D(days=120)
        self.give(45, start)                            # 450 points then: Soul Winner
        s, _, _ = engine.refresh(self.admin, start)
        self.assertEqual(s.level, 3)
        s, total, _ = engine.refresh(self.admin, self.today)   # all outside the window now: 0 points
        self.assertEqual((s.level, s.grace_until, total), (3, self.today + D(days=30), 0))
        s, _, _ = engine.refresh(self.admin, self.today + D(days=29))
        self.assertEqual(s.level, 3)
        s, _, _ = engine.refresh(self.admin, self.today + D(days=30))
        self.assertEqual(s.level, 2)                    # one level only

    def test_recovering_cancels_the_notice(self):
        self.give(25, self.today - D(days=100))
        ServiceStanding.objects.create(user=self.admin, level=2, since=self.today - D(days=100))
        s, _, _ = engine.refresh(self.admin, self.today)
        self.assertIsNotNone(s.grace_until)
        self.give(25, self.today)
        s, _, _ = engine.refresh(self.admin, self.today)
        self.assertEqual((s.level, s.grace_until), (2, None))


class NextStepsTestCase(Base):
    def test_the_steps_add_up_to_the_next_level(self):
        for total in (0, 37, 99, 378, 699, 999):
            level = engine.level_for(total)
            need, steps = engine.next_steps(total, level)
            worth = sum(n * (engine.POINTS["followup_on_time"] if "follow-up" in t else engine.POINTS["message"]) for n, t in steps)
            self.assertGreaterEqual(worth, need, (total, steps))
        self.assertEqual(engine.next_steps(1200, 5), (0, []))


class PluralTestCase(Base):
    def test_one_or_many(self):
        self.assertEqual(engine.short(1, "follow-up"), "follow-up completed on time")
        self.assertEqual(engine.short(2, "message"), "planned messages sent")
