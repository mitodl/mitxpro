"""Affiliate app factories"""

import factory
from factory import fuzzy
from factory.django import DjangoModelFactory

from affiliate import models
from ecommerce.factories import OrderFactory
from users.factories import UserFactory


class AffiliateFactory(DjangoModelFactory):
    """Factory for Affiliate"""

    code = factory.Sequence("affiliate-code-{0}".format)
    name = fuzzy.FuzzyText(prefix="Affiliate ", length=30)

    class Meta:
        model = models.Affiliate


class AffiliateReferralActionFactory(DjangoModelFactory):
    """Factory for AffiliateReferralAction"""

    affiliate = factory.SubFactory(AffiliateFactory)
    created_user = factory.SubFactory(UserFactory)
    created_order = factory.SubFactory(OrderFactory)

    class Meta:
        model = models.AffiliateReferralAction
