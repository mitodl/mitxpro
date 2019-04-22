"""
Test for ecommerce functions
"""
from base64 import b64encode
from decimal import Decimal
from datetime import timedelta
import hashlib
import hmac

import pytest

from courses.factories import CourseFactory, ProgramFactory
from ecommerce.api import (
    create_unfulfilled_order,
    generate_cybersource_sa_payload,
    generate_cybersource_sa_signature,
    ISO_8601_FORMAT,
    make_reference_id,
    redeem_coupon,
    best_coupon_for_basket,
    get_new_order_by_reference_number,
    get_product_price,
    get_product_version_price_with_discount,
    get_valid_coupon_versions,
    latest_product_version,
    latest_coupon_version,
    get_product_courses,
    get_data_consents,
)
from ecommerce.exceptions import EcommerceException, ParseException
from ecommerce.factories import (
    BasketFactory,
    BasketItemFactory,
    CouponRedemptionFactory,
    CouponVersionFactory,
    LineFactory,
    OrderFactory,
    ProductVersionFactory,
    ProductFactory,
)
from ecommerce.models import (
    CouponSelection,
    CouponRedemption,
    Order,
    OrderAudit,
    DataConsentUser,
)
from mitxpro.utils import now_in_utc

pytestmark = pytest.mark.django_db

# pylint: disable=redefined-outer-name

CYBERSOURCE_ACCESS_KEY = "access"
CYBERSOURCE_PROFILE_ID = "profile"
CYBERSOURCE_SECURITY_KEY = "security"
CYBERSOURCE_REFERENCE_PREFIX = "prefix"


@pytest.fixture(autouse=True)
def cybersource_settings(settings):
    """
    Set cybersource settings
    """
    settings.CYBERSOURCE_ACCESS_KEY = CYBERSOURCE_ACCESS_KEY
    settings.CYBERSOURCE_PROFILE_ID = CYBERSOURCE_PROFILE_ID
    settings.CYBERSOURCE_SECURITY_KEY = CYBERSOURCE_SECURITY_KEY
    settings.CYBERSOURCE_REFERENCE_PREFIX = CYBERSOURCE_REFERENCE_PREFIX


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
    base_url = "https://example.com/base_url/"
    payload = generate_cybersource_sa_payload(order, base_url)
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
        "item_0_code": "course",
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
        "override_custom_cancel_page": base_url,
        "override_custom_receipt_page": base_url,
        "profile_id": CYBERSOURCE_PROFILE_ID,
        "signed_date_time": now.strftime(ISO_8601_FORMAT),
        "signed_field_names": ",".join(signed_field_names),
        "transaction_type": "sale",
        "transaction_uuid": transaction_uuid,
        "unsigned_field_names": "",
    }
    now_mock.assert_called_once_with()


def test_payload_overrides():
    """No overrides should be provided if the link is not https"""
    order = OrderFactory.create()
    payload = generate_cybersource_sa_payload(order, "http://base_url")
    assert "override_custom_cancel_page" not in payload
    assert "override_custom_receipt_page" not in payload


def test_payload_coupons():
    """Coupon discounts should be factored into the total"""
    line1 = LineFactory.create()
    line2 = LineFactory.create(
        order=line1.order,
        product_version__product__content_object=CourseFactory.create(),
    )
    order = line1.order
    username = "username"
    order.purchaser.username = username
    order.purchaser.save()

    coupon_version = CouponVersionFactory.create()
    # Coupon only eligible for line2, not line1
    CouponRedemption.objects.create(coupon_version=coupon_version, order=order)

    payload = generate_cybersource_sa_payload(order, "base")
    signature = payload.pop("signature")
    assert generate_cybersource_sa_signature(payload) == signature
    signed_field_names = payload["signed_field_names"].split(",")
    assert signed_field_names == sorted(payload.keys())

    total_price = sum(
        get_product_version_price_with_discount(
            product_version=line.product_version, coupon_version=coupon_version
        )
        for line in [line1, line2]
    )
    assert payload["amount"] == str(total_price)
    assert payload["item_0_unit_price"] == str(line1.product_version.price)
    assert payload["item_1_unit_price"] == str(line2.product_version.price)


def test_make_reference_id():
    """
    make_reference_id should concatenate the reference prefix and the order id
    """
    order = OrderFactory.create()
    assert f"MITXPRO-{CYBERSOURCE_REFERENCE_PREFIX}-{order.id}" == make_reference_id(
        order
    )


@pytest.mark.parametrize("auto_only", [True, False])
def test_get_valid_coupon_versions(basket_and_coupons, auto_only):
    """
    Verify that the correct valid CouponPaymentVersions are returned for a list of coupons
    """
    best_versions = get_valid_coupon_versions(
        basket_and_coupons.basket_item.product,
        basket_and_coupons.basket_item.basket.user,
        auto_only,
    )
    expected_versions = [basket_and_coupons.coupongroup_worst.coupon_version]
    if not auto_only:
        expected_versions.append(basket_and_coupons.coupongroup_best.coupon_version)
    assert set(best_versions) == set(expected_versions)


def test_get_valid_coupon_versions_bad_dates(basket_and_coupons):
    """
    Verify that expired or future CouponPaymentVersions are not returned for a list of coupons
    """
    today = now_in_utc()
    civ_worst = basket_and_coupons.coupongroup_worst.coupon_version.payment_version
    civ_worst.activation_date = today + timedelta(days=1)
    civ_worst.save()
    civ_best = basket_and_coupons.coupongroup_best.coupon_version.payment_version
    civ_best.expiration_date = today - timedelta(days=1)
    civ_best.save()

    best_versions = get_valid_coupon_versions(
        basket_and_coupons.basket_item.product,
        basket_and_coupons.basket_item.basket.user,
    )
    assert best_versions == []


@pytest.mark.parametrize("order_status", [Order.FULFILLED, Order.FAILED])
def test_get_valid_coupon_versions_over_redeemed(basket_and_coupons, order_status):
    """
    Verify that CouponPaymentVersions that have exceeded redemption limits are not returned
    """
    civ_worst = basket_and_coupons.coupongroup_worst.coupon_version.payment_version
    civ_worst.max_redemptions = 1
    civ_worst.save()
    CouponRedemptionFactory(
        coupon_version=basket_and_coupons.coupongroup_worst.coupon_version,
        order=OrderFactory(status=order_status),
    )

    civ_best = basket_and_coupons.coupongroup_best.coupon_version.payment_version
    civ_best.max_redemptions_per_user = 1
    civ_best.save()
    CouponRedemptionFactory(
        coupon_version=basket_and_coupons.coupongroup_best.coupon_version,
        order=OrderFactory(
            purchaser=basket_and_coupons.basket_item.basket.user, status=order_status
        ),
    )

    best_versions = get_valid_coupon_versions(
        basket_and_coupons.basket_item.product,
        basket_and_coupons.basket_item.basket.user,
    )
    if order_status == Order.FULFILLED:
        assert best_versions == []
    else:
        assert best_versions == [
            basket_and_coupons.coupongroup_best.coupon_version,
            basket_and_coupons.coupongroup_worst.coupon_version,
        ]


@pytest.mark.parametrize("auto_only", [True, False])
def test_get_best_coupon_for_basket(basket_and_coupons, auto_only):
    """
    Verify that the CouponPaymentVersion with the best price is returned for a bucket based on auto filter
    """
    best_cv = best_coupon_for_basket(
        basket_and_coupons.basket_item.basket, auto_only=auto_only
    )
    if auto_only:
        assert best_cv == basket_and_coupons.coupongroup_worst.coupon_version
    else:
        assert best_cv == basket_and_coupons.coupongroup_best.coupon_version


@pytest.mark.parametrize("code", ["WORST", None])
def test_get_best_coupon_for_basket_by_code(basket_and_coupons, code):
    """
    Verify that the CouponPaymentVersion with the best price is returned for a bucket based on coupon code
    """
    best_cv = best_coupon_for_basket(
        basket_and_coupons.basket_item.basket, auto_only=False, code=code
    )
    if code:
        assert best_cv == basket_and_coupons.coupongroup_worst.coupon_version
    else:
        assert best_cv == basket_and_coupons.coupongroup_best.coupon_version


def test_get_best_coupon_for_basket_empty_basket():
    """
    Verify that the best_coupon_version() returns None if the basket has no product
    """
    assert best_coupon_for_basket(BasketFactory()) is None


def test_get_best_coupon_for_basket_no_coupons():
    """
    Verify that best_coupon_version() returns None if the product has no coupons
    """
    basket_item = BasketItemFactory()
    ProductVersionFactory(product=basket_item.product, price=Decimal(25.00))
    assert best_coupon_for_basket(basket_item.basket) is None


def test_get_best_coupon_for_basket_no_valid_coupons(basket_and_coupons):
    """
    Verify that best_coupon_version() returns None if the product coupons are invalid
    """
    today = now_in_utc()
    civ_worst = basket_and_coupons.coupongroup_worst.coupon_version.payment_version
    civ_worst.activation_date = today + timedelta(days=1)
    civ_worst.save()

    assert (
        best_coupon_for_basket(basket_and_coupons.basket_item.basket, code="WORST")
        is None
    )


def test_latest_coupon_version(basket_and_coupons):
    """
    Verify that the most recent coupon version is returned
    """
    coupon = basket_and_coupons.coupongroup_best.coupon
    assert (
        latest_coupon_version(coupon)
        == basket_and_coupons.coupongroup_best.coupon_version
    )
    new_version = CouponVersionFactory.create(coupon=coupon)
    assert latest_coupon_version(coupon) == new_version


def test_discount_price(basket_and_coupons):
    """
    Verify that the most recent coupon version is returned
    """
    coupon = basket_and_coupons.coupongroup_best.coupon
    assert (
        latest_coupon_version(coupon)
        == basket_and_coupons.coupongroup_best.coupon_version
    )
    new_version = CouponVersionFactory.create(coupon=coupon)
    assert latest_coupon_version(coupon) == new_version


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


def test_latest_product_version(basket_and_coupons):
    """
    Verify that the most recent product version is returned
    """
    product = basket_and_coupons.basket_item.product
    assert latest_product_version(product) == basket_and_coupons.product_version
    new_version = ProductVersionFactory.create(product=product)
    assert latest_product_version(product) == new_version


def test_get_product_price(basket_and_coupons):
    """
    Verify that the correct price for a product is returned
    """
    expected_price = (
        basket_and_coupons.basket_item.product.productversions.order_by("-created_on")
        .first()
        .price
    )
    assert expected_price == get_product_price(basket_and_coupons.basket_item.product)


@pytest.mark.parametrize("has_coupon", [True, False])
def test_get_product_version_price_with_discount(has_coupon, basket_and_coupons):
    """
    get_product_version_price_with_discount should check if the coupon exists and if so calculate price based on its
    discount.
    """
    product_version = basket_and_coupons.basket_item.product.productversions.order_by(
        "-created_on"
    ).first()
    product_version.price = Decimal("123.45")
    product_version.save()

    coupon_version = basket_and_coupons.coupongroup_best.coupon_version
    # Make sure to test that we round the results
    coupon_version.payment_version.amount = Decimal("0.5")
    price = get_product_version_price_with_discount(
        coupon_version=coupon_version if has_coupon else None,
        product_version=product_version,
    )
    assert price == (Decimal("61.72") if has_coupon else Decimal("123.45"))


def test_get_new_order_by_reference_number(basket_and_coupons):
    """
    get_new_order_by_reference_number returns an Order with status created
    """
    user = basket_and_coupons.basket_item.basket.user
    order = create_unfulfilled_order(user)
    same_order = get_new_order_by_reference_number(make_reference_id(order))
    assert same_order.id == order.id


@pytest.mark.parametrize(
    "reference_number, error",
    [
        ("XYZ-1-3", "Reference number must start with MITXPRO-"),
        ("MITXPRO-no_dashes_here", "Unable to find order number in reference number"),
        ("MITXPRO-something-NaN", "Unable to parse order number"),
        ("MITXPRO-not_matching-3", "CyberSource prefix doesn't match"),
    ],
)
def test_get_new_order_by_reference_number_parse_error(reference_number, error):
    """
    Test parse errors are handled well
    """
    with pytest.raises(ParseException) as ex:
        get_new_order_by_reference_number(reference_number=reference_number)
    assert ex.value.args[0] == error


def test_get_new_order_by_reference_number_missing(basket_and_coupons):
    """
    get_new_order_by_reference_number should error when the Order id is not found
    """
    user = basket_and_coupons.basket_item.basket.user
    order = create_unfulfilled_order(user)

    with pytest.raises(EcommerceException) as ex:
        # change order number to something not likely to already exist in database
        order.id = 98_765_432
        assert not Order.objects.filter(id=order.id).exists()
        get_new_order_by_reference_number(make_reference_id(order))
    assert ex.value.args[0] == f"Unable to find order {order.id}"


@pytest.mark.parametrize("has_coupon", [True, False])
def test_create_order(
    has_coupon, basket_and_coupons
):  # pylint: disable=too-many-locals
    """
    Create Order from a purchasable course
    """
    coupon = basket_and_coupons.coupongroup_best.coupon
    basket = basket_and_coupons.basket_item.basket
    basket.couponselection_set.all().delete()
    user = basket.user
    if has_coupon:
        CouponSelection.objects.create(coupon=coupon, basket=basket)

    order = create_unfulfilled_order(user)
    assert Order.objects.count() == 1
    assert order.status == Order.CREATED
    assert order.purchaser == user

    assert order.lines.count() == 1
    line = order.lines.first()
    assert line.product_version == latest_product_version(
        basket_and_coupons.basket_item.product
    )
    assert line.quantity == basket_and_coupons.basket_item.quantity

    assert OrderAudit.objects.count() == 1
    order_audit = OrderAudit.objects.first()
    assert order_audit.order == order
    assert order_audit.data_after == order.to_dict()

    # data_before only has updated_on different, since we only call save_and_log
    # after Order is already created
    data_before = order_audit.data_before
    dict_before = order.to_dict()
    del data_before["updated_on"]
    del dict_before["updated_on"]
    assert data_before == dict_before

    if has_coupon:
        assert (
            CouponRedemption.objects.filter(
                order=order,
                coupon_version=basket_and_coupons.coupongroup_best.coupon_version,
            ).count()
            == 1
        )
    else:
        assert CouponRedemption.objects.count() == 0


def test_get_product_courses():
    """
    Verify that the correct list of courses for a product is returned
    """
    program = ProgramFactory.create()
    CourseFactory.create_batch(5, program=program)
    courserun_product = ProductFactory.create()
    course_product = ProductFactory.create(content_object=CourseFactory.create())
    program_product = ProductFactory.create(content_object=program)
    assert get_product_courses(courserun_product) == [
        courserun_product.content_object.course
    ]
    assert get_product_courses(course_product) == [course_product.content_object]
    assert list(get_product_courses(program_product)) == list(
        program_product.content_object.courses.all()
    )


def test_get_data_consents(basket_and_coupons, basket_and_agreement):
    """
    Verify that the correct list of DataConsentUsers is returned for a basket
    """
    assert list(get_data_consents(basket_and_coupons.basket)) == []
    assert list(get_data_consents(basket_and_agreement.basket)) == [
        DataConsentUser.objects.get(
            agreement=basket_and_agreement.agreement,
            user=basket_and_agreement.basket.user,
            coupon=basket_and_agreement.coupon,
        )
    ]
