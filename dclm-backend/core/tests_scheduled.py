"""
The scheduled-task endpoint.

It runs management commands, so it is worth attacking. These tests exist
mainly to prove it cannot be turned into a way to run anything else.
"""
from django.test import override_settings
from rest_framework.test import APITestCase

from core.models import Location


class ScheduledTaskEndpointTestCase(APITestCase):
    url = "/api/tasks/run/"

    def setUp(self):
        Location.objects.create(id="bahrain", name="Bahrain", is_core=True)

    @override_settings(TASK_SECRET="")
    def test_it_refuses_everything_when_no_secret_is_configured(self):
        """A deployment that forgot to set the secret must fail loudly,
        not default to accepting anyone."""
        resp = self.client.post(self.url, {"command": "check_absences"}, format="json")
        self.assertEqual(resp.status_code, 503)

    @override_settings(TASK_SECRET="right-secret")
    def test_a_wrong_secret_is_refused(self):
        resp = self.client.post(
            self.url, {"command": "check_absences"}, format="json",
            HTTP_X_TASK_SECRET="wrong-secret")
        self.assertEqual(resp.status_code, 403)

    @override_settings(TASK_SECRET="right-secret")
    def test_no_secret_at_all_is_refused(self):
        resp = self.client.post(self.url, {"command": "check_absences"}, format="json")
        self.assertEqual(resp.status_code, 403)

    @override_settings(TASK_SECRET="right-secret")
    def test_only_the_scheduled_commands_can_be_named(self):
        """The difference between a scheduler and a remote shell."""
        for command in ["migrate", "flush", "createsuperuser",
                        "seed_demo_data", "shell", ""]:
            resp = self.client.post(
                self.url, {"command": command}, format="json",
                HTTP_X_TASK_SECRET="right-secret")
            self.assertEqual(resp.status_code, 400, f"{command} should be refused")

    @override_settings(TASK_SECRET="right-secret")
    def test_a_real_scheduled_command_runs(self):
        resp = self.client.post(
            self.url, {"command": "check_absences"}, format="json",
            HTTP_X_TASK_SECRET="right-secret")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["command"], "check_absences")

    @override_settings(TASK_SECRET="right-secret")
    def test_every_run_is_written_to_the_audit_log(self):
        """So scheduled runs are visible in the app, not only in a cloud
        console somebody has to remember to open."""
        from accounts.models import AuditLog
        AuditLog.objects.all().delete()
        self.client.post(
            self.url, {"command": "check_absences"}, format="json",
            HTTP_X_TASK_SECRET="right-secret")
        entry = AuditLog.objects.filter(action="Scheduled task").first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.entity_name, "check_absences")

    @override_settings(TASK_SECRET="right-secret")
    def test_a_get_request_is_refused(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
