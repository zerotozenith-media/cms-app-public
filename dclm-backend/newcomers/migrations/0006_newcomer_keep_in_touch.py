from django.db import migrations, models


class Migration(migrations.Migration):
    """F19: the "Keep in touch" tick. Newcomers already recorded were never
    asked, so they start unticked. New ones are ticked by default."""

    dependencies = [("newcomers", "0005_rename_stage_values")]

    operations = [
        migrations.AddField(model_name="newcomer", name="keep_in_touch", field=models.BooleanField(default=False)),
        migrations.AlterField(model_name="newcomer", name="keep_in_touch", field=models.BooleanField(default=True)),
    ]
