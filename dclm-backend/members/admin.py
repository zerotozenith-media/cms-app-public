from django.contrib import admin
from .models import Household, Member, MemberCategoryHistory


class MemberInline(admin.TabularInline):
    model = Member
    extra = 0
    fields = ("first_name", "surname", "category", "location")
    show_change_link = True


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "phone")
    search_fields = ("name", "address", "phone")
    inlines = [MemberInline]


class MemberCategoryHistoryInline(admin.TabularInline):
    model = MemberCategoryHistory
    extra = 0
    # Corrections are allowed (Batch 0.1, Finding 4) by Admin/Coordinator ,
    # not read-only, editable directly here.


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "category", "location", "household", "joined_date", "phone")
    list_filter = ("category", "location", "gender", "household")
    search_fields = ("surname", "first_name", "other_names", "email", "phone")
    autocomplete_fields = ("household", "location")
    inlines = [MemberCategoryHistoryInline]
    ordering = ("surname", "first_name")
