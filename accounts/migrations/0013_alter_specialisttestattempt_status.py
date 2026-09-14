from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_merge_20260911_1121"),
    ]

    operations = [
        migrations.AlterField(
            model_name="specialisttestattempt",
            name="status",
            field=models.CharField(
                choices=[
                    ("SUBMITTED", "Submitted"),
                    ("APPROVED", "Accepted"),
                    ("REJECTED", "Rejected"),
                ],
                default="SUBMITTED",
                max_length=20,
            ),
        ),
    ]
