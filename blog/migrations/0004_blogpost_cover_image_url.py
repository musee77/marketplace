from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0003_blogpost_category_blogcategory"),
    ]

    operations = [
        migrations.AddField(
            model_name="blogpost",
            name="cover_image_url",
            field=models.URLField(blank=True, help_text="Optional external cover image URL."),
        ),
    ]