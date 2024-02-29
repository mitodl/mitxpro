"""Factories for sheets app"""
import datetime

from factory import Faker, SubFactory, fuzzy
from factory.django import DjangoModelFactory

from sheets import models
from users.factories import UserFactory


class CouponGenerationRequestFactory(  # noqa: D101
    DjangoModelFactory
):
    purchase_order_id = Faker("pystr", max_chars=15)
    coupon_name = fuzzy.FuzzyText()

    class Meta:
        model = models.CouponGenerationRequest


class GoogleApiAuthFactory(DjangoModelFactory):  # noqa: D101
    requesting_user = SubFactory(UserFactory)
    access_token = Faker("pystr", max_chars=30)
    refresh_token = Faker("pystr", max_chars=30)

    class Meta:
        model = models.GoogleApiAuth


class GoogleFileWatchFactory(DjangoModelFactory):  # noqa: D101
    file_id = Faker("pystr", max_chars=15)
    channel_id = fuzzy.FuzzyText(prefix="Channel ")
    activation_date = Faker(
        "past_datetime", start_date="-30d", tzinfo=datetime.timezone.utc
    )
    expiration_date = Faker(
        "future_datetime", end_date="+30d", tzinfo=datetime.timezone.utc
    )

    class Meta:
        model = models.GoogleFileWatch
