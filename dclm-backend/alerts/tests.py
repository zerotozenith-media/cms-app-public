"""Phone and computer alerts (Kay, October 2026)."""
import base64
import datetime
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import override_settings
from django.utils import timezone

from accounts.models import Role, RolePermission, User
from core.tests_upgrade import Base
from enquiries.models import Enquiry, EnquirySource
from members.models import Member, MemberFollowUpTask
from newcomers.models import Newcomer

from .models import AlertSettings, Announcement, PushSubscription
from . import scheduled

BH = ZoneInfo("Asia/Bahrain")


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@override_settings(ALERTS_IN_BACKGROUND=False)
class AlertsBase(Base):
    def setUp(self):
        super().setUp()
        fu, _ = Role.objects.get_or_create(name="Helpers")
        for m in ("newcomers", "members"):
            RolePermission.objects.update_or_create(role=fu, module=m, defaults=dict(can_view=True, can_create=True, can_edit=True))
        self.gloria = User.objects.create_user(email="g@t.com", password="x", role=fu, location=self.bahrain,
                                               first_name="Gloria", last_name="Afari", can_shepherd=True, gender="Female")
        self.admin.first_name = "Chinedu"; self.admin.save()
        self.sent = []
        patcher = mock.patch("alerts.push._deliver", side_effect=lambda sub, payload: self.sent.append((sub.user_id, payload)) or True)
        patcher.start(); self.addCleanup(patcher.stop)
        self.src = EnquirySource.objects.create(name="Facebook")

    def device(self, user, n=1):
        return PushSubscription.objects.create(user=user, endpoint=f"https://push.example/{user.pk}/{n}", p256dh="k", auth="a")

    def to(self, user):
        return [p for uid, p in self.sent if uid == user.pk]


class DeviceTests(AlertsBase):
    def test_turning_on_and_off_for_this_device(self):
        body = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": {"p256dh": "BPk", "auth": "xyz"}, "device": "Chrome on Android"}
        self.assertEqual(self.client.post("/api/alerts/subscribe/", body, format="json").status_code, 201)
        st = self.client.get("/api/alerts/settings/?endpoint=https://fcm.googleapis.com/fcm/send/abc").data
        self.assertTrue(st["this_device"]); self.assertEqual(st["devices"], 1)
        # the same device again does not double up
        self.client.post("/api/alerts/subscribe/", body, format="json")
        self.assertEqual(PushSubscription.objects.count(), 1)
        self.client.post("/api/alerts/unsubscribe/", {"endpoint": body["endpoint"]}, format="json")
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_a_shared_device_belongs_to_whoever_turned_it_on_last(self):
        body = {"endpoint": "https://push.example/shared", "keys": {"p256dh": "a", "auth": "b"}}
        self.client.post("/api/alerts/subscribe/", body, format="json")
        self.client.force_authenticate(self.gloria)
        self.client.post("/api/alerts/subscribe/", body, format="json")
        self.assertEqual(PushSubscription.objects.get().user, self.gloria)

    def test_insecure_or_incomplete_devices_are_refused(self):
        self.assertEqual(self.client.post("/api/alerts/subscribe/", {"endpoint": "http://x.example/a", "keys": {"p256dh": "a", "auth": "b"}}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/alerts/subscribe/", {"endpoint": "https://x.example/a", "keys": {"p256dh": "a"}}, format="json").status_code, 400)

    def test_nobody_can_turn_off_someone_elses_device(self):
        d = self.device(self.gloria)
        self.client.post("/api/alerts/unsubscribe/", {"endpoint": d.endpoint}, format="json")
        self.assertTrue(PushSubscription.objects.filter(pk=d.pk).exists())

    def test_choices_are_saved_and_only_relevant_kinds_shown(self):
        self.client.force_authenticate(self.gloria)
        kinds = [k["key"] for k in self.client.get("/api/alerts/settings/").data["kinds"]]
        self.assertEqual(kinds, ["morning", "assigned", "announcements", "followup"])  # no Admin access, but she shepherds
        r = self.client.patch("/api/alerts/settings/", {"morning": False}, format="json")
        self.assertFalse(next(k for k in r.data["kinds"] if k["key"] == "morning")["on"])
        self.assertEqual(self.client.patch("/api/alerts/settings/", {"morning": "no"}, format="json").status_code, 400)
        self.client.force_authenticate(self.admin)
        kinds = [k["key"] for k in self.client.get("/api/alerts/settings/").data["kinds"]]
        self.assertEqual(kinds, ["morning", "assigned", "arrivals", "weekly", "announcements", "followup"])

    def test_test_alert(self):
        self.assertEqual(self.client.post("/api/alerts/test/").status_code, 400)
        self.device(self.admin)
        self.assertEqual(self.client.post("/api/alerts/test/").data["devices"], 1)
        self.assertEqual(self.to(self.admin)[0]["title"], "Alerts are working")

    def test_key_is_made_once_and_kept(self):
        a = self.client.get("/api/alerts/key/").data["public_key"]
        self.assertEqual(a, self.client.get("/api/alerts/key/").data["public_key"])
        self.assertEqual(len(base64.urlsafe_b64decode(a + "==")), 65)          # an uncompressed P-256 point
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/alerts/key/").status_code, 401)


class GivenTests(AlertsBase):
    def test_contact_given_by_hand_alerts_the_follow_up_person_only(self):
        self.device(self.gloria); self.device(self.admin)
        e = Enquiry.objects.create(name="Ada", source=self.src, phone="1", stage="contacted", gender="Female")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(f"/api/enquiries/{e.id}/", {"assigned_to": self.gloria.id}, format="json")
        [p] = self.to(self.gloria)
        self.assertEqual((p["title"], p["body"], p["url"]), ("1 person given to you", "Ada is yours to follow up.", f"/enquiries/{e.id}"))
        self.assertEqual(self.to(self.admin), [])

    def test_several_at_once_make_one_alert(self):
        self.device(self.gloria)
        es = [Enquiry.objects.create(name=n, source=self.src, phone="1", stage="contacted") for n in ("Ada", "Bea", "Cy", "Dee")]
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/api/enquiries/bulk-assign/", {"enquiries": [e.id for e in es], "assigned_to": self.gloria.id}, format="json")
        [p] = self.to(self.gloria)
        self.assertEqual(p["title"], "4 people given to you")
        self.assertEqual(p["body"], "Ada, Bea and 2 more are yours to follow up.")

    def test_nobody_is_told_about_people_they_gave_themselves(self):
        self.device(self.gloria)
        self.client.force_authenticate(self.gloria)
        e = Enquiry.objects.create(name="Ada", source=self.src, phone="1", stage="contacted")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(f"/api/enquiries/{e.id}/", {"assigned_to": self.gloria.id}, format="json")
        self.assertEqual(self.sent, [])

    def test_no_alert_when_nothing_changed_or_switched_off(self):
        self.device(self.gloria)
        e = Enquiry.objects.create(name="Ada", source=self.src, phone="1", stage="contacted", assigned_to=self.gloria)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(f"/api/enquiries/{e.id}/", {"assigned_to": self.gloria.id}, format="json")
        self.assertEqual(self.sent, [])
        AlertSettings.objects.update_or_create(user=self.gloria, defaults={"assigned": False})
        e2 = Enquiry.objects.create(name="Bea", source=self.src, phone="1", stage="contacted")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(f"/api/enquiries/{e2.id}/", {"assigned_to": self.gloria.id}, format="json")
        self.assertEqual(self.sent, [])

    def test_member_by_hand_bulk_and_auto_assign(self):
        self.device(self.gloria)
        a = self.member("Ada", "Eze", gender="Female")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.patch(f"/api/members/{a.id}/", {"assigned_to": self.gloria.id}, format="json")
        self.assertEqual(self.to(self.gloria)[-1]["url"], f"/members/{a.id}")
        b = self.member("Bea", "Eze", gender="Female")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/api/members/bulk-assign-shepherd/", {"member_ids": [a.id, b.id], "shepherd_id": self.gloria.id}, format="json")
        self.assertEqual(self.to(self.gloria)[-1]["body"], "Bea Eze is yours to follow up.")   # Ada already hers
        c = self.member("Cee", "Eze", gender="Female")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/api/members/assign-shepherds/", {}, format="json")
        c.refresh_from_db(); self.assertEqual(c.assigned_to, self.gloria)
        self.assertIn("Cee Eze", self.to(self.gloria)[-1]["body"])

    def test_registration_alerts_the_shepherd_and_the_people_who_handle_arrivals(self):
        other = User.objects.create_user(email="o@t.com", password="x", role=self.admin.role, location=self.bahrain)
        self.device(self.gloria); self.device(self.admin); self.device(other)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post("/api/newcomers/", {"name": "Mary John", "source": self.source.id, "location": "bahrain",
                                                      "gender": "Female", "phone": "97311119999"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual([p["title"] for p in self.to(self.gloria)], ["1 person given to you"])
        self.assertEqual([p["body"] for p in self.to(other)], ["Mary John registered at Bahrain and was given to Gloria Afari."])
        self.assertEqual(self.to(self.admin), [])                                  # added it themselves

    def test_qr_self_registration_alerts_arrival_handlers_and_the_shepherd(self):
        from attendance.models import MeetingType
        mt = MeetingType.objects.create(id="fri-worship", name="Friday Worship Service", day="Friday",
                                        frequency="weekly", detail_level="detailed", monthly_target=150)
        self.device(self.admin); self.device(self.gloria)
        self.client.force_authenticate(None)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post("/api/public/newcomer-registration/", {
                "name": "Fatima Al-Sayed", "address": "Flat 12", "city_governorate": "Manama", "phone": "+973 3600 1234",
                "email": "f@example.com", "gender": "Female", "age_group": "20_and_above", "prayer_request": "",
                "meeting_attended": mt.id, "is_first_timer": True, "is_new_resident": False,
                "form_loaded_at": (timezone.now() - datetime.timedelta(seconds=5)).isoformat()}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual([p["title"] for p in self.to(self.admin)], ["New newcomer registered"])
        self.assertEqual([p["title"] for p in self.to(self.gloria)], ["1 person given to you"])

    def test_new_contact_alerts_arrival_handlers_but_not_who_added_it(self):
        other = User.objects.create_user(email="o@t.com", password="x", role=self.admin.role)
        self.device(self.admin); self.device(other); self.device(self.gloria)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/api/enquiries/", {"name": "Joy Mensah", "source": self.src.id, "phone": "97300000001"}, format="json")
        self.assertEqual(self.to(self.admin), [])                                # added it
        self.assertEqual(self.to(other)[0]["title"], "New contact from Facebook")
        self.assertEqual(self.to(self.gloria), [])                              # no Admin access

    def test_a_failed_alert_never_stops_the_change(self):
        self.device(self.gloria)
        e = Enquiry.objects.create(name="Ada", source=self.src, phone="1", stage="contacted")
        with mock.patch("alerts.push._deliver", side_effect=RuntimeError("push service down")):
            with self.captureOnCommitCallbacks(execute=True):
                r = self.client.patch(f"/api/enquiries/{e.id}/", {"assigned_to": self.gloria.id}, format="json")
        self.assertEqual(r.status_code, 200)
        e.refresh_from_db(); self.assertEqual(e.assigned_to, self.gloria)


class ScheduledTests(AlertsBase):
    def at(self, y, m, d, h, mi=0):
        return datetime.datetime(y, m, d, h, mi, tzinfo=BH)

    def test_morning_goes_once_after_7_and_only_when_something_waits(self):
        self.device(self.gloria)
        mem = self.member("Ada", "Eze", assigned_to=self.gloria)
        MemberFollowUpTask.objects.create(member=mem, text="Call", missed_date=datetime.date(2026, 10, 8), due_date=datetime.date(2026, 10, 10), assigned_to=self.gloria)
        self.assertEqual(scheduled.morning(self.at(2026, 10, 12, 6, 59)), 0)
        self.assertEqual(scheduled.morning(self.at(2026, 10, 12, 7, 5)), 1)
        self.assertEqual(scheduled.morning(self.at(2026, 10, 12, 8, 5)), 0)          # once a day
        [p] = self.to(self.gloria)
        self.assertEqual(p["title"], "Good morning, Gloria")
        self.assertEqual(p["body"], "1 of your member follow-up overdue. Tap to open.")
        MemberFollowUpTask.objects.update(done=True)
        self.assertEqual(scheduled.morning(self.at(2026, 10, 13, 7, 5)), 0)           # nothing waiting, nothing sent

    def test_weekly_on_monday_for_leaders_only(self):
        self.device(self.gloria); self.device(self.admin)
        self.assertEqual(scheduled.weekly(self.at(2026, 10, 13, 9)), 0)               # a Tuesday
        self.assertEqual(scheduled.weekly(self.at(2026, 10, 12, 7, 31)), 1)
        self.assertEqual(scheduled.weekly(self.at(2026, 10, 12, 9)), 0)
        self.assertEqual(self.to(self.gloria), [])
        self.assertEqual(self.to(self.admin)[0]["title"], "Your week in follow-up")

    @override_settings(DCLM_TASK_SECRET="s", TASK_SECRET="s")
    def test_rides_on_the_hourly_scheduled_job(self):
        with mock.patch("alerts.scheduled.run", return_value="Alerts: 0 morning, 0 weekly.") as run:
            r = self.client.post("/api/tasks/run/", {"command": "check_absences"}, format="json", HTTP_X_TASK_SECRET="s")
        self.assertEqual(r.status_code, 200); run.assert_called_once()
        self.assertIn("Alerts:", r.data["output"])


class AnnouncementTests(AlertsBase):
    def test_admin_sends_to_everyone_and_it_is_recorded(self):
        self.device(self.gloria); self.device(self.admin, 1); self.device(self.admin, 2)
        r = self.client.post("/api/alerts/announcements/", {"title": "Ebenezer Night tonight", "body": "Starts at 10 pm.",
                                                           "audience": "everyone"}, format="json")
        self.assertEqual((r.status_code, r.data["people"], r.data["devices"]), (201, 2, 3))
        self.assertEqual(self.to(self.gloria)[0]["body"], "Starts at 10 pm. (Sent by Chinedu)")
        a = self.client.get("/api/alerts/announcements/").data
        self.assertEqual((a["people_with_alerts"], a["results"][0]["audience"]), (2, "Everyone"))

    def test_audiences_and_locations(self):
        qatar = __import__("core.models", fromlist=["Location"]).Location.objects.create(id="qatar", name="Qatar")
        q = User.objects.create_user(email="q@t.com", password="x", role=self.gloria.role, location=qatar)
        self.device(self.gloria); self.device(q)
        self.client.post("/api/alerts/announcements/", {"title": "T", "body": "B", "audience": "shepherds"}, format="json")
        self.assertEqual((len(self.to(self.gloria)), len(self.to(q))), (1, 0))   # q cannot shepherd
        self.client.post("/api/alerts/announcements/", {"title": "T", "body": "B", "audience": f"role-{self.gloria.role_id}", "location": "qatar"}, format="json")
        self.assertEqual((len(self.to(self.gloria)), len(self.to(q))), (1, 1))
        self.assertEqual(self.client.post("/api/alerts/announcements/", {"title": "T", "body": "B", "audience": "role-x"}, format="json").status_code, 400)

    def test_a_coordinator_at_one_location_reaches_only_that_location(self):
        from core.models import Location
        qatar = Location.objects.create(id="qatar", name="Qatar")
        coord = User.objects.create_user(email="c@t.com", password="x", role=self.admin.role, location=self.bahrain)
        q = User.objects.create_user(email="q@t.com", password="x", role=self.gloria.role, location=qatar)
        self.device(self.gloria); self.device(q)
        self.client.force_authenticate(coord)
        r = self.client.post("/api/alerts/announcements/", {"title": "T", "body": "B", "audience": "everyone", "location": "qatar"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual((len(self.to(self.gloria)), len(self.to(q))), (1, 0))      # forced to Bahrain
        self.assertEqual(Announcement.objects.get().location_id, "bahrain")

    def test_alert_endpoints_need_sign_in(self):
        self.client.force_authenticate(None)
        for url in ("/api/alerts/settings/", "/api/alerts/announcements/", "/api/alerts/key/"):
            self.assertEqual(self.client.get(url).status_code, 401, url)
        for url in ("/api/alerts/subscribe/", "/api/alerts/unsubscribe/", "/api/alerts/test/", "/api/alerts/announcements/"):
            self.assertEqual(self.client.post(url, {}, format="json").status_code, 401, url)

    def test_only_admin_edit_may_send_and_announcements_can_be_switched_off(self):
        self.client.force_authenticate(self.gloria)
        self.assertEqual(self.client.post("/api/alerts/announcements/", {"title": "T", "body": "B", "audience": "everyone"}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/alerts/announcements/").status_code, 403)
        self.client.force_authenticate(self.admin)
        self.device(self.gloria); AlertSettings.objects.update_or_create(user=self.gloria, defaults={"announcements": False})
        r = self.client.post("/api/alerts/announcements/", {"title": "T", "body": "B", "audience": "everyone"}, format="json")
        self.assertEqual(r.data["people"], 0)
        self.assertTrue(Announcement.objects.exists())


class _Inbox(BaseHTTPRequestHandler):
    got = []
    status = 201

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        type(self).got.append(({k.lower(): v for k, v in self.headers.items()}, self.rfile.read(n)))
        self.send_response(type(self).status); self.end_headers()

    def log_message(self, *a):
        pass


@override_settings(ALERTS_IN_BACKGROUND=False)
class RealDeliveryTests(Base):
    """The real library, real encryption, against a stand-in push service:
    what arrives must decrypt, with this phone's keys, to the alert sent."""

    def setUp(self):
        super().setUp()
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        self.phone_key = ec.generate_private_key(ec.SECP256R1())
        self.auth = os.urandom(16)
        pub = self.phone_key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self.server = HTTPServer(("127.0.0.1", 0), _Inbox)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        _Inbox.got = []; _Inbox.status = 201
        self.sub = PushSubscription.objects.create(user=self.admin, endpoint=f"http://127.0.0.1:{self.server.server_port}/push/1",
                                                   p256dh=b64(pub), auth=b64(self.auth))

    def test_the_alert_arrives_encrypted_and_signed(self):
        from alerts.push import keys, send
        import http_ece
        self.assertEqual(send(self.admin, "assigned", "1 person given to you", "Ada is yours to follow up.", "/enquiries/5"), 1)
        headers, body = _Inbox.got[0]
        self.assertEqual(headers.get("content-encoding"), "aes128gcm")
        self.assertIn(f"k={keys()[0]}", headers.get("authorization", ""))         # signed with this server's key
        clear = http_ece.decrypt(body, private_key=self.phone_key, auth_secret=self.auth, version="aes128gcm")
        self.assertEqual(json.loads(clear), {"title": "1 person given to you", "body": "Ada is yours to follow up.", "url": "/enquiries/5", "tag": "assigned"})
        self.sub.refresh_from_db(); self.assertIsNotNone(self.sub.last_sent_at)

    def test_a_device_that_is_gone_is_forgotten(self):
        from alerts.push import send
        _Inbox.status = 410
        self.assertEqual(send(self.admin, "assigned", "T", "B"), 0)
        self.assertFalse(PushSubscription.objects.filter(pk=self.sub.pk).exists())

    def test_a_service_error_keeps_the_device(self):
        from alerts.push import send
        _Inbox.status = 500
        self.assertEqual(send(self.admin, "assigned", "T", "B"), 0)
        self.assertTrue(PushSubscription.objects.filter(pk=self.sub.pk).exists())
