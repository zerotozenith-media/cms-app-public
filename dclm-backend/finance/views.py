from django.db.models import Sum
from django.utils import timezone
from rest_framework import viewsets, filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import log_audit
from accounts.permissions import ModulePermission, LocationScopedQuerySetMixin
from .models import Fund, PaymentMethod, ExpenseCategory, Project, Giving, Expense
from .serializers import (
    FundSerializer, PaymentMethodSerializer, ExpenseCategorySerializer,
    ProjectSerializer, GivingSerializer, ExpenseSerializer,
)


class FundViewSet(viewsets.ModelViewSet):
    module = "finance"
    permission_classes = [ModulePermission]
    queryset = Fund.objects.all()
    serializer_class = FundSerializer


class PaymentMethodViewSet(viewsets.ModelViewSet):
    module = "finance"
    permission_classes = [ModulePermission]
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    module = "finance"
    permission_classes = [ModulePermission]
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer


class ProjectViewSet(LocationScopedQuerySetMixin, viewsets.ModelViewSet):
    module = "finance"
    permission_classes = [ModulePermission]
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(self.request.user, "Created", "Project", instance.name, instance=instance)

    def perform_destroy(self, instance):
        name = instance.name
        log_audit(self.request.user, "Deleted", "Project", name)
        instance.delete()


class GivingViewSet(LocationScopedQuerySetMixin, viewsets.ModelViewSet):
    module = "finance"
    permission_classes = [ModulePermission]
    queryset = Giving.objects.select_related("fund", "method", "location", "project", "member")
    serializer_class = GivingSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["date", "amount"]

    def get_queryset(self):
        qs = super().get_queryset()
        project = self.request.query_params.get("project")
        fund = self.request.query_params.get("fund")
        method = self.request.query_params.get("method")
        if project:
            qs = qs.filter(project_id=project)
        if fund:
            qs = qs.filter(fund_id=fund)
        if method:
            qs = qs.filter(method_id=method)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            self.request.user, "Recorded giving", "Giving",
            f"{instance.fund.name} , {instance.amount}", instance=instance,
        )

    def perform_destroy(self, instance):
        name = f"{instance.fund.name} , {instance.amount}"
        log_audit(self.request.user, "Deleted", "Giving", name)
        instance.delete()


class ExpenseViewSet(LocationScopedQuerySetMixin, viewsets.ModelViewSet):
    module = "finance"
    permission_classes = [ModulePermission]
    queryset = Expense.objects.select_related("category", "location", "project")
    serializer_class = ExpenseSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["date", "amount"]

    def get_queryset(self):
        qs = super().get_queryset()
        project = self.request.query_params.get("project")
        category = self.request.query_params.get("category")
        if project:
            qs = qs.filter(project_id=project)
        if category:
            qs = qs.filter(category_id=category)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            self.request.user, "Recorded expense", "Expense",
            f"{instance.category.name} , {instance.amount}", instance=instance,
        )

    def perform_destroy(self, instance):
        name = f"{instance.category.name} , {instance.amount}"
        log_audit(self.request.user, "Deleted", "Expense", name)
        instance.delete()


def _location_filter(queryset, user):
    if user.is_superuser or not user.location_id:
        return queryset
    return queryset.filter(location_id=user.location_id)


class FinanceSummaryView(APIView):
    """
    Batch 3.7: a dedicated aggregation endpoint, same reasoning as the
    Dashboard (Batch 3.3), Members (3.4), and Attendance (3.5) stats
    endpoints , Giving and Expense records accumulate indefinitely, so
    "income all-time" and "by fund/category" breakdowns need real
    database aggregation, not a client-side sum of one paginated page.

    Phase 4.3 security review fix: this was a plain @api_view with only
    IsAuthenticated , meaning any logged-in user could see the Finance
    page's own detailed breakdown regardless of their role's actual
    Finance permission. Confirmed exploitable directly: a Location
    Coordinator with Members-only access could hit this endpoint and see
    real income totals and giving-by-fund data. Converted to a real
    class-based view specifically so it can reuse ModulePermission
    unchanged , the same, already-tested enforcement every ViewSet in
    the app uses , rather than write new permission logic to check by hand.
    """
    module = "finance"
    permission_classes = [ModulePermission]

    def get(self, request):
        user = request.user
        giving_qs = _location_filter(Giving.objects.all(), user)
        expense_qs = _location_filter(Expense.objects.all(), user)

        today = timezone.localdate()
        income_this_month = giving_qs.filter(
            date__year=today.year, date__month=today.month,
        ).aggregate(t=Sum("amount"))["t"] or 0

        income_total = giving_qs.aggregate(t=Sum("amount"))["t"] or 0
        expense_total = expense_qs.aggregate(t=Sum("amount"))["t"] or 0

        # Iterates every Fund explicitly (not a GROUP BY on Giving), so a
        # fund with zero activity still shows as BHD 0 rather than silently
        # disappearing , matching the demo's original intent of surfacing
        # funds that haven't received anything yet, not just ones that have.
        by_fund = [
            {"fund": f.name, "total": float(giving_qs.filter(fund=f).aggregate(t=Sum("amount"))["t"] or 0)}
            for f in Fund.objects.all().order_by("name")
        ]
        by_category = [
            {"category": row["category__name"], "total": float(row["total"])}
            for row in expense_qs.values("category__name").annotate(total=Sum("amount")).order_by("-total")
            if row["total"]
        ]

        return Response({
            "income_total": float(income_total),
            "income_this_month": float(income_this_month),
            "expense_total": float(expense_total),
            "net_total": float(income_total) - float(expense_total),
            "income_by_fund": by_fund,
            "expenses_by_category": by_category,
        })
