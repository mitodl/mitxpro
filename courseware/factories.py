"""Courseware factories"""

from datetime import UTC, timedelta

from factory import Faker, LazyAttribute, SubFactory, Trait
from factory.django import DjangoModelFactory

from courseware.constants import PLATFORM_EDX
from courseware.models import CoursewareUser, OpenEdxApiAuth
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
    access_token_expires_on = Faker(
        "date_time_between", start_date="+1d", end_date="+2d", tzinfo=UTC
    )

    class Meta:
        model = OpenEdxApiAuth

    class Params:
        expired = Trait(
            access_token_expires_on=LazyAttribute(
                lambda _: now_in_utc() - timedelta(days=1)
            )
        )
