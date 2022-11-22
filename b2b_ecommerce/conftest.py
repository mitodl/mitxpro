"""Fixtures for b2b_ecommerce"""
from types import SimpleNamespace

import pytest

from b2b_ecommerce.factories import B2BOrderFactory, B2BCouponFactory
from b2b_ecommerce.models import B2BCouponRedemption, B2BOrder


@pytest.fixture
def order_with_coupon():
    """Create a unfulfilled order with a coupon which is valid for it"""
    order = B2BOrderFactory.create(status=B2BOrder.CREATED)
    coupon = B2BCouponFactory.create(product=order.product_version.product)
    B2BCouponRedemption.objects.create(coupon=coupon, order=order)
    return SimpleNamespace(order=order, coupon=coupon)
