"""F19 and F20: follow-up journeys, plans, handovers and records."""
import datetime

from attendance.models import AttendanceSession, AttendanceSessionMember, MeetingType
from core.tests_upgrade import Base
from enquiries.models import Enquiry, EnquirySource
from newcomers.models import MilestoneType, NewcomerMilestone

from . import engine
from .models import Enrolment, MessageLog


class JourneyTestCase(Base):
    def setUp(self):
        super().setUp()
        self.esource = EnquirySource.objects.create(name="Instagram")

    def active(self, **who):
        return Enrolment.objects.filter(status="active", **who)

    def test_a_new_newcomer_who_ticked_keep_in_touch_starts_newcomers(self):
        n = self.newcomer("Joy Mensah", stage="new")
        self.assertEqual(self.active(newcomer=n).get().journey, "newcomers")

    def test_no_journey_without_the_tick(self):
        n = self.newcomer("Quiet Person", stage="new")
        Enrolment.objects.filter(newcomer=n).delete()
        n2 = type(n).objects.create(name="Unticked", source=self.source, location=self.bahrain, stage="new",
                                    created_at=self.today, stage_since=self.today, keep_in_touch=False)
        self.assertFalse(Enrolment.objects.filter(newcomer=n2).exists())

    def test_an_enquiry_starts_online_and_moves_to_newcomers_when_converted(self):
        e = Enquiry.objects.create(name="Grace Online", source=self.esource)
        self.assertEqual(self.active(enquiry=e).get().journey, "online")
        n = self.newcomer("Grace Online", stage="new")
        e.converted_newcomer = n; e.save()
        self.assertFalse(self.active(enquiry=e).exists())
        self.assertEqual(Enrolment.objects.get(enquiry=e).status, "moved")
        self.assertEqual(self.active(newcomer=n).get().journey, "newcomers")

    def test_salvation_moves_a_newcomer_to_new_converts_and_keeps_one_journey(self):
        n = self.newcomer("Daniel Okafor", stage="attending")
        ms = MilestoneType.objects.create(name="Salvation")
        NewcomerMilestone.objects.create(newcomer=n, milestone_type=ms, achieved_date=self.today)
        self.assertEqual([e.journey for e in self.active(newcomer=n)], ["converts"])
        self.assertEqual(Enrolment.objects.get(newcomer=n, journey="newcomers").status, "moved")

    def test_becoming_a_member_ends_newcomers_but_not_new_converts(self):
        n = self.newcomer("A Person", stage="attending")
        n.stage = "member"; n.save()
        self.assertFalse(self.active(newcomer=n).exists())
        n2 = self.newcomer("B Person", stage="attending")
        engine.start("converts", newcomer=n2)
        n2.stage = "member"; n2.save()
        self.assertEqual(self.active(newcomer=n2).get().journey, "converts")

    def test_not_interested_ends_the_journey(self):
        n = self.newcomer("C Person", stage="new")
        n.stage = "not-interested"; n.save()
        self.assertEqual(Enrolment.objects.get(newcomer=n).ended_reason, "Marked Not Interested")

    def test_the_standard_plan_days(self):
        n = self.newcomer("D Person", stage="new"); e = self.active(newcomer=n).get()
        self.assertEqual(engine.due_template(e, 1).theme, "Welcome")
        self.assertIsNone(engine.due_template(e, 2))
        self.assertEqual((engine.due_template(e, 3).theme, engine.due_template(e, 3).number), ("Welcome", 4))

    def test_a_personal_reply_moves_the_planned_message_to_tomorrow(self):
        n = self.newcomer("E Person", stage="new"); e = self.active(newcomer=n).get()
        e.started = self.today - datetime.timedelta(days=2); e.save()      # today is day 3
        planned = engine.due_template(e, engine.plan_day(e))
        engine.record(e, MessageLog.Kind.REPLY, self.admin, text="Thank you for sharing that.")
        e.refresh_from_db()
        tomorrow = self.today + datetime.timedelta(days=1)
        self.assertEqual(engine.due_template(e, engine.plan_day(e, tomorrow)), planned)

    def test_the_final_gentle_message_ends_the_plan(self):
        n = self.newcomer("F Person", stage="new"); e = self.active(newcomer=n).get()
        final = engine.due_template(e, 41)
        self.assertEqual(final.theme, "Final gentle message")
        engine.record(e, MessageLog.Kind.PLANNED, self.admin, template=final)
        e.refresh_from_db()
        self.assertEqual(e.status, "ended")

    def test_the_third_visit_switches_to_belonging(self):
        n = self.newcomer("G Person", stage="attending"); e = self.active(newcomer=n).get()
        MeetingType.objects.create(id="fri-worship", name="Friday Worship", day="Friday", frequency="weekly", detail_level="detailed")
        for k in range(3):
            s = AttendanceSession.objects.create(meeting_type_id="fri-worship", location=self.bahrain,
                                                 date=self.today - datetime.timedelta(days=7 * (k + 1)), mode="in-person", status="filled", men=5)
            AttendanceSessionMember.objects.create(session=s, newcomer=n)
        self.assertEqual(engine.due_template(e, 3).theme, "Belonging")
        self.assertIsNone(engine.due_template(e, 4))


class NextServiceTestCase(Base):
    def test_a_service_already_started_today_is_skipped_and_tomorrow_is_said(self):
        import datetime as dt
        from django.utils import timezone
        mt = MeetingType.objects.create(id="fri-worship", name="Friday Worship", day="Friday", frequency="weekly",
                                        detail_level="detailed", start_time=dt.time(19, 0))
        now = timezone.localtime().replace(hour=20, minute=0)
        AttendanceSession.objects.create(meeting_type=mt, location=self.bahrain, date=now.date(), mode="in-person", status="pending")
        AttendanceSession.objects.create(meeting_type=mt, location=self.bahrain, date=now.date() + dt.timedelta(days=1), mode="in-person", status="pending")
        self.assertEqual(engine.next_service("bahrain", now=now), "tomorrow at 7 pm")
        self.assertEqual(engine.next_service("bahrain", now=now.replace(hour=9)), "today at 7 pm")
