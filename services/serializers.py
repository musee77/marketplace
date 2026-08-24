from rest_framework import serializers
from .models import Service, Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon"]


class ServiceSerializer(serializers.ModelSerializer):
    specialist_username = serializers.CharField(source="specialist.username", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    average_rating = serializers.ReadOnlyField()
    review_count = serializers.ReadOnlyField()

    class Meta:
        model = Service
        fields = ["id", "specialist", "specialist_username", "category", "category_name", "title", "slug",
                  "description", "price", "delivery_days", "cover_image", "is_active", "created_at",
                  "average_rating", "review_count"]
        read_only_fields = ["slug", "specialist"]
