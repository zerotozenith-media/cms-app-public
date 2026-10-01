"""
A ready-made Follow-up role for the people who look after members and
newcomers (F6). A fresh installation had only Administrator and Location
Coordinator. Administrators can change it like any other role. If a role
with this name already exists it is left exactly as it is.

members edit is included because recording a member's follow-up visit
requires it.
"""
from django.db import migrations

PERMISSIONS = {
    "members": dict(can_view=True, can_edit=True),
    "newcomers": dict(can_view=True, can_create=True, can_edit=True),
    "attendance": dict(can_view=True),
    "reports": dict(can_view=True, can_create=True),
}


def create_role(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")
    if Role.objects.filter(name="Follow-up").exists():
        return
    role = Role.objects.create(name="Follow-up")
    for module, flags in PERMISSIONS.items():
        RolePermission.objects.create(role=role, module=module, **flags)


class Migration(migrations.Migration):

    dependencies = [("accounts", "0003_can_shepherd")]

    operations = [migrations.RunPython(create_role, migrations.RunPython.noop)]
