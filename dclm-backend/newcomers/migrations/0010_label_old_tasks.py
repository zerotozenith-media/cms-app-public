"""Labels tasks made before version 11.14. Kept apart from 0007, because on
PostgreSQL a data update in the same migration as new foreign keys stops
their indexes being made ("pending trigger events"). Running it again
changes nothing."""
from django.db import migrations


def label_old_tasks(apps, schema_editor):
    """The three tasks made from the welcome form are first-visit tasks; a
    done task with an outcome was a person reached. An attempt's time is
    taken as midday on its date."""
    import datetime
    from django.utils import timezone
    T = apps.get_model("newcomers", "NewcomerTask")
    T.objects.filter(text__in=["Schedule a home visit", "Share more about the church",
                               "Have a salvation conversation"]).update(kind="first-visit")
    T.objects.filter(done=True, result="").update(result="reached")
    A = apps.get_model("newcomers", "NewcomerContactAttempt")
    for a in A.objects.all():
        # Older attempts were given the time the field was added, which is
        # not their own day. Attempts with a real time are left alone.
        if timezone.localdate(a.at) == a.date:
            continue
        a.at = timezone.make_aware(datetime.datetime.combine(a.date, datetime.time(12, 0)))
        a.save(update_fields=["at"])


class Migration(migrations.Migration):

    dependencies = [
        ("newcomers", "0009_registration_per_phone"),
    ]

    operations = [
        migrations.RunPython(label_old_tasks, migrations.RunPython.noop),
    ]
