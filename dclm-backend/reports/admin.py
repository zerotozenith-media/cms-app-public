from django.contrib import admin
from .models import Service, Department, Testimony, WeeklyNote, Report


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Testimony)
class TestimonyAdmin(admin.ModelAdmin):
    list_display = ("date", "service", "member_name", "is_anonymous")
    list_filter = ("service", "is_anonymous")
    date_hierarchy = "date"
    search_fields = ("member_name", "text")


@admin.register(WeeklyNote)
class WeeklyNoteAdmin(admin.ModelAdmin):
    list_display = ("department", "week_label", "week_start")
    list_filter = ("department",)
    date_hierarchy = "week_start"


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("period_month", "period_year", "generated_by", "generated_at")
    list_filter = ("period_year", "period_month")
    readonly_fields = ("generated_at",)
