"""fixtures for ecommerce tests"""
from collections import namedtuple
from decimal import Decimal
from types import SimpleNamespace

import pytest

# pylint:disable=redefined-outer-name
from ecommerce.api import ValidatedBasket
from ecommerce.factories import (
    BasketItemFactory,
    CouponEligibilityFactory,
    CouponFactory,
    CouponPaymentFactory,
    CouponPaymentVersionFactory,
    CouponVersionFactory,
    CouponSelectionFactory,
    CompanyFactory,
    DataConsentUserFactory,
    ProductVersionFactory,
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
        payment=payment_worst, amount=Decimal("0.10000"), automatic=True
    )
    # Coupon payment for best coupon, with highest discount
    civ_best_old = CouponPaymentVersionFactory(
        payment=payment_best, amount=Decimal("0.50000")
    )
    # Coupon payment for best coupon, more recent than previous so takes precedence
    civ_best = CouponPaymentVersionFactory(
        payment=payment_best, amount=Decimal("1.00000")
    )

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
def validated_basket(basket_and_coupons):
    """Fixture for a ValidatedBasket object"""
    return ValidatedBasket(
        basket=basket_and_coupons.basket,
        basket_item=basket_and_coupons.basket_item,
        product_version=basket_and_coupons.product_version,
        coupon_version=basket_and_coupons.coupongroup_best.coupon_version,
        run_selection_ids={basket_and_coupons.run.id},
        data_consent_users=[],
    )


@pytest.fixture
def basket_and_agreement(basket_and_coupons):
    """
    Sample basket and data consent agreement
    """
    basket_item = basket_and_coupons.basket_item
    product = basket_and_coupons.product_version.product
    coupon = basket_and_coupons.coupongroup_best.coupon
    company = coupon.payment.latest_version.company
    agreement = DataConsentAgreementFactory(
        courses=[basket_and_coupons.run.course], company=company
    )
    DataConsentUserFactory.create(
        user=basket_item.basket.user, agreement=agreement, coupon=coupon
    )
    return SimpleNamespace(
        agreement=agreement, basket=basket_item.basket, product=product, coupon=coupon
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
        "include_future_runs": False,
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
        "include_future_runs": False,
    }


@pytest.fixture
def mock_hubspot_syncs(mocker):
    """Mock the sync_deal_with_hubspot task"""
    return SimpleNamespace(
        order=mocker.patch("hubspot.tasks.sync_deal_with_hubspot.delay"),
        line=mocker.patch("hubspot.tasks.sync_line_item_with_hubspot.delay"),
        product=mocker.patch("hubspot.tasks.sync_product_with_hubspot.delay"),
    )
