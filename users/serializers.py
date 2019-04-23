"""User serializers"""
from rest_framework import serializers

from users.models import LegalAddress, User


class LegalAddressSerializer(serializers.ModelSerializer):
    """Serializer for legal address"""

    # NOTE: the model defines these as allowing empty values for backwards compatibility
    #       so we override them here to require them for new writes
    first_name = serializers.CharField(max_length=60)
    last_name = serializers.CharField(max_length=60)

    street_address_1 = serializers.CharField(max_length=60)
    street_address_2 = serializers.CharField(max_length=60)
    street_address_3 = serializers.CharField(max_length=60)
    street_address_4 = serializers.CharField(max_length=60)
    street_address_5 = serializers.CharField(max_length=60)

    city = serializers.CharField(max_length=50)
    country = serializers.CharField(max_length=2, choices=COUNTRY_CHOICES)

    # only required in the US/CA
    state_or_territory = serializers.CharField(max_length=255, allow_blank=True)
    postal_code = serializers.CharField(max_length=10, allow_blank=True)

    created_on = serializers.DateTimeField(read_only=True)
    updated_on = serializers.DateTimeField(read_only=True)

    class Meta:
        model = LegalAddress


class UserSerializer(serializers.ModelSerializer):
    """Serializer for users"""

    # password is explicitly write_only
    password = serializers.CharField(write_only=True)

    # NOTE: legal_address not returned in rendered response for now because we
    #       don't want to expose this until we have the time to do it correctly

    @transaction.atomic
    def create(self, validated_data):
        """Create a new user"""
        legal_address_data = validated_data.pop("legal_address")

        username = validated_data.pop("username")
        email = validated_data.pop("email")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            username, email=email, password=password, **validated_data
        )

        # this side-effects such that user.legal_address is updated in-place
        LegalAddressSerializer(instance.legal_address, data=legal_address_data).save()

        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update an existing user"""
        legal_address_data = validated_data.pop("legal_address", None)
        password = validated_data.pop("password", None)

        if legal_address_data:
            # this side-effects such that instance.legal_address is updated in-place
            LegalAddressSerializer(
                instance.legal_address, data=legal_address_data
            ).save()

        # save() will be called in super().update()
        if password is not None:
            instance.set_password(password)

        return super().update(instance, validated_data)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "name",
            "email",
            "password" "is_anonymous",
            "is_authenticated",
            "created_on",
            "updated_on",
        )
        read_only_fields = (
            "username",
            "is_anonymous",
            "is_authenticated",
            "created_on",
            "updated_on",
        )
