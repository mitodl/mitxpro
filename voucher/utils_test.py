"""Tests for utils.py"""

import json
import re
from datetime import UTC, datetime

import pytest

from voucher.factories import VoucherFactory
from voucher.utils import (
    get_current_voucher,
    get_eligible_product_detail,
    read_pdf,
    remove_extra_spaces,
    voucher_upload_path,
)

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def mock_logger(mocker):
    """Mock the log"""
    return mocker.patch("voucher.utils.log")


def setup_pdf_parsing(settings):
    """Set the unique settings values for pdf parsing"""
    settings.VOUCHER_DOMESTIC_DATE_KEY = "UNIQUE01"
    settings.VOUCHER_DOMESTIC_EMPLOYEE_KEY = "UNIQUE02"
    settings.VOUCHER_DOMESTIC_EMPLOYEE_ID_KEY = "UNIQUE03"
    settings.VOUCHER_DOMESTIC_KEY = "UNIQUE04"
    settings.VOUCHER_DOMESTIC_COURSE_KEY = "UNIQUE05"
    settings.VOUCHER_DOMESTIC_CREDITS_KEY = "UNIQUE06"
    settings.VOUCHER_DOMESTIC_DATES_KEY = "UNIQUE07"
    settings.VOUCHER_DOMESTIC_AMOUNT_KEY = "UNIQUE08"
    settings.VOUCHER_INTERNATIONAL_EMPLOYEE_KEY = "UNIQUE09"
    settings.VOUCHER_INTERNATIONAL_PROGRAM_KEY = "UNIQUE10"
    settings.VOUCHER_INTERNATIONAL_COURSE_KEY = "UNIQUE11"
    settings.VOUCHER_INTERNATIONAL_SCHOOL_KEY = "UNIQUE12"
    settings.VOUCHER_INTERNATIONAL_EMPLOYEE_ID_KEY = "UNIQUE13"
    settings.VOUCHER_INTERNATIONAL_AMOUNT_KEY = "UNIQUE14"
    settings.VOUCHER_INTERNATIONAL_DATES_KEY = "UNIQUE15"
    settings.VOUCHER_INTERNATIONAL_COURSE_NAME_KEY = "UNIQUE16"
    settings.VOUCHER_INTERNATIONAL_COURSE_NUMBER_KEY = "UNIQUE17"


def test_remove_extra_spaces():
    """Test that remove_extra_spaces properly strips excess spaces"""
    result = "Hello World"
    string_1 = "Hello    \n\r\t     World"
    string_2 = "\n\r\t    Hello World  \n\r\t "
    string_3 = "  \n  \r   \t    Hello     \n  \r   \t   World    \n  \r   \t  "
    assert remove_extra_spaces(result) == result
    assert remove_extra_spaces(string_1) == result
    assert remove_extra_spaces(string_2) == result
    assert remove_extra_spaces(string_3) == result


def test_pdf_parsing_domestic(settings):
    """Test that pdf parsing correctly parses domestic voucher pdfs"""
    setup_pdf_parsing(settings)
    with open("voucher/.test/domestic_voucher.pdf", "rb") as pdf_file:  # noqa: PTH123
        values = read_pdf(pdf_file)
        expected_values = {
            "pdf": pdf_file,
            "employee_id": "1234567",
            "voucher_id": "299152-01",
            "course_start_date_input": datetime.strptime(  # noqa: DTZ007
                "04/30/2018", "%m/%d/%Y"
            ).date(),
            "course_id_input": "AMxB",
            "course_title_input": "Additive Manufacturing for Innovative Design and Production",
            "employee_name": "Stark, Anthony E",
        }
        assert values == expected_values


def test_pdf_parsing_domestic_offset_credits(settings):
    """Test that pdf parsing handles when the credits value is part of the course name column"""
    setup_pdf_parsing(settings)
    with open("voucher/.test/domestic_voucher_test_credits.pdf", "rb") as pdf_file:  # noqa: PTH123
        values = read_pdf(pdf_file)
        expected_values = {
            "pdf": pdf_file,
            "employee_id": "1234567",
            "voucher_id": "291510-03",
            "course_start_date_input": datetime.strptime(  # noqa: DTZ007
                "04/09/2018", "%m/%d/%Y"
            ).date(),
            "course_id_input": "SysEngxB3",
            "course_title_input": "Model-Based Systems Engineering: Documentation and Analysis",
            "employee_name": "Stark, Anthony E",
        }
        assert values == expected_values


def test_pdf_parsing_international(settings):
    """Test that pdf parsing correctly parses international voucher pdfs"""
    setup_pdf_parsing(settings)
    with open("voucher/.test/international_voucher.pdf", "rb") as pdf_file:  # noqa: PTH123
        values = read_pdf(pdf_file)
        expected_values = {
            "pdf": pdf_file,
            "employee_id": "7654321",
            "voucher_id": None,
            "course_start_date_input": datetime.strptime(  # noqa: DTZ007
                "9-Apr-2018", "%d-%b-%Y"
            ).date(),
            "course_id_input": "SysEngBx3",
            "course_title_input": "Model-Based Systems Engineering",
            "employee_name": 'STEVENS, ERIK "KILLMONGER"',
        }
        assert values == expected_values


def test_parse_not_pdf(mock_logger, settings):
    """Test that pdf parsing correctly throws an error when handed something that isn't a PDF"""
    setup_pdf_parsing(settings)
    read_pdf("abc")
    mock_logger.exception.assert_called_with("Could not parse PDF")


def test_get_current_voucher(user):
    """
    Test that get_current_voucher returns the most recently updated voucher for a user
    """
    assert get_current_voucher(user) is None
    voucher1 = VoucherFactory(user=user)
    assert get_current_voucher(user) == voucher1
    voucher2 = VoucherFactory(user=user)
    assert get_current_voucher(user) == voucher2
    voucher1.uploaded = datetime.now(tz=UTC)
    voucher1.save()
    assert get_current_voucher(user) == voucher1


def test_no_course_matches(mock_logger, voucher_and_user):
    """
    Test get_eligible_product_detail does not return any product_id, coupon_id, or course_run_display_title
    when no course matches
    """
    voucher = voucher_and_user.voucher
    product_id, coupon_id, course_run_display_title = get_eligible_product_detail(
        voucher
    )
    assert product_id is None
    assert coupon_id is None
    assert course_run_display_title is None
    mock_logger.error.assert_called_once_with(
        "Found no matching course runs for voucher %s", voucher.id
    )


def test_exact_course_match_without_coupon(
    mock_logger, voucher_and_exact_match, settings
):
    """
    Test get_eligible_product_detail logs an error if there is an exact match with no coupons
    """
    context = voucher_and_exact_match
    voucher = context.voucher
    settings.VOUCHER_COMPANY_ID = context.company.id

    product_id, coupon_id, course_run_display_title = get_eligible_product_detail(
        voucher
    )
    assert product_id is None
    assert coupon_id is None
    assert course_run_display_title is None
    mock_logger.error.assert_called_once_with(
        "Found no valid coupons for course run matching the voucher %s", voucher.id
    )


def _test_eligible_coupon_version(eligible_coupons, context):
    """
    Test that every eligible coupon exists in the context
    """
    product_ids = [product.id for product in context.products]
    coupon_ids = [
        coupon_version.coupon.id for coupon_version in context.coupon_versions
    ]
    titles = [
        "{title} - starts {start_date}".format(
            title=match.title, start_date=match.start_date.strftime("%b %d, %Y")
        )
        for match in context.partial_matches
    ]
    for eligible_coupon in eligible_coupons:
        product_id, coupon_id = json.loads(eligible_coupon[0])
        assert product_id in product_ids
        assert coupon_id in coupon_ids
        assert eligible_coupon[1] in titles


def test_exact_course_match(voucher_and_exact_match_with_coupon, settings):
    """
    Test get_eligible_product_detail returns correct product_id, coupon_id, and course_run_display_title
    when there is an exact match
    """
    context = voucher_and_exact_match_with_coupon
    voucher = context.voucher
    settings.VOUCHER_COMPANY_ID = context.company.id
    product_id, coupon_id, course_run_display_title = get_eligible_product_detail(
        voucher
    )
    assert product_id is not None
    assert coupon_id is not None
    assert course_run_display_title is not None
    assert course_run_display_title == "{title} - starts {start_date}".format(
        title=context.exact_match.title,
        start_date=context.exact_match.start_date.strftime("%b %d, %Y"),
    )
    assert product_id == context.product.id
    assert coupon_id == context.coupon_version.coupon.id


def test_voucher_upload_path(voucher_and_exact_match_with_coupon):
    """voucher_upload_path returns a unique filename based on original name"""
    voucher = voucher_and_exact_match_with_coupon.voucher
    assert (
        re.match(
            r"vouchers\/\w{8}\-\w{4}\-\w{4}\-\w{4}-\w{12}_%s" % voucher.pdf.name,  # noqa: UP031
            voucher_upload_path(voucher, voucher.pdf.name),
        )
        is not None
    )
