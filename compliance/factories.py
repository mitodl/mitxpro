"""Factories for compliance app"""

from factory import Faker, SubFactory, Trait
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from compliance.constants import (
    DECISION_COMPLETED,
    DECISION_DECLINED,
    RESULT_CHOICES,
    RESULT_DENIED,
    RESULT_SUCCESS,
)
from compliance.models import ExportsInquiryLog


class ExportsInquiryLogFactory(DjangoModelFactory):
    """Factory for ExportsInquiryLog"""

    user = SubFactory("users.factories.UserFactory")
    computed_result = FuzzyChoice(RESULT_CHOICES)

    reason_code = DECISION_COMPLETED
    info_code = Faker("numerify", text="###")

    encrypted_request = Faker("pystr", max_chars=30)
    encrypted_response = Faker("pystr", max_chars=30)

    class Meta:
        model = ExportsInquiryLog

    class Params:
        denied = Trait(computed_result=RESULT_DENIED, reason_code=DECISION_DECLINED)
        success = Trait(computed_result=RESULT_SUCCESS)
