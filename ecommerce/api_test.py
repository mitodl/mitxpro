"""
Test for ecommerce functions
"""
from base64 import b64encode
from decimal import Decimal
from datetime import timedelta
import hashlib
import hmac
from urllib.parse import urljoin
from unittest.mock import PropertyMock

import factory
from rest_framework.exceptions import ValidationError
import pytest

from courses.models import CourseRunEnrollment, ProgramEnrollment
from courses.factories import CourseFactory, ProgramFactory, CourseRunFactory
from ecommerce.api import (
    create_unfulfilled_order,
    generate_cybersource_sa_payload,
    generate_cybersource_sa_signature,
    ISO_8601_FORMAT,
    make_reference_id,
    redeem_coupon,
    get_new_order_by_reference_number,
    get_product_price,
    get_product_version_price_with_discount,
    get_valid_coupon_versions,
    latest_product_version,
    latest_coupon_version,
    get_product_courses,
    get_available_bulk_product_coupons,
    validate_basket_for_checkout,
    enroll_user_on_success,
)
from ecommerce.exceptions import EcommerceException, ParseException
from ecommerce.factories import (
    BasketFactory,
    CouponRedemptionFactory,
    CouponSelectionFactory,
    CouponVersionFactory,
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
    CouponSelection,
    CouponRedemption,
    CourseRunSelection,
    Order,
    OrderAudit,
    Product,
)
from mitxpro.utils import now_in_utc

pytestmark = pytest.mark.django_db
lazy = pytest.lazy_fixture

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
        "override_custom_receipt_page": urljoin(base_url, "dashboard/"),
        "profile_id": CYBERSOURCE_PROFILE_ID,
        "signed_date_time": now.strftime(ISO_8601_FORMAT),
        "signed_field_names": ",".join(signed_field_names),
        "transaction_type": "sale",
        "transaction_uuid": transaction_uuid,
        "unsigned_field_names": "",
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
    assert ex.value.args[0] == "No items in basket, cannot checkout"


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
    assert ex.value.args[0] == "Coupon is not valid for product"
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
        ex.value.args[0] == "Some runs present in basket which are not part of product"
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
    CourseRunEnrollment.objects.create(user=order.purchaser, run=runs[2])

    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket)
    assert ex.value.args[0] == "User is already enrolled in one or more runs in basket"


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

    assert ex.value.args[0] == "Two or more runs assigned for a single course"


def test_validate_basket_course_without_run_selection(basket_and_coupons):
    """
    Each course in a basket must have a run selected
    """
    CourseRunSelection.objects.all().delete()
    with pytest.raises(ValidationError) as ex:
        validate_basket_for_checkout(basket_and_coupons.basket)
    assert ex.value.args[0] == "One or more courses do not have a course run selection"


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
    assert ex.value.args[0] == f"Run {basket_and_coupons.run.id} is expired"


@pytest.mark.parametrize("has_redemption", [True, False])
def test_enroll_user_on_success(user, has_redemption):
    """
    Test that enroll_user_on_success creates objects that represent a user's enrollment
    in course runs and programs
    """
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

    enroll_user_on_success(order)
    created_program_enrollments = ProgramEnrollment.objects.all()
    assert len(created_program_enrollments) == 1
    assert created_program_enrollments[0].program == program
    assert created_program_enrollments[0].user == user
    if has_redemption:
        assert (
            created_program_enrollments[0].company
            == redemption.coupon_version.payment_version.company
        )
    created_course_run_enrollments = CourseRunEnrollment.objects.order_by("pk").all()
    assert len(created_course_run_enrollments) == len(run_selections)
    assert [
        run_enrollment.run for run_enrollment in created_course_run_enrollments
    ] == [selection.run for selection in run_selections]
