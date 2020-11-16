"""
Factories for voucher models
"""
import factory
from factory.django import DjangoModelFactory
from users.factories import UserFactory

from voucher.models import Voucher


class VoucherFactory(DjangoModelFactory):
    """
    Factory for Voucher
    """

    employee_name = factory.Faker("name")
    employee_id = factory.Faker("password", special_chars=False)

    course_start_date_input = factory.Faker("date_object")
    course_id_input = factory.Sequence("course-{0}".format)
    course_title_input = factory.fuzzy.FuzzyText(prefix="Course ")

    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Voucher
