from django.contrib import admin
from .models import MeetingType, AttendanceSession, AttendanceSessionMember


@admin.register(MeetingType)
class MeetingTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "day", "frequency", "detail_level", "monthly_target")
    list_filter = ("frequency", "detail_level")
    search_fields = ("name", "id")


class AttendanceSessionMemberInline(admin.TabularInline):
    model = AttendanceSessionMember
    extra = 0
    autocomplete_fields = ("member",)


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("meeting_type", "date", "location", "mode", "status", "total")
    list_filter = ("status", "mode", "location", "meeting_type")
    date_hierarchy = "date"
    autocomplete_fields = ("location",)
    inlines = [AttendanceSessionMemberInline]
