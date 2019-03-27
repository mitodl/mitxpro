"""User serializers"""
from rest_framework import serializers

from users.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for users"""

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "name",
            "email",
            "is_anonymous",
            "is_authenticated",
            "created_on",
            "updated_on",
        )
        read_only_fields = (
            "username",
            "name",
            "email",
            "is_anonymous",
            "is_authenticated",
            "created_on",
            "updated_on",
        )
