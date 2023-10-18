"""Tests for custom mail templatetags"""

from mail.templatetags.format_discount import format_discount


def test_format_discount():
    """format_discount should return a proper string with "-" sign"""

    assert format_discount(0) == "$0.00"
    assert format_discount(1) == "-$1.00"
    assert format_discount(-1) == "-$1.00"
    assert format_discount(1.00) == "-$1.00"
    assert format_discount(100.12) == "-$100.12"
    assert format_discount(-100.12) == "-$100.12"
    assert format_discount(100.577) == "-$100.58"
    assert format_discount(-100.577) == "-$100.58"
