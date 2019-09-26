"""
Functions for ecommerce
"""
from base64 import b64encode
import decimal
import hashlib
import hmac
import logging
from traceback import format_exc
from urllib.parse import quote_plus, urljoin, urlencode
import uuid

from django.conf import settings
from django.db.models import Q, Max, F, Count, Subquery
from django.db import transaction
from django.urls import reverse
from rest_framework.exceptions import ValidationError

from courses.constants import (
    CONTENT_TYPE_MODEL_PROGRAM,
    CONTENT_TYPE_MODEL_COURSE,
    CONTENT_TYPE_MODEL_COURSERUN,
)
from courses.models import (
    Course,
    CourseRun,
    CourseRunEnrollment,
    ProgramEnrollment,
    Program,
)
from courseware.api import enroll_in_edx_course_runs
from courseware.exceptions import (
    EdxApiEnrollErrorException,
    UnknownEdxApiEnrollException,
)
from ecommerce import mail_api
from ecommerce.constants import CYBERSOURCE_DECISION_ACCEPT, CYBERSOURCE_DECISION_CANCEL
from ecommerce.exceptions import EcommerceException
from ecommerce.models import (
    Basket,
    BasketItem,
    Company,
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
    Product,
    ProductCouponAssignment,
    Line,
    Order,
    Receipt,
)
from ecommerce.utils import send_support_email
from hubspot.task_helpers import sync_hubspot_deal
from mitxpro.utils import now_in_utc

log = logging.getLogger(__name__)

ISO_8601_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ENROLL_ERROR_EMAIL_SUBJECT = "MIT xPRO enrollment error"


# pylint: disable=too-many-lines
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


def make_receipt_url(*, base_url, readable_id):
    """
    Generate URL that user is redirected to on successful order

    Args:
        base_url (str): The base absolute url for the site
        readable_id (str): Program.readable_id or CourseRun.courseware_id
    Returns:
        str:
            The URL for the order receipt page
    """
    dashboard_url = urljoin(base_url, reverse("user-dashboard"))
    return f"{dashboard_url}?status=purchased&purchased={quote_plus(readable_id)}"


def get_readable_id(run_or_program):
    """
    Get the readable id for a course run or a program.

    Args:
        run_or_program (CourseRun or Program): A course run or a program

    Returns:
        str: The readable id
    """
    if isinstance(run_or_program, CourseRun):
        return run_or_program.courseware_id
    elif isinstance(run_or_program, Program):
        return run_or_program.readable_id
    else:
        raise Exception(f"Unexpected object {run_or_program}")


def sign_cybersource_payload(payload):
    """
    Return a payload signed with the CyberSource key

    Args:
        payload (dict): An unsigned payload to be sent to CyberSource

    Returns:
        dict:
            A signed payload to be sent to CyberSource
    """
    field_names = sorted(list(payload.keys()) + ["signed_field_names"])
    payload = {**payload, "signed_field_names": ",".join(field_names)}
    return {**payload, "signature": generate_cybersource_sa_signature(payload)}


# pylint: disable=too-many-locals
def _generate_cybersource_sa_payload(*, order, receipt_url, cancel_url):
    """
    Generates a payload dict to send to CyberSource for Secure Acceptance
    Args:
        order (Order): An order
        receipt_url (str): The URL to be used by Cybersource to redirect the user after completion of the purchase
        cancel_url (str): The URL to be used by Cybersource to redirect the user after they click cancel
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

    # At the moment there should only be one line
    product_version = order.lines.first().product_version
    product = product_version.product
    content_object = product.content_object
    readable_id = get_readable_id(content_object)

    merchant_fields = {
        "merchant_defined_data1": str(product.content_type),
        "merchant_defined_data2": readable_id,
        "merchant_defined_data3": "1",
    }

    if coupon_version is not None:
        merchant_fields["merchant_defined_data4"] = coupon_version.coupon.coupon_code
        merchant_fields["merchant_defined_data5"] = (  # company name
            coupon_version.payment_version.company.name
            if coupon_version.payment_version.company
            else ""
        )
        merchant_fields["merchant_defined_data6"] = (
            coupon_version.payment_version.payment_transaction or ""
        )
        merchant_fields["merchant_defined_data7"] = (
            coupon_version.payment_version.payment_type or ""
        )

    return {
        "access_key": settings.CYBERSOURCE_ACCESS_KEY,
        "amount": str(total),
        "consumer_id": order.purchaser.username,
        "currency": "USD",
        "locale": "en-us",
        **line_items,
        "line_item_count": order.lines.count(),
        **merchant_fields,
        "reference_number": order.reference_number,
        "profile_id": settings.CYBERSOURCE_PROFILE_ID,
        "signed_date_time": now_in_utc().strftime(ISO_8601_FORMAT),
        "override_custom_receipt_page": receipt_url,
        "override_custom_cancel_page": cancel_url,
        "transaction_type": "sale",
        "transaction_uuid": uuid.uuid4().hex,
        "unsigned_field_names": "",
    }


def generate_cybersource_sa_payload(*, order, receipt_url, cancel_url):
    """
    Generates a payload dict to send to CyberSource for Secure Acceptance
    Args:
        order (Order): An order
        receipt_url (str): The URL to be used by Cybersource to redirect the user after completion of the purchase
        cancel_url (str): The URL to be used by Cybersource to redirect the user after they click cancel
    Returns:
        dict: the payload to send to CyberSource via Secure Acceptance
    """
    return sign_cybersource_payload(
        _generate_cybersource_sa_payload(
            order=order, receipt_url=receipt_url, cancel_url=cancel_url
        )
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
                        & Q(
                            couponredemption__order__status__in=(
                                Order.FULFILLED,
                                Order.REFUNDED,
                            )
                        )
                    ),
                )
            )
        )
        .annotate(
            global_redemptions=(
                Count(
                    "couponredemption",
                    filter=(
                        Q(
                            couponredemption__order__status__in=(
                                Order.FULFILLED,
                                Order.REFUNDED,
                            )
                        )
                    ),
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
    except (EdxApiEnrollErrorException, UnknownEdxApiEnrollException):
        log.exception(
            "Order enrollment failure for order id: %s (user: %s, runs in order: %s)",
            order.id,
            order.purchaser.email,
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
                order=order,
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
        if enrollment.edx_enrolled:
            mail_api.send_course_run_enrollment_email(enrollment)

    for program in programs:
        try:
            enrollment, created = ProgramEnrollment.all_objects.get_or_create(
                user=order.purchaser,
                program=program,
                order=order,
                defaults=dict(company=company),
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
        details (str): Details of the error (typically a stack trace)

    Returns:
        str: The formatted error message
    """
    return "{name}({email}): Order #{order_id}, {error_obj} #{obj_id} ({obj_title})\n\n{details}".format(
        name=order.purchaser.username,
        email=order.purchaser.email,
        order_id=order.id,
        error_obj=("Run" if isinstance(obj, CourseRun) else "Program"),
        obj_id=obj.id,
        obj_title=obj.title,
        details=details,
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

        order = Order.objects.create(
            status=Order.CREATED, purchaser=user, total_price_paid=decimal.Decimal(0)
        )

        product_version = None
        for basket_item in basket.basketitems.all():
            product_version = latest_product_version(basket_item.product)
            Line.objects.create(
                order=order,
                product_version=product_version,
                quantity=basket_item.quantity,
            )

        coupon_version = None
        for coupon_selection in basket.couponselection_set.all():
            coupon = coupon_selection.coupon
            coupon_version = latest_coupon_version(coupon)
            redeem_coupon(coupon_version=coupon_version, order=order)
        order.total_price_paid = get_product_version_price_with_discount(
            coupon_version=coupon_version, product_version=product_version
        )
        order.save()
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
    full_coupon_payments = (
        CouponPayment.objects.annotate(max_created_on=Max("versions__created_on"))
        .filter(
            versions__coupon_type=CouponPaymentVersion.SINGLE_USE,
            max_created_on=F("versions__created_on"),
            versions__amount=1,
        )
        .with_ordered_versions()
    )
    for coupon_payment in full_coupon_payments:
        products = (
            Product.objects.annotate(
                product_coupon_ct=Count(
                    "couponeligibility",
                    filter=Q(
                        couponeligibility__coupon__enabled=True,
                        couponeligibility__coupon__payment=coupon_payment,
                    ),
                )
            )
            .filter(product_coupon_ct__gt=0, is_active=True)
            .with_ordered_versions()
            .order_by("id")
            .select_related("content_type")
        )
        if products.exists():
            yield coupon_payment, products


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


def create_coupons(
    *,
    name,
    product_ids,
    amount,
    num_coupon_codes,
    coupon_type,
    max_redemptions=1,
    tag=None,
    company_id=None,
    automatic=False,
    activation_date=None,
    expiration_date=None,
    payment_type=None,
    payment_transaction=None,
    coupon_code=None,
):
    """
    Create one or more coupons and whatever instances are needed for them.

    Args:
        name (str): Name of the CouponPayment
        company_id (int): The id for a Company object
        tag (str): The tag for the CouponPayment
        automatic (bool): Whether or not the coupon should be applied automatically
        activation_date (datetime.datetime): The date after which the coupon is valid. If None, the coupon is valid
        expiration_date (datetime.datetime): The date before which the coupon is valid. If None, the coupon never expires
        amount (decimal.Decimal): The percent of the coupon, between 0 and 1 (inclusive)
        num_coupon_codes (int): The number of coupon codes which should be created for the CouponPayment
        coupon_type (str): The type of coupon
        max_redemptions (int): The number of times a coupon can be redeemed before it becomes invalid
        payment_type (str): The type of payment
        payment_transaction (str): The transaction string
        coupon_code (str):
            If specified, the coupon code to use when creating the coupon. If not a random one will be generated.
        product_ids (list of int): A list of product ids

    Returns:
        CouponPaymentVersion:
        A CouponPaymentVersion. Other instances will be created at the same time and linked via foreign keys.

    """
    if company_id:
        company = Company.objects.get(id=company_id)
    else:
        company = None
    payment = CouponPayment.objects.create(name=name)
    payment_version = CouponPaymentVersion.objects.create(
        payment=payment,
        company=company,
        tag=tag,
        automatic=automatic,
        activation_date=activation_date,
        expiration_date=expiration_date,
        amount=amount,
        num_coupon_codes=num_coupon_codes,
        coupon_type=coupon_type,
        max_redemptions=max_redemptions,
        max_redemptions_per_user=1,
        payment_type=payment_type,
        payment_transaction=payment_transaction,
    )

    coupons = [
        Coupon(coupon_code=(coupon_code or uuid.uuid4().hex), payment=payment)
        for _ in range(num_coupon_codes)
    ]
    coupon_objs = Coupon.objects.bulk_create(coupons)
    versions = [
        CouponVersion(coupon=obj, payment_version=payment_version)
        for obj in coupon_objs
    ]
    eligibilities = [
        CouponEligibility(coupon=obj, product_id=product_id)
        for obj in coupon_objs
        for product_id in product_ids
    ]
    CouponVersion.objects.bulk_create(versions)
    CouponEligibility.objects.bulk_create(eligibilities)
    return payment_version


def determine_order_status_change(order, decision):
    """
    Detemine what the new order status should be based on the CyberSource decision.

    Args:
        order (OrderAbstract): An order object with a status field
        decision (str): The CyberSource decision

    Returns:
        str:
            Returns the new order status, or None if there is no status change
    """
    if order.status == Order.FAILED and decision == CYBERSOURCE_DECISION_CANCEL:
        # This is a duplicate message, ignore since it's already handled
        return None

    if order.status != Order.CREATED:
        raise EcommerceException(f"{order} is expected to have status 'created'")

    if decision != CYBERSOURCE_DECISION_ACCEPT:
        log.warning(
            "Order fulfillment failed: received a decision that wasn't ACCEPT for order %s",
            order,
        )
        return Order.FAILED

    return Order.FULFILLED


def make_checkout_url(*, product_id=None, code=None):
    """
    Helper function to create a checkout URL with appropriate query parameters.

    Args:
        product_id (int): A Product ID
        code (str): The coupon code

    Returns:
        str: The URL for the checkout page, including product and coupon code if available
    """
    base_checkout_url = urljoin(settings.SITE_BASE_URL, reverse("checkout-page"))
    if product_id is None and code is None:
        return base_checkout_url

    query_params = {}
    if product_id is not None:
        query_params["product"] = product_id
    if code is not None:
        query_params["code"] = code
    return f"{base_checkout_url}?{urlencode(query_params)}"


def fulfill_order(request_data):
    """
    Fulfill an order for end user purchase of a Product.

    Args:
        request_data (dict): Request data from CyberSource
    """
    # First, save this information in a receipt
    receipt = Receipt.objects.create(data=request_data)

    # Link the order with the receipt if we can parse it
    reference_number = request_data["req_reference_number"]
    order = Order.objects.get_by_reference_number(reference_number)
    receipt.order = order
    receipt.save()

    new_order_status = determine_order_status_change(order, request_data["decision"])
    if new_order_status is None:
        # This is a duplicate message, ignore since it's already handled
        return

    order.status = new_order_status
    order.save()
    sync_hubspot_deal(order)

    if order.status == Order.FULFILLED:
        complete_order(order)

    # Save to log everything to an audit table including enrollments created in complete_order
    order.save_and_log(None)
