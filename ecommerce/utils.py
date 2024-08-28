"""Utility functions for ecommerce"""

import datetime
import logging
from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse

from courses.constants import ENROLLABLE_ITEM_ID_SEPARATOR
from ecommerce.constants import DISCOUNT_TYPE_PERCENT_OFF
from ecommerce.exceptions import ParseException

log = logging.getLogger(__name__)
EMAIL_TIME_FORMAT = "%I:%M %p %Z"


def create_delete_rule(table_name):
    """Helper function to make SQL to create a rule to prevent deleting from the ecommerce table"""
    return f"CREATE RULE delete_protect AS ON DELETE TO ecommerce_{table_name} DO INSTEAD NOTHING"


def create_update_rule(table_name):
    """Helper function to make SQL to create a rule to prevent updating a row in the ecommerce table"""
    return f"CREATE RULE update_protect AS ON UPDATE TO ecommerce_{table_name} DO INSTEAD NOTHING"


def rollback_delete_rule(table_name):
    """Helper function to make SQL to create a rule to allow deleting from the ecommerce table"""
    return f"DROP RULE delete_protect ON ecommerce_{table_name}"


def rollback_update_rule(table_name):
    """Helper function to make SQL to create a rule to allow updating from the ecommerce table"""
    return f"DROP RULE update_protect ON ecommerce_{table_name}"


def get_order_id_by_reference_number(*, reference_number, prefix):
    """
    Parse a reference number received from CyberSource and return the order id.

    Args:
        reference_number (str):
            A string which contains the order id and the instance which generated it
        prefix (str):
            The prefix string which is attached to the reference number to distinguish from other
            reference numbers in other environments.

    Returns:
        int: An order id
    """
    prefix_with_dash = f"{prefix}-"
    if not reference_number.startswith(prefix_with_dash):
        log.error(
            "CyberSource prefix doesn't match: should start with %s but is %s",
            prefix_with_dash,
            reference_number,
        )
        raise ParseException(f"Reference number must start with {prefix_with_dash}")  # noqa: EM102
    try:
        order_id = int(reference_number[len(prefix_with_dash) :])
    except ValueError:
        raise ParseException("Unable to parse order number")  # noqa: B904, EM101

    return order_id


def make_checkout_url(
    *, product_id=None, code=None, run_tag=None, is_voucher_applied=False
):
    """
    Helper function to create a checkout URL with appropriate query parameters.

    Args:
        product_id (int|str): A Product ID or text ID
        code (str): The coupon code
        run_tag (str): A ProgramRun run tag
        is_voucher_applied (bool): Boolean to indicate if voucher is used for checkout

    Returns:
        str: The URL for the checkout page, including product and coupon code if available
    """
    base_checkout_url = urljoin(settings.SITE_BASE_URL, reverse("checkout-page"))
    if product_id is None and code is None:
        return base_checkout_url

    query_params = {"is_voucher_applied": is_voucher_applied}
    if product_id is not None:
        query_params["product"] = (
            product_id
            if run_tag is None
            else f"{product_id}{ENROLLABLE_ITEM_ID_SEPARATOR}{run_tag}"
        )
    if code is not None:
        query_params["code"] = code
    return f"{base_checkout_url}?{urlencode(query_params)}"


def validate_amount(discount_type, amount):
    """
    Validate the amount/discount value

        Case 1: If discount type is percent-off the amount can be between 0-1
        Case 2: If discount type is dollars-off the amount can be any value above 0
    """

    if amount <= 0:
        return "The amount is invalid, please specify a value greater than 0."

    if discount_type == DISCOUNT_TYPE_PERCENT_OFF and amount > 1:  # noqa: RET503
        return "The amount should be between (0 - 1) when discount type is percent-off."


def positive_or_zero(number):
    """Return 0 if a number is negative otherwise return number"""
    return 0 if number < 0 else number


class CouponUtils:
    """
    Common Utils for Coupon and B2BCoupon
    """

    @staticmethod
    def validate_unique_coupon_code(value, instance=None):
        """
        Validate the uniqueness of coupon codes in Coupon and B2BCoupon models.
        """
        if instance and instance.pk:
            existing_instance = instance.__class__.objects.get(pk=instance.pk)
            if (
                existing_instance.coupon_code != value
                and CouponUtils.is_existing_coupon_code(value)
            ):
                raise ValidationError(
                    {"coupon_code": "Coupon code already exists in the platform."}
                )
        elif CouponUtils.is_existing_coupon_code(value):
            if instance:
                raise ValidationError(
                    {"coupon_code": "Coupon code already exists in the platform."}
                )
            else:
                raise ValidationError("Coupon code already exists in the platform.")  # noqa: EM101

    @staticmethod
    def is_existing_coupon_code(value):
        """
        Check if the coupon code exists in either Coupon or B2BCoupon models.
        """
        from b2b_ecommerce.models import B2BCoupon
        from ecommerce.models import Coupon

        return (
            Coupon.objects.filter(coupon_code=value).exists()
            or B2BCoupon.objects.filter(coupon_code=value).exists()
        )


def format_run_date(run_date):
    """
    Format run date to return both date and time strings.

    Args:
        run_date (datetime): The datetime to format.

    Returns:
        tuple: A tuple containing the formatted date and time strings.
    """
    if run_date:
        from ecommerce.mail_api import EMAIL_DATE_FORMAT

        formatted_date_time = run_date.astimezone(datetime.UTC).strftime(
            f"{EMAIL_DATE_FORMAT}-{EMAIL_TIME_FORMAT}"
        )
        return tuple(formatted_date_time.split("-", 1))
    return "", ""
