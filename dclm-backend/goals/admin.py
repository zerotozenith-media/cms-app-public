from django.contrib import admin
from .models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("name", "horizon", "tracking", "period_type", "target", "current", "unit")
    list_filter = ("horizon", "tracking", "period_type")
    search_fields = ("name", "source")
