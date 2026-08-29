from django.contrib import admin
from .models import SearchKeyword, ContactMessage
from dataMarketplace.admin import custom_admin_site

@admin.register(SearchKeyword)
class SearchKeywordAdmin(admin.ModelAdmin):
    list_display = ("keyword", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("keyword",)

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "category", "status", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("name", "email", "subject", "message", "admin_notes")
    readonly_fields = ("created_at", "updated_at")

try:
    custom_admin_site.register(SearchKeyword, SearchKeywordAdmin)
    custom_admin_site.register(ContactMessage, ContactMessageAdmin)
except Exception:
    pass

