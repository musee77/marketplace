from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Review
from .serializers import ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("service", "reviewer", "reviewee")
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    http_method_names = ["get", "post", "head", "options"]  # reviews are immutable once posted

    def perform_create(self, serializer):
        order = serializer.validated_data["order"]
        if self.request.user != order.client:
            raise PermissionDenied("Only the client on this order can leave a review.")
        if not order.is_reviewable:
            raise ValidationError("This order isn't eligible for a review yet.")
        serializer.save(service=order.service, reviewer=order.client, reviewee=order.specialist)
