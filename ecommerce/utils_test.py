"""Tests for utility functions for ecommerce"""
import pytest

from ecommerce.constants import DISCOUNT_TYPE_PERCENT_OFF, DISCOUNT_TYPE_DOLLARS_OFF
from ecommerce.exceptions import ParseException
from ecommerce.utils import get_order_id_by_reference_number, validate_amount


@pytest.mark.parametrize(
    "reference_number, error",
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
    "discount_type, amount, error",
    [
        (
            DISCOUNT_TYPE_PERCENT_OFF,
            2,
            "The amount should be between (0 - 1) when discount type is percent-off.",
        ),
        (
            DISCOUNT_TYPE_DOLLARS_OFF,
            0,
            "The amount is invalid, please specify a value greater then 0.",
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
