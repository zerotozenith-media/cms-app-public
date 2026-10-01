"""
Shepherding becomes a tick on the account ("Can shepherd others") instead of
following the Worker member category. Everyone who could shepherd before, an
active account linked to a Worker, starts ticked, so nothing changes until an
administrator changes it.
"""
from django.db import migrations, models


def tick_current_shepherds(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_active=True, member__isnull=False,
                        member__category="Worker").update(can_shepherd=True)


class Migration(migrations.Migration):

    dependencies = [("accounts", "0002_profile_phone_and_photo"), ("members", "0006_restore_shepherds_from_newcomers")]

    operations = [
        migrations.AddField(model_name="user", name="can_shepherd", field=models.BooleanField(default=False)),
        migrations.RunPython(tick_current_shepherds, migrations.RunPython.noop),
    ]
