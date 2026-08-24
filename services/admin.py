from django.contrib import admin
from .models import Category, Service


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "specialist", "category", "price", "is_active", "created_at")
    list_filter = ("is_active", "category")
    search_fields = ("title", "specialist__username")
    prepopulated_fields = {"slug": ("title",)}
