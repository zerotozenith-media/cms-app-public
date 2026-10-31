from django.urls import path
from rest_framework.routers import DefaultRouter

from .remittance_api import RemittanceViewSet
from .monthend_api import (MoneySettingsView, MonthEndApproveView, MonthEndReopenView, MonthEndSendBackView,
                           MonthEndSendView, MonthEndView)
from .views import (
    FundViewSet, PaymentMethodViewSet, ExpenseCategoryViewSet,
    ProjectViewSet, GivingViewSet, ExpenseViewSet, FinanceSummaryView,
)

router = DefaultRouter()
router.register("funds", FundViewSet, basename="fund")
router.register(r"remittances", RemittanceViewSet, basename="remittance")
router.register("payment-methods", PaymentMethodViewSet, basename="payment-method")
router.register("expense-categories", ExpenseCategoryViewSet, basename="expense-category")
router.register("projects", ProjectViewSet, basename="project")
router.register("giving", GivingViewSet, basename="giving")
router.register("expenses", ExpenseViewSet, basename="expense")

urlpatterns = router.urls + [
    path("finance/summary/", FinanceSummaryView.as_view(), name="finance-summary"),
    path("month-end/", MonthEndView.as_view(), name="month-end"),
    path("month-end/send/", MonthEndSendView.as_view(), name="month-end-send"),
    path("month-end/approve/", MonthEndApproveView.as_view(), name="month-end-approve"),
    path("month-end/send-back/", MonthEndSendBackView.as_view(), name="month-end-send-back"),
    path("month-end/reopen/", MonthEndReopenView.as_view(), name="month-end-reopen"),
    path("money-settings/", MoneySettingsView.as_view(), name="money-settings"),
]
