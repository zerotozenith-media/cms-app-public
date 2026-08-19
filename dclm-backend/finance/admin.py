from django.contrib import admin
from .models import Fund, PaymentMethod, ExpenseCategory, Project, Giving, Expense


@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "target_amount", "amount_raised", "status", "target_date")
    list_filter = ("status", "location")
    search_fields = ("name", "id", "description")
    autocomplete_fields = ("location",)


@admin.register(Giving)
class GivingAdmin(admin.ModelAdmin):
    list_display = ("date", "fund", "method", "amount", "location", "project", "member")
    list_filter = ("fund", "method", "location", "project")
    date_hierarchy = "date"
    autocomplete_fields = ("location", "project", "member")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("date", "category", "amount", "location", "project")
    list_filter = ("category", "location", "project")
    date_hierarchy = "date"
    autocomplete_fields = ("location", "project")
