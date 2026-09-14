from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_accepted_test_attempt_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="specialisttestattempt",
            name="attempt_number",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.RemoveConstraint(
            model_name="specialisttestattempt",
            name="one_attempt_per_specialist_test",
        ),
    ]
