"""User serializers"""
from collections import defaultdict
import re

from django.db import transaction
import pycountry
from rest_framework import serializers

from mitxpro.serializers import WriteableSerializerMethodField
from users.models import LegalAddress, User

US_POSTAL_RE = re.compile(r"[0-9]{5}(-[0-9]{4})")
CA_POSTAL_RE = re.compile(r"[0-9][A-Z][0-9] [A-Z][0-9][A-Z]", flags=re.I)


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
    country = serializers.CharField(max_length=2)

    # only required in the US/CA
    state_or_territory = serializers.CharField(max_length=255, allow_blank=True)
    postal_code = serializers.CharField(max_length=10, allow_blank=True)

    created_on = serializers.DateTimeField(read_only=True)
    updated_on = serializers.DateTimeField(read_only=True)

    def validate(self, attrs):
        """Validate the entire object"""
        country_code = attrs["country"]
        country = pycountry.countries.get(alpha_2=country_code)

        # allow ourselves to return as much error information at once for user
        errors = defaultdict(list)

        if country is None:
            errors["country"].append(f"{country_code} is not a valid country code")

        state_or_territory_code = attrs["state_or_territory"]
        state_or_territory = pycountry.subdivisions.get(code=state_or_territory_code)

        if state_or_territory is None:
            errors["state_or_territory"].append(f"{state_or_territory_code} is not a valid state or territory code")
        if state_or_territory.country is not country:
            errors["state_or_territory"].append(f"{state_or_territory.name} is not a valid state or territory of {country.name}")

        postal_code = attrs.get("postal_code", None)
        if country.code in ["US", "CA"]:
            if not postal_code:
                errors["postal_code"].append(f"Postal Code is required for {country.name}")
            else:
                if country.code == "US" and not US_POSTAL_RE.match(postal_code):
                    errors["postal_code"].append(f"Postal Code must be in the format 'NNNNN' or 'NNNNN-NNNNN'")
                elif country.code == "CA" and not CA_POSTAL_RE.match(postal_code):
                    errors["postal_code"].append(f"Postal Code must be in the format 'ANA NAN'")

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    class Meta:
        model = LegalAddress


class UserSerializer(serializers.ModelSerializer):
    """Serializer for users"""

    # password is explicitly write_only
    password = serializers.CharField(write_only=True)
    email = WriteableSerializerMethodField()

    # NOTE: legal_address not returned in rendered response for now because we
    #       don't want to expose this until we have the time to do it correctly

    def validate_email(self, value):
        """Empty validation function, but this is required for WriteableSerializerMethodField"""
        return {"avatar": value}

    def get_email(self, instance):
        """Returns the email or None in the case of AnonymousUser"""
        return getattr(instance, "email", None)

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
        LegalAddressSerializer(user.legal_address, data=legal_address_data).save()

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
            "password",
            "is_anonymous",
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
