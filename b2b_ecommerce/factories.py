"""Factories for b2b_ecommerce"""
import factory
from factory import fuzzy
from factory.django import DjangoModelFactory

from b2b_ecommerce.models import B2BOrder
from ecommerce.factories import ProductVersionFactory


class B2BOrderFactory(DjangoModelFactory):
    """Factory for B2BOrder"""

    status = fuzzy.FuzzyChoice(choices=B2BOrder.STATUSES)
    num_seats = fuzzy.FuzzyInteger(low=0, high=1234)
    email = factory.Faker("email")
    per_item_price = fuzzy.FuzzyDecimal(low=1, high=123)
    total_price = factory.LazyAttribute(lambda obj: obj.per_item_price)
    product_version = factory.SubFactory(ProductVersionFactory)

    class Meta:
        model = B2BOrder
