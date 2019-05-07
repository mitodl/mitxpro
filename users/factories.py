"""Factory for Users"""
import string

from factory import Faker, SubFactory, RelatedFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyText
from social_django.models import UserSocialAuth

from users.models import LegalAddress, User


class UserFactory(DjangoModelFactory):
    """Factory for Users"""

    email = FuzzyText(suffix="@example.com")
    name = Faker("name")

    is_active = True

    legal_address = RelatedFactory("users.factories.LegalAddressFactory", "user")

    class Meta:
        model = User


class UserSocialAuthFactory(DjangoModelFactory):
    """Factory for UserSocialAuth"""

    provider = FuzzyText()
    user = SubFactory("users.factories.UserFactory")
    uid = FuzzyText()

    class Meta:
        model = UserSocialAuth


class LegalAddressFactory(DjangoModelFactory):
    """Factory for LegalAddress"""

    user = SubFactory("users.factories.UserFactory")

    first_name = Faker("first_name")
    last_name = Faker("last_name")

    street_address_1 = Faker("street_address")

    state_or_territory = Faker("lexify", text="??-??", letters=string.ascii_uppercase)
    city = Faker("city")
    country = Faker("country_code", representation="alpha-2")
    postal_code = Faker("postalcode")

    class Meta:
        model = LegalAddress
