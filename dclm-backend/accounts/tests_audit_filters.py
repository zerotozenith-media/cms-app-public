"""Audit Log search and filters (Kay, 5 November 2026)."""
import datetime

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User


class AuditFilters(APITestCase):
    def setUp(self):
        role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=role, module="admin", can_view=True, can_edit=True)
        self.admin = User.objects.create_user(email="a@t.com", password="x", role=role)
        self.client.force_authenticate(self.admin)
        def log(who, action, typ, name, when):
            a = AuditLog.objects.create(user=self.admin, user_name_snapshot=who, action=action, entity_type=typ, entity_name=name)
            AuditLog.objects.filter(pk=a.pk).update(timestamp=when)
        AuditLog.objects.all().delete()   # entries made by the setup above
        tz = timezone.get_current_timezone()
        # 23:30 Bahrain on 14 October is 20:30 UTC: still 14 October here.
        log("Grace", "Created", "Attendance Session", "Monday Bible Study · 2026-10-14", datetime.datetime(2026, 10, 14, 23, 30, tzinfo=tz))
        log("Grace", "Recorded attendance", "Attendance Session", "Monday Bible Study · 2026-10-14", datetime.datetime(2026, 10, 15, 0, 30, tzinfo=tz))
        log("Paul", "Deleted", "Giving", "Offering 4.000", datetime.datetime(2026, 9, 1, 9, 0, tzinfo=tz))

    def names(self, **params):
        r = self.client.get("/api/audit-log/", params)
        self.assertEqual(r.status_code, 200, r.data)
        return [(x["action"], x["entity_type"]) for x in r.data["results"]]

    def test_search_and_filters(self):
        self.assertEqual(len(self.names(search="Monday Bible Study 14")), 2)
        self.assertEqual(self.names(entity_type="Giving"), [("Deleted", "Giving")])
        self.assertEqual(self.names(who="Paul"), [("Deleted", "Giving")])
        self.assertEqual(self.names(action="Created"), [("Created", "Attendance Session")])
        self.assertEqual(self.names(date_from="2026-10-14", date_to="2026-10-14"), [("Created", "Attendance Session")])

    def test_choices(self):
        r = self.client.get("/api/audit-log/choices/")
        self.assertEqual(r.data["entity_types"], ["Attendance Session", "Giving"])
        self.assertEqual(r.data["people"], ["Grace", "Paul"])
        self.assertIn("Recorded attendance", r.data["actions"])
