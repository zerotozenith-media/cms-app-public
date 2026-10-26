"""Labels tasks made before version 11.14. Kept apart from 0008, because on
PostgreSQL a data update in the same migration as new foreign keys stops
their indexes being made ("pending trigger events")."""
from django.db import migrations


def label_old_tasks(apps, schema_editor):
    """Tasks made before 26 October 2026: absence tasks are the ones about a
    missed service, and a done task with an outcome was a person reached."""
    T = apps.get_model("members", "MemberFollowUpTask")
    T.objects.exclude(missed_meeting_name="").update(kind="absence")
    T.objects.filter(missed_session__isnull=False).update(kind="absence")
    T.objects.filter(done=True, result="").update(result="reached")


class Migration(migrations.Migration):

    dependencies = [
        ("members", "0009_alert_marks"),
    ]

    operations = [
        migrations.RunPython(label_old_tasks, migrations.RunPython.noop),
    ]
