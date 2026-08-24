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
