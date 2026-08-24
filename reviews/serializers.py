from rest_framework import serializers
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_username = serializers.CharField(source="reviewer.username", read_only=True)
    reviewee_username = serializers.CharField(source="reviewee.username", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "order", "service", "reviewer", "reviewer_username", "reviewee",
                  "reviewee_username", "rating", "comment", "created_at"]
        read_only_fields = ["service", "reviewer", "reviewee"]
