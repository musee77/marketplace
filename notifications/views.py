from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    """Show all notifications for the current user, marking unread ones as read."""
    qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")

    # Mark all unread as read on page visit
    unread_ids = list(qs.filter(is_read=False).values_list("pk", flat=True))
    if unread_ids:
        Notification.objects.filter(pk__in=unread_ids).update(is_read=True)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "notifications/notification_list.html", {
        "page_obj": page_obj,
        "notifications": page_obj,
        "newly_read_count": len(unread_ids),
    })


@login_required
@require_POST
def notification_mark_read(request, pk):
    """Mark a single notification as read (AJAX or plain POST)."""
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return notification_list(request)


@login_required
@require_POST
def notification_mark_all_read(request):
    """Mark every notification for the current user as read."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    from django.shortcuts import redirect
    return redirect("notifications:list")
