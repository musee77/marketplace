from .models import Notification


def unread_notifications_count(request):
    """Inject unread notification count into every template context."""
    if request.user and request.user.is_authenticated:
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {"unread_notifications_count": count}
    return {"unread_notifications_count": 0}
