from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender", "body", "created_at")
    fields = ("sender", "body", "is_approved", "is_rejected", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "created_at", "updated_at")
    inlines = [MessageInline]


from django.utils.html import format_html
from django.urls import reverse


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "short_body", "is_approved", "is_rejected", "quick_actions", "conversation", "created_at")
    list_filter = ("is_approved", "is_rejected")
    list_editable = ("is_approved", "is_rejected")
    search_fields = ("body", "sender__username")
    actions = ["approve_messages", "reject_messages"]

    @admin.display(description="Quick Moderation")
    def quick_actions(self, obj):
        if not obj.is_approved and not obj.is_rejected:
            approve_url = reverse("datahire_admin:approve_message", args=[obj.pk])
            reject_url = reverse("datahire_admin:reject_message", args=[obj.pk])
            return format_html(
                '<a class="button" style="background:#10b981;color:#fff;padding:4px 8px;border-radius:4px;text-decoration:none;font-weight:600;margin-right:4px;display:inline-block;white-space:nowrap;" href="{}">✓ Approve</a>'
                '<a class="button" style="background:#ef4444;color:#fff;padding:4px 8px;border-radius:4px;text-decoration:none;font-weight:600;display:inline-block;white-space:nowrap;" href="{}">✗ Reject</a>',
                approve_url,
                reject_url
            )
        elif obj.is_approved:
            return format_html('<span style="color:#10b981;font-weight:600;">✓ Approved</span>')
        else:
            return format_html('<span style="color:#ef4444;font-weight:600;">✗ Rejected</span>')

    @admin.display(description="Message")
    def short_body(self, obj):
        return obj.body[:80]

    @admin.action(description="Approve selected messages")
    def approve_messages(self, request, queryset):
        updated = queryset.update(is_approved=True, is_rejected=False)
        self.message_user(request, f"{updated} message(s) approved.")

    @admin.action(description="Reject selected messages")
    def reject_messages(self, request, queryset):
        updated = queryset.update(is_rejected=True, is_approved=False)
        self.message_user(request, f"{updated} message(s) rejected.")
