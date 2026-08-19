from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import Role, RolePermission, User, AuditLog, LoginAttempt


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [RolePermissionInline]


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    Django's built-in UserAdmin assumes a `username` field throughout ,
    fieldsets, add_fieldsets, ordering, ModelAdmin.list_display all
    reference it by default. Every one of those is overridden below for
    the email-based custom User model, not just list_display, otherwise
    the admin's own "add user" form breaks (same category of bug as the
    UserManager issue caught in Batch 1.2).
    """
    model = User
    ordering = ("email",)
    list_display = ("email", "get_full_name", "role", "location", "is_active", "is_staff")
    list_filter = ("role", "location", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "member")}),
        ("DCLM access", {"fields": ("role", "location")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "role", "location", "is_staff", "is_active"),
        }),
    )
    autocomplete_fields = ("location", "member")

    @admin.display(description="Name")
    def get_full_name(self, obj):
        return obj.get_full_name() or ","


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user_name_snapshot", "action", "entity_type", "entity_name")
    list_filter = ("entity_type", "action")
    search_fields = ("user_name_snapshot", "entity_name", "details")
    date_hierarchy = "timestamp"
    readonly_fields = [f.name for f in AuditLog._meta.fields]  # audit trail , never manually edited

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "email_attempted", "ip_address", "successful", "reason")
    list_filter = ("successful", "reason")
    search_fields = ("email_attempted", "ip_address")
    date_hierarchy = "timestamp"
    readonly_fields = [f.name for f in LoginAttempt._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
