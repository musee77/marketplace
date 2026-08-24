from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("service", "reviewer", "reviewee", "rating", "created_at")
    list_filter = ("rating",)
