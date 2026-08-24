from django.contrib import admin

from .models import SearchKeyword
from dataMarketplace.admin import custom_admin_site

class SearchKeywordAdmin(admin.ModelAdmin):
    list_display = ("keyword", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("keyword",)

try:
    custom_admin_site.register(SearchKeyword, SearchKeywordAdmin)
except Exception:
    pass
