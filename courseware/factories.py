"""Courseware factories"""
from datetime import timedelta

from factory import Faker, SubFactory, Trait, LazyAttribute
from factory.django import DjangoModelFactory
import pytz

from courseware.models import OpenEdxApiAuth, CoursewareUser
from courseware.constants import PLATFORM_EDX
from mitxpro.utils import now_in_utc


class CoursewareUserFactory(DjangoModelFactory):
    """Factory for CoursewareUser"""

    user = SubFactory("users.factories.UserFactory")
    platform = PLATFORM_EDX
    has_been_synced = True

    class Meta:
        model = CoursewareUser


class OpenEdxApiAuthFactory(DjangoModelFactory):
    """Factory for OpenEdxApiAuth"""

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
