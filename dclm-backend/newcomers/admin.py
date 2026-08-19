from django.contrib import admin
from .models import (
    NewcomerSource, MilestoneType, Newcomer, NewcomerStatusHistory,
    NewcomerMilestone, NewcomerTask, FollowUpUrgencySetting, PublicRegistrationAttempt,
)


@admin.register(NewcomerSource)
class NewcomerSourceAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(MilestoneType)
class MilestoneTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class NewcomerStatusHistoryInline(admin.TabularInline):
    model = NewcomerStatusHistory
    extra = 0


class NewcomerMilestoneInline(admin.TabularInline):
    model = NewcomerMilestone
    extra = 0
    autocomplete_fields = ("milestone_type",)


class NewcomerTaskInline(admin.TabularInline):
    model = NewcomerTask
    extra = 0
    autocomplete_fields = ("assigned_to",)


@admin.register(Newcomer)
class NewcomerAdmin(admin.ModelAdmin):
    list_display = ("name", "stage", "source", "assigned_to", "location", "stage_since", "is_first_timer", "is_new_resident")
    list_filter = ("stage", "location", "source", "gender", "age_group", "is_first_timer", "is_new_resident")
    search_fields = ("name", "phone", "email", "invited_by_name")
    autocomplete_fields = ("assigned_to", "location", "source", "meeting_attended", "invited_by_member")
    inlines = [NewcomerStatusHistoryInline, NewcomerMilestoneInline, NewcomerTaskInline]


@admin.register(FollowUpUrgencySetting)
class FollowUpUrgencySettingAdmin(admin.ModelAdmin):
    list_display = ("stage", "amber_days", "red_days")


@admin.register(PublicRegistrationAttempt)
class PublicRegistrationAttemptAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "ip_address", "successful", "reason")
    list_filter = ("successful", "reason")
    search_fields = ("ip_address",)
    date_hierarchy = "timestamp"
    readonly_fields = [f.name for f in PublicRegistrationAttempt._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
