from .models import Message

def unread_messages_count(request):
    if request.user and request.user.is_authenticated:
        unread_count = Message.objects.filter(
            conversation__participants=request.user,
            is_approved=True,
            is_read=False
        ).exclude(sender=request.user).count()
        return {'unread_messages_count': unread_count}
    return {'unread_messages_count': 0}
