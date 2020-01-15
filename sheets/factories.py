"""Factories for sheets app"""
import pytz
from factory import Faker, SubFactory, fuzzy
from factory.django import DjangoModelFactory

from sheets import models
from users.factories import UserFactory


class CouponGenerationRequestFactory(
    DjangoModelFactory
):  # pylint: disable=missing-docstring
    purchase_order_id = Faker("pystr", max_chars=15)
    coupon_name = fuzzy.FuzzyText()

    class Meta:
        model = models.CouponGenerationRequest


class GoogleApiAuthFactory(DjangoModelFactory):  # pylint: disable=missing-docstring
    requesting_user = SubFactory(UserFactory)
    access_token = Faker("pystr", max_chars=30)
    refresh_token = Faker("pystr", max_chars=30)

    class Meta:
        model = models.GoogleApiAuth


class GoogleFileWatchFactory(DjangoModelFactory):  # pylint: disable=missing-docstring
    file_id = Faker("pystr", max_chars=15)
    channel_id = fuzzy.FuzzyText(prefix="Channel ")
    activation_date = Faker("past_datetime", start_date="-30d", tzinfo=pytz.UTC)
    expiration_date = Faker("future_datetime", end_date="+30d", tzinfo=pytz.UTC)

    class Meta:
        model = models.GoogleFileWatch
