"""
Test for ecommerce functions
"""
from base64 import b64encode
from collections import namedtuple
from decimal import Decimal
from datetime import datetime, timedelta
from types import SimpleNamespace
import hashlib
import hmac

import pytest
import pytz

from courses.factories import CourseFactory, ProgramFactory
from ecommerce.api import (
    generate_cybersource_sa_payload,
    generate_cybersource_sa_signature,
    ISO_8601_FORMAT,
    make_reference_id,
    select_coupon,
    redeem_coupon,
)
from ecommerce.api import (
    get_eligible_coupons,
    get_valid_coupon_versions,
    best_coupon_version,
    discount_price,
)
from ecommerce.factories import (
    BasketItemFactory,
    CouponInvoiceVersionFactory,
    CouponFactory,
    CouponEligibilityFactory,
    CouponInvoiceFactory,
    CouponVersionFactory,
    LineFactory,
    ProductVersionFactory,
    CouponRedemptionFactory,
    OrderFactory,
)
from mitxpro.utils import now_in_utc

pytestmark = pytest.mark.django_db

# pylint: disable=redefined-outer-name

CYBERSOURCE_ACCESS_KEY = "access"
CYBERSOURCE_PROFILE_ID = "profile"
CYBERSOURCE_SECURITY_KEY = "security"
CYBERSOURCE_REFERENCE_PREFIX = "prefix"


CouponGroup = namedtuple(
    "CouponGroup",
    ["coupon", "coupon_version", "invoice", "invoice_version"],
    verbose=True,
)


@pytest.fixture(autouse=True)
def cybersource_settings(settings):
    """
    Set cybersource settings
    """
    settings.CYBERSOURCE_ACCESS_KEY = CYBERSOURCE_ACCESS_KEY
    settings.CYBERSOURCE_PROFILE_ID = CYBERSOURCE_PROFILE_ID
    settings.CYBERSOURCE_SECURITY_KEY = CYBERSOURCE_SECURITY_KEY
    settings.CYBERSOURCE_REFERENCE_PREFIX = CYBERSOURCE_REFERENCE_PREFIX


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

    coupongroup_worst = CouponGroup(coupon_worst, cv_worst, invoice_worst, civ_worst)
    coupongroup_best = CouponGroup(coupon_best, cv_best, invoice_best, civ_best)

    return SimpleNamespace(
        basket_item=basket_item,
        product_version=product_version,
        coupongroup_best=coupongroup_best,
        coupongroup_worst=coupongroup_worst,
    )


def test_valid_signature():
    """
    Signature is made up of a ordered key value list signed using HMAC 256 with a security key
    """
    payload = {"x": "y", "abc": "def", "key": "value", "signed_field_names": "abc,x"}
    signature = generate_cybersource_sa_signature(payload)

    message = ",".join(f"{key}={payload[key]}" for key in ["abc", "x"])

    digest = hmac.new(
        CYBERSOURCE_SECURITY_KEY.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    assert b64encode(digest).decode("utf-8") == signature


def test_signed_payload(mocker):
    """
    A valid payload should be signed appropriately
    """
    line1 = LineFactory.create()
    line2 = LineFactory.create(
        order=line1.order,
        product_version__product__content_object=CourseFactory.create(),
    )
    line3 = LineFactory.create(
        order=line1.order,
        product_version__product__content_object=ProgramFactory.create(),
    )
    order = line1.order
    username = "username"
    order.purchaser.username = username
    order.purchaser.save()
    transaction_uuid = "hex"

    now = now_in_utc()

    now_mock = mocker.patch("ecommerce.api.now_in_utc", autospec=True, return_value=now)

    mocker.patch(
        "ecommerce.api.uuid.uuid4",
        autospec=True,
        return_value=mocker.MagicMock(hex=transaction_uuid),
    )
    payload = generate_cybersource_sa_payload(order)
    signature = payload.pop("signature")
    assert generate_cybersource_sa_signature(payload) == signature
    signed_field_names = payload["signed_field_names"].split(",")
    assert signed_field_names == sorted(payload.keys())

    total_price = sum(line.product_version.price for line in [line1, line2, line3])

    assert payload == {
        "access_key": CYBERSOURCE_ACCESS_KEY,
        "amount": str(total_price),
        "consumer_id": username,
        "currency": "USD",
        "item_0_code": "course run",
        "item_0_name": line1.product_version.description,
        "item_0_quantity": line1.quantity,
        "item_0_sku": line1.product_version.product.content_object.id,
        "item_0_tax_amount": "0",
        "item_0_unit_price": str(line1.product_version.price),
        "item_1_code": "course",
        "item_1_name": line2.product_version.description,
        "item_1_quantity": line2.quantity,
        "item_1_sku": line2.product_version.product.content_object.id,
        "item_1_tax_amount": "0",
        "item_1_unit_price": str(line2.product_version.price),
        "item_2_code": "program",
        "item_2_name": line3.product_version.description,
        "item_2_quantity": line3.quantity,
        "item_2_sku": line3.product_version.product.content_object.id,
        "item_2_tax_amount": "0",
        "item_2_unit_price": str(line3.product_version.price),
        "line_item_count": 3,
        "locale": "en-us",
        "reference_number": make_reference_id(order),
        "profile_id": CYBERSOURCE_PROFILE_ID,
        "signed_date_time": now.strftime(ISO_8601_FORMAT),
        "signed_field_names": ",".join(signed_field_names),
        "transaction_type": "sale",
        "transaction_uuid": transaction_uuid,
        "unsigned_field_names": "",
    }
    now_mock.assert_called_once_with()


def test_make_reference_id():
    """
    make_reference_id should concatenate the reference prefix and the order id
    """
    order = OrderFactory.create()
    assert f"MITXPRO-{CYBERSOURCE_REFERENCE_PREFIX}-{order.id}" == make_reference_id(
        order
    )


def test_get_eligible_coupons(basket_and_coupons):
    """
    Verify that only eligible coupons for a product are returned
    """
    other_coupon = CouponFactory.create()
    eligible_coupons = list(
        get_eligible_coupons(basket_and_coupons.basket_item.product)
    )
    expected_coupons = [
        c.coupon.id
        for c in [
            basket_and_coupons.coupongroup_best,
            basket_and_coupons.coupongroup_worst,
        ]
    ]
    assert sorted(expected_coupons) == sorted(eligible_coupons)
    assert other_coupon.id not in eligible_coupons


def test_get_eligible_coupons_with_code(basket_and_coupons):
    """
    Verify that only eligible coupons for a product that match a specified code are returned
    """
    eligible_coupons = list(
        get_eligible_coupons(
            basket_and_coupons.basket_item.product,
            code=basket_and_coupons.coupongroup_worst.coupon.coupon_code,
        )
    )
    assert basket_and_coupons.coupongroup_worst.coupon.id in eligible_coupons
    assert basket_and_coupons.coupongroup_best.coupon.id not in eligible_coupons
    invalid_code_coupons = get_eligible_coupons(
        basket_and_coupons.basket_item.product, code="invalid_test_coupon_code"
    )
    assert not invalid_code_coupons


@pytest.mark.parametrize("auto_only", [True, False])
def test_get_valid_coupon_versions(basket_and_coupons, auto_only):
    """
    Verify that the correct valid CouponInvoiceVersions are returned for a list of coupons
    """
    coupon_ids = [
        c.coupon.id
        for c in [
            basket_and_coupons.coupongroup_best,
            basket_and_coupons.coupongroup_worst,
        ]
    ]
    best_versions = get_valid_coupon_versions(
        coupon_ids, basket_and_coupons.basket_item.basket.user, auto_only
    )
    expected_versions = [basket_and_coupons.coupongroup_worst.coupon_version]
    if not auto_only:
        expected_versions.append(basket_and_coupons.coupongroup_best.coupon_version)
    assert list(set(best_versions) - set(expected_versions)) == []


def test_get_valid_coupon_versions_bad_dates(basket_and_coupons):
    """
    Verify that expired or future CouponInvoiceVersions are not returned for a list of coupons
    """
    coupon_ids = [
        c.coupon.id
        for c in [
            basket_and_coupons.coupongroup_best,
            basket_and_coupons.coupongroup_worst,
        ]
    ]

    today = datetime.now(tz=pytz.UTC)
    civ_worst = basket_and_coupons.coupongroup_worst.coupon_version.invoice_version
    civ_worst.activation_date = today + timedelta(days=1)
    civ_worst.save()
    civ_best = basket_and_coupons.coupongroup_best.coupon_version.invoice_version
    civ_best.expiration_date = today - timedelta(days=1)
    civ_best.save()

    best_versions = get_valid_coupon_versions(
        coupon_ids, basket_and_coupons.basket_item.basket.user
    )
    assert best_versions == []


def test_get_valid_coupon_versions_over_redeemed(basket_and_coupons):
    """
    Verify that CouponInvoiceVersions that have exceeded redemption limits are not returned
    """
    coupon_ids = [
        c.coupon.id
        for c in [
            basket_and_coupons.coupongroup_best,
            basket_and_coupons.coupongroup_worst,
        ]
    ]

    civ_worst = basket_and_coupons.coupongroup_worst.coupon_version.invoice_version
    civ_worst.max_redemptions = 1
    civ_worst.save()
    CouponRedemptionFactory(
        coupon_version=basket_and_coupons.coupongroup_worst.coupon_version
    )

    civ_best = basket_and_coupons.coupongroup_best.coupon_version.invoice_version
    civ_best.max_redemptions_per_user = 1
    civ_best.save()
    CouponRedemptionFactory(
        coupon_version=basket_and_coupons.coupongroup_best.coupon_version,
        order=OrderFactory(purchaser=basket_and_coupons.basket_item.basket.user),
    )

    best_versions = get_valid_coupon_versions(
        coupon_ids, basket_and_coupons.basket_item.basket.user
    )
    assert best_versions == []


@pytest.mark.parametrize("auto_only", [True, False])
def test_get_best_coupon_version(basket_and_coupons, auto_only):
    """
    Verify that the CouponInvoiceVersion with the best price is returned for a bucket based on auto filter
    """
    best_cv = best_coupon_version(
        basket_and_coupons.basket_item.basket, auto_only=auto_only
    )
    if auto_only:
        assert best_cv == basket_and_coupons.coupongroup_worst.coupon_version
    else:
        assert best_cv == basket_and_coupons.coupongroup_best.coupon_version


@pytest.mark.parametrize("code", ["WORST", None])
def test_get_best_coupon_version_by_code(basket_and_coupons, code):
    """
    Verify that the CouponInvoiceVersion with the best price is returned for a bucket based on coupon code
    """
    best_cv = best_coupon_version(
        basket_and_coupons.basket_item.basket, auto_only=False, code=code
    )
    if code:
        assert best_cv == basket_and_coupons.coupongroup_worst.coupon_version
    else:
        assert best_cv == basket_and_coupons.coupongroup_best.coupon_version


def test_discount_price(basket_and_coupons):
    """
    Verify that the discount price is correctly calculated
    """
    coupon_version = basket_and_coupons.coupongroup_best.coupon_version
    price = basket_and_coupons.product_version.price
    discount = coupon_version.invoice_version.amount
    assert (
        discount_price(coupon_version, basket_and_coupons.basket_item.product)
        == price * discount
    )


def test_apply_coupon(basket_and_coupons):
    """
    Verify that a CouponSelection is created or updated
    """
    basket = basket_and_coupons.basket_item.basket
    best_coupon_version = basket_and_coupons.coupongroup_best.coupon_version
    worst_coupon_version = basket_and_coupons.coupongroup_worst.coupon_version
    new_selection = select_coupon(best_coupon_version, basket)
    assert new_selection.basket == basket
    assert new_selection.coupon == best_coupon_version.coupon

    updated_selection = select_coupon(worst_coupon_version, basket)
    assert updated_selection.basket == new_selection.basket
    assert updated_selection.coupon == worst_coupon_version.coupon
    assert updated_selection.pk == new_selection.pk


def test_redeem_coupon(basket_and_coupons):
    """
    Verify that a CouponRedemption is created or updated
    """
    order = OrderFactory()
    best_coupon_version = basket_and_coupons.coupongroup_best.coupon_version
    worst_coupon_version = basket_and_coupons.coupongroup_worst.coupon_version
    new_redemption = redeem_coupon(best_coupon_version, order)
    assert new_redemption.order == order
    assert new_redemption.coupon_version == best_coupon_version

    updated_redemption = redeem_coupon(worst_coupon_version, order)
    assert updated_redemption.order == new_redemption.order
    assert updated_redemption.coupon_version == worst_coupon_version
    assert updated_redemption.pk == new_redemption.pk
