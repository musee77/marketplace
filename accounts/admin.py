from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, SpecialistProfile, ClientProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "referral_code", "referred_by", "referral_count", "is_suspended", "date_created")
    list_filter = ("role", "is_suspended", "is_staff")
    search_fields = ("username", "email", "referral_code")
    fieldsets = UserAdmin.fieldsets + (
        ("Marketplace", {"fields": ("role", "phone", "avatar", "is_suspended")}),
        ("Referral Program", {"fields": ("referral_code", "referred_by")}),
    )


from django.utils.html import format_html
from django.urls import reverse


@admin.register(SpecialistProfile)
class SpecialistProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "headline", "hourly_rate", "is_approved", "is_verified", "is_available", "quick_actions")
    list_filter = ("is_approved", "is_verified", "is_available")
    list_editable = ("is_approved", "is_verified")
    search_fields = ("user__username", "headline", "skills")
    actions = ["approve_specialists", "reject_specialists"]

    @admin.display(description="Quick Approval")
    def quick_actions(self, obj):
        if not obj.is_approved:
            url = reverse("datahire_admin:approve_specialist", args=[obj.pk])
            return format_html(
                '<a class="button" style="background:#10b981;color:#fff;padding:5px 10px;border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;white-space:nowrap;" href="{}">✓ Approve</a>',
                url
            )
        else:
            revoke_url = reverse("datahire_admin:reject_specialist", args=[obj.pk])
            return format_html(
                '<span style="color:#10b981;font-weight:600;">✓ Approved</span> &nbsp;'
                '<a class="button" style="background:#ef4444;color:#fff;padding:3px 7px;font-size:0.75rem;border-radius:4px;text-decoration:none;display:inline-block;white-space:nowrap;" href="{}">Revoke</a>',
                revoke_url
            )

    @admin.action(description="Approve selected specialists")
    def approve_specialists(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} specialist(s) approved.")

    @admin.action(description="Reject (unapprove) selected specialists")
    def reject_specialists(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} specialist(s) rejected.")


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "location", "balance", "default_payment_method")
    list_filter = ("default_payment_method",)
    search_fields = ("user__username", "user__email", "company_name", "location")
    fieldsets = (
        ("Client Profile", {"fields": ("user", "company_name", "bio", "location")}),
        ("Billing", {"fields": ("billing_address", "default_payment_method")}),
        ("Financials", {
            "fields": ("balance",),
            "description": "Edit the client's available account balance. Use a positive amount to allow balance payments.",
        }),
        ("Record", {"fields": ("created_at",), "classes": ("collapse",)}),
    )
    readonly_fields = ("created_at",)
