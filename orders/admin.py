from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Order, Offer, OrderDocument


class OrderDocumentInline(admin.TabularInline):
    model = OrderDocument
    extra = 1
    fields = ("title", "file", "download_link", "uploaded_by", "created_at")
    readonly_fields = ("uploaded_by", "created_at")

    @admin.display(description="Download")
    def download_link(self, obj):
        if not obj.pk or not obj.file:
            return "-"
        url = reverse("orders:document_download", kwargs={"pk": obj.pk})
        return format_html('<a href="{}" target="_blank">Download</a>', url)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "service", "client", "specialist", "price", "platform_fee", "platform_fee_rate", "referrer", "referral_bonus", "status", "is_paid", "created_at")
    list_filter = ("status", "is_paid", "platform_fee_rate")
    search_fields = ("service__title", "client__username", "specialist__username", "referrer__username")
    inlines = [OrderDocumentInline]


@admin.register(OrderDocument)
class OrderDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "uploaded_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "order__id", "uploaded_by__username")
    readonly_fields = ("created_at",)


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "specialist", "client", "price", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "specialist__username", "client__username", "description")
    readonly_fields = ("created_at", "updated_at", "order")
    fieldsets = (
        ("Offer Details", {"fields": ("title", "description", "price", "delivery_days")}),
        ("Participants", {"fields": ("specialist", "client")}),
        ("Status & Tracking", {"fields": ("status", "order", "expires_at")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
