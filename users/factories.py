"""Factory for Users"""
from factory import Faker
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyText

from users.models import User


class UserFactory(DjangoModelFactory):
    """Factory for Users"""

    email = FuzzyText(suffix="@example.com")
    name = Faker("name")

    class Meta:
        model = User
