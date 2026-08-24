from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Order
from .serializers import OrderSerializer
from accounts.permissions import IsClient


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_manager:
            return Order.objects.all().select_related("service", "client", "specialist")
        if user.is_specialist:
            return Order.objects.filter(specialist=user, is_paid=True).select_related("service", "client")
        return Order.objects.filter(client=user).select_related("service", "specialist")

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsClient()]
        return super().get_permissions()

    def perform_create(self, serializer):
        service = serializer.validated_data["service"]
        serializer.save(client=self.request.user, specialist=service.specialist, price=service.price)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        order = self.get_object()
        if not order.is_paid:
            raise ValidationError({"detail": "This order cannot be modified because it is not paid."})
        new_status = request.data.get("status")
        user = request.user
        allowed = []
        if user == order.specialist:
            allowed = order.SPECIALIST_ACTIONS.get(order.status, [])
        elif user == order.client:
            allowed = order.CLIENT_ACTIONS.get(order.status, [])
        if new_status not in allowed:
            raise ValidationError({"status": f"Cannot move from {order.status} to {new_status}."})
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        return Response(OrderSerializer(order).data)
