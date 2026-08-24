from rest_framework import serializers
from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    service_title = serializers.CharField(source="service.title", read_only=True)
    client_username = serializers.CharField(source="client.username", read_only=True)
    specialist_username = serializers.CharField(source="specialist.username", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = ["id", "service", "service_title", "client", "client_username", "specialist",
                  "specialist_username", "status", "status_display", "requirements", "price",
                  "created_at", "updated_at", "due_date"]
        read_only_fields = ["client", "specialist", "price", "status"]
