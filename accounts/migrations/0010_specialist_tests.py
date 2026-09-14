from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0009_alter_clientprofile_default_payment_method_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SpecialistTest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="SpecialistTestQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("prompt", models.TextField()),
                ("option_a", models.CharField(max_length=500)),
                ("option_b", models.CharField(max_length=500)),
                ("option_c", models.CharField(max_length=500)),
                ("option_d", models.CharField(max_length=500)),
                ("correct_option", models.CharField(choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")], max_length=1)),
                ("order", models.PositiveIntegerField(default=0)),
                ("test", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="accounts.specialisttest")),
            ],
            options={"ordering": ["order", "pk"]},
        ),
        migrations.CreateModel(
            name="SpecialistTestAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.PositiveIntegerField(default=0)),
                ("total_questions", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(choices=[("SUBMITTED", "Submitted"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], default="SUBMITTED", max_length=20)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_test_attempts", to="accounts.user")),
                ("specialist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="test_attempts", to="accounts.user")),
                ("test", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="accounts.specialisttest")),
            ],
            options={"ordering": ["-submitted_at"]},
        ),
        migrations.AddConstraint(
            model_name="specialisttestattempt",
            constraint=models.UniqueConstraint(fields=("specialist", "test"), name="one_attempt_per_specialist_test"),
        ),
    ]
