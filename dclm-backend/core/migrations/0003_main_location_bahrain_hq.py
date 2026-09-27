"""
Name the main location Bahrain HQ.

Bahrain is the country, and further locations in Bahrain may follow, so
the main one is called Bahrain HQ. Only a main location still called
exactly "Bahrain" is renamed; a name somebody has already chosen is left
alone. It can be renamed again at any time in Admin, Config Lists.
"""
from django.db import migrations


def to_bahrain_hq(apps, schema_editor):
    Location = apps.get_model("core", "Location")
    Location.objects.filter(is_core=True, name__iexact="Bahrain").update(name="Bahrain HQ")


def back_to_bahrain(apps, schema_editor):
    Location = apps.get_model("core", "Location")
    Location.objects.filter(is_core=True, name="Bahrain HQ").update(name="Bahrain")


class Migration(migrations.Migration):

    dependencies = [("core", "0002_appsetting")]

    operations = [migrations.RunPython(to_bahrain_hq, back_to_bahrain)]
