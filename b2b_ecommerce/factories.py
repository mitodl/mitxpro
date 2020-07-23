"""Factories for b2b_ecommerce"""
from datetime import timezone

import factory
from factory import fuzzy
from factory.django import DjangoModelFactory

from b2b_ecommerce.models import B2BCoupon, B2BOrder, B2BCouponRedemption
from ecommerce.factories import (
    CompanyFactory,
    CouponPaymentVersionFactory,
    ProductFactory,
    ProductVersionFactory,
)


class B2BOrderFactory(DjangoModelFactory):
    """Factory for B2BOrder"""

    status = fuzzy.FuzzyChoice(choices=B2BOrder.STATUSES)
    num_seats = fuzzy.FuzzyInteger(low=0, high=1234)
    email = factory.Faker("email")
    per_item_price = fuzzy.FuzzyDecimal(low=1, high=123)
    total_price = factory.LazyAttribute(lambda obj: obj.per_item_price * obj.num_seats)
    product_version = factory.SubFactory(ProductVersionFactory)
    coupon_payment_version = factory.SubFactory(CouponPaymentVersionFactory)
    contract_number = fuzzy.FuzzyChoice(["", "abc123", "123456"])

    class Meta:
        model = B2BOrder


class B2BCouponFactory(DjangoModelFactory):
    """Factory for B2BCoupon"""

    name = fuzzy.FuzzyText()
    coupon_code = fuzzy.FuzzyText()
    activation_date = factory.Faker(
        "date_time_this_year", before_now=True, after_now=False, tzinfo=timezone.utc
    )
    expiration_date = factory.Faker(
        "date_time_this_year", before_now=False, after_now=True, tzinfo=timezone.utc
    )
    enabled = True
    reusable = False
    product = factory.SubFactory(ProductFactory)
    discount_percent = fuzzy.FuzzyDecimal(low=0, high=1, precision=5)
    company = factory.SubFactory(CompanyFactory)

    class Meta:
        model = B2BCoupon


class B2BCouponRedemptionFactory(DjangoModelFactory):
    """Factory for CouponRedemption"""

    coupon = factory.SubFactory(B2BCouponFactory)
    order = factory.SubFactory(B2BOrderFactory)

    class Meta:
        model = B2BCouponRedemption
