"""Factory for Users"""
import string

from factory import Faker, Trait, SubFactory, RelatedFactory, fuzzy
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyText
from social_django.models import UserSocialAuth

from users.models import LegalAddress, Profile, User, GENDER_CHOICES


class UserFactory(DjangoModelFactory):
    """Factory for Users"""

    username = FuzzyText()
    email = FuzzyText(suffix="@example.com")
    name = Faker("name")

    is_active = True

    legal_address = RelatedFactory("users.factories.LegalAddressFactory", "user")
    profile = RelatedFactory("users.factories.ProfileFactory", "user")

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


class ProfileFactory(DjangoModelFactory):
    """Factory for Profile"""

    user = SubFactory("users.factories.UserFactory")

    gender = fuzzy.FuzzyChoice(choices=[gender[0] for gender in GENDER_CHOICES])
    birth_year = Faker("year")
    company = Faker("company")
    job_title = Faker("word")

    class Meta:
        model = Profile

    class Params:
        incomplete = Trait(job_title="", company="", gender="", birth_year=None)
