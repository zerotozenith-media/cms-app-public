"""
Tests for online enquiries.

The behaviour worth protecting here is mostly about the boundary with
newcomers: an enquirer is not a newcomer until they attend, converting
keeps the link rather than moving the record, and the follow-up rules
match the rest of the system so workers learn one pattern.
"""
import datetime

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, RolePermission, User
from core.models import Location
from newcomers.models import Newcomer
from decimal import Decimal

from newcomers.models import NewcomerSource
from .models import EnquirySource, Campaign, Enquiry, EnquiryStatusHistory, EnquiryTask


class EnquiryAPITestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(
            role=self.role, module="newcomers",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@t.com", password="x", role=self.role)
        self.instagram = EnquirySource.objects.create(name="Instagram")
        self.client.force_authenticate(user=self.admin)

    def _enquiry(self, **kwargs):
        defaults = dict(name="Joy Mensah", source=self.instagram, social_handle="@joy")
        defaults.update(kwargs)
        return Enquiry.objects.create(**defaults)

    # ---- recording them ----

    def test_a_social_handle_alone_is_enough(self):
        """Often all the church has when someone first messages. Refusing
        it would mean losing the person entirely."""
        resp = self.client.post("/api/enquiries/", {
            "name": "Joy Mensah", "source": self.instagram.id, "social_handle": "@joy",
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["best_contact"], "@joy")

    def test_some_way_to_reach_them_is_required(self):
        resp = self.client.post("/api/enquiries/", {
            "name": "Nobody", "source": self.instagram.id,
        })
        self.assertEqual(resp.status_code, 400)

    def test_area_is_free_text_not_a_church_location(self):
        """An enquirer may be anywhere, including outside Bahrain."""
        enquiry = self._enquiry(area="Dubai")
        self.assertEqual(enquiry.area, "Dubai")

    def test_creating_records_the_first_status_entry(self):
        self.client.post("/api/enquiries/", {
            "name": "Joy", "source": self.instagram.id, "phone": "+973 3900 0000",
        })
        self.assertEqual(EnquiryStatusHistory.objects.count(), 1)

    # ---- moving them along ----

    def test_stage_change_is_recorded(self):
        enquiry = self._enquiry()
        resp = self.client.post(f"/api/enquiries/{enquiry.id}/change-stage/",
                                {"stage": "contacted", "note": "Replied on Instagram"})
        self.assertEqual(resp.status_code, 200)
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.stage, "contacted")
        self.assertTrue(EnquiryStatusHistory.objects.filter(
            enquiry=enquiry, stage="contacted").exists())

    def test_not_pursuing_requires_a_reason(self):
        """Otherwise the record says someone was dropped and nothing about
        why, which is no use to whoever reads it later."""
        enquiry = self._enquiry()
        resp = self.client.post(f"/api/enquiries/{enquiry.id}/change-stage/",
                                {"stage": "not-pursuing"})
        self.assertEqual(resp.status_code, 400)
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.stage, "new")

    def test_stage_cannot_be_changed_by_plain_patch(self):
        enquiry = self._enquiry()
        self.client.patch(f"/api/enquiries/{enquiry.id}/", {"stage": "attended"})
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.stage, "new")

    # ---- becoming a newcomer ----

    def test_converting_creates_a_linked_newcomer(self):
        enquiry = self._enquiry(phone="+973 3900 0000", enquiry_text="When are services?")
        resp = self.client.post(f"/api/enquiries/{enquiry.id}/convert/", {"location": "bahrain"})
        self.assertEqual(resp.status_code, 200)

        enquiry.refresh_from_db()
        self.assertIsNotNone(enquiry.converted_newcomer)
        self.assertEqual(enquiry.stage, "attended")

        newcomer = enquiry.converted_newcomer
        self.assertEqual(newcomer.name, "Joy Mensah")
        self.assertEqual(newcomer.phone, "+973 3900 0000")

    def test_conversion_records_the_original_platform(self):
        """The point of the whole feature: knowing how many people in the
        room first came through social media."""
        enquiry = self._enquiry()
        self.client.post(f"/api/enquiries/{enquiry.id}/convert/", {"location": "bahrain"})
        enquiry.refresh_from_db()
        self.assertIn("Instagram", enquiry.converted_newcomer.source.name)

    def test_the_enquiry_is_kept_after_conversion(self):
        """Deleting it would destroy the only record that this newcomer
        started as an online enquiry."""
        enquiry = self._enquiry()
        self.client.post(f"/api/enquiries/{enquiry.id}/convert/", {"location": "bahrain"})
        self.assertTrue(Enquiry.objects.filter(id=enquiry.id).exists())

    def test_cannot_convert_the_same_person_twice(self):
        enquiry = self._enquiry()
        self.client.post(f"/api/enquiries/{enquiry.id}/convert/", {"location": "bahrain"})
        resp = self.client.post(f"/api/enquiries/{enquiry.id}/convert/", {"location": "bahrain"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Newcomer.objects.count(), 1)

    def test_conversion_rejects_an_unknown_location(self):
        enquiry = self._enquiry()
        resp = self.client.post(f"/api/enquiries/{enquiry.id}/convert/", {"location": "nowhere"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Newcomer.objects.count(), 0)

    # ---- follow-up ----

    def test_task_cannot_be_completed_by_plain_patch(self):
        enquiry = self._enquiry()
        task = EnquiryTask.objects.create(
            enquiry=enquiry, text="Reply", due_date=timezone.localdate())
        self.client.patch(f"/api/enquiry-tasks/{task.id}/", {"done": True})
        task.refresh_from_db()
        self.assertFalse(task.done)

    def test_completing_requires_all_four_outcome_fields(self):
        enquiry = self._enquiry()
        task = EnquiryTask.objects.create(
            enquiry=enquiry, text="Reply", due_date=timezone.localdate())
        resp = self.client.post(f"/api/enquiry-tasks/{task.id}/complete/",
                                {"contact_method": "WhatsApp"})
        self.assertEqual(resp.status_code, 400)
        task.refresh_from_db()
        self.assertFalse(task.done)

    def test_completing_with_everything_records_the_outcome(self):
        enquiry = self._enquiry()
        task = EnquiryTask.objects.create(
            enquiry=enquiry, text="Reply", due_date=timezone.localdate())
        resp = self.client.post(f"/api/enquiry-tasks/{task.id}/complete/", {
            "contact_method": "WhatsApp",
            "contact_goal": "Invite her to Friday service",
            "contact_scripture": "Psalm 122:1",
            "contact_root_cause": "New to Bahrain, looking for a church",
            "contact_next_step": "Send her the address",
        })
        self.assertEqual(resp.status_code, 200)
        task.refresh_from_db()
        self.assertTrue(task.done)
        self.assertEqual(task.contact_method, "WhatsApp")

    def test_a_task_inherits_the_enquiry_assignee(self):
        worker = User.objects.create_user(email="w@t.com", password="x", role=self.role)
        enquiry = self._enquiry(assigned_to=worker)
        resp = self.client.post("/api/enquiry-tasks/", {
            "enquiry": enquiry.id, "text": "Reply", "due_date": str(timezone.localdate()),
        })
        self.assertEqual(resp.data["assigned_to"], worker.id)

    def test_filter_tasks_by_done(self):
        enquiry = self._enquiry()
        EnquiryTask.objects.create(enquiry=enquiry, text="Open", due_date=timezone.localdate())
        EnquiryTask.objects.create(enquiry=enquiry, text="Closed",
                                   due_date=timezone.localdate(), done=True)
        resp = self.client.get("/api/enquiry-tasks/?done=false")
        self.assertEqual([t["text"] for t in resp.data["results"]], ["Open"])

    # ---- permissions ----

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get("/api/enquiries/").status_code, (401, 403))

    def test_a_role_without_newcomers_access_is_denied(self):
        other_role = Role.objects.create(name="Attendance Only")
        RolePermission.objects.create(role=other_role, module="attendance", can_view=True)
        user = User.objects.create_user(email="usher@t.com", password="x", role=other_role)
        self.client.force_authenticate(user=user)
        self.assertEqual(self.client.get("/api/enquiries/").status_code, 403)

    # ---- reporting ----

    def test_stats_separate_active_from_finished(self):
        self._enquiry(name="Active one")
        converted = self._enquiry(name="Converted one")
        self.client.post(f"/api/enquiries/{converted.id}/convert/", {"location": "bahrain"})
        resp = self.client.get("/api/enquiries/stats/")
        self.assertEqual(resp.data["active"], 1)
        self.assertEqual(resp.data["converted"], 1)


class CampaignTestCase(APITestCase):
    """
    Campaign and spend are marketing data behind their own `outreach`
    permission. The behaviour worth protecting: a follow-up worker sees
    the person and how to reach them but never what the church paid to
    find them, and whoever runs the adverts can see performance without
    also being an administrator.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)

        self.admin_role = Role.objects.create(name="Administrator")
        for module in ["newcomers", "outreach", "admin"]:
            RolePermission.objects.create(
                role=self.admin_role, module=module,
                can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@t.com", password="x", role=self.admin_role)

        # Follow-up worker: newcomers, deliberately no outreach.
        self.worker_role = Role.objects.create(name="Follow-up Team")
        RolePermission.objects.create(role=self.worker_role, module="newcomers",
            can_view=True, can_create=True, can_edit=True)
        self.worker = User.objects.create_user(email="worker@t.com", password="x", role=self.worker_role)

        # Outreach: campaigns, but not admin.
        self.outreach_role = Role.objects.create(name="Outreach")
        RolePermission.objects.create(role=self.outreach_role, module="outreach",
            can_view=True, can_create=True, can_edit=True)
        RolePermission.objects.create(role=self.outreach_role, module="newcomers", can_view=True)
        self.outreach = User.objects.create_user(email="outreach@t.com", password="x", role=self.outreach_role)

        self.facebook = EnquirySource.objects.create(name="Facebook")
        self.campaign = Campaign.objects.create(
            name="Christmas Service 2026", source=self.facebook, spend=Decimal("120.000"))

    def _enquiry(self, name, converted=False):
        newcomer = None
        if converted:
            source = NewcomerSource.objects.create(name=f"FB {name}")
            newcomer = Newcomer.objects.create(
                name=name, source=source, location=self.bahrain, stage="new",
                created_at=timezone.localdate(), stage_since=timezone.localdate())
        return Enquiry.objects.create(
            name=name, source=self.facebook, phone="+973 3300 0000",
            campaign=self.campaign, converted_newcomer=newcomer)

    # ---- who sees what ----

    def test_follow_up_worker_never_sees_the_campaign(self):
        self._enquiry("Joy")
        self.client.force_authenticate(user=self.worker)
        resp = self.client.get("/api/enquiries/")
        record = resp.data["results"][0]
        self.assertNotIn("campaign", record)
        self.assertNotIn("campaign_name", record)

    def test_follow_up_worker_still_sees_the_person(self):
        """Hiding the campaign must not hide what they need to do the job."""
        self._enquiry("Joy")
        self.client.force_authenticate(user=self.worker)
        record = self.client.get("/api/enquiries/").data["results"][0]
        self.assertEqual(record["name"], "Joy")
        self.assertTrue(record["best_contact"])

    def test_follow_up_worker_cannot_reach_the_campaigns_endpoint(self):
        self.client.force_authenticate(user=self.worker)
        self.assertEqual(self.client.get("/api/campaigns/").status_code, 403)

    def test_outreach_role_sees_the_campaign(self):
        self._enquiry("Joy")
        self.client.force_authenticate(user=self.outreach)
        record = self.client.get("/api/enquiries/").data["results"][0]
        self.assertEqual(record["campaign_name"], "Christmas Service 2026")

    def test_outreach_role_is_not_an_administrator(self):
        """The point of a separate module: seeing ad performance should
        not require the ability to create users."""
        self.client.force_authenticate(user=self.outreach)
        self.assertEqual(self.client.get("/api/users/").status_code, 403)

    def test_campaigns_require_authentication(self):
        self.assertIn(self.client.get("/api/campaigns/").status_code, (401, 403))

    # ---- the numbers ----

    def test_conversion_and_cost_are_computed(self):
        self._enquiry("Converted", converted=True)
        self._enquiry("Not yet")
        self.client.force_authenticate(user=self.admin)
        row = self.client.get("/api/campaigns/").data["results"][0]
        self.assertEqual(row["enquiries_received"], 2)
        self.assertEqual(row["converted"], 1)
        self.assertEqual(row["conversion_rate"], 50)
        self.assertEqual(row["cost_per_enquiry"], 60.0)
        self.assertEqual(row["cost_per_newcomer"], 120.0)

    def test_cost_per_newcomer_is_none_before_anyone_converts(self):
        """Dividing by zero would be wrong; so would reporting 0, which
        reads as free."""
        self._enquiry("Not yet")
        self.client.force_authenticate(user=self.admin)
        row = self.client.get("/api/campaigns/").data["results"][0]
        self.assertIsNone(row["cost_per_newcomer"])

    def test_organic_campaign_reports_no_cost(self):
        organic = Campaign.objects.create(name="None (organic)", spend=Decimal("0"))
        Enquiry.objects.create(name="Walk up", source=self.facebook,
                               social_handle="@x", campaign=organic)
        self.client.force_authenticate(user=self.admin)
        rows = self.client.get("/api/campaigns/").data["results"]
        row = next(r for r in rows if r["name"] == "None (organic)")
        self.assertIsNone(row["cost_per_enquiry"])
        self.assertEqual(row["enquiries_received"], 1)

    def test_summary_totals(self):
        self._enquiry("Converted", converted=True)
        self.client.force_authenticate(user=self.admin)
        data = self.client.get("/api/campaigns/summary/").data
        self.assertEqual(data["total_spend"], 120.0)
        self.assertEqual(data["total_converted"], 1)
        self.assertEqual(data["cost_per_newcomer"], 120.0)

    def test_creating_a_campaign_is_audited(self):
        from accounts.models import AuditLog
        self.client.force_authenticate(user=self.admin)
        self.client.post("/api/campaigns/", {"name": "Easter 2027", "spend": "50.000"})
        self.assertTrue(AuditLog.objects.filter(entity_type="Campaign", entity_name="Easter 2027").exists())
