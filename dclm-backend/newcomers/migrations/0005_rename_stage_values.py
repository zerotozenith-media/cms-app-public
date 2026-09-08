"""
Rename the stage values on existing records.

The choices changed in the previous migration, but rows already in the
database still hold "visiting" and "integrated". Without this they would
sit in a stage the pipeline no longer has a column for, so those people
would simply vanish from the board.
"""
from django.db import migrations


def rename_forwards(apps, schema_editor):
    Newcomer = apps.get_model("newcomers", "Newcomer")
    History = apps.get_model("newcomers", "NewcomerStatusHistory")
    for model in (Newcomer, History):
        model.objects.filter(stage="visiting").update(stage="attending")
        model.objects.filter(stage="integrated").update(stage="member")


def rename_backwards(apps, schema_editor):
    Newcomer = apps.get_model("newcomers", "Newcomer")
    History = apps.get_model("newcomers", "NewcomerStatusHistory")
    for model in (Newcomer, History):
        model.objects.filter(stage="attending").update(stage="visiting")
        model.objects.filter(stage="member").update(stage="integrated")


class Migration(migrations.Migration):
    dependencies = [("newcomers", "0004_alter_followupurgencysetting_stage_and_more")]
    operations = [migrations.RunPython(rename_forwards, rename_backwards)]
