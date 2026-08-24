import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BlogPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=200, unique=True)),
                ("excerpt", models.CharField(max_length=300)),
                ("content", models.TextField()),
                ("cover_image", models.ImageField(blank=True, null=True, upload_to="blog/")),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("PUBLISHED", "Published")], default="DRAFT", max_length=10)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("seo_title", models.CharField(blank=True, max_length=60)),
                ("seo_description", models.CharField(blank=True, max_length=160)),
                ("canonical_url", models.URLField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("author", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="blog_posts", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-published_at", "-created_at"],
                "indexes": [models.Index(fields=["status", "published_at"], name="blog_blogpo_status_6e95d4_idx")],
            },
        ),
    ]
