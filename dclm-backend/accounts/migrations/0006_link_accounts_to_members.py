"""
Link each login account to its member record where the full name matches
exactly one member (accounts/linking.py). Accounts already linked, and
names that match nobody or more than one person, are left alone for an
administrator to choose in Admin, Users, Member record.
"""
from django.db import migrations


def link(apps, schema_editor):
    from accounts.linking import find_member
    User = apps.get_model("accounts", "User")
    Member = apps.get_model("members", "Member")
    for u in User.objects.filter(member__isnull=True).order_by("id"):
        m = find_member(u, Member, User)
        if m:
            u.member_id = m.id
            u.save(update_fields=["member"])


class Migration(migrations.Migration):

    dependencies = [("accounts", "0005_gender"), ("members", "0007_manual_followup_tasks")]

    operations = [migrations.RunPython(link, migrations.RunPython.noop)]
