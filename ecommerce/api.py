"""
Functions for ecommerce
"""
from base64 import b64encode
import decimal
import hashlib
import hmac
import logging
from traceback import format_exc
from urllib.parse import urljoin
import uuid

from django.conf import settings
from django.db.models import Q, Max, F, Count, Subquery
from django.db import transaction
from rest_framework.exceptions import ValidationError
from requests.exceptions import HTTPError

from courses.constants import (
    CONTENT_TYPE_MODEL_PROGRAM,
    CONTENT_TYPE_MODEL_COURSE,
    CONTENT_TYPE_MODEL_COURSERUN,
)
from courses.models import Course, CourseRun, CourseRunEnrollment, ProgramEnrollment
from courseware.api import enroll_in_edx_course_runs
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
    CouponSelection,
    CourseRunSelection,
    DataConsentAgreement,
    DataConsentUser,
    ProductCouponAssignment,
    Line,
    Order,
)
from hubspot.task_helpers import sync_hubspot_deal
from mitxpro.utils import now_in_utc, send_support_email

log = logging.getLogger(__name__)

ISO_8601_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ENROLL_ERROR_EMAIL_SUBJECT = "MIT xPRO enrollment error"
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


def get_valid_coupon_versions(
    product, user, auto_only=False, code=None, full_discount=False, company=None
):  # pylint:disable=too-many-arguments
    """
    Given a list of coupon ids, determine which of them are valid based on payment version dates and redemptions.

    Args:
        product (Product): product to filter CouponEligibility by
        user (User): User of coupons
        auto_only (bool): Whether or not to filter by automatic=True
        code (str): A coupon code to filter by
        full_discount (bool): If true, only include 100% off coupons
        company (Company): a company to filter by

    Returns:
        list of CouponVersion: CouponVersion objects sorted by discount, highest first.
    """
    now = now_in_utc()

    # Get enabled coupons eligible for the product
    product_coupon_subquery = CouponEligibility.objects.select_related("coupon").filter(
        product=product, coupon__enabled=True
    )
    if code:
        product_coupon_subquery = product_coupon_subquery.filter(
            coupon__coupon_code=code
        )

    # Get the latest versions for product coupons
    coupon_version_subquery = CouponVersion.objects.filter(
        coupon__in=Subquery(product_coupon_subquery.values_list("coupon", flat=True))
    )

    if full_discount:
        coupon_version_subquery = coupon_version_subquery.filter(
            payment_version__amount=decimal.Decimal(1)
        )

    if auto_only:
        coupon_version_subquery = coupon_version_subquery.filter(
            payment_version__automatic=True
        )

    if company is not None:
        coupon_version_subquery = coupon_version_subquery.filter(
            payment_version__company=company
        )

    coupon_version_subquery = coupon_version_subquery.order_by(
        "coupon", "-created_on"
    ).distinct("coupon")

    # Exclude versions with too many redemptions or active dates outside of today.
    query = (
        CouponVersion.objects.select_related("coupon", "payment_version")
        .filter(pk__in=Subquery(coupon_version_subquery.values_list("pk", flat=True)))
        .filter(
            Q(payment_version__expiration_date__gte=now)
            | Q(payment_version__expiration_date__isnull=True)
        )
        .filter(
            Q(payment_version__activation_date__lte=now)
            | Q(payment_version__activation_date__isnull=True)
        )
        .annotate(
            user_redemptions=(
                Count(
                    "couponredemption",
                    filter=(
                        Q(couponredemption__order__purchaser=user)
                        & Q(couponredemption__order__status=Order.FULFILLED)
                    ),
                )
            )
        )
        .annotate(
            global_redemptions=(
                Count(
                    "couponredemption",
                    filter=(Q(couponredemption__order__status=Order.FULFILLED)),
                )
            )
        )
        .exclude(user_redemptions__gte=F("payment_version__max_redemptions_per_user"))
        .exclude(global_redemptions__gte=F("payment_version__max_redemptions"))
    )

    return query.order_by("-payment_version__amount")


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


def complete_order(order):
    """
    Enrolls a user in all items associated with their Order and gets rid of checkout-related objects
    so that the user starts fresh next time they go through ecommerce.

    Args:
        order (Order): A fulfilled order
    """
    enroll_user_in_order_items(order)

    # If this order included assigned coupons, update them to indicate that they're redeemed
    order_coupon_ids = order.couponredemption_set.values_list(
        "coupon_version__coupon__id", flat=True
    )
    if order_coupon_ids:
        updated_count = ProductCouponAssignment.objects.filter(
            email=order.purchaser.email, product_coupon__coupon__in=order_coupon_ids
        ).update(redeemed=True)
        if updated_count:
            log.info(
                "Set %s coupon assignment(s) to redeemed (user: %s, coupon ids: %s)",
                updated_count,
                order.purchaser.email,
                str(order_coupon_ids),
            )

    # clear the basket
    with transaction.atomic():
        BasketItem.objects.filter(basket__user=order.purchaser).delete()
        CourseRunSelection.objects.filter(basket__user=order.purchaser).delete()
        CouponSelection.objects.filter(basket__user=order.purchaser).delete()


def enroll_user_in_order_items(order):
    """
    Enroll the user in the CourseRuns associated with their Order, and create local records of their
    enrollments.

    Args:
        order (Order): An order
    """
    basket = order.purchaser.basket
    runs = CourseRun.objects.filter(courserunselection__basket=basket)
    programs = get_order_programs(order)
    company = get_company_affiliation(order)

    try:
        enroll_in_edx_course_runs(order.purchaser, runs)
        edx_request_success = True
    except HTTPError as exc:
        log.exception(
            "edX API enrollment failure for user %s (order id: %s, run ids: %s, response: %s)",
            order.purchaser.username,
            order.id,
            str([run.id for run in runs]),
            exc.response.content.decode("utf-8"),
        )
        edx_request_success = False
    except Exception:  # pylint: disable=broad-except
        log.exception(
            "Unexpected edX enrollment error for user %s (order id: %s, run ids: %s)",
            order.purchaser.username,
            order.id,
            str([run.id for run in runs]),
        )
        edx_request_success = False

    voucher = (
        order.purchaser.vouchers.filter(
            product_id__in=order.lines.all().values_list(
                "product_version__product__id", flat=True
            )
        )
        .order_by("uploaded")
        .last()
    )
    voucher_target = None
    if (
        voucher
        and voucher.is_redeemed()
        and voucher.product is not None
        and voucher.enrollment is None
    ):
        voucher_target = voucher.product.content_object

    for run in runs:
        try:
            enrollment, created = CourseRunEnrollment.all_objects.get_or_create(
                user=order.purchaser,
                run=run,
                defaults=dict(company=company, edx_enrolled=edx_request_success),
            )
            if not created and not enrollment.active:
                enrollment.reactivate_and_save()
        except:  # pylint: disable=bare-except
            send_support_email(
                ENROLL_ERROR_EMAIL_SUBJECT,
                format_enrollment_message(order, run, format_exc()),
            )
            raise
        if voucher_target == run:
            voucher.enrollment = enrollment
            voucher.save()
    for program in programs:
        try:
            enrollment, created = ProgramEnrollment.all_objects.get_or_create(
                user=order.purchaser, program=program, defaults=dict(company=order)
            )
            if not created and not enrollment.active:
                enrollment.reactivate_and_save()
        except:  # pylint: disable=bare-except
            send_support_email(
                ENROLL_ERROR_EMAIL_SUBJECT,
                format_enrollment_message(order, program, format_exc()),
            )
            raise


def format_enrollment_message(order, obj, details):
    """
    Return a formatted error message for a failed enrollment

    Args:
        order (Order): the order with a failed enrollment
        obj (Program or CourseRun): the object that failed enrollment

    Returns:
        str: The formatted error message
    """
    return (
        "{name}({email}): Order #{order_id}, {error_obj} #{obj_id} ({obj_title})\n\n{details}".format(
            name=order.purchaser.name,
            email=order.purchaser.email,
            order_id=order.id,
            error_obj=("Run" if isinstance(obj, CourseRun) else "Program"),
            obj_id=obj.id,
            obj_title=obj.title,
            details=details,
        ),
    )


def get_company_affiliation(order):
    """ Get a company affiliated with an order via coupon """
    redemption = CouponRedemption.objects.filter(order=order).last()
    if redemption:
        return redemption.coupon_version.payment_version.company
    return None


def get_order_programs(order):
    """
    Returns all Programs in an Order

    Args:
        order (Order): An order

    Returns:
        list of Program: A list of Programs that were purchased in the order
    """
    return [
        line.product_version.product.content_object
        for line in order.lines.select_related("product_version__product").all()
        if line.product_version.product.content_type.model == CONTENT_TYPE_MODEL_PROGRAM
    ]


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
    with transaction.atomic():
        # Note: validation is assumed to already have happen when the basket is being modified
        basket, _ = Basket.objects.get_or_create(user=user)

        order = Order.objects.create(status=Order.CREATED, purchaser=user)

        for basket_item in basket.basketitems.all():
            product_version = latest_product_version(basket_item.product)
            Line.objects.create(
                order=order,
                product_version=product_version,
                quantity=basket_item.quantity,
            )

        for coupon_selection in basket.couponselection_set.all():
            coupon = coupon_selection.coupon
            redeem_coupon(coupon_version=latest_coupon_version(coupon), order=order)
        order.save_and_log(user)
    sync_hubspot_deal(order)
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


# pylint: disable=too-many-branches
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
        raise ValidationError({"items": "No items in basket, cannot checkout"})

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
            raise ValidationError({"coupons": "Coupon is not valid for product"})

    # Basket item runs must be linked to the basket item product
    run_queryset = product.run_queryset
    if (
        CourseRunSelection.objects.filter(basket=basket)
        .exclude(run__in=run_queryset)
        .exists()
    ):
        raise ValidationError(
            {"runs": "Some runs present in basket which are not part of product"}
        )

    # User must not already be enrolled in a course run covered by the product
    if CourseRunEnrollment.objects.filter(
        user=basket.user, run__in=run_queryset
    ).exists():
        raise ValidationError(
            {"runs": "User is already enrolled in one or more runs in basket"}
        )

    # User must have selected one run id for each course in basket
    runs = list(CourseRun.objects.filter(courserunselection__basket=basket))
    courses_runs = {}
    for run in runs:
        if run.course_id not in courses_runs:
            courses_runs[run.course_id] = run.id
        elif courses_runs[run.course_id] != run.id:
            raise ValidationError(
                {"runs": "Two or more runs assigned for a single course"}
            )

    if (
        len(courses_runs)
        != Course.objects.filter(courseruns__id__in=run_queryset).distinct().count()
    ):
        # This is != but it could be < because the > case should be covered in previous clauses.
        # The user can only select more courses than a product has if they are selecting runs outside
        # of the product, which we checked above.
        raise ValidationError({"runs": "Each course must have a course run selection"})

    # All run ids must be purchasable and enrollable by user
    for run in runs:
        if not run.is_unexpired:
            raise ValidationError({"runs": f"Run {run.id} is expired"})

    # User must have signed any data consent agreements necessary for the basket
    data_consents = get_or_create_data_consents(basket)
    for data_consent in data_consents:
        if data_consent.consent_date is None:
            raise ValidationError(
                {"data_consents": "The data consent agreement has not yet been signed"}
            )


def fetch_and_serialize_unused_coupons(user):
    """
    Fetches any unredeemed coupons assigned to a user and returns serialized coupon information

    Args:
        user (User): A user
    Returns:
        list: A list of dicts that represent an unreedeemed coupon, e.g.:
            {
                "coupon_code": "abcdef012345,
                "product_id": 123,
                "expiration_date": "2050-01-01T00:00:00.000000Z"
            }
    """
    unused_product_coupon_ids = ProductCouponAssignment.objects.filter(
        email=user.email, redeemed=False
    ).values_list("product_coupon", flat=True)
    if not unused_product_coupon_ids:
        return []

    now = now_in_utc()
    coupons_data = (
        CouponEligibility.objects.filter(id__in=unused_product_coupon_ids)
        .select_related("coupon__payment")
        .annotate(max_created_on=Max("coupon__payment__versions__created_on"))
        .filter(max_created_on=F("coupon__payment__versions__created_on"))
        .filter(
            Q(coupon__payment__versions__expiration_date=None)
            | Q(coupon__payment__versions__expiration_date__gt=now)
        )
        .order_by("coupon__payment__versions__expiration_date")
        .values(
            "product__id",
            "coupon__payment__versions__expiration_date",
            "coupon__coupon_code",
        )
    )
    return [
        {
            "coupon_code": coupon_data["coupon__coupon_code"],
            "product_id": coupon_data["product__id"],
            "expiration_date": coupon_data[
                "coupon__payment__versions__expiration_date"
            ],
        }
        for coupon_data in coupons_data
    ]


def get_or_create_data_consents(basket):
    """
    Get or create DataConsentUser objects for a basket.

    Args:
        basket (Basket): A user's basket

    Returns:
        list of models.DataConsentUser: A list of data consent agreements
    """
    data_consents = []
    coupon_selections = CouponSelection.objects.filter(basket=basket)
    if coupon_selections:
        courselists = [
            get_product_courses(item.product) for item in basket.basketitems.all()
        ]
        courses = [course for courselist in courselists for course in courselist]

        for coupon_selection in coupon_selections:
            company = latest_coupon_version(
                coupon_selection.coupon
            ).payment_version.company
            if company:
                agreements = (
                    DataConsentAgreement.objects.filter(company=company)
                    .filter(courses__in=courses)
                    .distinct()
                )

                data_consents.extend(
                    [
                        DataConsentUser.objects.get_or_create(
                            user=basket.user,
                            agreement=agreement,
                            coupon=coupon_selection.coupon,
                        )[0]
                        for agreement in agreements
                    ]
                )
    return data_consents
