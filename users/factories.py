"""Factory for Users"""
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyText
from social_django.models import UserSocialAuth

from users.models import User


class UserFactory(DjangoModelFactory):
    """Factory for Users"""

    email = FuzzyText(suffix="@example.com")
    name = Faker("name")

    class Meta:
        model = User


class UserSocialAuthFactory(DjangoModelFactory):
    """Factory for UserSocialAuth"""

    provider = FuzzyText()
    user = SubFactory(UserFactory)
    uid = FuzzyText()

    class Meta:
        model = UserSocialAuth
