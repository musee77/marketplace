from django.contrib import admin

from .models import BlogCategory, BlogPost


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "author", "published_at", "updated_at")
    list_filter = ("status", "category", "published_at")
    search_fields = ("title", "excerpt", "content", "seo_title")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
    fieldsets = (
        (None, {"fields": ("title", "slug", "category", "author", "excerpt", "content", "cover_image")}),
        ("Publishing", {"fields": ("status",)}),
        ("SEO", {"fields": ("seo_title", "seo_description", "canonical_url")}),
    )
