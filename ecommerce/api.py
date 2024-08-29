"""
Functions for ecommerce
"""

import decimal
import hashlib
import hmac
import logging
import re
import uuid
from base64 import b64encode
from collections import defaultdict
from collections.abc import Iterable
from datetime import timedelta
from typing import NamedTuple
from urllib.parse import quote_plus, urljoin

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Max, Prefetch, Q, Subquery
from django.http import HttpRequest
from django.urls import reverse
from ipware import get_client_ip
from rest_framework.exceptions import ValidationError

import sheets.tasks
from affiliate.models import AffiliateReferralAction
from courses.api import create_program_enrollments, create_run_enrollments
from courses.constants import (
    CONTENT_TYPE_MODEL_COURSE,
    CONTENT_TYPE_MODEL_COURSERUN,
    CONTENT_TYPE_MODEL_PROGRAM,
    PROGRAM_RUN_ID_PATTERN,
)
from courses.models import CourseRun, Program, ProgramRun
from courses.utils import is_program_text_id
from ecommerce.constants import (
    CYBERSOURCE_DECISION_ACCEPT,
    CYBERSOURCE_DECISION_CANCEL,
    DISCOUNT_TYPE_DOLLARS_OFF,
    DISCOUNT_TYPE_PERCENT_OFF,
)
from ecommerce.exceptions import EcommerceException
from ecommerce.mail_api import send_ecommerce_order_receipt
from ecommerce.models import (
    Basket,
    BasketItem,
    BulkCouponAssignment,
    Company,
    Coupon,
    CouponEligibility,
    CouponPayment,
    CouponPaymentVersion,
    CouponRedemption,
    CouponSelection,
    CouponVersion,
    DataConsentAgreement,
    DataConsentUser,
    Line,
    LineRunSelection,
    Order,
    Product,
    ProductCouponAssignment,
    ProductVersion,
    ProgramRunLine,
    Receipt,
    TaxRate,
)
from ecommerce.utils import positive_or_zero
from hubspot_xpro.task_helpers import sync_hubspot_deal
from maxmind.api import ip_to_country_code
from mitxpro.utils import case_insensitive_equal, first_or_none, now_in_utc

log = logging.getLogger(__name__)

ISO_8601_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


# Calculated Tax Rate is (rate applied, adjusted amount)
CalculatedTaxRate = tuple[decimal.Decimal, str, decimal.Decimal]


def determine_visitor_country(request: HttpRequest or None) -> str or None:
    """
    Determines the country the user is in for tax purposes.

    If the learner's IP geolocates to a location that we assess tax for, this
    returns that location code. Otherwise, it will return the country code from
    the learner's profile. (The set of locations that we assess tax for is
    relatively small so we want to prefer the user's self-reported location,
    unless they're physically somewhere else that also charges tax.)

    Args:
        request (HttpRequest): the current request object
    Returns:
        The resolved country, or the learner's profile country code
    """

    if not request or not request.user.is_authenticated:
        return None

    profile_country_code = (
        request.user.legal_address.country if request.user.is_authenticated else None
    )

    if settings.ECOMMERCE_FORCE_PROFILE_COUNTRY:
        return profile_country_code

    try:
        client_ip, _ = get_client_ip(request)
        ip_country_code = ip_to_country_code(client_ip)

        if TaxRate.objects.filter(active=True, country_code=ip_country_code).exists():
            return ip_country_code

        return profile_country_code  # noqa: TRY300
    except TypeError:
        return profile_country_code


def calculate_tax(
    request: HttpRequest, item_price: decimal.Decimal
) -> CalculatedTaxRate:
    """
    Calculate the tax to be assessed for the given amount.

    This uses the logged in user's profile and their IP to determine whether or
    not to charge tax - if _both_ the IP's country and the profile country code
    match, _and_ there's a TaxRate for the country, then we charge tax.
    Otherwise, we don't.

    Args:
        request_ip (HttpRequest): The current request.
        item_price (Decimal): The amount to be taxed.
    Returns:
        tuple(rate applied, country code, adjusted amount): The rate applied and the adjusted amount based on the determined country code.
    """

    resolved_country_code = determine_visitor_country(request)

    if resolved_country_code is None:
        return (0, "", item_price)

    try:
        tax_rate = TaxRate.objects.filter(
            active=True, country_code__iexact=resolved_country_code
        ).get()

        tax_inclusive_amt = item_price + (
            decimal.Decimal(item_price) * (tax_rate.tax_rate / 100)
        )

        return (tax_rate.tax_rate, resolved_country_code, tax_inclusive_amt)  # noqa: TRY300
    except TaxRate.DoesNotExist:
        pass

    return (0, "", item_price)


def display_taxes(request):
    """
    Returns a boolean to manage the taxes display.

    Args:
        request(HttpRequest): Request object

    Returns:
        Boolean: True if flag and taxes are enabled for the specific country.
    """
    visitor_country = determine_visitor_country(request)
    return (
        settings.FEATURES.get("ENABLE_TAXES_DISPLAY", False)
        and TaxRate.objects.filter(active=True, country_code=visitor_country).exists()
    )


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
        raise Exception(f"Unexpected object {run_or_program}")  # noqa: EM102, TRY002, TRY004


def sign_cybersource_payload(payload):
    """
    Return a payload signed with the CyberSource key

    Args:
        payload (dict): An unsigned payload to be sent to CyberSource

    Returns:
        dict:
            A signed payload to be sent to CyberSource
    """
    field_names = sorted(list(payload.keys()) + ["signed_field_names"])  # noqa: RUF005
    payload = {**payload, "signed_field_names": ",".join(field_names)}
    return {**payload, "signature": generate_cybersource_sa_signature(payload)}


def _generate_cybersource_sa_payload(*, order, receipt_url, cancel_url, ip_address):
    """
    Generates a payload dict to send to CyberSource for Secure Acceptance
    Args:
        order (Order): An order
        receipt_url (str): The URL to be used by Cybersource to redirect the user after completion of the purchase
        cancel_url (str): The URL to be used by Cybersource to redirect the user after they click cancel
        ip_address (str): The user's IP address
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
    total_tax_assessed = 0
    for i, line in enumerate(order.lines.all()):
        product_version = line.product_version
        product_price_dict = get_product_version_price_with_discount_tax(
            coupon_version=coupon_version,
            product_version=product_version,
            tax_rate=order.tax_rate,
        )
        line_items[f"item_{i}_code"] = str(product_version.product.content_type)
        line_items[f"item_{i}_name"] = str(product_version.description)[:254]
        line_items[f"item_{i}_quantity"] = line.quantity
        line_items[f"item_{i}_sku"] = product_version.product.content_object.id
        line_items[f"item_{i}_tax_amount"] = str(
            decimal.Decimal(product_price_dict["tax_assessed"]).quantize(
                decimal.Decimal("0.01")
            )
        )
        line_items[f"item_{i}_unit_price"] = str(product_price_dict["price"])

        total += product_price_dict["price"]
        total_tax_assessed += product_price_dict["tax_assessed"]

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
        "amount": str(
            decimal.Decimal(total + total_tax_assessed).quantize(
                decimal.Decimal("0.01")
            )
        ),
        "tax_amount": str(
            decimal.Decimal(total_tax_assessed).quantize(decimal.Decimal("0.01"))
        ),
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
        "customer_ip_address": ip_address if ip_address else None,
    }


def generate_cybersource_sa_payload(*, order, receipt_url, cancel_url, ip_address=None):
    """
    Generates a payload dict to send to CyberSource for Secure Acceptance
    Args:
        order (Order): An order
        receipt_url (str): The URL to be used by Cybersource to redirect the user after completion of the purchase
        cancel_url (str): The URL to be used by Cybersource to redirect the user after they click cancel
        ip_address (str): The user's IP address
    Returns:
        dict: the payload to send to CyberSource via Secure Acceptance
    """
    return sign_cybersource_payload(
        _generate_cybersource_sa_payload(
            order=order,
            receipt_url=receipt_url,
            cancel_url=cancel_url,
            ip_address=ip_address,
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


def get_valid_coupon_versions(  # noqa: PLR0913
    product,
    user,
    auto_only=False,  # noqa: FBT002
    code=None,
    full_discount=False,  # noqa: FBT002
    company=None,
):
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

    # Get all enabled global coupons
    global_coupon_subquery = Coupon.objects.filter(is_global=True, enabled=True)

    if code:
        product_coupon_subquery = product_coupon_subquery.filter(
            coupon__coupon_code=code
        )
        global_coupon_subquery = global_coupon_subquery.filter(coupon_code=code)

    # Get the latest versions for product coupons
    coupon_version_subquery = CouponVersion.objects.filter(
        coupon__in=Subquery(product_coupon_subquery.values_list("coupon", flat=True))
    )
    global_coupon_version_subquery = CouponVersion.objects.filter(
        coupon__in=global_coupon_subquery.values_list("pk", flat=True)
    )

    if product:
        product_version = latest_product_version(product)
        if product_version and product_version.requires_enrollment_code:
            global_coupon_version_subquery = global_coupon_version_subquery.exclude(
                payment_version__coupon_type=CouponPaymentVersion.PROMO
            )

    if full_discount:
        # We can only get full discount for dollars-off when we know the price

        if product is None or not product.productversions.exists():
            coupon_version_subquery = coupon_version_subquery.filter(
                payment_version__amount=decimal.Decimal(1)
            )
            global_coupon_version_subquery = global_coupon_version_subquery.filter(
                payment_version__amount=decimal.Decimal(1)
            )
        else:
            product_version = latest_product_version(product)
            coupon_version_subquery = coupon_version_subquery.filter(
                Q(
                    payment_version__discount_type=DISCOUNT_TYPE_PERCENT_OFF,
                    payment_version__amount=decimal.Decimal(1),
                )
                | Q(
                    payment_version__discount_type=DISCOUNT_TYPE_DOLLARS_OFF,
                    payment_version__amount__gte=product_version.price,
                )
            ).distinct()

            global_coupon_version_subquery = global_coupon_version_subquery.filter(
                Q(
                    payment_version__discount_type=DISCOUNT_TYPE_PERCENT_OFF,
                    payment_version__amount=decimal.Decimal(1),
                )
                | Q(
                    payment_version__discount_type=DISCOUNT_TYPE_DOLLARS_OFF,
                    payment_version__amount__gte=product_version.price,
                )
            ).distinct()

    if auto_only:
        coupon_version_subquery = coupon_version_subquery.filter(
            payment_version__automatic=True
        )
        global_coupon_version_subquery = global_coupon_version_subquery.filter(
            payment_version__automatic=True
        )

    if company is not None:
        coupon_version_subquery = coupon_version_subquery.filter(
            payment_version__company=company
        )
        global_coupon_version_subquery = global_coupon_version_subquery.filter(
            payment_version__company=company
        )

    coupon_version_subquery = coupon_version_subquery.order_by(
        "coupon", "-created_on"
    ).distinct("coupon")

    global_coupon_version_subquery = global_coupon_version_subquery.order_by(
        "coupon", "-created_on"
    ).distinct("coupon")

    combined_coupon_versions_list = list(
        coupon_version_subquery.values_list("pk", flat=True)
    ) + list(global_coupon_version_subquery.values_list("pk", flat=True))

    # Exclude versions with too many redemptions or active dates outside of today.
    query = (
        CouponVersion.objects.select_related("coupon", "payment_version")
        .filter(pk__in=combined_coupon_versions_list)
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


def best_coupon_for_product(product, user, auto_only=False, code=None):  # noqa: FBT002
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
        product_version = latest_product_version(product)
        best_price = product_version.price
        best_coupon = validated_versions[0]
        # Let's calculate the discount for the valid coupons and return the best one
        for valid_coupon in validated_versions:
            calculated_discount_price = get_product_version_price_with_discount(
                product_version=product_version, coupon_version=valid_coupon
            )
            if calculated_discount_price < best_price:
                best_price = calculated_discount_price
                best_coupon = valid_coupon
        return best_coupon
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
    discount_amount = 0

    if coupon_version and (
        coupon_version.coupon.is_global
        or CouponEligibility.objects.filter(
            coupon__versions=coupon_version, product__productversions=product_version
        ).exists()
    ):
        discount_amount = coupon_version.payment_version.calculate_discount_amount(
            price=price
        )
    return positive_or_zero(price - discount_amount)


def get_product_version_price_with_discount_tax(
    *, coupon_version, product_version, tax_rate
):
    """
    Uses get_product_version_price_with_discount to get the price for the item
    and then add the specified tax amount to it.

    Args:
        coupon_version (CouponVersion): the CouponVersion object
        product_version (ProductVersion): the ProductVersion object
        tax_rate (Decimal): the tax rate to apply

    Returns:
        dict:
        - price (Decimal): discounted price for the Product
        - tax_assessed (Decimal): tax assessed for the discounted price
    """

    product_version_price = get_product_version_price_with_discount(
        coupon_version=coupon_version, product_version=product_version
    )

    return {
        "price": product_version_price,
        "tax_assessed": (
            0
            if not tax_rate
            else decimal.Decimal(product_version_price * (tax_rate / 100))
        ),
    }


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


def set_coupons_to_redeemed(redeemed_email, coupon_ids):
    """
    Updates coupon assignment records to indicate that they have been redeemed, and starts a task to
    update the status of the corresponding coupon assignment spreadsheet rows if they exist.

    Args:
        redeemed_email (str): The email address that was used to redeem the given coupons
        coupon_ids (iterable of int): ecommerce.models.Coupon id values for the Coupons that were redeemed
    """
    updated_assignments = []
    with transaction.atomic():
        assignments = (
            ProductCouponAssignment.objects.select_for_update()
            .filter(product_coupon__coupon__in=coupon_ids)
            .select_related("product_coupon__coupon")
        )
        for assignment in assignments:
            if not assignment.redeemed:
                assignment.redeemed = True
                # We allow codes to be redeemed by an email other than the one that was assigned. If the user that
                # redeemed this code does not match the email on the ProductCouponAssignment, update the db record.
                if not case_insensitive_equal(redeemed_email, assignment.email):
                    assignment.original_email = assignment.email
                    assignment.email = redeemed_email
                assignment.save()
                updated_assignments.append(assignment)
    # If the redeemed coupons were assigned in bulk enrollment spreadsheets, update those spreadsheets
    # to reflect that they were redeemed
    updated_assignments_in_bulk = [
        assignment
        for assignment in updated_assignments
        if assignment.bulk_assignment and assignment.bulk_assignment.assignment_sheet_id
    ]
    if updated_assignments_in_bulk:
        sheet_update_map = defaultdict(dict)
        for assignment in updated_assignments_in_bulk:
            sheet_update_map[assignment.bulk_assignment.assignment_sheet_id][
                assignment.product_coupon.coupon.coupon_code
            ] = assignment.email
        sheets.tasks.set_assignment_rows_to_enrolled.delay(sheet_update_map)


def clear_and_delete_baskets(user=None):
    """
    Delete baskets and all the associated items.

    Args:
       user (User, optional): The user whose baskets should be deleted. If not provided, expired baskets will be deleted.
    """
    cutoff_date = now_in_utc() - timedelta(days=settings.BASKET_EXPIRY_DAYS)
    basket_filter = {"user": user} if user else {"updated_on__lte": cutoff_date}

    with transaction.atomic():
        baskets = Basket.objects.select_for_update(skip_locked=True).filter(
            **basket_filter
        )
        log.info(
            "Basket deletion requested for baskets Ids: %s",
            [basket.id for basket in baskets],
        )
        for basket in baskets:
            log.info("Clearing and deleting basket with Id: %s", basket.id)

            with transaction.atomic():
                basket_items = basket.basketitems.all()
                log.info(
                    "Deleting basket items: %s",
                    list(basket_items.values_list("id", flat=True)),
                )
                basket_items.delete()

                course_run_selections = basket.courserunselection_set.all()
                course_run_selections_ids = list(
                    course_run_selections.values_list("id", flat=True)
                )
                log.info(
                    "Deleting course run selections: %s", course_run_selections_ids
                )
                course_run_selections.delete()

                coupon_selections = basket.couponselection_set.all()
                coupon_selections_ids = list(
                    coupon_selections.values_list("id", flat=True)
                )
                log.info("Deleting coupon selections: %s", coupon_selections_ids)
                coupon_selections.delete()

                log.info("Deleting basket: %s", basket.id)
                basket.delete()


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
        set_coupons_to_redeemed(order.purchaser.email, order_coupon_ids)

    # clear and delete the basket
    clear_and_delete_baskets(order.purchaser)


def enroll_user_in_order_items(order):
    """
    Enroll the user in the CourseRuns associated with their Order, and create local records of their
    enrollments.

    Args:
        order (Order): An order
    """
    order_line = Line.objects.prefetch_related("line_selections__run").get(order=order)
    runs = [line_selection.run for line_selection in order_line.line_selections.all()]
    programs = get_order_programs(order)
    company = get_company_affiliation(order)

    if programs and not runs:
        log.error(
            "An order is being completed for a program, but does not have any course run selections. "
            "(Order: %d, purchaser: '%s', program(s): %s)",
            order.id,
            order.purchaser.email,
            [program.readable_id for program in programs],
        )

    successful_run_enrollments = []
    if runs:
        successful_run_enrollments, _ = create_run_enrollments(
            order.purchaser,
            runs,
            order=order,
            company=company,
            keep_failed_enrollments=True,
        )

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
    voucher_enrollment = first_or_none(
        enrollment
        for enrollment in successful_run_enrollments
        if enrollment.run == voucher_target
    )
    if voucher_enrollment is not None:
        voucher.enrollment = voucher_enrollment
        voucher.save()

    if programs:
        create_program_enrollments(
            order.purchaser, programs, order=order, company=company
        )


def get_company_affiliation(order):
    """Get a company affiliated with an order via coupon"""
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


def create_unfulfilled_order(validated_basket, affiliate_id=None, **kwargs):
    """
    Create a new Order which is not fulfilled for a purchasable Product. Note that validation should
    be done in the basket REST API so the validation is not done here (different from MicroMasters).

    This now also takes the request as an argument, so that the necessary tax
    fields can be filled out and tax calculated as well.

    Args:
        validated_basket (ValidatedBasket): The validated Basket and related objects
        affiliate_id (Optional[int]): The id of the Affiliate record to associate with this order

    Keyword Args:
        request (HttpRequest): The current request object, for tax calculation.

    Returns:
        Order: A newly created Order for the Product in the basket
    """
    with transaction.atomic():
        total_price_paid = get_product_version_price_with_discount(
            coupon_version=validated_basket.coupon_version,
            product_version=validated_basket.product_version,
        )
        country_code = determine_visitor_country(
            kwargs["request"] if "request" in kwargs else None  # noqa: SIM401
        )

        try:
            tax_rate_info = TaxRate.objects.filter(active=True).get(
                country_code=country_code
            )
        except (TaxRate.DoesNotExist, TaxRate.MultipleObjectsReturned):
            # not using get_or_create here because we don't want the rate to stick around
            tax_rate_info = TaxRate()

        order = Order.objects.create(
            status=Order.CREATED,
            purchaser=validated_basket.basket.user,
            total_price_paid=total_price_paid,
            tax_country_code=country_code,
            tax_rate=tax_rate_info.tax_rate,
            tax_rate_name=tax_rate_info.tax_rate_name,
        )
        line = Line.objects.create(
            order=order,
            product_version=validated_basket.product_version,
            quantity=validated_basket.basket_item.quantity,
        )
        if validated_basket.basket_item.program_run:
            ProgramRunLine.objects.create(
                line=line, program_run=validated_basket.basket_item.program_run
            )
        if validated_basket.run_selection_ids:
            LineRunSelection.objects.bulk_create(
                LineRunSelection(line=line, run_id=run_id)
                for run_id in validated_basket.run_selection_ids
            )
        if validated_basket.coupon_version:
            redeem_coupon(coupon_version=validated_basket.coupon_version, order=order)
        if affiliate_id is not None:
            AffiliateReferralAction.objects.create(
                affiliate_id=affiliate_id, created_order=order
            )
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
    if product.content_type.model == CONTENT_TYPE_MODEL_COURSERUN:  # noqa: RET503
        return [product.content_object.course]
    elif product.content_type.model == CONTENT_TYPE_MODEL_COURSE:
        return [product.content_object]
    elif product.content_type.model == CONTENT_TYPE_MODEL_PROGRAM:
        return list(
            product.content_object.courses.all().order_by("position_in_program")
        )


def bulk_assign_product_coupons(desired_assignments, bulk_assignment=None):
    """
    Assign product coupons to emails in bulk and create a record of this bulk creation

    Args:
        desired_assignments (Iterable[(str, int)]): An iterable of emails paired with the
            CouponEligibility id that each email should be assigned
        bulk_assignment (Optional[BulkCouponAssignment]): A BulkCouponAssignment object, or
            None if a new one should be created

    Returns:
        (BulkCouponAssignment, List[ProductCouponAssignment]): The BulkCouponAssignment object paired with
            all of the ProductCouponAssignments that were created for it
    """
    bulk_assignment = bulk_assignment or BulkCouponAssignment.objects.create()
    return (
        bulk_assignment,
        ProductCouponAssignment.objects.bulk_create(
            ProductCouponAssignment(
                email=email,
                product_coupon_id=product_coupon_id,
                bulk_assignment=bulk_assignment,
            )
            for email, product_coupon_id in desired_assignments
        ),
    )


class ValidatedBasket(NamedTuple):
    """An object representing a Basket and related objects that have been validated to be ready for checkout"""

    basket: Basket
    basket_item: BasketItem
    product_version: ProductVersion
    coupon_version: CouponVersion | None
    run_selection_ids: Iterable[int] | None
    data_consent_users: Iterable[DataConsentUser] | None


def _validate_basket_contents(basket):
    """
    Verifies that the contents of the basket and the item being purchased are all valid, and returns objects from
    the database that are related to the basket.

    Args:
        basket (Basket): The basket being validated

    Returns:
        (BasketItem, Product, ProductVersion): The basket item, product, and product version associated with
            the basket
    """
    # A basket is expected to have a one item (which in turn will create one Line)
    basket_items = basket.basketitems.all()
    if len(basket_items) == 0:
        raise ValidationError(
            {"items": "No items in basket. Cannot complete checkout."}
        )
    if len(basket_items) > 1:
        log.error(
            "User %s is checking out %d items in their basket. Baskets should only have one BasketItem.",
            basket.user.email,
            len(basket_items),
        )
        raise ValidationError(
            {
                "items": "Something went wrong with the items being purchased. Please contact support."
            }
        )
    basket_item = basket_items[0]
    product = basket_item.product
    if product.is_active is False or product.content_object.live is False:
        log.error(
            "User %s is checking out with a product in their basket that was not live (%s).",
            basket.user.email,
            product.content_object.text_id,
        )
        raise ValidationError(
            {"items": "This item cannot be purchased. Please contact support."}
        )
    product_version = latest_product_version(basket_item.product)
    return basket_item, product, product_version


def _validate_basket_run_selections(basket, product_object):
    """
    Verifies that the course run selections for the given basket are valid, and returns the course run IDs of the
    selected course runs.

    Args:
        basket (Basket): The basket being validated
        product_object (Union([Program, CourseRun])): The program or course run being purchased

    Returns:
        set of int: The course run IDs of the selected course runs
    """
    course_run_selections = basket.courserunselection_set.all()
    if len(course_run_selections) == 0:
        raise ValidationError({"runs": "You must select a date for each course."})
    if isinstance(product_object, Program):
        valid_course_ids = set(
            product_object.courses.live().values_list("id", flat=True)
        )
    else:
        valid_course_ids = {product_object.course_id}
    if len(course_run_selections) < len(valid_course_ids):
        raise ValidationError({"runs": "You must select a date for each course."})
    selected_course_ids = {
        selection.run.course_id for selection in course_run_selections
    }
    if len(course_run_selections) > len(
        valid_course_ids
    ) or not selected_course_ids.issubset(valid_course_ids):
        raise ValidationError({"runs": "Some invalid courses were selected."})
    for selection in course_run_selections:
        if not selection.run.is_unexpired:
            raise ValidationError(
                {
                    "runs": f"Course '{selection.run.title}' is not accepting enrollments."
                }
            )
    selected_course_run_ids = {
        run_selection.run_id for run_selection in course_run_selections
    }
    if basket.user.courserunenrollment_set.filter(
        run__in=selected_course_run_ids
    ).exists():
        raise ValidationError(
            {"runs": "You are already enrolled in one or more of these courses."}
        )
    return selected_course_run_ids


def _validate_coupon_selection(basket, product):
    """
    Verifies that the any coupons applied to the basket are valid, and returns the coupon version if a
    valid coupon code was applied.

    Args:
        basket (Basket): The basket being validated
        product (Product): The product being purchased

    Returns:
        Optional(CouponVersion): The coupon version associated with the applied coupon code (or None if no code was
            applied to the basket)
    """
    coupon_selections = basket.couponselection_set
    if coupon_selections.count() > 1:
        log.error(
            "User %s is checking out with multiple coupon selections. There should be one or zero.",
            basket.user.email,
        )
        raise ValidationError(
            {
                "coupons": "Something went wrong with your coupon. Please clear it and try again."
            }
        )
    coupon_selection = first_or_none(coupon_selections.all())
    if coupon_selection is None:
        coupon_version = None
    else:
        valid_product_coupon_versions = get_valid_coupon_versions(
            product=product, user=basket.user, code=coupon_selection.coupon.coupon_code
        )
        coupon_version = first_or_none(valid_product_coupon_versions)
        if coupon_version is None:
            raise ValidationError({"coupons": "Coupon is not valid for product."})
    return coupon_version


def validate_basket_for_checkout(user):
    """
    Validate basket for checkout

    Args:
        user (User): The user whose basket needs validation

    Returns:
        ValidatedBasket: The validated Basket and related objects
    """
    basket = Basket.objects.prefetch_related(
        "basketitems__product__content_object",
        "couponselection_set__coupon",
        "courserunselection_set__run",
    ).get(user=user)

    basket_item, product, product_version = _validate_basket_contents(basket)
    selected_course_run_ids = _validate_basket_run_selections(
        basket, product.content_object
    )
    coupon_version = _validate_coupon_selection(basket, product)

    # check for require enrollment code
    if product_version.requires_enrollment_code and not coupon_version:
        raise ValidationError({"coupons": "Enrollment Code is required"})

    # User must have signed any data consent agreements necessary for the basket
    data_consent_users = get_or_create_data_consent_users(basket)
    for data_consent_user in data_consent_users:
        if data_consent_user.consent_date is None:
            raise ValidationError(
                {"data_consents": "The data consent agreement has not yet been signed."}
            )

    return ValidatedBasket(
        basket=basket,
        basket_item=basket_item,
        product_version=product_version,
        coupon_version=coupon_version,
        run_selection_ids=selected_course_run_ids,
        data_consent_users=data_consent_users,
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
        email__iexact=user.email, redeemed=False
    ).values_list("product_coupon", flat=True)
    if not unused_product_coupon_ids:
        return []

    now = now_in_utc()
    coupons_data = (
        CouponEligibility.objects.filter(id__in=unused_product_coupon_ids)
        .select_related("coupon", "coupon__payment", "product")
        .annotate(max_created_on=Max("coupon__payment__versions__created_on"))
        .filter(max_created_on=F("coupon__payment__versions__created_on"))
        .filter(
            Q(coupon__payment__versions__expiration_date=None)
            | Q(coupon__payment__versions__expiration_date__gt=now)
        )
        .exclude(product__is_active=False)
        .distinct()
    )

    return sorted(
        [
            {
                "coupon_code": coupon_eligibility.coupon.coupon_code,
                "product_id": coupon_eligibility.product.id,
                "expiration_date": coupon_eligibility.coupon.payment.latest_version.expiration_date,
                "product_title": coupon_eligibility.product.title,
                "product_type": coupon_eligibility.product.type_string,
                "thumbnail_url": coupon_eligibility.product.thumbnail_url,
                "start_date": coupon_eligibility.product.start_date,
            }
            for coupon_eligibility in coupons_data
        ],
        key=lambda coupon: coupon["expiration_date"] or now + timedelta(weeks=9999),
    )


def get_or_create_data_consent_users(basket):
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
                # We will give priority to the course based consent if one exists, otherwise we'll try to fetch global
                # consent
                agreements = (
                    DataConsentAgreement.objects.filter(company=company)
                    .filter(courses__in=courses)
                    .distinct()
                )

                if not agreements:
                    # Ideally, There should always be only one global consent agreement for a company at maximum
                    global_agreement = DataConsentAgreement.objects.filter(
                        company=company, is_global=True
                    )
                    if global_agreement.count() > 1:
                        log.error(
                            "More than one global agreement found for the company: %s",
                            company,
                        )
                    else:
                        agreements = list(global_agreement)

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


def create_coupons(  # noqa: PLR0913
    *,
    name,
    product_ids,
    amount,
    num_coupon_codes,
    coupon_type,
    max_redemptions=1,
    max_redemptions_per_user=1,
    tag=None,
    company_id=None,
    automatic=False,
    is_global=False,
    activation_date=None,
    expiration_date=None,
    payment_type=None,
    discount_type,
    payment_transaction=None,
    coupon_code=None,
    product_program_run_map=None,
    include_future_runs=False,
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
        discount_type (str): The type of discount (percent-off or dollars-off)
        payment_transaction (str): The transaction string
        coupon_code (str):
            If specified, the coupon code to use when creating the coupon. If not a random one will be generated.
        product_ids (list of int): A list of product ids
        product_program_run_map (dict): An optional dictionary that maps a product id to an associated ProgramRun id.
            If provided, the CouponEligibility records for those products will be mapped to the given ProgramRuns.
        include_future_runs (bool): Whether or not coupon will available for future runs


    Returns:
        CouponPaymentVersion:
        A CouponPaymentVersion. Other instances will be created at the same time and linked via foreign keys.

    """
    company = Company.objects.get(id=company_id) if company_id else None
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
        max_redemptions_per_user=max_redemptions_per_user,
        payment_type=payment_type,
        discount_type=discount_type,
        payment_transaction=payment_transaction,
    )

    coupons = [
        Coupon(
            coupon_code=(coupon_code or uuid.uuid4().hex),
            payment=payment,
            include_future_runs=include_future_runs,
            is_global=is_global,
        )
        for _ in range(num_coupon_codes)
    ]

    try:
        with transaction.atomic():
            coupon_objs = Coupon.objects.bulk_create(coupons)
    except IntegrityError:
        log.warning(
            "Falling back to create Coupons for coupon payment {} and company {}".format(  # noqa: G001, UP032
                name, company_id
            )
        )

        new_coupon_codes = [coupon.coupon_code for coupon in coupons]
        existing_coupon_codes = Coupon.objects.filter(
            coupon_code__in=new_coupon_codes
        ).values_list("coupon_code", flat=True)
        if existing_coupon_codes:
            for coupon in coupons:
                if coupon.coupon_code in existing_coupon_codes:
                    coupon.coupon_code = uuid.uuid4().hex
        coupon_objs = Coupon.objects.bulk_create(coupons)

    versions = [
        CouponVersion(coupon=obj, payment_version=payment_version)
        for obj in coupon_objs
    ]
    product_program_run_map = product_program_run_map or {}
    eligibilities = [
        CouponEligibility(
            coupon=obj,
            product_id=product_id,
            program_run_id=product_program_run_map.get(product_id),
        )
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
        raise EcommerceException(f"{order} is expected to have status 'created'")  # noqa: EM102

    if decision != CYBERSOURCE_DECISION_ACCEPT:
        log.warning(
            "Order fulfillment failed: received a decision that wasn't ACCEPT for order %s",
            order,
        )
        return Order.FAILED

    return Order.FULFILLED


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
    req_bill_to_email = request_data.get("req_bill_to_email")
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
        send_ecommerce_order_receipt(
            order=order, cyber_source_provided_email=req_bill_to_email
        )

    # Save to log everything to an audit table including enrollments created in complete_order
    order.save_and_log(None)


def get_product_from_text_id(text_id):
    """
    Fetches a product from a text id that references a Program or CourseRun. If the text id is for a
    Program, and that id has a program run suffix (ex: "+R1"), an associated ProgramRun is also returned.

    Args:
        text_id (str): A text id for a Program/CourseRun

    Returns:
        (Product, Program or CourseRun, ProgramRun): A tuple containing the Product for the CourseRun/Program,
            the Program/CourseRun associated with the text id, and a matching ProgramRun if the text id
            indicated one
    """
    program_run_id_match = re.match(PROGRAM_RUN_ID_PATTERN, text_id)
    # This text id matches the pattern of a program text id with a program run attached
    if program_run_id_match:
        match_dict = program_run_id_match.groupdict()
        potential_prog_run_id = match_dict["run_tag"]
        potential_text_id_base = match_dict["text_id_base"]
        # A Program's own text id may end with something that looks like a ProgramRun suffix, but has
        # no associated ProgramRun (ex: program.readable_id == "program-v1:my+program+R1"). This query looks
        # for a Program with a ProgramRun that matches the suffix, or one that matches the full given text id
        # without a ProgramRun. The version with a matching ProgramRun is preferred.
        program = (
            Program.objects.filter(
                Q(
                    readable_id=potential_text_id_base,
                    programruns__run_tag=potential_prog_run_id,
                )
                | Q(readable_id=text_id)
            )
            .order_by("-programruns__run_tag")
            .prefetch_related(
                Prefetch(
                    "programruns",
                    queryset=ProgramRun.objects.filter(run_tag=potential_prog_run_id),
                    to_attr="matching_program_runs",
                )
            )
            .prefetch_related("products")
            .first()
        )
        if not program:
            raise Program.DoesNotExist(
                f"Could not find Program with readable_id={text_id} "  # noqa: EM102
                "or readable_id={potential_text_id_base} with program run {potential_prog_run_id}"
            )
        program_run = first_or_none(program.matching_program_runs)
        product = first_or_none(program.products.all())
        if not product:
            raise Product.DoesNotExist(f"Product for {program} does not exist")  # noqa: EM102
        return product, program, program_run
    # This is a "normal" text id that should match a CourseRun/Program
    else:
        if is_program_text_id(text_id):
            content_object_model = Program
            content_object_filter = dict(readable_id=text_id)  # noqa: C408
        else:
            content_object_model = CourseRun
            content_object_filter = dict(courseware_id=text_id)  # noqa: C408
        content_object = (
            content_object_model.objects.filter(**content_object_filter)
            .prefetch_related("products")
            .first()
        )
        if not content_object:
            raise content_object_model.DoesNotExist(
                f"{content_object_model._meta.model} matching filter {content_object_filter} does not exist"  # noqa: EM102, SLF001
            )
        product = first_or_none(content_object.products.all())
        if not product:
            raise Product.DoesNotExist(f"Product for {content_object} does not exist")  # noqa: EM102
        return product, content_object, None


def get_product_from_querystring_id(qs_product_id):
    """
    Fetches a product from a querystring product id value, which may be a numerical or text id

    Args:
        qs_product_id (str): A product id from a querystring

    Returns:
        (Product, Program or CourseRun, ProgramRun): A tuple containing the Product that matches the id,
            the Program/CourseRun associated with that product, and a matching ProgramRun if the product id
            indicated one
    """
    if isinstance(qs_product_id, int) or qs_product_id.isdigit():
        product = Product.objects.get(id=int(qs_product_id))
        return product, product.content_object, None
    else:
        # Text IDs for Programs/CourseRuns have '+' characters, which represent spaces in URL-encoded strings
        parsed_product_text_id = qs_product_id.replace(" ", "+")
        return get_product_from_text_id(parsed_product_text_id)
