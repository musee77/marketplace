from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0011_order_platform_fee_rate_order_referral_bonus_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="is_simulated",
            field=models.BooleanField(
                default=False,
                help_text="Marks demo data created by the seed command, not a real customer order.",
            ),
        ),
    ]
