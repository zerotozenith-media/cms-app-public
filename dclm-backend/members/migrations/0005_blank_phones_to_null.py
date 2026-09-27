"""
Store a member's missing phone number as nothing, not as an empty string.

Phone numbers are unique on the member roll. An empty string counted as a
number, so once one member had been added without a phone, adding a
second one without a phone failed with a server error. The model now
stores a blank as nothing. This converts any already saved the old way.
"""
from django.db import migrations


def blanks_to_null(apps, schema_editor):
    Member = apps.get_model("members", "Member")
    for m in Member.objects.filter(phone__isnull=False):
        cleaned = (m.phone or "").strip()
        if not cleaned:
            Member.objects.filter(pk=m.pk).update(phone=None)
        elif cleaned != m.phone:
            # Only tidy the spacing when that does not collide with
            # somebody else's number.
            if not Member.objects.filter(phone=cleaned).exclude(pk=m.pk).exists():
                Member.objects.filter(pk=m.pk).update(phone=cleaned)


class Migration(migrations.Migration):

    dependencies = [
        ("members", "0004_member_from_newcomer_member_is_leader"),
    ]

    operations = [
        migrations.RunPython(blanks_to_null, migrations.RunPython.noop),
    ]
