from django.db import migrations, models


def convert_approved_to_accepted(apps, schema_editor):
    SpecialistTestAttempt = apps.get_model("accounts", "SpecialistTestAttempt")
    SpecialistTestAttempt.objects.filter(status="APPROVED").update(status="ACCEPTED")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_alter_specialisttestattempt_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="specialisttestattempt",
            name="status",
            field=models.CharField(
                choices=[
                    ("SUBMITTED", "Submitted"),
                    ("ACCEPTED", "Accepted"),
                    ("REJECTED", "Rejected"),
                ],
                default="SUBMITTED",
                max_length=20,
            ),
        ),
        migrations.RunPython(convert_approved_to_accepted, migrations.RunPython.noop),
    ]
