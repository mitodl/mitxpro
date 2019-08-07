"""Tests for utility functions for ecommerce"""
import pytest

from ecommerce.exceptions import ParseException
from ecommerce.utils import get_order_id_by_reference_number


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
