from .clientip import get_client_ip
from .names import display_name
from members.models import Member
import datetime
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Location
from .models import Role, RolePermission, User, AuditLog, LoginAttempt


class LocationAPITestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.others = Location.objects.create(id="others", name="Others", note="Qatar")
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="admin",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@test.com", password="RealPass123!", role=self.role)
        self.client.force_authenticate(user=self.admin)

    def test_deleting_core_location_returns_clean_400_not_500(self):
        resp = self.client.delete(f"/api/locations/{self.bahrain.id}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST,
            "Deleting the core location must be a clean 400, not an unhandled 500.")
        self.assertTrue(Location.objects.filter(id="bahrain").exists())

    def test_deleting_non_core_location_succeeds(self):
        resp = self.client.delete(f"/api/locations/{self.others.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Location.objects.filter(id="others").exists())

    def test_is_core_is_read_only(self):
        resp = self.client.patch(f"/api/locations/{self.others.id}/", {"is_core": True})
        self.others.refresh_from_db()
        self.assertFalse(self.others.is_core, "is_core must not be settable through the API.")


class UserAPITestCase(APITestCase):
    def setUp(self):
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="admin",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.coord_role = Role.objects.create(name="Location Coordinator")
        self.admin = User.objects.create_user(email="admin@test.com", password="RealPass123!", role=self.role)
        self.client.force_authenticate(user=self.admin)

    def test_create_user_hashes_password_not_stored_plain(self):
        resp = self.client.post("/api/users/", {
            "email": "grace@test.com", "password": "GracePass123!", "role": self.coord_role.id,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", resp.data, "Password must never be returned in the response.")
        user = User.objects.get(email="grace@test.com")
        self.assertNotEqual(user.password, "GracePass123!")
        self.assertTrue(user.check_password("GracePass123!"), "The hashed password must still verify correctly.")

    def test_create_user_without_password_rejected(self):
        resp = self.client.post("/api/users/", {"email": "nopass@test.com", "role": self.coord_role.id})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_rejected(self):
        resp = self.client.post("/api/users/", {
            "email": "weak@test.com", "password": "123", "role": self.coord_role.id,
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_without_password_leaves_password_unchanged(self):
        user = User.objects.create_user(email="sarah@test.com", password="OriginalPass123!", role=self.coord_role)
        self.client.patch(f"/api/users/{user.id}/", {"first_name": "Sarah"})
        user.refresh_from_db()
        self.assertTrue(user.check_password("OriginalPass123!"), "Password must survive an edit that doesn't touch it.")

    def test_update_with_new_password_rehashes_it(self):
        user = User.objects.create_user(email="sarah@test.com", password="OldPass123!", role=self.coord_role)
        self.client.patch(f"/api/users/{user.id}/", {"password": "NewPass456!"})
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPass456!"))
        self.assertFalse(user.check_password("OldPass123!"))

    def test_deleting_sole_administrator_returns_clean_400_not_500(self):
        resp = self.client.delete(f"/api/users/{self.admin.id}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST,
            "Deleting the last Administrator must be a clean 400, not an unhandled 500.")
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

    def test_failed_delete_does_not_leave_a_false_audit_entry(self):
        """
        The delete-then-fail-validation path must not leave a "Deleted
        User" entry behind claiming something happened that didn't ,
        found this exact risk while fixing the self-deletion ordering
        bug below, and it needed its own explicit test.
        """
        AuditLog.objects.all().delete()
        self.client.delete(f"/api/users/{self.admin.id}/")  # rejected , last Administrator
        self.assertFalse(
            AuditLog.objects.filter(action="Deleted", entity_type="User").exists(),
            "A rejected deletion must not leave behind an audit entry claiming it succeeded.",
        )

    def test_deleting_administrator_succeeds_once_a_second_one_exists(self):
        second_admin = User.objects.create_user(email="second@test.com", password="Pass123456!", role=self.role)
        resp = self.client.delete(f"/api/users/{self.admin.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_deleting_non_administrator_is_unaffected_by_the_rule(self):
        coord = User.objects.create_user(email="coord@test.com", password="Pass123456!", role=self.coord_role)
        resp = self.client.delete(f"/api/users/{coord.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


class AuditLogAPITestCase(APITestCase):
    def setUp(self):
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="admin",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@test.com", password="RealPass123!", role=self.role)
        self.client.force_authenticate(user=self.admin)
        AuditLog.objects.create(user=self.admin, user_name_snapshot="admin@test.com",
            action="Created", entity_type="Member", entity_name="Test Member")

    def test_audit_log_is_read_only(self):
        resp = self.client.post("/api/audit-log/", {
            "user_name_snapshot": "fake", "action": "Fabricated", "entity_type": "Member",
        })
        self.assertIn(resp.status_code, [403, 405], "Audit log must never be writable through the API.")

    def test_audit_log_cannot_be_deleted_via_api(self):
        entry = AuditLog.objects.first()
        resp = self.client.delete(f"/api/audit-log/{entry.id}/")
        self.assertIn(resp.status_code, [403, 405])
        self.assertTrue(AuditLog.objects.filter(id=entry.id).exists())

    def test_filter_by_entity_type(self):
        AuditLog.objects.create(user=self.admin, user_name_snapshot="admin@test.com",
            action="Created", entity_type="Location", entity_name="Bahrain")
        resp = self.client.get("/api/audit-log/?entity_type=Location")
        self.assertEqual(len(resp.data["results"]), 1)


class LoginFlowAPITestCase(APITestCase):
    """
    Batch 1.4 verified honeypot/lockout/rate-limiting extensively via
    manual shell scripts at the time, but never converted that into
    permanent automated coverage , found and fixed while touching this
    same endpoint in Batch 3.2 to add role_permissions to the response.
    """
    def setUp(self):
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="members",
            can_view=True, can_create=True, can_edit=False, can_delete=False)
        RolePermission.objects.create(role=self.role, module="finance",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.user = User.objects.create_user(email="chinedu@test.com", password="RealPass123!", role=self.role)

    def test_successful_login_returns_user_and_role_permissions(self):
        resp = self.client.post("/api/auth/login/", {"email": "chinedu@test.com", "password": "RealPass123!"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["email"], "chinedu@test.com")
        self.assertEqual(resp.data["user"]["role"], "Administrator")

        perms = {p["module"]: p for p in resp.data["user"]["role_permissions"]}
        self.assertEqual(len(perms), 2)
        self.assertTrue(perms["members"]["can_view"])
        self.assertFalse(perms["members"]["can_edit"])
        self.assertTrue(perms["finance"]["can_delete"])

    def test_login_response_includes_real_location_name_not_just_id(self):
        bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        User.objects.create_user(email="coord@test.com", password="RealPass123!", role=self.role, location=bahrain)
        resp = self.client.post("/api/auth/login/", {"email": "coord@test.com", "password": "RealPass123!"})
        self.assertEqual(resp.data["user"]["location"], "bahrain")
        self.assertEqual(resp.data["user"]["location_name"], "Bahrain")

    def test_administrator_with_no_location_gets_null_location_name(self):
        resp = self.client.post("/api/auth/login/", {"email": "chinedu@test.com", "password": "RealPass123!"})
        self.assertIsNone(resp.data["user"]["location"])
        self.assertIsNone(resp.data["user"]["location_name"])

    def test_user_with_no_role_gets_empty_permissions_not_an_error(self):
        User.objects.create_user(email="norole@test.com", password="RealPass123!")
        resp = self.client.post("/api/auth/login/", {"email": "norole@test.com", "password": "RealPass123!"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["user"]["role_permissions"], [])

    def test_wrong_password_rejected(self):
        resp = self.client.post("/api/auth/login/", {"email": "chinedu@test.com", "password": "wrong"})
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn("access", resp.data)

    def test_honeypot_rejects_silently_with_generic_message(self):
        resp = self.client.post("/api/auth/login/", {
            "email": "chinedu@test.com", "password": "RealPass123!", "website": "http://spam.example",
        })
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data["detail"], "Invalid email or password.")

    def test_account_locks_after_five_failed_attempts(self):
        for _ in range(5):
            resp = self.client.post("/api/auth/login/", {"email": "chinedu@test.com", "password": "wrong"})
            self.assertEqual(resp.status_code, 401)
        resp = self.client.post("/api/auth/login/", {"email": "chinedu@test.com", "password": "RealPass123!"})
        self.assertEqual(resp.status_code, 429,
            "The 6th attempt must be locked out even with the CORRECT password.")


class LoginAttemptAPITestCase(APITestCase):
    def setUp(self):
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="admin",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@test.com", password="RealPass123!", role=self.role)
        self.client.force_authenticate(user=self.admin)
        LoginAttempt.objects.create(email_attempted="test@test.com", ip_address="1.2.3.4",
            successful=False, reason="invalid_credentials")
        LoginAttempt.objects.create(email_attempted="admin@test.com", ip_address="5.6.7.8",
            successful=True, reason="success")

    def test_read_only(self):
        resp = self.client.post("/api/login-attempts/", {"email_attempted": "fake@test.com"})
        self.assertIn(resp.status_code, [403, 405])

    def test_filter_by_successful(self):
        resp = self.client.get("/api/login-attempts/?successful=false")
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["reason"], "invalid_credentials")


class DisplayNameTestCase(TestCase):
    """
    One rule for how a person's name appears, used by every serializer,
    the audit log and the assignment engine. Caught on a real screen: the
    follow-up list showed "sarah@dclm-bh.org" where a leader expects
    "Sarah Osei", because the User account had no first or last name but
    the linked member record did.
    """
    def setUp(self):
        self.location = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.role = Role.objects.create(name="Worker")

    def _member(self, first, surname):
        return Member.objects.create(
            surname=surname, first_name=first, location=self.location,
            joined_date=datetime.date(2020, 1, 1), category=Member.Category.WORKER,
        )

    def test_prefers_the_linked_member_name(self):
        user = User.objects.create_user(email="sarah@dclm-bh.org", password="x", role=self.role)
        user.member = self._member("Sarah", "Osei")
        user.save()
        self.assertEqual(display_name(user), "Sarah Osei")

    def test_falls_back_to_account_name_when_no_member_is_linked(self):
        user = User.objects.create_user(
            email="x@dclm-bh.org", password="x", role=self.role,
            first_name="Grace", last_name="Thomas",
        )
        self.assertEqual(display_name(user), "Grace Thomas")

    def test_falls_back_to_email_as_a_last_resort(self):
        user = User.objects.create_user(email="nobody@dclm-bh.org", password="x", role=self.role)
        self.assertEqual(display_name(user), "nobody@dclm-bh.org")

    def test_handles_no_user_at_all(self):
        """The audit log passes None for system-generated actions."""
        self.assertIsNone(display_name(None))


class ClientIpTestCase(TestCase):
    """
    Working out the caller's address.

    Found in production on Azure: X-Forwarded-For there carries the source
    port, so the header read "102.91.5.47:152". Stored into a
    GenericIPAddressField on PostgreSQL, which is an inet column, that
    raised a DataError and turned every public registration and every
    login into a 500. It never appeared in development because SQLite
    stores the column as text and validates nothing.
    """
    def _request(self, forwarded=None, remote="127.0.0.1"):
        from django.test import RequestFactory
        req = RequestFactory().post("/")
        req.META["REMOTE_ADDR"] = remote
        if forwarded is not None:
            req.META["HTTP_X_FORWARDED_FOR"] = forwarded
        return req

    def test_azure_style_header_with_a_port(self):
        self.assertEqual(get_client_ip(self._request("102.91.5.47:152")), "102.91.5.47")

    def test_a_plain_address_is_unchanged(self):
        self.assertEqual(get_client_ip(self._request("102.91.5.47")), "102.91.5.47")

    def test_the_first_proxy_entry_is_used(self):
        self.assertEqual(
            get_client_ip(self._request("102.91.5.47:152, 10.0.0.1, 10.0.0.2")),
            "102.91.5.47")

    def test_bare_ipv6_is_not_mistaken_for_an_address_with_a_port(self):
        """IPv6 is full of colons. Stripping after the last one would
        quietly corrupt a valid address."""
        self.assertEqual(get_client_ip(self._request("2001:db8::1")), "2001:db8::1")

    def test_bracketed_ipv6_with_a_port(self):
        self.assertEqual(get_client_ip(self._request("[2001:db8::1]:443")), "2001:db8::1")

    def test_falls_back_to_remote_addr_when_there_is_no_header(self):
        self.assertEqual(get_client_ip(self._request(remote="10.1.2.3")), "10.1.2.3")

    def test_rubbish_never_takes_the_request_down(self):
        """Logging an imperfect address is a far smaller problem than
        refusing a visitor who is trying to register."""
        self.assertEqual(get_client_ip(self._request("not-an-address", remote="bad")), "0.0.0.0")

    def test_the_result_is_always_storable(self):
        import ipaddress
        for header in ["102.91.5.47:152", "2001:db8::1", "[2001:db8::1]:443",
                       "not-an-address", "", "10.0.0.1, 10.0.0.2"]:
            ip = get_client_ip(self._request(header))
            ipaddress.ip_address(ip)   # raises if it could not go in an inet column


class StaleRefreshTokenTestCase(APITestCase):
    """
    A refresh token naming a user who has since been deleted.

    Seen in production after the demo accounts were removed while a
    browser still held their token: the stock view let User.DoesNotExist
    escape and every page load logged a 500. An invalid token deserves a
    401, which the client already knows how to handle.
    """
    def test_a_token_for_a_deleted_user_gives_401_not_500(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        role = Role.objects.create(name="Temporary")
        user = User.objects.create_user(email="gone@t.com", password="x", role=role)
        token = str(RefreshToken.for_user(user))
        user.delete()

        resp = self.client.post("/api/auth/token/refresh/", {"refresh": token}, format="json")
        self.assertEqual(resp.status_code, 401)
        self.assertIn("sign in again", str(resp.data).lower())

    def test_a_valid_token_still_refreshes(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        role = Role.objects.create(name="Still here")
        user = User.objects.create_user(email="here@t.com", password="x", role=role)
        token = str(RefreshToken.for_user(user))

        resp = self.client.post("/api/auth/token/refresh/", {"refresh": token}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
