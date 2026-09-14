from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_specialist_tests"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("CLIENT", "Client"),
                    ("SPECIALIST", "Specialist"),
                    ("EDITOR", "Editor"),
                    ("MANAGER", "Manager"),
                ],
                default="CLIENT",
                max_length=20,
            ),
        ),
    ]