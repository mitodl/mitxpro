"""fixtures for ecommerce tests"""
from collections import namedtuple
from decimal import Decimal
from types import SimpleNamespace

import pytest

# pylint:disable=redefined-outer-name

from courses.factories import ProgramFactory, CourseFactory
from ecommerce.factories import (
    BasketItemFactory,
    CouponEligibilityFactory,
    CouponFactory,
    CouponPaymentFactory,
    CouponPaymentVersionFactory,
    CouponVersionFactory,
    CouponSelectionFactory,
    CompanyFactory,
    ProductVersionFactory,
    ProductFactory,
    DataConsentAgreementFactory,
)
from ecommerce.models import CourseRunSelection

CouponGroup = namedtuple(
    "CouponGroup", ["coupon", "coupon_version", "payment", "payment_version"]
)


@pytest.fixture()
def basket_and_coupons():
    """
    Sample basket and coupon
    """
    basket_item = BasketItemFactory()

    # Some prices for the basket item product
    ProductVersionFactory(product=basket_item.product, price=Decimal("15.00"))
    product_version = ProductVersionFactory(
        product=basket_item.product, price=Decimal("25.00")
    )

    run = basket_item.product.content_object
    CourseRunSelection.objects.create(run=run, basket=basket_item.basket)

    payment_worst = CouponPaymentFactory()
    payment_best = CouponPaymentFactory()
    coupon_worst = CouponFactory(payment=payment_worst, coupon_code="WORST")
    coupon_best = CouponFactory(payment=payment_best, coupon_code="BEST")

    # Coupon payment for worst coupon, with lowest discount
    civ_worst = CouponPaymentVersionFactory(
        payment=payment_worst, amount=Decimal("0.10"), automatic=True
    )
    # Coupon payment for best coupon, with highest discount
    civ_best_old = CouponPaymentVersionFactory(
        payment=payment_best, amount=Decimal("0.50")
    )
    # Coupon payment for best coupon, more recent than previous so takes precedence
    civ_best = CouponPaymentVersionFactory(payment=payment_best, amount=Decimal("1.00"))

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
        run=run,
    )


@pytest.fixture
def basket_and_agreement():
    """
    Sample basket and data consent agreement
    """
    program = ProgramFactory.create()
    CourseFactory.create_batch(5, program=program)
    product = ProductFactory.create(content_object=program)
    ProductVersionFactory(product=product, price=Decimal("15.00"))
    basket_item = BasketItemFactory(product=product, quantity=1)
    company = CompanyFactory.create()
    coupon = CouponFactory(payment=CouponPaymentFactory())
    payment_version = CouponPaymentVersionFactory(
        payment=coupon.payment, amount=Decimal("0.40"), company=company
    )
    CouponVersionFactory(payment_version=payment_version, coupon=coupon)
    CouponEligibilityFactory(coupon=coupon, product=product)
    CouponSelectionFactory.create(basket=basket_item.basket, coupon=coupon)
    return SimpleNamespace(
        agreement=DataConsentAgreementFactory(
            courses=program.courses.all(), company=company
        ),
        basket=basket_item.basket,
        product=product,
        coupon=coupon,
    )


@pytest.fixture
def coupon_product_ids():
    """ Product ids for creating coupons """
    product_versions = ProductVersionFactory.create_batch(3)
    return [product_version.product.id for product_version in product_versions]


@pytest.fixture
def promo_coupon_json(coupon_product_ids):
    """ JSON for creating a promo coupon """
    return {
        "tag": None,
        "name": "TEST NAME 2",
        "automatic": True,
        "activation_date": "2018-01-01T00:00:00Z",
        "expiration_date": "2019-12-31T00:00:00Z",
        "amount": 0.75,
        "coupon_code": "TESTPROMOCODE",
        "coupon_type": "promo",
        "company": CompanyFactory.create().id,
        "payment_type": "purchase_order",
        "payment_transaction": "fake_transaction_num",
        "product_ids": coupon_product_ids,
    }


@pytest.fixture
def single_use_coupon_json(coupon_product_ids):
    """JSON for creating a batch of single-use coupons"""
    return {
        "tag": "TEST TAG 1",
        "name": "TEST NAME 1",
        "automatic": True,
        "activation_date": "2018-01-01T00:00:00Z",
        "expiration_date": "2019-12-31T00:00:00Z",
        "amount": 0.75,
        "num_coupon_codes": 5,
        "coupon_type": "single-use",
        "company": CompanyFactory.create().id,
        "payment_type": "credit_card",
        "payment_transaction": "fake_transaction_num",
        "product_ids": coupon_product_ids,
    }


@pytest.fixture
def mock_hubspot_syncs(mocker):
    """Mock the sync_deal_with_hubspot task"""
    return SimpleNamespace(
        order=mocker.patch("ecommerce.tasks.sync_deal_with_hubspot.delay"),
        line=mocker.patch("ecommerce.tasks.sync_line_item_with_hubspot.delay"),
        product=mocker.patch("ecommerce.tasks.sync_product_with_hubspot.delay"),
    )
