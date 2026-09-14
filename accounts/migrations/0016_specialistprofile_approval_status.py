from django.db import migrations, models


def initialize_approval_status(apps, schema_editor):
    SpecialistProfile = apps.get_model("accounts", "SpecialistProfile")
    SpecialistProfile.objects.filter(is_approved=True).update(approval_status="APPROVED")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0015_specialisttestattempt_retake_history"),
    ]

    operations = [
        migrations.AddField(
            model_name="specialistprofile",
            name="approval_status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("APPROVED", "Approved"),
                    ("REJECTED", "Rejected"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
        migrations.RunPython(initialize_approval_status, migrations.RunPython.noop),
    ]