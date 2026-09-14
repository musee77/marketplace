from django.shortcuts import redirect

from .models import SpecialistProfile


class SpecialistApprovalMiddleware:
    """Keep specialists in the assessment flow until a manager approves them."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and user.is_specialist:
            path = request.path
            allowed = (
                path == "/"
                or path.startswith("/accounts/specialist-tests/")
                or path.startswith("/accounts/logout/")
                or path.startswith("/static/")
                or path.startswith("/media/")
            )
            if not allowed:
                profile = SpecialistProfile.objects.filter(user=user).first()
                if not profile or not profile.has_platform_access:
                    return redirect("accounts:specialist_tests")
        return self.get_response(request)