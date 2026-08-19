from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    FundViewSet, PaymentMethodViewSet, ExpenseCategoryViewSet,
    ProjectViewSet, GivingViewSet, ExpenseViewSet, FinanceSummaryView,
)

router = DefaultRouter()
router.register("funds", FundViewSet, basename="fund")
router.register("payment-methods", PaymentMethodViewSet, basename="payment-method")
router.register("expense-categories", ExpenseCategoryViewSet, basename="expense-category")
router.register("projects", ProjectViewSet, basename="project")
router.register("giving", GivingViewSet, basename="giving")
router.register("expenses", ExpenseViewSet, basename="expense")

urlpatterns = router.urls + [
    path("finance/summary/", FinanceSummaryView.as_view(), name="finance-summary"),
]
