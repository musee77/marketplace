from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0018_order_referral_discount_applied"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="editor_approved",
            field=models.BooleanField(default=False, help_text="An editor must review this order before delivery"),
        ),
        migrations.AddField(
            model_name="order",
            name="edited_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="edited_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="edited_orders", to=settings.AUTH_USER_MODEL),
        ),
    ]