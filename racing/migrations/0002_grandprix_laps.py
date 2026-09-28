from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("racing", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="grandprix",
            name="laps",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                verbose_name="Круги",
            ),
        ),
    ]
