"""
Give back the shepherd that members who came through the newcomer pipeline
lost when they joined. Joining used to leave them with nobody. Only members
with no shepherd now are touched.
"""
from django.db import migrations


def restore(apps, schema_editor):
    Member = apps.get_model("members", "Member")
    User = apps.get_model("accounts", "User")
    for m in Member.objects.filter(assigned_to__isnull=True, from_newcomer__isnull=False,
                                   from_newcomer__assigned_to__isnull=False).select_related("from_newcomer"):
        # Only a shepherd who can shepherd members there: an active account
        # of a Worker at the member's location.
        ok = User.objects.filter(id=m.from_newcomer.assigned_to_id, is_active=True,
                                 member__category="Worker", member__location_id=m.location_id).exists()
        if ok:
            m.assigned_to_id = m.from_newcomer.assigned_to_id
            m.save(update_fields=["assigned_to"])


class Migration(migrations.Migration):

    dependencies = [("members", "0005_blank_phones_to_null"), ("newcomers", "0005_rename_stage_values"),
                    ("accounts", "0001_initial")]

    operations = [migrations.RunPython(restore, migrations.RunPython.noop)]
