"""User serializers"""

import logging
import re
from collections import defaultdict

import pycountry
from django.db import transaction
from rest_framework import serializers
from social_django.models import UserSocialAuth

from courseware.api import validate_name_with_edx
from courseware.exceptions import EdxApiRegistrationValidationException
from courseware.tasks import change_edx_user_email_async
from ecommerce.api import fetch_and_serialize_unused_coupons
from hubspot_xpro.task_helpers import sync_hubspot_user
from mail import verification_api
from mitxpro.serializers import WriteableSerializerMethodField
from users.constants import USER_REGISTRATION_FAILED_MSG
from users.models import ChangeEmailRequest, LegalAddress, Profile, User

log = logging.getLogger()

US_POSTAL_RE = re.compile(r"[0-9]{5}(-[0-9]{4}){0,1}")
CA_POSTAL_RE = re.compile(r"[A-Z]\d[A-Z] \d[A-Z]\d$", flags=re.I)
USER_NAME_RE = re.compile(
    r"""
    ^                               # Start of string
    (?![~!@&)(+:'.?/,`-]+)          # String should not start from character(s) in this set - They can exist in elsewhere
    ([^/^$#*=\[\]`%_;<>{}\"|]+)     # String should not contain characters(s) from this set - All invalid characters
    $                               # End of string
    """,
    flags=re.I | re.VERBOSE | re.MULTILINE,
)


class LegalAddressSerializer(serializers.ModelSerializer):
    """Serializer for legal address"""

    # NOTE: the model defines these as allowing empty values for backwards compatibility
    #       so we override them here to require them for new writes
    first_name = serializers.CharField(max_length=60)
    last_name = serializers.CharField(max_length=60)

    street_address = WriteableSerializerMethodField()
    city = serializers.CharField(max_length=50)
    country = serializers.CharField(max_length=2)
    vat_id = serializers.CharField(max_length=255, allow_blank=True, required=False)

    # only required in the US/CA
    state_or_territory = serializers.CharField(max_length=255, allow_blank=True)
    postal_code = serializers.CharField(max_length=10, allow_blank=True)

    def validate_first_name(self, value):
        """Validate the first name of the user"""
        if value and not USER_NAME_RE.match(value):
            raise serializers.ValidationError("First name is not valid")  # noqa: EM101
        return value

    def validate_last_name(self, value):
        """Validate the last name of the user"""
        if value and not USER_NAME_RE.match(value):
            raise serializers.ValidationError("Last name is not valid")  # noqa: EM101
        return value

    def validate_street_address(self, value):
        """Validate an incoming street address list"""
        if not value or not isinstance(value, list):
            raise serializers.ValidationError(
                "street_address must be a list of street lines"  # noqa: EM101
            )
        if len(value) > 5:  # noqa: PLR2004
            raise serializers.ValidationError(
                "street_address list must be 5 items or less"  # noqa: EM101
            )
        if any(len(line) > 60 for line in value):  # noqa: PLR2004
            raise serializers.ValidationError(
                "street_address lines must be 60 characters or less"  # noqa: EM101
            )
        return {f"street_address_{idx + 1}": line for idx, line in enumerate(value)}

    def get_street_address(self, instance):
        """Return the list of street address lines"""
        return [
            line
            for line in [
                instance.street_address_1,
                instance.street_address_2,
                instance.street_address_3,
                instance.street_address_4,
                instance.street_address_5,
            ]
            if line
        ]

    def validate(self, attrs):
        """Validate the entire object"""
        country_code = attrs["country"]
        country = pycountry.countries.get(alpha_2=country_code)

        # allow ourselves to return as much error information at once for user
        errors = defaultdict(list)

        postal_code = attrs.get("postal_code", None)
        if country and country.alpha_2 in ["US", "CA"]:
            state_or_territory_code = attrs["state_or_territory"]
            state_or_territory = pycountry.subdivisions.get(
                code=state_or_territory_code
            )

            if not state_or_territory:
                errors["state_or_territory"].append(
                    f"State/territory is required for {country.name}"
                )
            elif state_or_territory.country is not country:
                errors["state_or_territory"].append(
                    f"{state_or_territory.name} is not a valid state or territory of {country.name}"
                )

            if not postal_code:
                errors["postal_code"].append(
                    f"Postal Code is required for {country.name}"
                )
            elif country.alpha_2 == "US" and not US_POSTAL_RE.match(postal_code):
                errors["postal_code"].append(
                    "Postal Code must be in the format 'NNNNN' or 'NNNNN-NNNNN'"
                )
            elif country.alpha_2 == "CA" and not CA_POSTAL_RE.match(postal_code):
                errors["postal_code"].append(
                    "Postal Code must be in the format 'ANA NAN'"
                )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    class Meta:
        model = LegalAddress
        fields = (
            "first_name",
            "last_name",
            "street_address",
            "street_address_1",
            "street_address_2",
            "street_address_3",
            "street_address_4",
            "street_address_5",
            "city",
            "state_or_territory",
            "country",
            "postal_code",
            "vat_id",
        )
        extra_kwargs = {
            "street_address_1": {"write_only": True},
            "street_address_2": {"write_only": True},
            "street_address_3": {"write_only": True},
            "street_address_4": {"write_only": True},
            "street_address_5": {"write_only": True},
        }


class ExtendedLegalAddressSerializer(LegalAddressSerializer):
    """Serializer class that includes email address as part of the legal address"""

    email = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()

    def get_email(self, instance):
        """Get email from the linked user object"""
        return instance.user.email

    def get_company(self, instance):
        """Get company from the linked user object"""
        return instance.user.profile.company

    class Meta:
        model = LegalAddress
        fields = LegalAddressSerializer.Meta.fields + ("email", "company")  # noqa: RUF005
        extra_kwargs = LegalAddressSerializer.Meta.extra_kwargs


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for Profile"""

    class Meta:
        model = Profile
        fields = (
            "id",
            "birth_year",
            "gender",
            "company",
            "company_size",
            "industry",
            "job_title",
            "job_function",
            "years_experience",
            "leadership_level",
            "highest_education",
            "created_on",
            "updated_on",
        )
        read_only_fields = ("created_on", "updated_on")
        extra_kwargs = {
            "birth_year": {"allow_null": False, "required": True},
            "gender": {"allow_blank": False, "required": True},
            "company": {"allow_blank": False, "required": True},
            "job_title": {"allow_blank": False, "required": True},
        }


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for Profile within UserSerializer"""

    class Meta:
        model = Profile
        fields = (
            "birth_year",
            "gender",
            "company",
            "company_size",
            "industry",
            "job_title",
            "job_function",
            "years_experience",
            "leadership_level",
            "highest_education",
        )


class PublicUserSerializer(serializers.ModelSerializer):
    """Serializer for public user data"""

    class Meta:
        model = User
        fields = ("id", "username", "name", "created_on", "updated_on")


class UserSerializer(serializers.ModelSerializer):
    """Serializer for users"""

    # password is explicitly write_only
    password = serializers.CharField(write_only=True, required=False)
    email = WriteableSerializerMethodField()
    username = WriteableSerializerMethodField()
    legal_address = LegalAddressSerializer(allow_null=True)
    profile = UserProfileSerializer(allow_null=True, required=False)
    unused_coupons = serializers.SerializerMethodField()

    def validate_email(self, value):
        """Empty validation function, but this is required for WriteableSerializerMethodField"""
        return {"email": value.strip().lower()}

    def validate_username(self, value):
        """Empty validation function, but this is required for WriteableSerializerMethodField"""
        return {"username": value}

    def get_email(self, instance):
        """Return the email or None in the case of AnonymousUser"""
        return getattr(instance, "email", None)

    def get_username(self, instance):
        """Return the username or None in the case of AnonymousUser"""
        return getattr(instance, "username", None)

    def get_unused_coupons(self, instance):
        """Return a list of unused coupons"""
        if not instance.is_anonymous:
            return fetch_and_serialize_unused_coupons(instance)
        return []

    def validate(self, data):
        """Validate user data"""
        name = data.get("name")
        if name:
            try:
                openedx_validation_msg = validate_name_with_edx(name)
            except EdxApiRegistrationValidationException as exc:
                log.exception("Unable to create user account: %s", exc)  # noqa: TRY401
                raise serializers.ValidationError(USER_REGISTRATION_FAILED_MSG)  # noqa: B904

            if openedx_validation_msg:
                raise serializers.ValidationError(USER_REGISTRATION_FAILED_MSG)

        return data

    def create(self, validated_data):
        """Create a new user"""
        legal_address_data = validated_data.pop("legal_address")
        profile_data = validated_data.pop("profile", None)

        username = validated_data.pop("username")
        email = validated_data.pop("email")
        password = validated_data.pop("password")

        with transaction.atomic():
            user = User.objects.create_user(
                username,
                email=email,
                password=password,
                affiliate_id=self.context.get("affiliate_id", None),
                **validated_data,
            )

            # this side-effects such that user.legal_address and user.profile are updated in-place
            if legal_address_data:
                legal_address = LegalAddressSerializer(
                    user.legal_address, data=legal_address_data
                )
                if legal_address.is_valid():
                    legal_address.save()

            if profile_data:
                profile = UserProfileSerializer(user.profile, data=profile_data)
                if profile.is_valid():
                    profile.save()

        sync_hubspot_user(user)

        return user

    def update(self, instance, validated_data):
        """Update an existing user"""
        legal_address_data = validated_data.pop("legal_address", None)
        profile_data = validated_data.pop("profile", None)
        password = validated_data.pop("password", None)

        with transaction.atomic():
            # this side-effects such that user.legal_address and user.profile are updated in-place
            if legal_address_data:
                address_serializer = LegalAddressSerializer(
                    instance.legal_address, data=legal_address_data
                )
                if address_serializer.is_valid(raise_exception=True):
                    address_serializer.save()

            if profile_data:
                profile_serializer = UserProfileSerializer(
                    instance.profile, data=profile_data
                )
                if profile_serializer.is_valid(raise_exception=True):
                    profile_serializer.save()

            # save() will be called in super().update()
            if password is not None:
                instance.set_password(password)

            user = super().update(instance, validated_data)

        sync_hubspot_user(user)
        return user

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "name",
            "email",
            "password",
            "legal_address",
            "profile",
            "is_anonymous",
            "is_authenticated",
            "created_on",
            "updated_on",
            "unused_coupons",
        )
        read_only_fields = (
            "username",
            "is_anonymous",
            "is_authenticated",
            "created_on",
            "updated_on",
            "unused_coupons",
        )


class ChangeEmailRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for starting a user email change"""

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    new_email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate the change request"""
        # verify no other user has this email address
        errors = {}

        user = attrs["user"]
        new_email = attrs["new_email"]
        password = attrs.pop("password")

        if user.email == new_email:
            # verify the user isn't trying to change their email to their current one
            # this would indicate a programming error on the frontend if this request is allowed
            errors["email"] = "Provided email address is same as your current one"
        elif User.objects.filter(email=new_email).exists():
            errors["email"] = "Invalid email address"

        if errors:
            raise serializers.ValidationError(errors)

        # verify the password verifies for the current user
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid Password")  # noqa: EM101

        return attrs

    def create(self, validated_data):
        """Create the email change request"""
        change_request = super().create(validated_data)

        verification_api.send_verify_email_change_email(
            self.context["request"], change_request
        )

        return change_request

    class Meta:
        model = ChangeEmailRequest

        fields = ("user", "new_email", "password")


class ChangeEmailRequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for confirming a user email change"""

    confirmed = serializers.BooleanField()

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update an email change request"""
        if User.objects.filter(email=instance.new_email).exists():
            log.debug(
                "User %s tried to change email address to one already in use", instance
            )
            raise serializers.ValidationError("Unable to change email")  # noqa: EM101

        result = super().update(instance, validated_data)

        # change request has been confirmed
        if result.confirmed:
            user = result.user
            old_email = user.email
            user.email = result.new_email
            user.save()
            # delete social_auth entry to avoid old email account access
            try:
                user_social_auth = UserSocialAuth.objects.get(uid=old_email, user=user)
                user_social_auth.delete()
            except UserSocialAuth.DoesNotExist:
                pass
            change_edx_user_email_async.delay(user.id)

        return result

    class Meta:
        model = ChangeEmailRequest

        fields = ("confirmed",)


class StateProvinceSerializer(serializers.Serializer):
    """Serializer for pycountry states/provinces"""

    code = serializers.CharField()
    name = serializers.CharField()


class CountrySerializer(serializers.Serializer):
    """Serializer for pycountry countries, with states for US/CA"""

    code = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    states = serializers.SerializerMethodField()

    def get_code(self, instance):
        """Get the country alpha_2 code"""
        return instance.alpha_2

    def get_name(self, instance):
        """Get the country name (common name preferred if available)"""
        if hasattr(instance, "common_name"):
            return instance.common_name
        return instance.name

    def get_states(self, instance):
        """Get a list of states/provinces if USA or Canada"""
        if instance.alpha_2 in ("US", "CA"):
            return StateProvinceSerializer(
                instance=sorted(
                    pycountry.subdivisions.get(country_code=instance.alpha_2),
                    key=lambda state: state.name,
                ),
                many=True,
            ).data
        return []
