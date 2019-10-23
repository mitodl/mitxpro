"""Factories for sheets app"""

from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

from sheets import models
from users.factories import UserFactory


class CouponGenerationRequestFactory(
    DjangoModelFactory
):  # pylint: disable=missing-docstring
    transaction_id = Faker("pystr", max_chars=15)

    class Meta:
        model = models.CouponGenerationRequest


class GoogleApiAuthFactory(DjangoModelFactory):  # pylint: disable=missing-docstring
    requesting_user = SubFactory(UserFactory)
    access_token = Faker("pystr", max_chars=30)
    refresh_token = Faker("pystr", max_chars=30)

    class Meta:
        model = models.GoogleApiAuth
