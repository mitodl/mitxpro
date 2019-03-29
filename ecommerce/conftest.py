"""fixtures for ecommerce tests"""
from collections import namedtuple
from decimal import Decimal
from types import SimpleNamespace

import pytest

from ecommerce.factories import (
    BasketItemFactory,
    CouponEligibilityFactory,
    CouponFactory,
    CouponInvoiceFactory,
    CouponInvoiceVersionFactory,
    CouponVersionFactory,
    ProductVersionFactory,
    CouponSelectionFactory,
)

CouponGroup = namedtuple(
    "CouponGroup",
    ["coupon", "coupon_version", "invoice", "invoice_version"],
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

    invoice_worst = CouponInvoiceFactory()
    invoice_best = CouponInvoiceFactory()
    coupon_worst = CouponFactory(invoice=invoice_worst, coupon_code="WORST")
    coupon_best = CouponFactory(invoice=invoice_best, coupon_code="BEST")

    # Coupon invoice for worst coupon, with lowest discount
    civ_worst = CouponInvoiceVersionFactory(
        invoice=invoice_worst, amount=Decimal(0.1), automatic=True
    )
    # Coupon invoice for best coupon, with highest discount
    civ_best_old = CouponInvoiceVersionFactory(
        invoice=invoice_best, amount=Decimal(0.5)
    )
    # Coupon invoice for best coupon, more recent than previous so takes precedence
    civ_best = CouponInvoiceVersionFactory(invoice=invoice_best, amount=Decimal(0.4))

    # Coupon version for worst coupon
    cv_worst = CouponVersionFactory(invoice_version=civ_worst, coupon=coupon_worst)
    # Coupon version for best coupon
    CouponVersionFactory(invoice_version=civ_best_old, coupon=coupon_best)
    # Most recent coupon version for best coupon
    cv_best = CouponVersionFactory(invoice_version=civ_best, coupon=coupon_best)

    # Both best and worst coupons eligible for the product
    CouponEligibilityFactory(coupon=coupon_best, product=basket_item.product)
    CouponEligibilityFactory(coupon=coupon_worst, product=basket_item.product)

    # Apply one of the coupons to the basket
    CouponSelectionFactory.create(basket=basket_item.basket, coupon=coupon_best)

    coupongroup_worst = CouponGroup(coupon_worst, cv_worst, invoice_worst, civ_worst)
    coupongroup_best = CouponGroup(coupon_best, cv_best, invoice_best, civ_best)

    return SimpleNamespace(
        basket=basket_item.basket,
        basket_item=basket_item,
        product_version=product_version,
        coupongroup_best=coupongroup_best,
        coupongroup_worst=coupongroup_worst,
    )
