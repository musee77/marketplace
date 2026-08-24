from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0002_rename_blog_blogpo_status_6e95d4_idx_blog_blogpo_status_aa5436_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlogCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, unique=True)),
                ("slug", models.SlugField(max_length=100, unique=True)),
            ],
            options={
                "ordering": ["name"],
                "verbose_name_plural": "Blog categories",
            },
        ),
        migrations.AddField(
            model_name="blogpost",
            name="category",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="posts", to="blog.blogcategory"),
        ),
    ]