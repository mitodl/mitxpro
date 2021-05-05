"""
Test for ecommerce functions
"""
from base64 import b64encode
from collections import defaultdict
from decimal import Decimal
from datetime import timedelta
import hashlib
import hmac
from unittest.mock import PropertyMock
import uuid

import factory
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import ValidationError
import pytest

from affiliate.factories import AffiliateFactory
from courses.models import CourseRunEnrollment, ProgramEnrollment, CourseRun, Program
from courses.factories import (
    CourseFactory,
    ProgramFactory,
    CourseRunFactory,
    CourseRunEnrollmentFactory,
    ProgramRunFactory,
)
from ecommerce.api import (
    create_coupons,
    create_unfulfilled_order,
    generate_cybersource_sa_payload,
    generate_cybersource_sa_signature,
    get_readable_id,
    ISO_8601_FORMAT,
    redeem_coupon,
    get_product_price,
    get_product_version_price_with_discount,
    get_valid_coupon_versions,
    latest_product_version,
    latest_coupon_version,
    make_receipt_url,
    get_product_courses,
    get_available_bulk_product_coupons,
    get_full_price_coupon_product_set,
    get_or_create_data_consent_users,
    bulk_assign_product_coupons,
    validate_basket_for_checkout,
    complete_order,
    enroll_user_in_order_items,
    fetch_and_serialize_unused_coupons,
    get_product_from_text_id,
    get_product_from_querystring_id,
    best_coupon_for_product,
)
from ecommerce.factories import (
    BasketFactory,
    CompanyFactory,
    CouponRedemptionFactory,
    CouponSelectionFactory,
    CouponVersionFactory,
    CouponFactory,
    CouponPaymentVersionFactory,
    LineFactory,
    OrderFactory,
    ProductVersionFactory,
    ProductFactory,
    CourseRunSelectionFactory,
    CouponEligibilityFactory,
    ProductCouponAssignmentFactory,
    BulkCouponAssignmentFactory,
    BasketItemFactory,
    LineRunSelectionFactory,
    CouponPaymentFactory,
)
from ecommerce.models import (
    BasketItem,
    Coupon,
    CouponPaymentVersion,
    CouponSelection,
    CouponRedemption,
    CourseRunSelection,
    DataConsentUser,
    Order,
    OrderAudit,
    Product,
    ProductCouponAssignment,
    LineRunSelection,
)
from ecommerce.test_utils import unprotect_version_tables
from mitxpro.test_utils import update_namespace
from mitxpro.utils import now_in_utc
from voucher.factories import VoucherFactory
from voucher.models import Voucher

pytestmark = pytest.mark.django_db
lazy = pytest.lazy_fixture
# pylint: disable=redefined-outer-name,too-many-lines,unused-argument,too-many-arguments

CYBERSOURCE_ACCESS_KEY = "access"
CYBERSOURCE_PROFILE_ID = "profile"
CYBERSOURCE_SECURITY_KEY = "security"


@pytest.fixture(autouse=True)
def cybersource_settings(settings):
    """
    Set cybersource settings
    """
    settings.CYBERSOURCE_ACCESS_KEY = CYBERSOURCE_ACCESS_KEY
    settings.CYBERSOURCE_PROFILE_ID = CYBERSOURCE_PROFILE_ID
    settings.CYBERSOURCE_SECURITY_KEY = CYBERSOURCE_SECURITY_KEY


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


def test_make_receipt_url():
    """make_receipt_url should generate a URL for use by users returning from a successful CyberSource payment"""
    assert (
        make_receipt_url(base_url="https://mit.edu/", readable_id="a readable id")
        == "https://mit.edu/dashboard/?status=purchased&purchased=a+readable+id"
    )


def test_get_readable_id():
    """get_readable_id should get the readable id for a CourseRun or a Program"""
    run = CourseRunFactory.create()
    assert get_readable_id(run) == run.courseware_id
    assert get_readable_id(run.course.program) == run.course.program.readable_id


# pylint: disable=too-many-locals
@pytest.mark.parametrize("has_coupon", [True, False])
@pytest.mark.parametrize("has_company", [True, False])
@pytest.mark.parametrize("is_program_product", [True, False])
@pytest.mark.parametrize("user_ip", ["194.100.0.1", "", None])
@pytest.mark.flaky(max_runs=3, min_passes=1)
def test_signed_payload(mocker, has_coupon, has_company, is_program_product, user_ip):
    """
    A valid payload should be signed appropriately
    """
    line1 = LineFactory.create(
        product_version__product__content_object=ProgramFactory.create()
        if is_program_product
        else CourseRunFactory.create()
    )
    line2 = LineFactory.create(
        order=line1.order,
        product_version__product__content_object=CourseRunFactory.create(),
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

    payment_transaction_number = "transaction_number"
    if has_coupon:
        coupon_version = CouponRedemptionFactory.create(
            order=order,
            coupon_version__payment_version__payment_type=CouponPaymentVersion.PAYMENT_PO,
            coupon_version__payment_version__payment_transaction=payment_transaction_number,
            **(
                {"coupon_version__payment_version__company": None}
                if not has_company
                else {}
            ),
        ).coupon_version

    now = now_in_utc()

    now_mock = mocker.patch("ecommerce.api.now_in_utc", autospec=True, return_value=now)

    mocker.patch(
        "ecommerce.api.uuid.uuid4",
        autospec=True,
        return_value=mocker.MagicMock(hex=transaction_uuid),
    )
    receipt_url = "https://example.com/base_url/receipt/"
    cancel_url = "https://example.com/base_url/cancel/"
    payload = generate_cybersource_sa_payload(
        order=order, receipt_url=receipt_url, cancel_url=cancel_url, ip_address=user_ip
    )
    signature = payload.pop("signature")
    assert generate_cybersource_sa_signature(payload) == signature
    signed_field_names = payload["signed_field_names"].split(",")
    assert signed_field_names == sorted(payload.keys())

    total_price = sum(line.product_version.price for line in [line1, line2, line3])

    content_object = line1.product_version.product.content_object

    other_merchant_fields = (
        {
            "merchant_defined_data4": coupon_version.coupon.coupon_code,
            "merchant_defined_data5": coupon_version.payment_version.company.name
            if coupon_version.payment_version.company
            else "",
            "merchant_defined_data6": payment_transaction_number,
            "merchant_defined_data7": CouponPaymentVersion.PAYMENT_PO,
        }
        if has_coupon
        else {}
    )

    assert payload == {
        "access_key": CYBERSOURCE_ACCESS_KEY,
        "amount": str(total_price),
        "consumer_id": username,
        "currency": "USD",
        "item_0_code": "program" if is_program_product else "course run",
        "item_0_name": line1.product_version.description,
        "item_0_quantity": line1.quantity,
        "item_0_sku": line1.product_version.product.content_object.id,
        "item_0_tax_amount": "0",
        "item_0_unit_price": str(line1.product_version.price),
        "item_1_code": "course run",
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
        "reference_number": order.reference_number,
        "override_custom_receipt_page": receipt_url,
        "override_custom_cancel_page": cancel_url,
        "profile_id": CYBERSOURCE_PROFILE_ID,
        "signed_date_time": now.strftime(ISO_8601_FORMAT),
        "signed_field_names": ",".join(signed_field_names),
        "transaction_type": "sale",
        "transaction_uuid": transaction_uuid,
        "unsigned_field_names": "",
        "merchant_defined_data1": "program" if is_program_product else "course run",
        "merchant_defined_data2": content_object.readable_id
        if is_program_product
        else content_object.courseware_id,
        "merchant_defined_data3": "1",
        **other_merchant_fields,
        "customer_ip_address": user_ip if user_ip else None,
    }
    now_mock.assert_called_once_with()


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
    assert str(coupon_version) == "CouponVersion {} for {}".format(
        coupon_version.coupon.coupon_code, str(coupon_version.payment_version)
    )
    # Coupon only eligible for line2, not line1
    CouponRedemption.objects.create(coupon_version=coupon_version, order=order)

    payload = generate_cybersource_sa_payload(
        order=order, receipt_url="receipt", cancel_url="cancel"
    )
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


@pytest.mark.parametrize("auto_only", [True, False])
def test_get_valid_coupon_versions(basket_and_coupons, auto_only):
    """
    Verify that the correct valid CouponPaymentVersions are returned for a list of coupons
    """
    best_versions = list(
        get_valid_coupon_versions(
            basket_and_coupons.basket_item.product,
            basket_and_coupons.basket_item.basket.user,
            auto_only,
        )
    )
    expected_versions = [basket_and_coupons.coupongroup_worst.coupon_version]
    if not auto_only:
        expected_versions.append(basket_and_coupons.coupongroup_best.coupon_version)
    assert set(best_versions) == set(expected_versions)


@pytest.mark.parametrize("is_global", [True, False])
def test_get_valid_coupon_versions_after_redemption(user, is_global):
    """
    Verify that the correct valid CouponPaymentVersions are returned before and after redemption
    """
    payment = CouponPaymentFactory()
    civ_old = CouponPaymentVersionFactory(
        payment=payment,
        amount=Decimal("0.50000"),
        max_redemptions_per_user=1,
        num_coupon_codes=1,
    )
    civ_new = CouponPaymentVersionFactory(
        payment=payment,
        amount=Decimal("1.00000"),
        max_redemptions_per_user=1,
        num_coupon_codes=1,
    )
    coupon = CouponFactory(
        payment=payment, coupon_code="TESTCOUPON1", is_global=is_global
    )
    CouponVersionFactory(payment_version=civ_old, coupon=coupon)
    cv_new = CouponVersionFactory(payment_version=civ_new, coupon=coupon)

    product = ProductFactory()
    if not is_global:
        CouponEligibilityFactory.create(coupon=coupon, product=product)

    coupon_versions = list(get_valid_coupon_versions(product, user))
    expected_versions = [cv_new]
    assert coupon_versions == expected_versions

    order = OrderFactory.create(purchaser=user, status=Order.FULFILLED)
    redeem_coupon(cv_new, order)
    assert list(get_valid_coupon_versions(product, user)) == []


@pytest.mark.parametrize("is_global", [True, False])
def test_get_valid_coupon_versions_with_max_redemptions_per_user(user, is_global):
    """
    Verify that the correct CouponPaymentVersions are returned before and after redemption
    """
    amount = "1.00000"
    coupon_code = "TESTCOUPON1"
    coupon_type = CouponPaymentVersion.PROMO
    max_redemptions = 3
    max_redemptions_per_user = 2

    coupon_payment_version = CouponPaymentVersionFactory.create(
        amount=Decimal(amount),
        coupon_type=coupon_type,
        max_redemptions=max_redemptions,
        max_redemptions_per_user=max_redemptions_per_user,
        num_coupon_codes=1,
    )
    coupon_version = CouponVersionFactory.create(
        payment_version=coupon_payment_version,
        coupon__coupon_code=coupon_code,
        coupon__is_global=is_global,
    )
    products = ProductFactory.create_batch(max_redemptions_per_user + 1)
    if not is_global:
        CouponEligibilityFactory.create_batch(
            len(products),
            coupon=coupon_version.coupon,
            product=factory.Iterator(products),
        )

    assert list(get_valid_coupon_versions(products[0], user, code=coupon_code)) == [
        coupon_version
    ]
    redeem_coupon(
        coupon_version=coupon_version,
        order=OrderFactory.create(purchaser=user, status=Order.FULFILLED),
    )

    assert list(get_valid_coupon_versions(products[1], user, code=coupon_code)) == [
        coupon_version
    ]
    redeem_coupon(
        coupon_version=coupon_version,
        order=OrderFactory.create(purchaser=user, status=Order.FULFILLED),
    )

    # max_redemptions_per_user was set to 2, so the coupon should no longer be valid for this user
    assert list(get_valid_coupon_versions(products[2], user, code=coupon_code)) == []


def test_global_coupons_apply_all_products(user):
    """
    Verify that a coupon created with is_global=True is valid for all products, even those
    created after the coupon.
    """
    coupon = CouponVersionFactory(coupon__is_global=True, coupon__enabled=True).coupon
    CouponVersionFactory.create(coupon__enabled=True)

    coupon_version = coupon.versions.first()

    CouponPaymentVersionFactory(payment=coupon.payment, amount=Decimal(1))
    product = ProductVersionFactory.create().product
    product_2 = ProductVersionFactory.create().product
    versions = get_valid_coupon_versions(product, user)

    # Check that only the global coupon is returned
    assert coupon.is_global
    assert len(versions) == 1
    assert versions[0] == coupon_version

    # Check that the global coupon is applied to all products
    assert best_coupon_for_product(product, user) == coupon_version
    assert best_coupon_for_product(product_2, user) == coupon_version


def test_get_valid_coupon_versions_bad_dates(basket_and_coupons):
    """
    Verify that expired or future CouponPaymentVersions are not returned for a list of coupons
    """
    today = now_in_utc()
    with unprotect_version_tables():
        civ_worst = basket_and_coupons.coupongroup_worst.coupon_version.payment_version
        civ_worst.activation_date = today + timedelta(days=1)
        civ_worst.save()
        civ_best = basket_and_coupons.coupongroup_best.coupon_version.payment_version
        civ_best.expiration_date = today - timedelta(days=1)
        civ_best.save()

    best_versions = list(
        get_valid_coupon_versions(
            basket_and_coupons.basket_item.product,
            basket_and_coupons.basket_item.basket.user,
        )
    )
    assert best_versions == []


def test_get_valid_coupon_versions_full_discount(basket_and_coupons):
    """Verify that only 100% coupons are returned if full_discount kwarg is True"""
    assert list(
        get_valid_coupon_versions(
            basket_and_coupons.basket_item.product,
            basket_and_coupons.basket_item.basket.user,
            full_discount=True,
        )
    ) == [basket_and_coupons.coupongroup_best.coupon_version]
    assert basket_and_coupons.coupongroup_best.payment_version.amount == Decimal(1.0)


def test_get_valid_coupon_versions_by_company(basket_and_coupons):
    """Verify that valid coupons are filtered by company"""
    company = basket_and_coupons.coupongroup_worst.payment_version.company
    assert list(
        get_valid_coupon_versions(
            basket_and_coupons.basket_item.product,
            basket_and_coupons.basket_item.basket.user,
            company=company,
        )
    ) == [basket_and_coupons.coupongroup_worst.coupon_version]


@pytest.mark.parametrize(
    "order_status", [Order.FULFILLED, Order.FAILED, Order.REFUNDED]
)
def test_get_valid_coupon_versions_over_redeemed(basket_and_coupons, order_status):
    """
    Verify that CouponPaymentVersions that have exceeded redemption limits are not returned
    """
    with unprotect_version_tables():
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
                purchaser=basket_and_coupons.basket_item.basket.user,
                status=order_status,
            ),
        )

    best_versions = list(
        get_valid_coupon_versions(
            basket_and_coupons.basket_item.product,
            basket_and_coupons.basket_item.basket.user,
        )
    )
    if order_status in (Order.FULFILLED, Order.REFUNDED):
        assert best_versions == []
    else:
        assert best_versions == [
            basket_and_coupons.coupongroup_best.coupon_version,
            basket_and_coupons.coupongroup_worst.coupon_version,
        ]


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
    with unprotect_version_tables():
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


@pytest.mark.parametrize("hubspot_api_key", [None, "fake-key"])
def test_get_by_reference_number(
    settings, validated_basket, basket_and_coupons, mock_hubspot_syncs, hubspot_api_key
):
    """
    get_by_reference_number returns an Order with status created
    """
    settings.HUBSPOT_API_KEY = hubspot_api_key
    order = create_unfulfilled_order(validated_basket)
    same_order = Order.objects.get_by_reference_number(order.reference_number)
    assert same_order.id == order.id
    if hubspot_api_key:
        assert mock_hubspot_syncs.order.called_with(order.id)
    else:
        assert mock_hubspot_syncs.order.not_called()


def test_get_by_reference_number_missing(validated_basket):
    """
    get_by_reference_number should return an empty queryset if the order id is missing
    """
    order = create_unfulfilled_order(validated_basket)

    # change order number to something not likely to already exist in database
    order.id = 98_765_432
    assert not Order.objects.filter(id=order.id).exists()
    with pytest.raises(Order.DoesNotExist):
        Order.objects.get_by_reference_number(order.reference_number)


@pytest.mark.parametrize("hubspot_api_key", [None, "fake-key"])
@pytest.mark.parametrize("has_coupon", [True, False])
def test_create_unfulfilled_order(
    settings,
    validated_basket,
    has_coupon,
    basket_and_coupons,
    hubspot_api_key,
    mock_hubspot_syncs,
):  # pylint: disable=too-many-locals
    """
    create_unfulfilled_order should create an Order from a purchasable course
    """
    settings.HUBSPOT_API_KEY = hubspot_api_key
    new_validated_basket = validated_basket
    if not has_coupon:
        new_validated_basket = update_namespace(validated_basket, coupon_version=None)

    order = create_unfulfilled_order(new_validated_basket)
    assert Order.objects.count() == 1
    assert order.status == Order.CREATED
    assert order.purchaser == new_validated_basket.basket.user

    assert order.lines.count() == 1
    line = order.lines.first()
    assert line.product_version == latest_product_version(
        basket_and_coupons.basket_item.product
    )
    assert line.quantity == basket_and_coupons.basket_item.quantity
    line_run_selections = LineRunSelection.objects.filter(
        line=line, run_id__in={basket_and_coupons.run.id}
    )
    assert line_run_selections.count() == 1

    assert OrderAudit.objects.count() == 0

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

    if hubspot_api_key:
        assert mock_hubspot_syncs.order.called_with(order.id)
    else:
        assert mock_hubspot_syncs.order.not_called()


@pytest.mark.parametrize("has_program_run", [True, False])
def test_create_unfulfilled_order_program_run(validated_basket, has_program_run):
    """
    create_unfulfilled_order should associate a ProgramRunLine with a Line in an order if
    the basket item has a program run attached
    """
    basket_item = BasketItemFactory.create(
        basket=validated_basket.basket, with_program_run=has_program_run
    )
    product_version = ProductVersionFactory(product=basket_item.product)
    new_validated_basket = update_namespace(
        validated_basket, basket_item=basket_item, product_version=product_version
    )

    order = create_unfulfilled_order(new_validated_basket)
    assert order.lines.count() == 1
    line = order.lines.first()
    if has_program_run:
        assert line.programrunline.program_run == basket_item.program_run
    else:
        with pytest.raises(ObjectDoesNotExist):
            line.programrunline  # pylint: disable=pointless-statement


def test_create_unfulfilled_order_affiliate(validated_basket):
    """
    create_unfulfilled_order should add a database record tracking the order creation if an affiliate id is passed in
    """
    affiliate = AffiliateFactory.create()
    order = create_unfulfilled_order(validated_basket, affiliate_id=affiliate.id)
    affiliate_referral_action = order.affiliate_order_actions.first()
    assert affiliate_referral_action.affiliate == affiliate
    assert affiliate_referral_action.created_order == order


def test_get_product_courses():
    """
    Verify that the correct list of courses for a product is returned
    """
    program = ProgramFactory.create()
    courses = CourseFactory.create_batch(5, program=program)
    courserun_product = ProductFactory.create(content_object=CourseRunFactory.create())
    course_product = ProductFactory.create(content_object=courses[0])
    program_product = ProductFactory.create(content_object=program)
    assert get_product_courses(courserun_product) == [
        courserun_product.content_object.course
    ]
    assert get_product_courses(course_product) == [course_product.content_object]
    assert list(get_product_courses(program_product)) == list(
        program_product.content_object.courses.all().order_by("position_in_program")
    )


def test_get_available_bulk_product_coupons():
    """
    get_available_bulk_product_coupons should return a queryset of CouponEligibility objects that can be sent out in
    bulk enrollment invitations
    """
    first_product_coupon = CouponEligibilityFactory.create(coupon__enabled=True)
    assert str(
        first_product_coupon
    ) == "CouponProduct for product {}, coupon {}".format(
        first_product_coupon.product, first_product_coupon.coupon
    )
    # Create more valid product coupons that apply to the same payment and product
    additional_product_coupons = CouponEligibilityFactory.create_batch(
        3,
        coupon__enabled=True,
        coupon__payment=first_product_coupon.coupon.payment,
        product=first_product_coupon.product,
    )
    # Create existing deliveries for the last two, rendering them invalid
    ProductCouponAssignmentFactory.create_batch(
        2, product_coupon=factory.Iterator(additional_product_coupons[1:])
    )
    # Create another product coupon that should not be valid due to it not being enabled
    CouponEligibilityFactory.create(
        coupon__enabled=False,
        coupon__payment=first_product_coupon.coupon.payment,
        product=first_product_coupon.product,
    )

    available_qset = get_available_bulk_product_coupons(
        first_product_coupon.coupon.payment.id, first_product_coupon.product.id
    )
    assert available_qset.count() == 2
    assert list(available_qset) == [first_product_coupon, additional_product_coupons[0]]


def test_get_full_price_coupon_product_set():
    """get_full_price_coupon_product_set should yield 100%-off coupons paired with the products they apply to"""
    coupons = CouponFactory.create_batch(
        4, enabled=factory.Iterator([True, True, True, False])
    )
    # Create two 100% coupons
    valid_payment_versions = CouponPaymentVersionFactory.create_batch(
        2,
        amount=1,
        payment=factory.Iterator([coupon.payment for coupon in coupons[0:2]]),
        coupon_type=CouponPaymentVersion.SINGLE_USE,
    )
    # Create another 100% coupon, then deprecate it with a newer 50% version
    CouponPaymentVersionFactory.create_batch(
        2,
        amount=factory.Iterator([1, 0.5]),
        payment=coupons[2].payment,
        coupon_type=CouponPaymentVersion.SINGLE_USE,
    )
    # Create another 100% coupon with a disabled Coupon
    CouponPaymentVersionFactory.create(
        amount=1,
        payment=coupons[3].payment,
        coupon_type=CouponPaymentVersion.SINGLE_USE,
    )
    product_coupons = CouponEligibilityFactory.create_batch(
        len(coupons), coupon=factory.Iterator(coupons)
    )
    # Also apply the second full price coupon payment to the same product as that the first applies to. This will test
    # to make sure that the "products" map doesn't have repeat entries for the same product.
    first_coupon_product = product_coupons[0].product
    product_coupons.insert(
        2,
        CouponEligibilityFactory.create(
            product=first_coupon_product, coupon=product_coupons[1].coupon
        ),
    )

    coupon_product_pairs = list(get_full_price_coupon_product_set())
    assert len(coupon_product_pairs) == len(valid_payment_versions)
    try:
        assert [pair[0] for pair in coupon_product_pairs] == [
            payment_version.payment for payment_version in valid_payment_versions
        ]
    except AssertionError:
        assert [pair[0] for pair in reversed(coupon_product_pairs)] == [
            payment_version.payment for payment_version in valid_payment_versions
        ]

    first_product_qset = coupon_product_pairs[0][1]
    assert first_product_qset.first() == product_coupons[0].product
    second_product_qset = coupon_product_pairs[1][1]
    try:
        assert set(second_product_qset) == {
            product_coupon.product for product_coupon in product_coupons[1:3]
        }
    except AssertionError:
        assert second_product_qset.first() == product_coupons[2:3][0].product


def test_bulk_assign_product_coupons():
    """
    bulk_assign_product_coupons should pair emails with available coupons, assign the coupons to those
    emails, and group them by a bulk assignment record.
    """
    emails = sorted(["abc@example.com", "def@example.com", "ghi@example.com"])
    product_coupons = CouponEligibilityFactory.create_batch(len(emails) + 2)
    paired_email_coupon_assignments = list(zip(emails, product_coupons))

    # Pass in generators to make sure there isn't any issue with email/product coupon iterables being exhausted
    bulk_assignment, new_assignments = bulk_assign_product_coupons(
        zip(emails, [pc.id for pc in product_coupons])
    )
    assert list(new_assignments) == list(ProductCouponAssignment.objects.order_by("id"))
    assert len(new_assignments) == len(emails)
    assert paired_email_coupon_assignments == [
        (a.email, a.product_coupon) for a in new_assignments
    ]
    assert all(a.bulk_assignment_id == bulk_assignment.id for a in new_assignments)


@pytest.mark.parametrize("has_coupon", [True, False])
def test_validate_basket_all_good(basket_and_coupons, has_coupon):
    """If everything is valid no exception should be raised"""
    if not has_coupon:
        CouponSelection.objects.all().delete()
    validated_basket = validate_basket_for_checkout(basket_and_coupons.basket.user)
    assert validated_basket.basket == basket_and_coupons.basket
    assert validated_basket.basket_item == basket_and_coupons.basket_item
    assert validated_basket.product_version == basket_and_coupons.product_version
    if has_coupon:
        assert (
            validated_basket.coupon_version
            == basket_and_coupons.coupongroup_best.coupon_version
        )
    else:
        assert validated_basket.coupon_version is None
    assert validated_basket.run_selection_ids == {basket_and_coupons.run.id}


def test_validate_basket_no_item(basket_and_coupons):
    """An empty basket should be rejected"""
    BasketItem.objects.all().delete()
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket.user)
    assert "No items in basket" in ex.value.args[0]["items"]


def test_validate_basket_two_items(basket_and_coupons):
    """A basket with multiple items should be rejected """
    BasketItem.objects.create(
        product=Product.objects.first(), quantity=1, basket=basket_and_coupons.basket
    )
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket.user)
    assert "Something went wrong" in ex.value.args[0]["items"]


def test_validate_basket_two_coupons(basket_and_coupons):
    """A basket cannot have multiple coupons"""
    CouponSelectionFactory.create(basket=basket_and_coupons.basket)
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket.user)
    assert "Something went wrong with your coupon" in ex.value.args[0]["coupons"]


def test_validate_basket_invalid_coupon(mocker, basket_and_coupons):
    """An invalid coupon should be rejected in the basket"""
    patched_get_coupon_versions = mocker.patch(
        "ecommerce.api.get_valid_coupon_versions", return_value=[]
    )
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket.user)
    assert "Coupon is not valid" in ex.value.args[0]["coupons"]
    patched_get_coupon_versions.assert_called_once_with(
        product=basket_and_coupons.product_version.product,
        user=basket_and_coupons.basket.user,
        code=basket_and_coupons.coupongroup_best.coupon.coupon_code,
    )


def test_validate_basket_different_product(basket_and_coupons):
    """All course run selections should be linked to the product being purchased"""
    CourseRunSelection.objects.all().delete()
    CourseRunSelection.objects.create(
        run=CourseRunFactory.create(), basket=basket_and_coupons.basket
    )
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket.user)
    assert ex.value.args[0]["runs"] == "Some invalid courses were selected."


def test_validate_basket_two_runs_same_course(basket_and_coupons):
    """
    User should not be able to select two runs for the same course
    """
    CourseRunSelection.objects.all().delete()
    program = ProgramFactory.create()
    courses = CourseFactory.create_batch(2, program=program, live=True)
    runs = CourseRunFactory.create_batch(
        3, course=factory.Iterator([courses[0], courses[1], courses[1]])
    )

    product = basket_and_coupons.product_version.product
    product.content_object = program
    product.save()

    CourseRunSelectionFactory.create_batch(
        len(runs), run=factory.Iterator(runs), basket=basket_and_coupons.basket
    )

    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket.user)

    assert ex.value.args[0]["runs"] == "Some invalid courses were selected."


def test_validate_basket_already_enrolled(basket_and_coupons):
    """
    User should not be able to purchase a product if they are
    already enrolled in even one of the runs for that product.
    """
    CourseRunSelection.objects.all().delete()
    program = ProgramFactory.create()
    runs = [
        CourseRunFactory.create(course__program=program, course__live=True)
        for _ in range(4)
    ]

    product = basket_and_coupons.product_version.product
    product.content_object = program
    product.save()

    CourseRunSelectionFactory.create_batch(
        len(runs), run=factory.Iterator(runs), basket=basket_and_coupons.basket
    )
    user = basket_and_coupons.basket.user
    CourseRunEnrollmentFactory.create(
        order__purchaser=user, order__status=Order.FULFILLED, user=user, run=runs[2]
    )

    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket.user)
    assert "You are already enrolled" in ex.value.args[0]["runs"]


def test_validate_basket_course_without_run_selection(basket_and_coupons):
    """
    Each course in a basket must have a run selected
    """
    CourseRunSelection.objects.all().delete()
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket.user)
    assert ex.value.args[0]["runs"] == "You must select a date for each course."


def test_validate_basket_run_expired(mocker, basket_and_coupons):
    """
    Each run selected must be valid
    """
    patched = mocker.patch(
        "courses.models.CourseRun.is_unexpired", new_callable=PropertyMock
    )
    patched.return_value = False
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket.user)
    assert (
        ex.value.args[0]["runs"]
        == f"Course '{basket_and_coupons.run.title}' is not accepting enrollments."
    )


@pytest.mark.parametrize("is_signed", [True, False])
def test_validate_basket_unsigned_data_consent(basket_and_agreement, is_signed):
    """
    All data consent agreements must be signed on checkout
    """
    data_consent = DataConsentUser.objects.get(
        agreement=basket_and_agreement.agreement,
        user=basket_and_agreement.basket.user,
        coupon=basket_and_agreement.coupon,
    )
    data_consent.consent_date = now_in_utc() if is_signed else None
    data_consent.save()

    if not is_signed:
        with pytest.raises(ValidationError) as ex:
            validate_basket_for_checkout(basket_and_agreement.basket.user)
        assert (
            ex.value.args[0]["data_consents"]
            == "The data consent agreement has not yet been signed."
        )
    else:
        validate_basket_for_checkout(basket_and_agreement.basket.user)


def test_validate_global_data_consent(basket_and_agreement):
    """
    Basket should contain the global data consent agreement if no course specific agreement exists
    """
    course_agreement = get_or_create_data_consent_users(basket_and_agreement.basket)
    assert len(course_agreement) >= 1
    assert (
        course_agreement[0].agreement.company == basket_and_agreement.agreement.company
    )
    assert course_agreement[0].agreement.is_global is False
    assert (
        course_agreement[0].agreement.courses == basket_and_agreement.agreement.courses
    )

    basket_and_agreement.agreement.courses.clear()
    basket_and_agreement.agreement.is_global = True
    basket_and_agreement.agreement.save()
    global_agreement = get_or_create_data_consent_users(basket_and_agreement.basket)
    assert len(global_agreement) >= 1
    assert (
        global_agreement[0].agreement.company == basket_and_agreement.agreement.company
    )
    assert global_agreement[0].agreement.is_global is True


def test_complete_order(mocker, user, basket_and_coupons):
    """
    Test that complete_order enrolls a user in the items in their order and clears out checkout-related objects
    """
    patched_enroll = mocker.patch("ecommerce.api.enroll_user_in_order_items")
    basket_and_coupons.basket.user = user
    basket_and_coupons.basket.save()
    assert BasketItem.objects.filter(basket__user=user).count() > 0
    assert CourseRunSelection.objects.filter(basket__user=user).count() > 0
    assert CouponSelection.objects.filter(basket__user=user).count() > 0
    order = OrderFactory.create(purchaser=user, status=Order.CREATED)

    complete_order(order)
    patched_enroll.assert_called_once_with(order)
    assert BasketItem.objects.filter(basket__user=user).count() == 0
    assert CourseRunSelection.objects.filter(basket__user=user).count() == 0
    assert CouponSelection.objects.filter(basket__user=user).count() == 0


def test_complete_order_coupon_assignments(mocker, user, basket_and_coupons):
    """
    Test that complete_order sets relevant product assignments to redeemed
    """
    mocker.patch("ecommerce.api.enroll_user_in_order_items")
    patched_set_enrolled = mocker.patch("sheets.tasks.set_assignment_rows_to_enrolled")
    basket_and_coupons.basket.user = user
    basket_and_coupons.basket.save()
    order = OrderFactory.create(purchaser=user, status=Order.CREATED)
    coupon_redemptions = CouponRedemptionFactory.create_batch(3, order=order)
    order_coupons = [
        redemption.coupon_version.coupon for redemption in coupon_redemptions
    ]
    bulk_assignment = BulkCouponAssignmentFactory.create()
    non_sheet_bulk_assignment = BulkCouponAssignmentFactory.create(
        assignment_sheet_id=None
    )
    coupon_assignments = ProductCouponAssignmentFactory.create_batch(
        len(coupon_redemptions),
        # Set assignment email as uppercase to test that the email match is case-insensitive
        email=order.purchaser.email.upper(),
        product_coupon__coupon=factory.Iterator(order_coupons),
        bulk_assignment=factory.Iterator(
            [None, non_sheet_bulk_assignment, bulk_assignment]
        ),
    )

    complete_order(order)
    for coupon_assignment in coupon_assignments:
        coupon_assignment.refresh_from_db()
        assert coupon_assignment.redeemed is True
    patched_set_enrolled.delay.assert_called_once_with(
        defaultdict(
            dict,
            {
                bulk_assignment.assignment_sheet_id: {
                    order_coupons[2].coupon_code: order.purchaser.email.upper()
                }
            },
        )
    )


def test_validate_basket_product_inactive(basket_and_coupons):
    """
    If the product or program/courserun in a basket is inactive, a validation error should be raised
    """
    product = basket_and_coupons.product_version.product
    product.is_active = False
    product.save()

    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket.user)
    assert "This item cannot be purchased" in ex.value.args[0]["items"]


def test_validate_basket_not_live(basket_and_coupons):
    """
    If the pprogram/courserun in a basket is not live, a validation error should be raised
    """
    course_run = basket_and_coupons.product_version.product.content_object
    course_run.live = False
    course_run.save()

    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket.user)
    assert "This item cannot be purchased" in ex.value.args[0]["items"]


@pytest.mark.parametrize("has_redemption", [True, False])
def test_enroll_user_in_order_items(mocker, user, has_redemption):
    """
    Test that enroll_user_in_order_items creates objects that represent a user's enrollment
    in course runs and programs
    """
    patched_enroll = mocker.patch("courses.api.enroll_in_edx_course_runs")
    patched_send_email = mocker.patch(
        "ecommerce.mail_api.send_course_run_enrollment_email"
    )
    program = ProgramFactory.create()
    runs = CourseRunFactory.create_batch(2, course__program=program)
    line = LineFactory.create(
        order__purchaser=user,
        order__status=Order.FULFILLED,
        product_version__product__content_object=program,
    )
    order = line.order
    LineRunSelectionFactory.create_batch(
        len(runs), line=line, run=factory.Iterator(runs)
    )
    if has_redemption:
        redemption = CouponRedemptionFactory.create(order=order)

    enroll_user_in_order_items(order)
    created_program_enrollments = ProgramEnrollment.objects.all()
    assert len(created_program_enrollments) == 1
    assert created_program_enrollments[0].program == program
    assert created_program_enrollments[0].user == user
    assert created_program_enrollments[0].order == order
    if has_redemption:
        assert (
            created_program_enrollments[0].company
            == redemption.coupon_version.payment_version.company
        )
    created_course_run_enrollments = CourseRunEnrollment.objects.order_by(
        "run__pk"
    ).all()
    created_course_runs = [
        run_enrollment.run for run_enrollment in created_course_run_enrollments
    ]
    for enrollment in created_course_run_enrollments:
        assert enrollment.order == order
    assert len(created_course_run_enrollments) == len(runs)
    assert created_course_runs == runs
    enroll_args = patched_enroll.call_args[0]
    assert enroll_args[0] == user
    assert set(enroll_args[1]) == set(created_course_runs)
    assert patched_send_email.call_count == len(created_course_run_enrollments)
    for enrollment in created_course_run_enrollments:
        patched_send_email.assert_any_call(enrollment)


def test_enroll_user_in_order_items_with_voucher(mocker, user):
    """
    Test that enroll_user_in_order_items attaches the enrollment to a voucher if a suitable one exists
    """
    run = CourseRunFactory.create()
    line = LineFactory.create(
        order__purchaser=user,
        order__status=Order.FULFILLED,
        product_version__product__content_object=run,
    )
    LineRunSelectionFactory.create(line=line, run=run)
    order = line.order
    product = line.product_version.product
    voucher = VoucherFactory(
        user=user,
        product=product,
        coupon=CouponEligibilityFactory.create(product=product).coupon,
    )
    enrollments = CourseRunEnrollmentFactory.create_batch(
        2, user=user, run=factory.Iterator([CourseRunFactory.create(), run])
    )
    CouponRedemptionFactory.create(coupon_version__coupon=voucher.coupon)
    patched_create_run_enrollments = mocker.patch(
        "ecommerce.api.create_run_enrollments",
        autospec=True,
        return_value=(enrollments, True),
    )

    enroll_user_in_order_items(order)
    patched_create_run_enrollments.assert_called_once()
    assert Voucher.objects.get(id=voucher.id).enrollment == enrollments[1]


def test_enroll_user_program_no_runs(mocker, user):
    """
    Test that enroll_user_in_order_items logs an error if an order for a program is being completed
    without any course run selections.
    """
    patched_log = mocker.patch("ecommerce.api.log")
    order = OrderFactory.create(purchaser=user, status=Order.FULFILLED)
    BasketFactory.create(user=user)
    program = ProgramFactory.create()
    LineFactory.create(order=order, product_version__product__content_object=program)

    enroll_user_in_order_items(order)
    patched_log.error.assert_called_once()
    assert (
        "An order is being completed for a program, but does not have any course run selections"
        in patched_log.error.call_args[0][0]
    )


def test_fetch_and_serialize_unused_coupons_empty(user):
    """
    Test that fetch_and_serialize_unused_coupons returns an empty list for users
    that have no unredeemed coupon assignments
    """
    ProductCouponAssignmentFactory.create(email=user.email, redeemed=True)
    unused_coupons = fetch_and_serialize_unused_coupons(user)
    assert unused_coupons == []


def test_fetch_and_serialize_unused_coupons(user):
    """
    Test that fetch_and_serialize_unused_coupons returns an serialized coupon assignments
    if those coupons are the most recent versions and are unexpired
    """
    now = now_in_utc()
    future = now + timedelta(days=5)
    past = now - timedelta(days=5)

    coupons = CouponFactory.create_batch(2)
    # Create 3 payment versions – the first 2 will apply to the same coupon, and the
    # first will be the most up-to-date version for the coupon. The last payment version
    # will be set to expired.
    payment_versions = CouponPaymentVersionFactory.create_batch(
        3,
        expiration_date=factory.Iterator([future, future, past]),
        created_on=factory.Iterator([future, past, future]),
        payment=factory.Iterator(
            [coupons[0].payment, coupons[0].payment, coupons[1].payment]
        ),
    )
    product_coupons = CouponEligibilityFactory.create_batch(
        2, coupon=factory.Iterator(coupons)
    )
    expected_payment_version = payment_versions[0]
    expected_product_coupon = product_coupons[0]

    # Create assignments for the user and set all to be unredeemed/unused
    ProductCouponAssignmentFactory.create_batch(
        len(product_coupons),
        # Set assignment email as uppercase to test that the email match is case-insensitive
        email=user.email.upper(),
        redeemed=False,
        product_coupon=factory.Iterator(product_coupons),
    )

    unused_coupons = fetch_and_serialize_unused_coupons(user)

    assert unused_coupons == [
        {
            "coupon_code": expected_product_coupon.coupon.coupon_code,
            "product_id": expected_product_coupon.product.id,
            "expiration_date": expected_payment_version.expiration_date,
            "product_title": expected_product_coupon.product.title,
            "product_type": expected_product_coupon.product.type_string,
            "thumbnail_url": expected_product_coupon.product.thumbnail_url,
            "start_date": expected_product_coupon.product.start_date,
        }
    ]


def test_fetch_and_serialize_unused_coupons_for_active_products(user):
    """
    Test that fetch_and_serialize_unused_coupons returns an serialized coupon assignments
    if those coupons are the most recent versions and are unexpired and exclude the inactive products.
    """
    now = now_in_utc()
    future = now + timedelta(days=5)
    past = now - timedelta(days=5)

    courserun_active_product = ProductFactory.create(
        content_object=CourseRunFactory.create(), is_active=True
    )
    courserun_inactive_product = ProductFactory.create(
        content_object=CourseRunFactory.create(), is_active=False
    )

    coupons = CouponFactory.create_batch(2)
    payment_versions = CouponPaymentVersionFactory.create_batch(
        3,
        expiration_date=factory.Iterator([future, future, past]),
        created_on=factory.Iterator([future, past, future]),
        payment=factory.Iterator(
            [coupons[0].payment, coupons[0].payment, coupons[1].payment]
        ),
    )

    product_coupons = CouponEligibilityFactory.create_batch(
        2,
        coupon=factory.Iterator(coupons),
        product=factory.Iterator(
            [courserun_active_product, courserun_inactive_product]
        ),
    )
    expected_payment_version = payment_versions[0]
    expected_product_coupon = product_coupons[0]

    # Create assignments for the user and set all to be unredeemed/unused
    ProductCouponAssignmentFactory.create_batch(
        len(product_coupons),
        # Set assignment email as uppercase to test that the email match is case-insensitive
        email=user.email.upper(),
        redeemed=False,
        product_coupon=factory.Iterator(product_coupons),
    )

    unused_coupons = fetch_and_serialize_unused_coupons(user)

    assert unused_coupons == [
        {
            "coupon_code": expected_product_coupon.coupon.coupon_code,
            "product_id": expected_product_coupon.product.id,
            "expiration_date": expected_payment_version.expiration_date,
            "product_title": expected_product_coupon.product.title,
            "product_type": expected_product_coupon.product.type_string,
            "thumbnail_url": expected_product_coupon.product.thumbnail_url,
            "start_date": expected_product_coupon.product.start_date,
        }
    ]


def test_fetch_and_serialize_unused_coupons_for_all_inactive_products(user):
    """
    Test that fetch_and_serialize_unused_coupons returns [] as all products
    are not active ones.
    """
    courserun_inactive_product = ProductFactory.create(
        content_object=CourseRunFactory.create(), is_active=False
    )

    coupons = CouponFactory.create_batch(2)
    product_coupons = CouponEligibilityFactory.create_batch(
        2,
        coupon=factory.Iterator(coupons),
        product=factory.Iterator(
            [courserun_inactive_product, courserun_inactive_product]
        ),
    )

    # Create assignments for the user and set all to be unredeemed/unused
    ProductCouponAssignmentFactory.create_batch(
        len(product_coupons),
        # Set assignment email as uppercase to test that the email match is case-insensitive
        email=user.email.upper(),
        redeemed=False,
        product_coupon=factory.Iterator(product_coupons),
    )

    unused_coupons = fetch_and_serialize_unused_coupons(user)
    assert unused_coupons == []


@pytest.mark.parametrize("use_defaults", [True, False])
def test_create_coupons(use_defaults):
    """create_coupons should fill in good default parameters where necessary"""
    product = ProductVersionFactory.create().product
    name = "n a m e"
    coupon_type = CouponPaymentVersion.SINGLE_USE
    amount = Decimal("123")
    num_coupon_codes = 12

    optional = (
        {}
        if use_defaults
        else {
            "tag": "a tag",
            "automatic": True,
            "activation_date": now_in_utc() - timedelta(1),
            "expiration_date": now_in_utc() + timedelta(1),
            "payment_type": CouponPaymentVersion.PAYMENT_CC,
            "payment_transaction": "transaction",
            "coupon_code": "a coupon code",
            "company_id": CompanyFactory.create().id,
        }
    )

    payment_version = create_coupons(
        name=name,
        product_ids=[product.id],
        amount=amount,
        num_coupon_codes=num_coupon_codes,
        coupon_type=coupon_type,
        **optional,
    )
    assert payment_version.payment.name == name
    assert payment_version.coupon_type == coupon_type
    assert payment_version.amount == amount
    assert payment_version.tag == (None if use_defaults else optional["tag"])
    assert payment_version.automatic is (
        False if use_defaults else optional["automatic"]
    )
    assert payment_version.activation_date == (
        None if use_defaults else optional["activation_date"]
    )
    assert payment_version.expiration_date == (
        None if use_defaults else optional["expiration_date"]
    )
    assert payment_version.payment_type == (
        None if use_defaults else optional["payment_type"]
    )
    assert payment_version.payment_transaction == (
        None if use_defaults else optional["payment_transaction"]
    )
    assert payment_version.company_id == (
        None if use_defaults else optional["company_id"]
    )

    coupons = list(Coupon.objects.filter(payment__versions=payment_version))
    assert len(coupons) == num_coupon_codes
    for coupon in coupons:
        if use_defaults:
            # Automatically generated coupon codes are UUIDs and should be parseable.
            # An exception will be raised otherwise.
            uuid.UUID(coupon.coupon_code)
        else:
            assert coupon.coupon_code == optional["coupon_code"]


@pytest.mark.parametrize(
    "input_text_id,run_text_id,program_text_id,prog_run_tag",
    [
        ["course-v1:some+run", "course-v1:some+run", None, None],
        ["program-v1:some+program", None, "program-v1:some+program", None],
        ["program-v1:some+program+R1", None, "program-v1:some+program+R1", None],
        ["program-v1:some+program+R1", None, "program-v1:some+program", "R1"],
    ],
)
def test_get_product_from_text_id(
    input_text_id, run_text_id, program_text_id, prog_run_tag
):
    """
    get_product_from_text_id should fetch a Product, Program/CourseRun, and (if applicable) a ProgramRun
    based on the given text id
    """
    expected_content_object = None
    if run_text_id:
        expected_content_object = CourseRunFactory.create(courseware_id=run_text_id)
    if program_text_id:
        expected_content_object = ProgramFactory.create(readable_id=program_text_id)
        if prog_run_tag:
            ProgramRunFactory.create(
                program=expected_content_object, run_tag=prog_run_tag
            )
    expected_product = ProductFactory.create(content_object=expected_content_object)

    product, content_object, program_run = get_product_from_text_id(input_text_id)
    assert product == expected_product
    assert content_object is not None
    assert content_object == expected_content_object
    if prog_run_tag is not None:
        assert program_run is not None
        assert program_run.run_tag == prog_run_tag
        assert program_run.program == content_object


def test_get_product_from_text_id_failure():
    """
    get_product_from_text_id should raise exceptions if the object(s) indicated by the text id don't exist
    or they don't have associated products
    """
    program_without_product = ProgramFactory.create()
    run_without_product = CourseRunFactory.create()
    program_run = ProgramRunFactory.create(program=program_without_product)
    invalid_prog_run_text_id = (
        f"{program_without_product.text_id}+{program_run.run_tag}5"
    )
    arg_exception_map = {
        program_without_product.text_id: Product.DoesNotExist,
        run_without_product.text_id: Product.DoesNotExist,
        program_run.full_readable_id: Product.DoesNotExist,
        "course-v1:doesnt+exist": CourseRun.DoesNotExist,
        "program-v1:doesnt+exist": Program.DoesNotExist,
        invalid_prog_run_text_id: Program.DoesNotExist,
    }
    for text_id, expected_exception in arg_exception_map.items():
        with pytest.raises(expected_exception):
            get_product_from_text_id(text_id)


@pytest.mark.parametrize(
    "qs_product_id,exp_text_id",
    [
        ["123", None],
        ["course-v1:some+id", "course-v1:some+id"],
        ["course-v1:some id", "course-v1:some+id"],
    ],
)
def test_get_product_from_querystring_id(mocker, qs_product_id, exp_text_id):
    """
    get_product_from_querystring_id should fetch a Product, Program/CourseRun, and (if applicable) a ProgramRun
    based on a querystring product id value.
    """
    product = ProductFactory.create(id=123)
    patched_get_product = mocker.patch(
        "ecommerce.api.get_product_from_text_id",
        return_value=(product, product.content_object, None),
    )
    returned_product, returned_content_object, _ = get_product_from_querystring_id(
        qs_product_id
    )
    assert returned_product == product
    assert returned_content_object == product.content_object
    assert patched_get_product.called is (exp_text_id is not None)
    if exp_text_id is not None:
        patched_get_product.assert_called_once_with(exp_text_id)
