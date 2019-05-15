"""
Functions for ecommerce
"""
from base64 import b64encode
import decimal
import hashlib
import hmac
import logging
from urllib.parse import urljoin
import uuid

from django.conf import settings
from django.db.models import Q, Max, F, Count
from django.db import transaction
from rest_framework.exceptions import ValidationError

from courses.constants import (
    CONTENT_TYPE_MODEL_PROGRAM,
    CONTENT_TYPE_MODEL_COURSE,
    CONTENT_TYPE_MODEL_COURSERUN,
)
from courses.models import Course, CourseRun, CourseRunEnrollment, ProgramEnrollment
from ecommerce.exceptions import EcommerceException, ParseException
from ecommerce.models import (
    Basket,
    BasketItem,
    Coupon,
    CouponEligibility,
    CouponVersion,
    CouponRedemption,
    CouponPayment,
    CouponPaymentVersion,
    CourseRunSelection,
    Line,
    Order,
)
from mitxpro.utils import now_in_utc

ISO_8601_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
log = logging.getLogger(__name__)

_REFERENCE_NUMBER_PREFIX = "MITXPRO-"


def generate_cybersource_sa_signature(payload):
    """
    Generate an HMAC SHA256 signature for the CyberSource Secure Acceptance payload
    Args:
        payload (dict): The payload to be sent to CyberSource
    Returns:
        str: The signature
    """
    # This is documented in certain CyberSource sample applications:
    # http://apps.cybersource.com/library/documentation/dev_guides/Secure_Acceptance_SOP/html/wwhelp/wwhimpl/js/html/wwhelp.htm#href=creating_profile.05.6.html
    keys = payload["signed_field_names"].split(",")
    message = ",".join(f"{key}={payload[key]}" for key in keys)

    digest = hmac.new(
        settings.CYBERSOURCE_SECURITY_KEY.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    return b64encode(digest).decode("utf-8")


def generate_cybersource_sa_payload(order, base_url):
    """
    Generates a payload dict to send to CyberSource for Secure Acceptance
    Args:
        order (Order): An order
        base_url (str): The base URL to be used by Cybersource to redirect the user after completion of the purchase
    Returns:
        dict: the payload to send to CyberSource via Secure Acceptance
    """
    # http://apps.cybersource.com/library/documentation/dev_guides/Secure_Acceptance_WM/Secure_Acceptance_WM.pdf
    # Section: API Fields

    # NOTE: be careful about max length here, many (all?) string fields have a max
    # length of 255. At the moment none of these fields should go over that, due to database
    # constraints or other reasons

    coupon_redemption = CouponRedemption.objects.filter(order=order).first()
    coupon_version = (
        coupon_redemption.coupon_version if coupon_redemption is not None else None
    )

    line_items = {}
    total = 0
    for i, line in enumerate(order.lines.all()):
        product_version = line.product_version
        unit_price = get_product_version_price_with_discount(
            coupon_version=coupon_version, product_version=product_version
        )
        line_items[f"item_{i}_code"] = str(product_version.product.content_type)
        line_items[f"item_{i}_name"] = str(product_version.description)[:254]
        line_items[f"item_{i}_quantity"] = line.quantity
        line_items[f"item_{i}_sku"] = product_version.product.content_object.id
        line_items[f"item_{i}_tax_amount"] = "0"
        line_items[f"item_{i}_unit_price"] = str(unit_price)

        total += unit_price

    payload = {
        "access_key": settings.CYBERSOURCE_ACCESS_KEY,
        "amount": str(total),
        "consumer_id": order.purchaser.username,
        "currency": "USD",
        "locale": "en-us",
        **line_items,
        "line_item_count": order.lines.count(),
        "reference_number": make_reference_id(order),
        "profile_id": settings.CYBERSOURCE_PROFILE_ID,
        "signed_date_time": now_in_utc().strftime(ISO_8601_FORMAT),
        "override_custom_receipt_page": urljoin(base_url, "dashboard/"),
        "transaction_type": "sale",
        "transaction_uuid": uuid.uuid4().hex,
        "unsigned_field_names": "",
    }

    field_names = sorted(list(payload.keys()) + ["signed_field_names"])
    payload["signed_field_names"] = ",".join(field_names)
    payload["signature"] = generate_cybersource_sa_signature(payload)

    return payload


def make_reference_id(order):
    """
    Make a reference id
    Args:
        order (Order):
            An order
    Returns:
        str:
            A reference number for use with CyberSource to keep track of orders
    """
    return (
        f"{_REFERENCE_NUMBER_PREFIX}{settings.CYBERSOURCE_REFERENCE_PREFIX}-{order.id}"
    )


def latest_coupon_version(coupon):
    """
    Get the most recent CouponVersion for a coupon

    Args:
        coupon (Coupon): A coupon object

    Returns:
        CouponVersion: The CouponVersion for the coupon
    """
    return coupon.versions.order_by("-created_on").first()


def get_valid_coupon_versions(product, user, auto_only=False, code=None):
    """
    Given a list of coupon ids, determine which of them are valid based on payment version dates and redemptions.

    Args:
        product (Product): product to filter CouponEligibility by
        user (User): User of coupons
        auto_only (bool): Whether or not to filter by automatic=True
        code (str): A coupon code to filter by

    Returns:
        list of CouponVersion: CouponVersion objects sorted by discount, highest first.
    """
    valid_coupons = []
    now = now_in_utc()

    with transaction.atomic():
        # Get the ids of the latest coupon versions
        product_coupon_query = CouponEligibility.objects.select_related(
            "coupon"
        ).filter(product=product, coupon__enabled=True)
        if code:
            product_coupon_query = product_coupon_query.filter(coupon__coupon_code=code)

        cv_latest = (
            CouponVersion.objects.select_related("coupon")
            .filter(coupon__in=product_coupon_query.values_list("coupon", flat=True))
            .order_by("coupon", "-created_on")
            .distinct("coupon")
            .values_list("pk")
        )

        # filter by expiration and activation dates
        query = (
            CouponVersion.objects.select_related("payment_version")
            .filter(pk__in=cv_latest)
            .filter(
                Q(payment_version__expiration_date__gte=now)
                | Q(payment_version__expiration_date__isnull=True)
            )
            .filter(
                Q(payment_version__activation_date__lte=now)
                | Q(payment_version__activation_date__isnull=True)
            )
        )

        if auto_only:
            query = query.filter(payment_version__automatic=True)

        # filter by redemption counts
        for coupon_version in query:
            redemptions_global = (
                CouponRedemption.objects.select_related("coupon_version", "order")
                .filter(coupon_version=coupon_version)
                .filter(order__status=Order.FULFILLED)
            )
            redemptions_user = redemptions_global.filter(order__purchaser=user)
            if (
                coupon_version.payment_version.max_redemptions
                > redemptions_global.count()
                and coupon_version.payment_version.max_redemptions_per_user
                > redemptions_user.count()
            ):
                valid_coupons.append(coupon_version)
        return sorted(
            valid_coupons, key=lambda x: x.payment_version.amount, reverse=True
        )


def best_coupon_for_basket(basket, auto_only=False, code=None):
    """
    Get the best eligible coupon for the basket.
    Assumes that the basket only contains one item/product.

    Args:
        basket (Basket): the basket Object
        auto_only (bool): Only retrieve `automatic` Coupons
        code (str): A coupon code to filter by

    Returns:
        CouponVersion: the CouponVersion with the highest discount, or None
    """
    basket_item = basket.basketitems.first()
    if basket_item:
        return best_coupon_for_product(
            basket_item.product, basket.user, auto_only=auto_only, code=code
        )
    return None


def best_coupon_for_product(product, user, auto_only=False, code=None):
    """
    Get the best eligible coupon for a product and user.

    Args:
        product (Product): the Product Object
        user (User): The user buying the product
        auto_only (bool): Only retrieve `automatic` Coupons
        code (str): A coupon code to filter by

    Returns:
        CouponVersion: the CouponVersion with the highest product discount, or None
    """
    validated_versions = get_valid_coupon_versions(product, user, auto_only, code=code)
    if validated_versions:
        return validated_versions[0]
    return None


def latest_product_version(product):
    """
    Get the most recent ProductVersion for a product

    Args:
        product (Product): A product object

    Returns:
        ProductVersion: The ProductVersion for the product
    """
    return product.productversions.order_by("-created_on").first()


def get_product_price(product):
    """
    Retrieve the price for the latest version of a product

    Args:
        product (Product): A product object

    Returns:
        Decimal: the price of a product
    """
    return latest_product_version(product).price


def round_half_up(number):
    """
    Round a decimal number using the ROUND_HALF_UP rule so we match what decimal.js does by default.

    Args:
        number (decimal.Decimal): A decimal number

    Returns:
        decimal.Decimal:
            A rounded decimal number
    """
    return number.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)


def get_product_version_price_with_discount(*, coupon_version, product_version):
    """
    Determine the new discounted price for a product after the coupon discount is applied

    Args:
        coupon_version (CouponVersion): the CouponVersion object
        product_version (ProductVersion): the ProductVersion object

    Returns:
        Decimal: the discounted price for the Product
    """
    price = product_version.price
    if (
        coupon_version
        and CouponEligibility.objects.filter(
            coupon__versions=coupon_version, product__productversions=product_version
        ).exists()
    ):
        discount = round_half_up(coupon_version.payment_version.amount * price)
    else:
        discount = 0
    return price - discount


def redeem_coupon(coupon_version, order):
    """
    Redeem a coupon for an order by creating/updating the CouponRedemption for that order.
    Assumes there should only be one CouponRedemption per order.

    Args:
        coupon_version (CouponVersion): a CouponVersion object
        order: (Order): an Order object

    Returns:
        CouponRedemption: a CouponRedemption object

    """
    coupon_redemption, _ = CouponRedemption.objects.update_or_create(
        order=order, defaults={"coupon_version": coupon_version}
    )
    return coupon_redemption


def get_new_order_by_reference_number(reference_number):
    """
    Parse a reference number received from CyberSource and lookup the corresponding Order.
    Args:
        reference_number (str):
            A string which contains the order id and the instance which generated it
    Returns:
        Order:
            An order
    """
    if not reference_number.startswith(_REFERENCE_NUMBER_PREFIX):
        raise ParseException(
            "Reference number must start with {}".format(_REFERENCE_NUMBER_PREFIX)
        )
    reference_number = reference_number[len(_REFERENCE_NUMBER_PREFIX) :]

    try:
        order_id_pos = reference_number.rindex("-")
    except ValueError:
        raise ParseException("Unable to find order number in reference number")

    try:
        order_id = int(reference_number[order_id_pos + 1 :])
    except ValueError:
        raise ParseException("Unable to parse order number")

    prefix = reference_number[:order_id_pos]
    if prefix != settings.CYBERSOURCE_REFERENCE_PREFIX:
        log.error(
            "CyberSource prefix doesn't match: %s != %s",
            prefix,
            settings.CYBERSOURCE_REFERENCE_PREFIX,
        )
        raise ParseException("CyberSource prefix doesn't match")

    try:
        return Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise EcommerceException("Unable to find order {}".format(order_id))


def enroll_user_on_success(order):  # pylint: disable=unused-argument
    """
    Check if the order is successful, then enroll the user and create local records of their
    enrollments.

    Args:
        order (Order): An order
    """
    basket = order.purchaser.basket
    runs = CourseRun.objects.filter(courserunselection__basket=basket)
    # pylint: disable=fixme
    # TODO: Actually enroll the user in the given course runs on Open edX
    for run in runs:
        CourseRunEnrollment.objects.get_or_create(user=order.purchaser, run=run)
    for line in order.lines.all():
        if (
            line.product_version.product.content_type.model
            == CONTENT_TYPE_MODEL_PROGRAM
        ):
            ProgramEnrollment.objects.get_or_create(
                user=order.purchaser,
                program=line.product_version.product.content_object,
            )


@transaction.atomic
def create_unfulfilled_order(user):
    """
    Create a new Order which is not fulfilled for a purchasable Product. Note that validation should
    be done in the basket REST API so the validation is not done here (different from MicroMasters).

    Args:
        user (User):
            The purchaser

    Returns:
        Order: A newly created Order for the Product in the basket
    """
    # Note: validation is assumed to already have happen when the basket is being modified
    basket, _ = Basket.objects.get_or_create(user=user)

    order = Order.objects.create(status=Order.CREATED, purchaser=user)

    for basket_item in basket.basketitems.all():
        product_version = latest_product_version(basket_item.product)
        Line.objects.create(
            order=order, product_version=product_version, quantity=basket_item.quantity
        )

    for coupon_selection in basket.couponselection_set.all():
        coupon = coupon_selection.coupon
        redeem_coupon(coupon_version=latest_coupon_version(coupon), order=order)
    order.save_and_log(user)
    return order


def get_product_courses(product):
    """
    Get all courses for a product

    Args:
        product(Product): The product to retrieve courses for

    Returns:
        list of Course: list of Courses associated with the Product

    """
    if product.content_type.model == CONTENT_TYPE_MODEL_COURSERUN:
        return [product.content_object.course]
    elif product.content_type.model == CONTENT_TYPE_MODEL_COURSE:
        return [product.content_object]
    elif product.content_type.model == CONTENT_TYPE_MODEL_PROGRAM:
        return list(
            product.content_object.courses.all().order_by("position_in_program")
        )


def get_full_price_coupon_product_set():
    """
    Queries the database for CouponPayments that give a 100% off discount and returns those
    CouponPayments in a tuple with the Product that they apply to.

    Returns:
        iterable of tuple(CouponPayment, CouponEligibility): An iterable of CouponPayments paired with the
            CouponEligibility objects associated with them
    """
    full_coupon_payments = CouponPayment.objects.annotate(
        max_created_on=Max("versions__created_on")
    ).filter(
        versions__coupon_type=CouponPaymentVersion.SINGLE_USE,
        max_created_on=F("versions__created_on"),
        versions__amount=1,
    )
    for coupon_payment in full_coupon_payments:
        product_coupons = (
            CouponEligibility.objects.select_related("product")
            .filter(coupon__enabled=True, coupon__payment=coupon_payment)
            .distinct("product")
        )
        if product_coupons.exists():
            yield coupon_payment, product_coupons


def get_available_bulk_product_coupons(coupon_payment_id, product_id):
    """
    Queries the database for bulk enrollment product coupons that haven't already been sent to other users

    Args:
        coupon_payment_id (int): Id for a CouponPayment
        product_id (int): Id for a Product

    Returns:
        CouponEligibility queryset: Product coupons that can be used for bulk enrollment
    """
    return (
        CouponEligibility.objects.select_related("product")
        .select_related("coupon__payment")
        .annotate(existing_assignments=Count("productcouponassignment"))
        .filter(
            coupon__enabled=True,
            coupon__payment=coupon_payment_id,
            product__id=product_id,
            existing_assignments=0,
        )
    )


def validate_basket_for_checkout(basket):
    """
    Validate basket for checkout

    Args:
        basket (Basket): A user's basket
    """
    # Only one basket item allowed
    try:
        basket_item = BasketItem.objects.get(basket=basket)
    except BasketItem.DoesNotExist:
        raise ValidationError("No items in basket, cannot checkout")

    product = basket_item.product
    # No more than one coupon allowed
    try:
        coupon = Coupon.objects.get(couponselection__basket=basket)
    except Coupon.DoesNotExist:
        coupon = None

    # Coupon must be valid for the product
    if coupon is not None:
        if not get_valid_coupon_versions(
            product=product, user=basket.user, code=coupon.coupon_code
        ):
            raise ValidationError("Coupon is not valid for product")

    # Basket item runs must be linked to the basket item product
    run_queryset = product.run_queryset
    if (
        CourseRunSelection.objects.filter(basket=basket)
        .exclude(run__in=run_queryset)
        .exists()
    ):
        raise ValidationError(
            "Some runs present in basket which are not part of product"
        )

    # User must not already be enrolled in a course run covered by the product
    if CourseRunEnrollment.objects.filter(
        user=basket.user, run__in=run_queryset
    ).exists():
        raise ValidationError("User is already enrolled in one or more runs in basket")

    # User must have selected one run id for each course in basket
    runs = list(CourseRun.objects.filter(courserunselection__basket=basket))
    courses_runs = {}
    for run in runs:
        if run.course_id not in courses_runs:
            courses_runs[run.course_id] = run.id
        elif courses_runs[run.course_id] != run.id:
            raise ValidationError("Two or more runs assigned for a single course")

    if (
        len(courses_runs)
        != Course.objects.filter(courseruns__id__in=run_queryset).distinct().count()
    ):
        # This is != but it could be < because the > case should be covered in previous clauses.
        # The user can only select more courses than a product has if they are selecting runs outside
        # of the product, which we checked above.
        raise ValidationError("One or more courses do not have a course run selection")

    # All run ids must be purchasable and enrollable by user
    for run in runs:
        if not run.is_unexpired:
            raise ValidationError(f"Run {run.id} is expired")
