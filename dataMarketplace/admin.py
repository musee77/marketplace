from django.contrib.admin import AdminSite
from django.contrib import admin as default_admin

from accounts.models import User, SpecialistProfile, ClientProfile
from services.models import Category, Service
from orders.models import Order, Offer, OrderDocument
from chat.models import Conversation, Message
from reviews.models import Review
from core.models import SearchKeyword
from blog.models import BlogCategory, BlogPost
from blog import admin as blog_admin

# Project-wide custom admin site
class SynovaeAnalyticsAdminSite(AdminSite):
    site_header = "Synovae Analytics administration"
    site_title = "Synovae Analytics — Admin"
    index_title = "Dashboard"
    login_template = "admin/login.html"
    index_template = "admin/index.html"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(
            {
                "total_users": User.objects.count(),
                "total_specialists": User.objects.filter(role=User.Role.SPECIALIST).count(),
                "total_clients": User.objects.filter(role=User.Role.CLIENT).count(),
                "total_services": Service.objects.count(),
                "total_orders": Order.objects.count(),
                "pending_orders": Order.objects.filter(status=Order.Status.PENDING).count(),
                "pending_messages": Message.objects.filter(is_approved=False, is_rejected=False).count(),
                "pending_specialists": SpecialistProfile.objects.filter(is_approved=False).count(),
                "total_reviews": Review.objects.count(),
                "total_conversations": Conversation.objects.count(),
                "total_categories": Category.objects.count(),
                "recent_orders": Order.objects.select_related("client", "specialist", "service").order_by("-created_at")[:5],
                "recent_pending_specialists": SpecialistProfile.objects.filter(is_approved=False).select_related("user").order_by("-created_at")[:5],
                "recent_pending_messages": Message.objects.filter(is_approved=False, is_rejected=False).select_related("sender", "conversation").order_by("-created_at")[:5],
                "recent_users": User.objects.order_by("-date_created")[:5],
            }
        )
        return super().index(request, extra_context=extra_context)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path("approve-specialist/<int:profile_id>/", self.admin_view(self.approve_specialist_view), name="approve_specialist"),
            path("reject-specialist/<int:profile_id>/", self.admin_view(self.reject_specialist_view), name="reject_specialist"),
            path("approve-message/<int:message_id>/", self.admin_view(self.approve_message_view), name="approve_message"),
            path("reject-message/<int:message_id>/", self.admin_view(self.reject_message_view), name="reject_message"),
        ]
        return custom_urls + urls

    def approve_specialist_view(self, request, profile_id):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        profile = get_object_or_404(SpecialistProfile, pk=profile_id)
        profile.is_approved = True
        profile.save(update_fields=["is_approved"])
        messages.success(request, f"Specialist '{profile.user.get_full_name() or profile.user.username}' has been approved.")
        return redirect(request.META.get("HTTP_REFERER") or "datahire_admin:index")

    def reject_specialist_view(self, request, profile_id):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        profile = get_object_or_404(SpecialistProfile, pk=profile_id)
        profile.is_approved = False
        profile.save(update_fields=["is_approved"])
        messages.warning(request, f"Specialist '{profile.user.get_full_name() or profile.user.username}' approval revoked.")
        return redirect(request.META.get("HTTP_REFERER") or "datahire_admin:index")

    def approve_message_view(self, request, message_id):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        msg = get_object_or_404(Message, pk=message_id)
        msg.is_approved = True
        msg.is_rejected = False
        msg.save(update_fields=["is_approved", "is_rejected"])
        messages.success(request, f"Message #{msg.pk} from {msg.sender.username} approved.")
        return redirect(request.META.get("HTTP_REFERER") or "datahire_admin:index")

    def reject_message_view(self, request, message_id):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        msg = get_object_or_404(Message, pk=message_id)
        msg.is_approved = False
        msg.is_rejected = True
        msg.save(update_fields=["is_approved", "is_rejected"])
        messages.warning(request, f"Message #{msg.pk} from {msg.sender.username} rejected.")
        return redirect(request.META.get("HTTP_REFERER") or "datahire_admin:index")


custom_admin_site = SynovaeAnalyticsAdminSite(name="datahire_admin")

# Re-register all app models into the custom site.
try:
    from accounts import admin as accounts_admin
    from services import admin as services_admin
    from orders import admin as orders_admin
    from chat import admin as chat_admin
    from reviews import admin as reviews_admin
    from notifications.models import Notification
    from notifications import admin as notifications_admin

    # Unregister from default site if present
    for m in (User, SpecialistProfile, ClientProfile, Category, Service, Order, Offer, OrderDocument, Conversation, Message, Review, Notification, SearchKeyword, BlogCategory, BlogPost):
        try:
            default_admin.site.unregister(m)
        except Exception:
            pass

    # Register with custom admin site
    try:
        custom_admin_site.register(User, accounts_admin.CustomUserAdmin)
    except Exception:
        pass
    try:
        custom_admin_site.register(SpecialistProfile, accounts_admin.SpecialistProfileAdmin)
    except Exception:
        pass
    try:
        custom_admin_site.register(ClientProfile, accounts_admin.ClientProfileAdmin)
    except Exception:
        pass

    try:
        custom_admin_site.register(Category, services_admin.CategoryAdmin)
    except Exception:
        pass
    try:
        custom_admin_site.register(Service, services_admin.ServiceAdmin)
    except Exception:
        pass

    try:
        custom_admin_site.register(Order, orders_admin.OrderAdmin)
    except Exception:
        pass
    try:
        custom_admin_site.register(Offer, orders_admin.OfferAdmin)
    except Exception:
        pass
    try:
        custom_admin_site.register(OrderDocument, orders_admin.OrderDocumentAdmin)
    except Exception:
        pass

    try:
        custom_admin_site.register(Conversation, chat_admin.ConversationAdmin)
    except Exception:
        pass
    try:
        custom_admin_site.register(Message, chat_admin.MessageAdmin)
    except Exception:
        pass

    try:
        custom_admin_site.register(Review, reviews_admin.ReviewAdmin)
    except Exception:
        pass

    try:
        custom_admin_site.register(Notification, notifications_admin.NotificationAdmin)
    except Exception:
        pass

    try:
        custom_admin_site.register(BlogPost, blog_admin.BlogPostAdmin)
    except Exception:
        pass
    try:
        custom_admin_site.register(BlogCategory, blog_admin.BlogCategoryAdmin)
    except Exception:
        pass
except Exception:
    pass
