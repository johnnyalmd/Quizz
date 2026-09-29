from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("study", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="attempt",
            name="total",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attempt",
            name="results",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
