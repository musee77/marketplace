from rest_framework import viewsets, permissions, filters
from django.utils.text import slugify

from .models import Service, Category
from .serializers import ServiceSerializer, CategorySerializer
from accounts.permissions import IsSpecialist, IsOwnerOrManager


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.select_related("specialist", "category").filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrManager]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "specialist__username"]
    ordering_fields = ["price", "created_at"]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsSpecialist()]
        return super().get_permissions()

    def perform_create(self, serializer):
        title = serializer.validated_data["title"]
        base = slugify(title)
        slug = base
        i = 1
        while Service.objects.filter(slug=slug).exists():
            i += 1
            slug = f"{base}-{i}"
        serializer.save(specialist=self.request.user, slug=slug)
