from django.contrib import admin
from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "note", "is_core")
    list_filter = ("is_core",)
    search_fields = ("name", "id", "note")
