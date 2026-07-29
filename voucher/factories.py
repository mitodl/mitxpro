"""
Factories for voucher models
"""

import factory
from factory.django import DjangoModelFactory

from users.factories import UserFactory
from voucher.models import Voucher
from datetime import UTC


class VoucherFactory(DjangoModelFactory):
    """
    Factory for Voucher
    """

    employee_name = factory.Faker("name")
    employee_id = factory.Faker("password", special_chars=False)

    course_start_date_input = factory.Faker(
        "date_time_this_month", before_now=True, after_now=False, tzinfo=UTC
    )
    course_id_input = factory.Sequence("course-{}".format)
    course_title_input = factory.fuzzy.FuzzyText(prefix="Course ")

    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Voucher
