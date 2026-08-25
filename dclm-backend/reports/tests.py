import datetime
import io

from django.test import TestCase
from pypdf import PdfReader
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import AuditLog, Role, RolePermission, User
from attendance.models import MeetingType, AttendanceSession
from core.models import Location
from finance.models import Fund, PaymentMethod, ExpenseCategory, Giving, Expense
from .models import Service, Department, Testimony, WeeklyNote, Report
from newcomers.models import Newcomer, NewcomerSource
from .pdf import gather_report_data, render_report_pdf


def pdf_text(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() for page in reader.pages)


class ReportDataGatheringTestCase(TestCase):
    """
    Tests the actual data-gathering logic precisely, via the Python dict
    it produces , this is the real business logic worth testing exactly;
    PDF generation itself is tested structurally + with real content
    extraction separately below.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.mt = MeetingType.objects.create(id="fri-worship", name="Friday Worship Service",
            day="Friday", frequency="weekly", detail_level="detailed", monthly_target=150)
        self.fund = Fund.objects.create(name="Tithe")
        self.method = PaymentMethod.objects.create(name="Cash")
        self.category = ExpenseCategory.objects.create(name="Rent")
        self.role = Role.objects.create(name="Administrator")
        self.user = User.objects.create_user(email="admin@test.com", password="x", role=self.role)

    def test_only_includes_data_within_the_requested_month(self):
        AttendanceSession.objects.create(meeting_type=self.mt, date=datetime.date(2026, 8, 7),
            location=self.bahrain, mode="in-person", status="filled", men=38, women=52)
        AttendanceSession.objects.create(meeting_type=self.mt, date=datetime.date(2026, 7, 10),
            location=self.bahrain, mode="in-person", status="filled", men=30, women=44)  # different month

        data = gather_report_data(2026, 8, "", self.user)
        self.assertEqual(data["fw_total"], 90)  # only August's session
        self.assertEqual(data["fw_session_count"], 1)

    def test_finance_totals_are_scoped_to_the_month(self):
        Giving.objects.create(date=datetime.date(2026, 8, 7), fund=self.fund, method=self.method,
            amount="850.000", location=self.bahrain)
        Giving.objects.create(date=datetime.date(2026, 9, 1), fund=self.fund, method=self.method,
            amount="500.000", location=self.bahrain)  # next month, must not count
        Expense.objects.create(date=datetime.date(2026, 8, 5), category=self.category,
            amount="600.000", location=self.bahrain)

        data = gather_report_data(2026, 8, "", self.user)
        self.assertEqual(data["income_total"], 850)
        self.assertEqual(data["expense_total"], 600)
        self.assertEqual(data["net_total"], 250)

    def test_other_additions_passed_through_verbatim(self):
        data = gather_report_data(2026, 8, "Building fund crossed a milestone.", self.user)
        self.assertEqual(data["other_additions"], "Building fund crossed a milestone.")


class ReportPDFGenerationTestCase(TestCase):
    """
    Tests the actual rendered PDF , structural validity AND real content
    extraction, so this proves the numbers genuinely end up in the file
    a person would open, not just in an intermediate Python dict.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.fund = Fund.objects.create(name="Tithe")
        self.method = PaymentMethod.objects.create(name="Cash")
        self.role = Role.objects.create(name="Administrator")
        self.user = User.objects.create_user(email="admin@test.com", password="x", role=self.role)
        Giving.objects.create(date=datetime.date(2026, 8, 7), fund=self.fund, method=self.method,
            amount="970.500", location=self.bahrain)

    def test_generates_a_structurally_valid_pdf(self):
        pdf_bytes = render_report_pdf(2026, 8, "", self.user)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"), "Output must be a real PDF, not just bytes.")
        self.assertGreater(len(pdf_bytes), 1000)

    def test_real_financial_figure_actually_appears_in_the_rendered_pdf(self):
        pdf_bytes = render_report_pdf(2026, 8, "", self.user)
        text = pdf_text(pdf_bytes)
        self.assertIn("970.5", text, "The real giving amount must actually appear in the rendered PDF text.")

    def test_other_additions_text_actually_appears_in_the_rendered_pdf(self):
        pdf_bytes = render_report_pdf(2026, 8, "A very specific unique testing phrase 8f3k2.", self.user)
        text = pdf_text(pdf_bytes)
        self.assertIn("A very specific unique testing phrase 8f3k2.", text)


class ReportAPITestCase(APITestCase):
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="reports",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.viewer_role = Role.objects.create(name="Viewer")
        RolePermission.objects.create(role=self.viewer_role, module="reports",
            can_view=True, can_create=False, can_edit=False, can_delete=False)
        self.admin = User.objects.create_user(email="admin@test.com", password="x", role=self.role)
        self.viewer = User.objects.create_user(email="viewer@test.com", password="x", role=self.viewer_role)

        self.fund = Fund.objects.create(name="Tithe")
        self.method = PaymentMethod.objects.create(name="Cash")
        Giving.objects.create(date=datetime.date(2026, 8, 7), fund=self.fund, method=self.method,
            amount="850.000", location=self.bahrain)

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_generate_creates_a_real_report_with_a_stored_pdf_file(self):
        self.auth(self.admin)
        resp = self.client.post("/api/reports/generate/", {"period_month": 8, "period_year": 2026})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        report = Report.objects.get(id=resp.data["id"])
        self.assertTrue(report.pdf_file.name)
        report.pdf_file.open("rb")
        content = report.pdf_file.read()
        report.pdf_file.close()
        self.assertTrue(content.startswith(b"%PDF"))

    def test_generating_the_same_period_twice_is_rejected(self):
        self.auth(self.admin)
        self.client.post("/api/reports/generate/", {"period_month": 8, "period_year": 2026})
        resp2 = self.client.post("/api/reports/generate/", {"period_month": 8, "period_year": 2026})
        self.assertEqual(resp2.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Report.objects.count(), 1)

    def test_viewer_cannot_generate_a_report(self):
        self.auth(self.viewer)
        resp = self.client.post("/api/reports/generate/", {"period_month": 8, "period_year": 2026})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_plain_post_to_reports_endpoint_is_rejected(self):
        """Reports must only be created via generate(), never a plain POST."""
        self.auth(self.admin)
        resp = self.client.post("/api/reports/", {"period_month": 8, "period_year": 2026})
        self.assertEqual(resp.status_code, 405)

    def test_generate_writes_audit_log(self):
        self.auth(self.admin)
        AuditLog.objects.all().delete()
        self.client.post("/api/reports/generate/", {"period_month": 8, "period_year": 2026})
        self.assertTrue(AuditLog.objects.filter(action="Generated", entity_type="Report").exists())

    def test_filter_reports_by_year(self):
        self.auth(self.admin)
        self.client.post("/api/reports/generate/", {"period_month": 8, "period_year": 2026})
        Giving.objects.create(date=datetime.date(2025, 3, 1), fund=self.fund, method=self.method,
            amount="1.000", location=self.bahrain)
        self.client.post("/api/reports/generate/", {"period_month": 3, "period_year": 2025})
        resp = self.client.get("/api/reports/?year=2025")
        self.assertEqual(len(resp.data["results"]), 1)


class TestimonyWeeklyNoteFilterTestCase(APITestCase):
    """
    Batch 3.9 finding: the frontend's service/department filter
    dropdowns were sending real query params that the backend silently
    ignored , caught while writing this batch's delivery notes, not by
    the frontend integration test, which only confirmed the dropdowns
    changed selection, not that they actually filtered anything.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.role = Role.objects.create(name="Administrator")
        RolePermission.objects.create(role=self.role, module="reports",
            can_view=True, can_create=True, can_edit=True, can_delete=True)
        self.admin = User.objects.create_user(email="admin3@test.com", password="x", role=self.role)
        self.friday = Service.objects.create(name="Friday Worship Service")
        self.monday = Service.objects.create(name="Monday Bible Study")
        self.followup = Department.objects.create(name="Follow-up / Care")
        self.ushering = Department.objects.create(name="Ushering")

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_filter_testimonies_by_service(self):
        Testimony.objects.create(member_name="A", is_anonymous=False, date=datetime.date.today(),
            service=self.friday, text="Testimony A")
        Testimony.objects.create(member_name="B", is_anonymous=False, date=datetime.date.today(),
            service=self.monday, text="Testimony B")
        self.auth(self.admin)
        resp = self.client.get(f"/api/testimonies/?service={self.friday.id}")
        results = resp.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "Testimony A")

    def test_filter_weekly_notes_by_department(self):
        WeeklyNote.objects.create(department=self.followup, week_label="Week 1", week_start=datetime.date.today(),
            highlights="", challenges="Need more volunteers", prayer_points="")
        WeeklyNote.objects.create(department=self.ushering, week_label="Week 1", week_start=datetime.date.today(),
            highlights="", challenges="Need more ushers", prayer_points="")
        self.auth(self.admin)
        resp = self.client.get(f"/api/weekly-notes/?department={self.ushering.id}")
        results = resp.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["challenges"], "Need more ushers")


class ReportSectionsTestCase(TestCase):
    """
    Covers the sections and behaviour added when the report moved from
    HTML to ReportLab: the newcomers section, the attendance trend, and
    the requirement that a sparse month still produces a usable report
    rather than failing.
    """
    def setUp(self):
        self.bahrain = Location.objects.create(id="bahrain", name="Bahrain", is_core=True)
        self.mt = MeetingType.objects.create(
            id="fri-worship", name="Friday Worship Service", day="Friday",
            frequency="weekly", detail_level="detailed")
        self.role = Role.objects.create(name="Administrator")
        self.user = User.objects.create_user(email="admin@test.com", password="x", role=self.role)

    def _session(self, day, men=10, women=15):
        return AttendanceSession.objects.create(
            meeting_type=self.mt, date=datetime.date(2026, 8, day), location=self.bahrain,
            mode="in-person", status="filled", men=men, women=women,
            youth_boys=2, youth_girls=3, children_boys=4, children_girls=1)

    def _newcomer(self, name, stage, source):
        return Newcomer.objects.create(
            name=name, source=source, location=self.bahrain, stage=stage,
            created_at=datetime.date(2026, 8, 10), stage_since=datetime.date(2026, 8, 10))

    # ---- new sections ----

    def test_newcomer_figures_are_gathered(self):
        source = NewcomerSource.objects.create(name="Invited by a member")
        self._newcomer("Contacted One", "contacted", source)
        self._newcomer("Visiting One", "visiting", source)
        self._newcomer("Untouched", "new", source)

        data = gather_report_data(2026, 8, "", self.user)
        self.assertEqual(data["newcomers_registered"], 3)
        self.assertEqual(data["newcomers_contacted"], 2, "Anyone past New counts as contacted")
        self.assertEqual(data["newcomers_visiting"], 1)

    def test_newcomers_are_broken_down_by_source(self):
        invited = NewcomerSource.objects.create(name="Invited by a member")
        website = NewcomerSource.objects.create(name="Church website")
        self._newcomer("A", "visiting", invited)
        self._newcomer("B", "new", invited)
        self._newcomer("C", "contacted", website)

        rows = {r["source"]: r for r in gather_report_data(2026, 8, "", self.user)["newcomer_rows"]}
        self.assertEqual(rows["Invited by a member"]["registered"], 2)
        self.assertEqual(rows["Invited by a member"]["returned"], 1)
        self.assertEqual(rows["Church website"]["contacted"], 1)

    def test_newcomers_outside_the_month_are_excluded(self):
        source = NewcomerSource.objects.create(name="Walk-in")
        Newcomer.objects.create(
            name="July Person", source=source, location=self.bahrain, stage="new",
            created_at=datetime.date(2026, 7, 20), stage_since=datetime.date(2026, 7, 20))
        self.assertEqual(gather_report_data(2026, 8, "", self.user)["newcomers_registered"], 0)

    def test_attendance_trend_follows_the_main_service_in_date_order(self):
        self._session(14, men=20)
        self._session(7, men=10)
        data = gather_report_data(2026, 8, "", self.user)
        self.assertEqual(len(data["trend_values"]), 2)
        self.assertLess(data["trend_values"][0], data["trend_values"][1],
                        "Earlier session must come first, not whatever order the DB returned")

    def test_average_is_rounded_not_truncated(self):
        self._session(7, men=10, women=10)    # 10+10+2+3+4+1 = 30
        self._session(14, men=11, women=10)   # 31
        data = gather_report_data(2026, 8, "", self.user)
        self.assertEqual(data["fw_total"], 61)
        self.assertEqual(data["fw_average"], 31, "30.5 should round, not truncate to 30")

    def test_attendance_rows_split_youth_and_children(self):
        self._session(7)
        row = gather_report_data(2026, 8, "", self.user)["attendance_rows"][0]
        self.assertEqual(row["youth"], 5, "Boys and girls combined into one youth figure")
        self.assertEqual(row["children"], 5)

    # ---- degrading gracefully ----

    def test_a_month_with_no_data_still_produces_a_valid_pdf(self):
        """Early months will be sparse. A report that fails on an empty
        month is worse than one that says there is nothing to report."""
        pdf = render_report_pdf(2019, 1, "", self.user)
        self.assertTrue(pdf.startswith(b"%PDF"))
        text = pdf_text(pdf)
        self.assertIn("No filled sessions recorded", text)
        self.assertIn("None recorded this period", text)

    def test_a_single_session_does_not_break_the_trend_chart(self):
        """A line chart needs two points. One session must not raise."""
        self._session(7)
        pdf = render_report_pdf(2026, 8, "", self.user)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_no_giving_does_not_break_the_charts(self):
        self._session(7)
        pdf = render_report_pdf(2026, 8, "", self.user)
        self.assertIn("No giving recorded this period", pdf_text(pdf))

    # ---- content actually reaches the page ----

    def test_headline_figures_appear_on_the_cover(self):
        self._session(7, men=10, women=10)
        pdf_bytes = render_report_pdf(2026, 8, "", self.user)
        first_page = PdfReader(io.BytesIO(pdf_bytes)).pages[0].extract_text()
        self.assertIn("MONTHLY REPORT", first_page)
        self.assertIn("AUGUST 2026", first_page)
        self.assertIn("THE MONTH AT A GLANCE", first_page,
                      "The cover carries the headline figures, not just a title")

    def test_every_numbered_section_is_present(self):
        text = pdf_text(render_report_pdf(2026, 8, "", self.user))
        for section in ["1. Executive Summary", "2. Attendance", "3. Finance",
                        "4. Newcomers and Follow-up", "5. Testimonies",
                        "6. Challenges", "7. Goals and Growth", "8. Conclusion"]:
            self.assertIn(section, text)
