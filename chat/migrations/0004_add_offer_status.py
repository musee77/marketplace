# Generated migration for adding offer_status field to Message model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_message_message_type_message_offer_delivery_days_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='offer_status',
            field=models.CharField(
                choices=[('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('DECLINED', 'Declined')],
                default='PENDING',
                max_length=20
            ),
        ),
    ]
