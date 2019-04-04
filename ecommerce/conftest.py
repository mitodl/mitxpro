"""fixtures for ecommerce tests"""
from collections import namedtuple
from decimal import Decimal
from types import SimpleNamespace

import pytest

from ecommerce.factories import (
    BasketItemFactory,
    CouponEligibilityFactory,
    CouponFactory,
    CouponPaymentFactory,
    CouponPaymentVersionFactory,
    CouponVersionFactory,
    ProductVersionFactory,
    CouponSelectionFactory,
)

CouponGroup = namedtuple(
    "CouponGroup",
    ["coupon", "coupon_version", "payment", "payment_version"],
    verbose=True,
)


@pytest.fixture()
def basket_and_coupons():
    """
    Sample basket and coupon
    """
    basket_item = BasketItemFactory()

    # Some prices for the basket item product
    ProductVersionFactory(product=basket_item.product, price=Decimal(15.00))
    product_version = ProductVersionFactory(
        product=basket_item.product, price=Decimal(25.00)
    )

    payment_worst = CouponPaymentFactory()
    payment_best = CouponPaymentFactory()
    coupon_worst = CouponFactory(payment=payment_worst, coupon_code="WORST")
    coupon_best = CouponFactory(payment=payment_best, coupon_code="BEST")

    # Coupon payment for worst coupon, with lowest discount
    civ_worst = CouponPaymentVersionFactory(
        payment=payment_worst, amount=Decimal(0.1), automatic=True
    )
    # Coupon payment for best coupon, with highest discount
    civ_best_old = CouponPaymentVersionFactory(
        payment=payment_best, amount=Decimal(0.5)
    )
    # Coupon payment for best coupon, more recent than previous so takes precedence
    civ_best = CouponPaymentVersionFactory(payment=payment_best, amount=Decimal(0.4))

    # Coupon version for worst coupon
    cv_worst = CouponVersionFactory(payment_version=civ_worst, coupon=coupon_worst)
    # Coupon version for best coupon
    CouponVersionFactory(payment_version=civ_best_old, coupon=coupon_best)
    # Most recent coupon version for best coupon
    cv_best = CouponVersionFactory(payment_version=civ_best, coupon=coupon_best)

    # Both best and worst coupons eligible for the product
    CouponEligibilityFactory(coupon=coupon_best, product=basket_item.product)
    CouponEligibilityFactory(coupon=coupon_worst, product=basket_item.product)

    # Apply one of the coupons to the basket
    CouponSelectionFactory.create(basket=basket_item.basket, coupon=coupon_best)

    coupongroup_worst = CouponGroup(coupon_worst, cv_worst, payment_worst, civ_worst)
    coupongroup_best = CouponGroup(coupon_best, cv_best, payment_best, civ_best)

    return SimpleNamespace(
        basket=basket_item.basket,
        basket_item=basket_item,
        product_version=product_version,
        coupongroup_best=coupongroup_best,
        coupongroup_worst=coupongroup_worst,
    )
