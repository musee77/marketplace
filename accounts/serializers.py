from rest_framework import serializers
from .models import User, SpecialistProfile, ClientProfile


class SpecialistProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    average_rating = serializers.ReadOnlyField()
    review_count = serializers.ReadOnlyField()

    class Meta:
        model = SpecialistProfile
        fields = ["id", "username", "full_name", "headline", "bio", "skills", "hourly_rate",
                  "years_experience", "location", "is_verified", "is_available", "portfolio_url",
                  "average_rating", "review_count"]
        read_only_fields = ["is_verified"]


class ClientProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ClientProfile
        fields = ["id", "username", "company_name", "bio", "location"]


class UserSerializer(serializers.ModelSerializer):
    specialist_profile = SpecialistProfileSerializer(read_only=True)
    client_profile = ClientProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role", "phone",
                  "is_suspended", "date_created", "specialist_profile", "client_profile"]
        read_only_fields = ["role", "is_suspended", "date_created"]
