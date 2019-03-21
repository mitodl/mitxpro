"""Courseware factories"""
from factory import Faker, SubFactory, Trait
from factory.django import DjangoModelFactory
import pytz

from courseware.models import OpenEdxApiAuth


class OpenEdxApiAuthFactory(DjangoModelFactory):
    """Factory for Users"""

    user = SubFactory("users.factories.UserFactory")
    refresh_token = Faker("pystr", max_chars=30)
    access_token = Faker("pystr", max_chars=30)
    access_token_expires_on = Faker("future_datetime", end_date="+1h", tzinfo=pytz.utc)

    class Meta:
        model = OpenEdxApiAuth

    class Params:
        expired = Trait(access_token_expires_on=Faker("past_datetime", tzinfo=pytz.utc))
