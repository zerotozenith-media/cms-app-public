import datetime
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User
from core.models import Location
from .models import Fund, PaymentMethod, ExpenseCategory, Project, Giving, Expense


class FinanceAPITestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.others = Location.objects.create(id="others", name="Others", note="Qatar")

        self.admin_role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.admin_role, module="finance",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.viewer_role = Role.objects.create(name="Viewer")
        RolePermission.objects.create(role=self.viewer_role, module="finance",
            can_view=True, can_create=False, can_edit=False, can_delete=False)

        self.admin = User.objects.create_user(email="admin@test.com", password="x", role=self.admin_role)
        self.coord = User.objects.create_user(email="coord@test.com", password="x",
            role=self.admin_role, location=self.bahrain)
        self.viewer = User.objects.create_user(email="viewer@test.com", password="x",
            role=self.viewer_role, location=self.bahrain)

        self.fund = Fund.objects.create(name="Building")
        self.method = PaymentMethod.objects.create(name="Online Transfer")
        self.category = ExpenseCategory.objects.create(name="Rent")

        self.project = Project.objects.create(
            id="qatar-building", name="Qatar Building Project", location=self.others,
            target_amount=Decimal("20000.000"), status="Active",
        )

    def auth(self, user):
        self.client.force_authenticate(user=user)

    # --- Permissions ---

    def test_viewer_cannot_record_giving(self):
        self.auth(self.viewer)
        resp = self.client.post("/api/giving/", {
            "date": "2026-08-07", "fund": self.fund.id, "method": self.method.id,
            "amount": "850.000", "location": "bahrain",
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # --- Location scoping ---

    def test_coordinator_only_sees_own_location_giving(self):
        Giving.objects.create(date=datetime.date.today(), fund=self.fund, method=self.method,
            amount=Decimal("100.000"), location=self.bahrain)
        Giving.objects.create(date=datetime.date.today(), fund=self.fund, method=self.method,
            amount=Decimal("200.000"), location=self.others)
        self.auth(self.coord)
        resp = self.client.get("/api/giving/")
        results = resp.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(Decimal(results[0]["amount"]), Decimal("100.000"))

    # --- Decimal precision (BHD uses 3 decimal places) ---

    def test_amount_preserves_three_decimal_places(self):
        self.auth(self.admin)
        resp = self.client.post("/api/giving/", {
            "date": "2026-08-07", "fund": self.fund.id, "method": self.method.id,
            "amount": "970.500", "location": "others", "project": "qatar-building",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(resp.data["amount"]), Decimal("970.500"))

    # --- Project amount_raised / amount_spent: live computation, not stale ---

    def test_amount_raised_reflects_newly_created_giving_immediately(self):
        self.auth(self.admin)
        resp0 = self.client.get(f"/api/projects/{self.project.id}/")
        self.assertEqual(Decimal(resp0.data["amount_raised"]), Decimal("0"))

        self.client.post("/api/giving/", {
            "date": "2026-08-07", "fund": self.fund.id, "method": self.method.id,
            "amount": "970.500", "location": "others", "project": "qatar-building",
        })
        self.client.post("/api/giving/", {
            "date": "2026-08-08", "fund": self.fund.id, "method": self.method.id,
            "amount": "500.000", "location": "others", "project": "qatar-building",
        })

        resp1 = self.client.get(f"/api/projects/{self.project.id}/")
        self.assertEqual(Decimal(resp1.data["amount_raised"]), Decimal("1470.500"),
            "amount_raised must reflect newly created Giving immediately, not a stale value.")

    def test_amount_spent_reflects_newly_created_expense_immediately(self):
        self.auth(self.admin)
        self.client.post("/api/expenses/", {
            "date": "2026-08-05", "category": self.category.id, "amount": "600.000",
            "location": "others", "description": "Materials", "project": "qatar-building",
        })
        resp = self.client.get(f"/api/projects/{self.project.id}/")
        self.assertEqual(Decimal(resp.data["amount_spent"]), Decimal("600.000"))

    def test_deleting_project_does_not_delete_giving_just_unlinks_it(self):
        g = Giving.objects.create(date=datetime.date.today(), fund=self.fund, method=self.method,
            amount=Decimal("100.000"), location=self.others, project=self.project)
        self.auth(self.admin)
        self.client.delete(f"/api/projects/{self.project.id}/")
        g.refresh_from_db()
        self.assertIsNone(g.project, "Deleting a project must SET_NULL on linked Giving, not cascade-delete it.")

    # --- Filtering ---

    def test_filter_giving_by_project(self):
        other_project = Project.objects.create(id="other-proj", name="Other", location=self.bahrain, target_amount=1000)
        Giving.objects.create(date=datetime.date.today(), fund=self.fund, method=self.method,
            amount=Decimal("100.000"), location=self.others, project=self.project)
        Giving.objects.create(date=datetime.date.today(), fund=self.fund, method=self.method,
            amount=Decimal("50.000"), location=self.bahrain, project=other_project)
        self.auth(self.admin)
        resp = self.client.get(f"/api/giving/?project={self.project.id}")
        self.assertEqual(len(resp.data["results"]), 1)

    def test_filter_expenses_by_category(self):
        other_cat = ExpenseCategory.objects.create(name="Utilities")
        Expense.objects.create(date=datetime.date.today(), category=self.category,
            amount=Decimal("600.000"), location=self.bahrain)
        Expense.objects.create(date=datetime.date.today(), category=other_cat,
            amount=Decimal("220.000"), location=self.bahrain)
        self.auth(self.admin)
        resp = self.client.get(f"/api/expenses/?category={other_cat.id}")
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(Decimal(resp.data["results"][0]["amount"]), Decimal("220.000"))

    # --- Audit logging ---

    def test_record_giving_writes_audit_log(self):
        self.auth(self.admin)
        AuditLog.objects.all().delete()
        self.client.post("/api/giving/", {
            "date": "2026-08-07", "fund": self.fund.id, "method": self.method.id,
            "amount": "850.000", "location": "bahrain",
        })
        entry = AuditLog.objects.filter(action="Recorded giving", entity_type="Giving")
        self.assertTrue(entry.exists())

    # --- Real file upload (Batch 2.8) ---

    def test_expense_receipt_file_can_actually_be_uploaded(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.auth(self.admin)
        receipt = SimpleUploadedFile(
            "receipt.txt", b"Utilities receipt content, Aug 2026, BHD 220",
            content_type="text/plain",
        )
        resp = self.client.post("/api/expenses/", {
            "date": "2026-08-04", "category": self.category.id, "amount": "220.000",
            "location": "bahrain", "description": "Electricity and water", "receipt_file": receipt,
        }, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["receipt_file"], "Response must include a real file reference.")

        expense = Expense.objects.get(id=resp.data["id"])
        expense.receipt_file.open("rb")
        content = expense.receipt_file.read()
        expense.receipt_file.close()
        self.assertEqual(content, b"Utilities receipt content, Aug 2026, BHD 220",
            "The actual uploaded content must be retrievable afterward, not just a filename recorded.")


class FinanceSummaryTestCase(APITestCase):
    """
    Batch 3.7: dedicated aggregation endpoint, same reasoning as
    Dashboard/Members/Attendance stats endpoints.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.others = Location.objects.create(id="others", name="Others", note="Qatar")

        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="finance",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin@test.com", password="x", is_superuser=True)
        self.coord = User.objects.create_user(email="coord@test.com", password="x",
            role=self.role, location=self.bahrain)

        self.tithe = Fund.objects.create(name="Tithe")
        self.missions = Fund.objects.create(name="Missions")  # deliberately never given to
        self.method = PaymentMethod.objects.create(name="Cash")
        self.rent = ExpenseCategory.objects.create(name="Rent")

        Giving.objects.create(date=datetime.date(2026, 8, 7), fund=self.tithe, method=self.method,
            amount=Decimal("850.000"), location=self.bahrain)
        Giving.objects.create(date=datetime.date(2026, 8, 7), fund=self.tithe, method=self.method,
            amount=Decimal("300.000"), location=self.others)
        Giving.objects.create(date=datetime.date(2026, 7, 1), fund=self.tithe, method=self.method,
            amount=Decimal("500.000"), location=self.bahrain)  # last month, must not count in "this month"
        Expense.objects.create(date=datetime.date(2026, 8, 5), category=self.rent,
            amount=Decimal("400.000"), location=self.bahrain)

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_admin_sees_totals_across_all_locations(self):
        self.auth(self.admin)
        resp = self.client.get("/api/finance/summary/")
        self.assertEqual(resp.data["income_total"], 1650.0)  # 850+300+500
        self.assertEqual(resp.data["expense_total"], 400.0)
        self.assertEqual(resp.data["net_total"], 1250.0)

    def test_coordinator_sees_only_their_location_totals(self):
        self.auth(self.coord)
        resp = self.client.get("/api/finance/summary/")
        self.assertEqual(resp.data["income_total"], 1350.0)  # 850+500, Bahrain only

    def test_income_this_month_excludes_prior_months_using_real_calendar_month(self):
        self.auth(self.admin)
        resp = self.client.get("/api/finance/summary/")
        self.assertEqual(resp.data["income_this_month"], 1150.0)  # 850+300, excludes the 500 from July

    def test_income_by_fund_includes_funds_with_zero_activity(self):
        """
        Missions has never received a gift , must still appear at BHD 0,
        not silently disappear, matching the original demo's intent of
        surfacing funds that haven't received anything yet.
        """
        self.auth(self.admin)
        resp = self.client.get("/api/finance/summary/")
        by_fund = {f["fund"]: f["total"] for f in resp.data["income_by_fund"]}
        self.assertEqual(by_fund["Tithe"], 1650.0)
        self.assertIn("Missions", by_fund)
        self.assertEqual(by_fund["Missions"], 0.0)

    def test_expenses_by_category_excludes_zero_activity_categories(self):
        """Expenses intentionally use the opposite rule from funds , only
        categories with real spending are shown, matching the demo."""
        ExpenseCategory.objects.create(name="Unused Category")
        self.auth(self.admin)
        resp = self.client.get("/api/finance/summary/")
        categories = [c["category"] for c in resp.data["expenses_by_category"]]
        self.assertIn("Rent", categories)
        self.assertNotIn("Unused Category", categories)

    def test_unauthenticated_denied(self):
        resp = self.client.get("/api/finance/summary/")
        self.assertEqual(resp.status_code, 401)


class GivingFilterTestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="finance",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin2@test.com", password="x", role=self.role)
        self.fund = Fund.objects.create(name="Tithe")
        self.cash = PaymentMethod.objects.create(name="Cash")
        self.online = PaymentMethod.objects.create(name="Online Transfer")

    def test_filter_giving_by_method(self):
        Giving.objects.create(date=datetime.date.today(), fund=self.fund, method=self.cash,
            amount=Decimal("100.000"), location=self.bahrain)
        Giving.objects.create(date=datetime.date.today(), fund=self.fund, method=self.online,
            amount=Decimal("200.000"), location=self.bahrain)
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(f"/api/giving/?method={self.online.id}")
        results = resp.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(Decimal(results[0]["amount"]), Decimal("200.000"))


class FinanceSummaryPermissionTestCase(APITestCase):
    """
    Phase 4.3 security review: finance_summary was a plain @api_view
    with only IsAuthenticated, meaning any logged-in user , regardless
    of their role's actual Finance permission , could see the Finance
    page's own detailed income/expense breakdown. Confirmed exploitable
    directly against a real Members-only user before the fix. Converted
    to a real class-based view specifically to reuse ModulePermission,
    the same enforcement every other endpoint in the app already uses.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.members_only_role = Role.objects.create(name="Members Only")
        RolePermission.objects.create(role=self.members_only_role, module="members",
            can_view=True, can_create=True, can_edit=False, can_delete=False)
        self.members_only_user = User.objects.create_user(
            email="members_only@test.com", password="x", role=self.members_only_role, location=self.bahrain,
        )
        self.finance_role = Role.objects.create(name="Finance Officer")
        RolePermission.objects.create(role=self.finance_role, module="finance",
            can_view=True, can_create=True, can_edit=True, can_delete=False)
        self.finance_user = User.objects.create_user(
            email="finance_user@test.com", password="x", role=self.finance_role, location=self.bahrain,
        )
        fund = Fund.objects.create(name="Tithe")
        method = PaymentMethod.objects.create(name="Cash")
        Giving.objects.create(date=datetime.date.today(), fund=fund, method=method,
            amount=Decimal("5000.000"), location=self.bahrain)

    def test_user_without_finance_permission_is_denied(self):
        self.client.force_authenticate(user=self.members_only_user)
        resp = self.client.get("/api/finance/summary/")
        self.assertEqual(resp.status_code, 403)

    def test_user_with_real_finance_permission_still_works(self):
        """The fix must not be overly broad , a genuinely authorized
        user must still get real, correct data."""
        self.client.force_authenticate(user=self.finance_user)
        resp = self.client.get("/api/finance/summary/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["income_total"], 5000.0)

    def test_unauthenticated_request_is_denied(self):
        resp = self.client.get("/api/finance/summary/")
        self.assertIn(resp.status_code, (401, 403))
