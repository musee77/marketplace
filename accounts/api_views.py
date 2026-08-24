from rest_framework import viewsets, mixins, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import User, SpecialistProfile, ClientProfile
from .serializers import UserSerializer, SpecialistProfileSerializer, ClientProfileSerializer
from .permissions import IsManager


class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Managers can list/inspect all users; anyone authenticated sees only themselves via /me/."""
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated(), IsManager()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsManager])
    def toggle_suspend(self, request, pk=None):
        user = self.get_object()
        user.is_suspended = not user.is_suspended
        user.save(update_fields=["is_suspended"])
        return Response(UserSerializer(user).data)


class SpecialistProfileViewSet(viewsets.ModelViewSet):
    queryset = SpecialistProfile.objects.select_related("user")
    serializer_class = SpecialistProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        verified = self.request.query_params.get("verified")
        if verified is not None:
            qs = qs.filter(is_verified=verified.lower() == "true")
        return qs

    def perform_update(self, serializer):
        # only the owner or a manager may edit; owners can't self-verify
        instance = self.get_object()
        if instance.user != self.request.user and not self.request.user.is_manager:
            raise permissions.PermissionDenied("Not your profile.")
        serializer.save()

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsManager])
    def toggle_verify(self, request, pk=None):
        profile = self.get_object()
        profile.is_verified = not profile.is_verified
        profile.save(update_fields=["is_verified"])
        return Response(SpecialistProfileSerializer(profile).data)


class ClientProfileViewSet(viewsets.ModelViewSet):
    queryset = ClientProfile.objects.select_related("user")
    serializer_class = ClientProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.user != self.request.user and not self.request.user.is_manager:
            raise permissions.PermissionDenied("Not your profile.")
        serializer.save()
