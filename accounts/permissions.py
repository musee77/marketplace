from rest_framework import permissions


class IsManager(permissions.BasePermission):
    message = "Only managers can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_manager)


class IsSpecialist(permissions.BasePermission):
    message = "Only specialists can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_specialist)


class IsClient(permissions.BasePermission):
    message = "Only clients can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_client)


class IsOwnerOrManager(permissions.BasePermission):
    """Object-level: only the owner (obj.user or obj) or a manager may edit."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_manager:
            return True
        owner = getattr(obj, "user", obj)
        return owner == request.user
