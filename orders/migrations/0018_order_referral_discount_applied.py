from django.db import migrations, models


def preserve_existing_order_prices(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Order.objects.all().update(referral_discount_applied=True)


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0017_merge_20260908_1349"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="referral_discount_applied",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(preserve_existing_order_prices, migrations.RunPython.noop),
    ]