from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_specialist_tests"),
    ]

    operations = [
        migrations.AddField(
            model_name="specialisttestattempt",
            name="responses",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
