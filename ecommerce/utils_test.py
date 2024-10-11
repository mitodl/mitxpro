"""Tests for utility functions for ecommerce"""

from urllib.parse import urljoin

import pytest
from django.contrib.admin.models import CHANGE, LogEntry
from django.urls import reverse

from ecommerce.constants import DISCOUNT_TYPE_DOLLARS_OFF, DISCOUNT_TYPE_PERCENT_OFF
from ecommerce.exceptions import ParseException
from ecommerce.factories import CouponFactory
from ecommerce.models import Coupon
from ecommerce.utils import (
    deactivate_coupons,
    get_order_id_by_reference_number,
    make_checkout_url,
    validate_amount,
)


@pytest.mark.parametrize(
    "reference_number, error",  # noqa: PT006
    [
        ("XYZ-1-3", "Reference number must start with MITXPRO-cyb-prefix-"),
        ("MITXPRO-cyb-prefix-NaN", "Unable to parse order number"),
    ],
)
def test_get_order_id_by_reference_number_parse_error(reference_number, error):
    """
    Test parse errors are handled well
    """
    with pytest.raises(ParseException) as ex:
        get_order_id_by_reference_number(
            reference_number=reference_number, prefix="MITXPRO-cyb-prefix"
        )
    assert ex.value.args[0] == error


@pytest.mark.parametrize(
    "discount_type, amount, error",  # noqa: PT006
    [
        (
            DISCOUNT_TYPE_PERCENT_OFF,
            2,
            "The amount should be between (0 - 1) when discount type is percent-off.",
        ),
        (
            DISCOUNT_TYPE_DOLLARS_OFF,
            0,
            "The amount is invalid, please specify a value greater than 0.",
        ),
        (DISCOUNT_TYPE_PERCENT_OFF, 1, None),
        (DISCOUNT_TYPE_DOLLARS_OFF, 1, None),
    ],
)
def test_validate_amount_with_discount_type(discount_type, amount, error):
    """
    Test validate_amount returns proper validation message
    """
    assert error == validate_amount(discount_type, amount)


@pytest.mark.parametrize(
    (
        "product_id",
        "coupon_code",
        "run_tag",
        "is_voucher_applied",
        "expected_query_params",
    ),
    [
        (
            1,
            "test_coupon_code",
            "R1",
            True,
            "?is_voucher_applied=True&product=1%2BR1&code=test_coupon_code",
        ),
        (
            None,
            "test_coupon_code",
            "R1",
            True,
            "?is_voucher_applied=True&code=test_coupon_code",
        ),
        (
            1,
            None,
            "R1",
            True,
            "?is_voucher_applied=True&product=1%2BR1",
        ),
        (
            None,
            None,
            "R1",
            True,
            "",
        ),
        (
            1,
            "test_coupon_code",
            None,
            True,
            "?is_voucher_applied=True&product=1&code=test_coupon_code",
        ),
        (
            None,
            "test_coupon_code",
            None,
            True,
            "?is_voucher_applied=True&code=test_coupon_code",
        ),
        (
            1,
            None,
            None,
            True,
            "?is_voucher_applied=True&product=1",
        ),
        (
            None,
            None,
            None,
            True,
            "",
        ),
        (
            1,
            "test_coupon_code",
            "R1",
            False,
            "?is_voucher_applied=False&product=1%2BR1&code=test_coupon_code",
        ),
        (
            None,
            "test_coupon_code",
            "R1",
            False,
            "?is_voucher_applied=False&code=test_coupon_code",
        ),
        (
            1,
            None,
            "R1",
            False,
            "?is_voucher_applied=False&product=1%2BR1",
        ),
        (
            None,
            None,
            "R1",
            False,
            "",
        ),
        (
            1,
            "test_coupon_code",
            None,
            False,
            "?is_voucher_applied=False&product=1&code=test_coupon_code",
        ),
        (
            None,
            "test_coupon_code",
            None,
            False,
            "?is_voucher_applied=False&code=test_coupon_code",
        ),
        (
            1,
            None,
            None,
            False,
            "?is_voucher_applied=False&product=1",
        ),
        (
            None,
            None,
            None,
            False,
            "",
        ),
    ],
)
def test_make_checkout_url(  # noqa: PLR0913
    settings,
    product_id,
    coupon_code,
    run_tag,
    is_voucher_applied,
    expected_query_params,
):
    """Test `make_checkout_url` returns the expected checkout URL"""

    assert (
        make_checkout_url(
            product_id=product_id,
            code=coupon_code,
            run_tag=run_tag,
            is_voucher_applied=is_voucher_applied,
        )
        == f"{urljoin(settings.SITE_BASE_URL, reverse('checkout-page'))}{expected_query_params}"
    )


@pytest.mark.django_db
def test_deactivate_coupon(user):
    """Test coupon deactivation and log entry creation based on user presence."""
    coupons_list = CouponFactory.create_batch(10)
    coupons = Coupon.objects.filter(id__in=[coupon.id for coupon in coupons_list])

    assert coupons.filter(enabled=True).count() == len(coupons)

    deactivate_coupons(coupons)
    assert coupons.filter(enabled=False).count() == len(coupons)
    assert LogEntry.objects.count() == 0

    coupons.update(enabled=True)

    deactivate_coupons(coupons, user_id=user.id)
    assert coupons.filter(enabled=False).count() == len(coupons)
    assert LogEntry.objects.filter(user_id=user.id).count() == len(coupons)

    log_entry = LogEntry.objects.filter(user_id=user.id).first()
    assert log_entry.action_flag == CHANGE
    assert log_entry.change_message == "Deactivated coupon"
