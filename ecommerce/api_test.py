"""
Test for ecommerce functions
"""
from base64 import b64encode
from decimal import Decimal
from datetime import timedelta
import hashlib
import hmac
from unittest.mock import PropertyMock
import uuid

import factory
from rest_framework.exceptions import ValidationError
import pytest

from courses.constants import ENROLL_CHANGE_STATUS_REFUNDED
from courses.models import CourseRunEnrollment, ProgramEnrollment
from courses.factories import (
    CourseFactory,
    ProgramFactory,
    CourseRunFactory,
    CourseRunEnrollmentFactory,
    ProgramEnrollmentFactory,
)
from courseware.exceptions import (
    EdxApiEnrollErrorException,
    UnknownEdxApiEnrollException,
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
    validate_basket_for_checkout,
    complete_order,
    enroll_user_in_order_items,
    fetch_and_serialize_unused_coupons,
    ENROLL_ERROR_EMAIL_SUBJECT,
    format_enrollment_message,
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
)
from ecommerce.test_utils import unprotect_version_tables
from mitxpro.utils import now_in_utc
from voucher.factories import VoucherFactory
from voucher.models import Voucher

pytestmark = pytest.mark.django_db
lazy = pytest.lazy_fixture

# pylint: disable=redefined-outer-name,too-many-lines

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
def test_signed_payload(mocker, has_coupon, has_company, is_program_product):
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
        order=order, receipt_url=receipt_url, cancel_url=cancel_url
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


@pytest.mark.parametrize("order_status", [Order.FULFILLED, Order.FAILED])
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
    if order_status == Order.FULFILLED:
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
    basket_and_coupons, mock_hubspot_syncs, settings, hubspot_api_key
):
    """
    get_by_reference_number returns an Order with status created
    """
    settings.HUBSPOT_API_KEY = hubspot_api_key
    user = basket_and_coupons.basket_item.basket.user
    order = create_unfulfilled_order(user)
    same_order = Order.objects.get_by_reference_number(order.reference_number)
    assert same_order.id == order.id
    if hubspot_api_key:
        assert mock_hubspot_syncs.order.called_with(order.id)
    else:
        assert mock_hubspot_syncs.order.not_called()


def test_get_by_reference_number_missing(basket_and_coupons):
    """
    get_by_reference_number should return an empty queryset if the order id is missing
    """
    user = basket_and_coupons.basket_item.basket.user
    order = create_unfulfilled_order(user)

    # change order number to something not likely to already exist in database
    order.id = 98_765_432
    assert not Order.objects.filter(id=order.id).exists()
    with pytest.raises(Order.DoesNotExist):
        Order.objects.get_by_reference_number(order.reference_number)


@pytest.mark.parametrize("hubspot_api_key", [None, "fake-key"])
@pytest.mark.parametrize("has_coupon", [True, False])
def test_create_order(
    has_coupon, basket_and_coupons, settings, hubspot_api_key, mock_hubspot_syncs
):  # pylint: disable=too-many-locals
    """
    Create Order from a purchasable course
    """
    settings.HUBSPOT_API_KEY = hubspot_api_key
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

    if hubspot_api_key:
        assert mock_hubspot_syncs.order.called_with(order.id)
    else:
        assert mock_hubspot_syncs.order.not_called()


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


@pytest.mark.parametrize("has_coupon", [True, False])
def test_validate_basket_all_good(basket_and_coupons, has_coupon):
    """If everything is valid no exception should be raised"""
    if not has_coupon:
        CouponSelection.objects.all().delete()
    assert validate_basket_for_checkout(basket_and_coupons.basket) is None


def test_validate_basket_no_item(basket_and_coupons):
    """An empty basket should be rejected"""
    BasketItem.objects.all().delete()
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket)
    assert ex.value.args[0]["items"] == "No items in basket, cannot checkout"


def test_validate_basket_two_items(basket_and_coupons):
    """An empty basket should be rejected"""
    BasketItem.objects.create(
        product=Product.objects.first(), quantity=1, basket=basket_and_coupons.basket
    )
    # We don't raise ValidationError here since this should have been caught in BasketSerializer already
    with pytest.raises(BasketItem.MultipleObjectsReturned):
        validate_basket_for_checkout(basket_and_coupons.basket)


def test_validate_basket_two_coupons(basket_and_coupons):
    """A basket cannot have two coupons"""
    CouponSelectionFactory.create(basket=basket_and_coupons.basket)
    # We don't raise ValidationError here since this should have been caught in BasketSerializer already
    with pytest.raises(Coupon.MultipleObjectsReturned):
        validate_basket_for_checkout(basket_and_coupons.basket)


def test_validate_basket_invalid_coupon(mocker, basket_and_coupons):
    """An invalid coupon should be rejected in the basket"""
    patched = mocker.patch(
        "ecommerce.api.get_valid_coupon_versions", return_value=False
    )
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket)
    assert ex.value.args[0]["coupons"] == "Coupon is not valid for product"
    patched.assert_called_once_with(
        product=basket_and_coupons.product_version.product,
        user=basket_and_coupons.basket.user,
        code=basket_and_coupons.coupongroup_best.coupon.coupon_code,
    )


def test_validate_basket_different_product(basket_and_coupons):
    """All course run selections should be linked to the product being purchased"""
    CourseRunSelection.objects.create(
        run=CourseRunFactory.create(), basket=basket_and_coupons.basket
    )
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket)
    assert (
        ex.value.args[0]["runs"]
        == "Some runs present in basket which are not part of product"
    )


def test_validate_basket_already_enrolled(basket_and_coupons):
    """
    User should not be able to purchase a product if they are
    already enrolled in even one of the runs for that product.
    """
    CourseRunSelection.objects.all().delete()
    program = ProgramFactory.create()
    runs = [CourseRunFactory.create(course__program=program) for _ in range(4)]

    product = basket_and_coupons.product_version.product
    product.content_object = program
    product.save()

    order = OrderFactory.create(
        purchaser=basket_and_coupons.basket.user, status=Order.FULFILLED
    )
    CourseRunEnrollmentFactory.create(order=order, user=order.purchaser, run=runs[2])

    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket)
    assert (
        ex.value.args[0]["runs"]
        == "User is already enrolled in one or more runs in basket"
    )


def test_validate_basket_two_runs_for_a_course(basket_and_coupons):
    """
    User should not be able to be enrolled in two runs for the same course
    """
    CourseRunSelection.objects.all().delete()
    program = ProgramFactory.create()
    course = CourseFactory.create(program=program)
    runs = [CourseRunFactory.create(course=course) for _ in range(4)]

    product = basket_and_coupons.product_version.product
    product.content_object = program
    product.save()

    for run in runs:
        CourseRunSelection.objects.create(run=run, basket=basket_and_coupons.basket)

    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket)

    assert ex.value.args[0]["runs"] == "Two or more runs assigned for a single course"


def test_validate_basket_course_without_run_selection(basket_and_coupons):
    """
    Each course in a basket must have a run selected
    """
    CourseRunSelection.objects.all().delete()
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket)
    assert ex.value.args[0]["runs"] == "Each course must have a course run selection"


def test_validate_basket_run_expired(mocker, basket_and_coupons):
    """
    Each run selected must be valid
    """
    patched = mocker.patch(
        "courses.models.CourseRun.is_unexpired", new_callable=PropertyMock
    )
    patched.return_value = False
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket)
    assert ex.value.args[0]["runs"] == f"Run {basket_and_coupons.run.id} is expired"


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
            validate_basket_for_checkout(basket_and_agreement.basket)
        assert (
            ex.value.args[0]["data_consents"]
            == "The data consent agreement has not yet been signed"
        )
    else:
        validate_basket_for_checkout(basket_and_agreement.basket)


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
    basket_and_coupons.basket.user = user
    basket_and_coupons.basket.save()
    order = OrderFactory.create(purchaser=user, status=Order.CREATED)
    coupon_redemption = CouponRedemptionFactory.create(order=order)
    coupon_assignment = ProductCouponAssignmentFactory.create(
        email=order.purchaser.email,
        product_coupon__coupon=coupon_redemption.coupon_version.coupon,
    )

    complete_order(order)
    coupon_assignment.refresh_from_db()
    assert coupon_assignment.redeemed is True


@pytest.mark.parametrize("has_redemption", [True, False])
def test_enroll_user_in_order_items(mocker, user, has_redemption):
    """
    Test that enroll_user_in_order_items creates objects that represent a user's enrollment
    in course runs and programs
    """
    patched_enroll = mocker.patch("ecommerce.api.enroll_in_edx_course_runs")
    patched_send_email = mocker.patch(
        "ecommerce.mail_api.send_course_run_enrollment_email"
    )
    order = OrderFactory.create(purchaser=user, status=Order.FULFILLED)
    if has_redemption:
        redemption = CouponRedemptionFactory.create(order=order)
    basket = BasketFactory.create(user=user)
    run_selections = CourseRunSelectionFactory.create_batch(2, basket=basket)
    program = ProgramFactory.create()
    LineFactory.create_batch(
        3,
        order=order,
        product_version__product__content_object=factory.Iterator(
            [selection.run for selection in run_selections] + [program]
        ),
    )

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
    course_runs = [
        run_enrollment.run for run_enrollment in created_course_run_enrollments
    ]
    for enrollment in created_course_run_enrollments:
        assert enrollment.order == order
    assert len(created_course_run_enrollments) == len(run_selections)
    assert course_runs == [selection.run for selection in run_selections]
    enroll_args = patched_enroll.call_args[0]
    assert enroll_args[0] == user
    assert set(enroll_args[1]) == set(course_runs)
    assert patched_send_email.call_count == len(created_course_run_enrollments)
    for enrollment in created_course_run_enrollments:
        patched_send_email.assert_any_call(enrollment)


def test_enroll_user_in_order_items_with_voucher(mocker, user):
    """
    Test that enroll_user_in_order_items attaches the enrollment to a voucher if a suitable one exists
    """
    patched_enroll = mocker.patch("ecommerce.api.enroll_in_edx_course_runs")
    order = OrderFactory.create(purchaser=user, status=Order.FULFILLED)
    basket = BasketFactory.create(user=user)
    run_selection = CourseRunSelectionFactory.create(basket=basket)
    product = ProductFactory.create(content_object=run_selection.run)
    LineFactory(order=order, product_version__product=product)
    voucher = VoucherFactory(
        user=user,
        product=product,
        coupon=CouponEligibilityFactory.create(product=product).coupon,
    )
    CouponRedemptionFactory.create(coupon_version__coupon=voucher.coupon)

    enroll_user_in_order_items(order)
    assert patched_enroll.call_count == 1

    created_course_run_enrollments = CourseRunEnrollment.objects.order_by("pk").all()
    assert created_course_run_enrollments.count() == 1
    assert (
        Voucher.objects.get(id=voucher.id).enrollment
        == created_course_run_enrollments.first()
    )


def test_enroll_user_in_order_items_reactivate(mocker, user):
    """
    Test that enroll_user_in_order_items attaches the enrollment to a voucher if a suitable one exists
    """
    mocker.patch("ecommerce.api.enroll_in_edx_course_runs")
    order = OrderFactory.create(purchaser=user, status=Order.FULFILLED)
    basket = BasketFactory.create(user=user)
    run_selections = CourseRunSelectionFactory.create_batch(2, basket=basket)
    program = ProgramFactory.create()
    LineFactory.create_batch(
        3,
        order=order,
        product_version__product__content_object=factory.Iterator(
            [selection.run for selection in run_selections] + [program]
        ),
    )
    # Create inactive enrollments that should be set to active after this method is executed
    course_run_enrollment = CourseRunEnrollmentFactory.create(
        active=False,
        change_status=ENROLL_CHANGE_STATUS_REFUNDED,
        user=user,
        run=run_selections[0].run,
        order=order,
    )
    program_enrollment = ProgramEnrollmentFactory(
        active=False,
        change_status=ENROLL_CHANGE_STATUS_REFUNDED,
        user=user,
        program=program,
        order=order,
    )

    enroll_user_in_order_items(order)
    course_run_enrollment.refresh_from_db()
    program_enrollment.refresh_from_db()
    assert course_run_enrollment.active is True
    assert program_enrollment.active is True


@pytest.mark.parametrize(
    "exception_cls", [EdxApiEnrollErrorException, UnknownEdxApiEnrollException]
)
def test_enroll_user_in_order_items_api_fail(mocker, user, exception_cls):
    """
    Test that enroll_user_in_order_items logs a message and still creates local enrollment records
    when the edX API request fails
    """
    course_run = CourseRunFactory.build()
    patched_enroll_in_runs = mocker.patch(
        "ecommerce.api.enroll_in_edx_course_runs",
        side_effect=exception_cls(user, course_run, mocker.Mock()),
    )
    patched_log_exception = mocker.patch("ecommerce.api.log.exception")
    order = OrderFactory.create(purchaser=user, status=Order.FULFILLED)
    basket = BasketFactory.create(user=user)
    CourseRunSelectionFactory.create_batch(2, basket=basket)

    enroll_user_in_order_items(order)
    assert (
        CourseRunEnrollment.objects.filter(user=user, edx_enrolled=False).count() == 2
    )
    patched_enroll_in_runs.assert_called_once()
    patched_log_exception.assert_called_once()


@pytest.mark.parametrize("enroll_type", ["CourseRun", "Program"])
def test_enroll_user_in_order_exception(mocker, user, enroll_type):
    """
    Test that enroll_user_in_order_items sends an email to support if an enrollment fails
    """
    patched_send_support_email = mocker.patch("ecommerce.api.send_support_email")
    mocker.patch("ecommerce.api.enroll_in_edx_course_runs")
    order = OrderFactory.create(purchaser=user, status=Order.FULFILLED)
    basket = BasketFactory.create(user=user)
    run_selections = CourseRunSelectionFactory.create_batch(2, basket=basket)
    program = ProgramFactory.create()
    LineFactory.create_batch(
        3,
        order=order,
        product_version__product__content_object=factory.Iterator(
            [selection.run for selection in run_selections] + [program]
        ),
    )
    mocker.patch(
        f"ecommerce.api.{enroll_type}Enrollment.all_objects.get_or_create",
        side_effect=Exception(),
    )

    with pytest.raises(Exception):
        enroll_user_in_order_items(order)

    patched_send_support_email.assert_called_once()
    assert patched_send_support_email.call_args[0][0] == ENROLL_ERROR_EMAIL_SUBJECT
    for item in (user.username, user.email, f"Order #{order.id}"):
        assert item in patched_send_support_email.call_args[0][1]


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
        email=user.email,
        redeemed=False,
        product_coupon=factory.Iterator(product_coupons),
    )

    unused_coupons = fetch_and_serialize_unused_coupons(user)

    assert unused_coupons == [
        {
            "coupon_code": expected_product_coupon.coupon.coupon_code,
            "product_id": expected_product_coupon.product.id,
            "expiration_date": expected_payment_version.expiration_date,
        }
    ]


@pytest.mark.parametrize("is_program", [True, False])
def test_format_enrollment_message(is_program):
    """Test that format_enrollment_message formats a message correctly"""
    product_object = (
        ProgramFactory.create() if is_program else CourseRunFactory.create()
    )
    product_version = ProductVersionFactory.create(
        product=ProductFactory.create(content_object=product_object)
    )
    order = LineFactory.create(product_version=product_version).order
    details = "TestException on line 21"
    assert format_enrollment_message(order, product_object, details) == (
        "{name}({email}): Order #{order_id}, {error_obj} #{obj_id} ({obj_title})\n\n{details}".format(
            name=order.purchaser.username,
            email=order.purchaser.email,
            order_id=order.id,
            error_obj=("Program" if is_program else "Run"),
            obj_id=product_object.id,
            obj_title=product_object.title,
            details=details,
        )
    )


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
