"""Courseware factories"""
from datetime import timedelta

from factory import Faker, SubFactory, Trait, LazyAttribute
from factory.django import DjangoModelFactory
import pytz

from courseware.models import OpenEdxApiAuth
from mitxpro.utils import now_in_utc


class OpenEdxApiAuthFactory(DjangoModelFactory):
    """Factory for Users"""

    user = SubFactory("users.factories.UserFactory")
    refresh_token = Faker("pystr", max_chars=30)
    access_token = Faker("pystr", max_chars=30)
    access_token_expires_on = Faker("future_datetime", end_date="+1h", tzinfo=pytz.utc)

    class Meta:
        model = OpenEdxApiAuth

    class Params:
        expired = Trait(
            access_token_expires_on=LazyAttribute(
                lambda _: now_in_utc() - timedelta(days=1)
            )
        )
