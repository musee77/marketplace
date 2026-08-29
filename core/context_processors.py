from accounts.models import User


def promotional_activity(request):
    """Expose recent public member activity for the floating activity toast."""
    recent_members = (
        User.objects.filter(
            is_active=True,
            is_suspended=False,
            role__in=(User.Role.CLIENT, User.Role.SPECIALIST),
        )
        .exclude(is_staff=True)
        .only("username", "first_name", "role", "date_created")
        .order_by("-date_created")[:5]
    )
    return {"promotional_activity": recent_members}


def inquiries_updates_count(request):
    """Expose inquiries count and pending/unread status for navbar updates dropdown."""
    if request.user and request.user.is_authenticated:
        from .models import ContactMessage
        from django.db.models import Q
        
        user = request.user
        if user.is_manager:
            pending_count = ContactMessage.objects.filter(status=ContactMessage.Status.PENDING).count()
            return {
                "inquiries_updates_count": pending_count,
                "pending_inquiries_count": pending_count,
                "user_inquiries_unread_count": 0,
            }
        else:
            user_inquiries_unread = ContactMessage.objects.filter(
                Q(user=user) | Q(email__iexact=user.email),
                is_read_by_user=False,
            ).exclude(admin_reply="").count()
            return {
                "inquiries_updates_count": user_inquiries_unread,
                "pending_inquiries_count": 0,
                "user_inquiries_unread_count": user_inquiries_unread,
            }
    return {
        "inquiries_updates_count": 0,
        "pending_inquiries_count": 0,
        "user_inquiries_unread_count": 0,
    }

