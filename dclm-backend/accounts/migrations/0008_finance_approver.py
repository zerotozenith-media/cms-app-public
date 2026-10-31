"""The Finance Approver role and the Approve month-end permission (Kay, 30
October 2026). The person who approves a month is never the person who
prepared it. Administrators get the permission too; any role can be given
it in Admin, Roles & Permissions."""
from django.db import migrations


def approver_role(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Perm = apps.get_model("accounts", "RolePermission")
    role, _ = Role.objects.get_or_create(name="Finance Approver")
    for module in ("finance", "reports"):
        Perm.objects.get_or_create(role=role, module=module,
                                   defaults=dict(can_view=True, can_create=False, can_edit=False, can_delete=False))
    Perm.objects.update_or_create(role=role, module="monthend",
                                  defaults=dict(can_view=True, can_create=False, can_edit=True, can_delete=False))
    for admin in Role.objects.filter(name="Administrator"):
        Perm.objects.update_or_create(role=admin, module="monthend",
                                      defaults=dict(can_view=True, can_create=True, can_edit=True, can_delete=True))


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_followup_coordinator"),
    ]

    operations = [
        migrations.RunPython(approver_role, migrations.RunPython.noop),
    ]
