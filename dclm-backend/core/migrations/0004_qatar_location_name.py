"""
Name the Qatar location Qatar.

Version 10 called it "Others", with "Qatar" only in its note, so every
screen, report and QR code for Qatar said "Others". Only the location
still called exactly "Others" with the short code "others" is renamed,
and a note that merely repeated "Qatar" is tidied. It can be renamed
again at any time in Admin, Config Lists.
"""
from django.db import migrations


OLD_NOTES = ("qatar, supporting location", "qatar , supporting location", "qatar")


def to_qatar(apps, schema_editor):
    Location = apps.get_model("core", "Location")
    for loc in Location.objects.filter(id="others", name__iexact="Others"):
        loc.name = "Qatar"
        if (loc.note or "").strip().lower() in OLD_NOTES:
            loc.note = "Supporting location"
        loc.save(update_fields=["name", "note"])


def back_to_others(apps, schema_editor):
    Location = apps.get_model("core", "Location")
    for loc in Location.objects.filter(id="others", name="Qatar"):
        loc.name = "Others"
        if loc.note == "Supporting location":
            loc.note = "Qatar, supporting location"
        loc.save(update_fields=["name", "note"])


class Migration(migrations.Migration):

    dependencies = [("core", "0003_main_location_bahrain_hq")]

    operations = [migrations.RunPython(to_qatar, back_to_others)]
