"""Tests for utils.py"""
import json
import re
from datetime import datetime
import difflib

import pytest
import pytz

from voucher.factories import VoucherFactory
from voucher.utils import (
    read_pdf,
    get_current_voucher,
    get_eligible_coupon_choices,
    voucher_upload_path,
    remove_extra_spaces,
)

# pylint: disable=redefined-outer-name

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def mock_logger(mocker):
    """ Mock the log """
    yield mocker.patch("voucher.utils.log")


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
    with open("voucher/.test/domestic_voucher.pdf", "rb") as pdf_file:
        values = read_pdf(pdf_file)
        expected_values = {
            "pdf": pdf_file,
            "employee_id": "1234567",
            "voucher_id": "299152-01",
            "course_start_date_input": datetime.strptime(
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
    with open("voucher/.test/domestic_voucher_test_credits.pdf", "rb") as pdf_file:
        values = read_pdf(pdf_file)
        expected_values = {
            "pdf": pdf_file,
            "employee_id": "1234567",
            "voucher_id": "291510-03",
            "course_start_date_input": datetime.strptime(
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
    with open("voucher/.test/international_voucher.pdf", "rb") as pdf_file:
        values = read_pdf(pdf_file)
        expected_values = {
            "pdf": pdf_file,
            "employee_id": "7654321",
            "voucher_id": None,
            "course_start_date_input": datetime.strptime(
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
    voucher1.uploaded = datetime.now(tz=pytz.UTC)
    voucher1.save()
    assert get_current_voucher(user) == voucher1


def test_no_course_matches(mock_logger, voucher_and_user):
    """
    Test match_courses_to_voucher return an empty queryset on no course matches
    """
    voucher = voucher_and_user.voucher
    assert len(get_eligible_coupon_choices(voucher)) == 0
    mock_logger.error.assert_called_once_with(
        "Found no matching course runs for voucher %s", voucher.id
    )


def test_partial_course_matches_without_coupons(
    mock_logger, voucher_and_partial_matches, settings
):
    """
    Test match_courses_to_voucher logs an error if there are partial matches with no coupons
    """
    context = voucher_and_partial_matches
    voucher = context.voucher
    settings.VOUCHER_COMPANY_ID = context.company.id
    assert len(get_eligible_coupon_choices(voucher)) == 0
    mock_logger.error.assert_called_once_with(
        "Found no valid coupons for matches for voucher %s", voucher.id
    )


def test_exact_course_match_without_coupon(
    mock_logger, voucher_and_exact_match, settings
):
    """
    Test match_courses_to_voucher logs an error if there is an exact match with no coupons
    """
    context = voucher_and_exact_match
    voucher = context.voucher
    settings.VOUCHER_COMPANY_ID = context.company.id
    assert len(get_eligible_coupon_choices(voucher)) == 0
    mock_logger.error.assert_called_once_with(
        "Found no valid coupons for matches for voucher %s", voucher.id
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


def test_partial_course_matches(voucher_and_partial_matches_with_coupons, settings):
    """
    Test match_courses_to_voucher returns correct eligible choices when there are partial matches
    """
    context = voucher_and_partial_matches_with_coupons
    voucher = context.voucher
    settings.VOUCHER_COMPANY_ID = context.company.id
    eligible_coupons = get_eligible_coupon_choices(voucher)
    eligible_coupons_titles = [
        eligible_coupon[1] for eligible_coupon in eligible_coupons
    ]
    coupon_eligibility_list = [
        "{} - starts {}".format(
            coupon_eligibility.product.content_object.title,
            coupon_eligibility.product.content_object.start_date.strftime("%b %d, %Y"),
        )
        for coupon_eligibility in context.coupon_eligibility_list
    ]

    close_matches = difflib.get_close_matches(
        voucher.course_title_input,
        coupon_eligibility_list,
        len(coupon_eligibility_list),
        cutoff=0,
    )

    assert len(eligible_coupons) == len(context.coupon_eligibility_list)
    assert eligible_coupons_titles == close_matches

    _test_eligible_coupon_version(eligible_coupons, context)


@pytest.mark.parametrize("empty_field", ["course_id_input", "course_title_input"])
def test_partial_course_matches_with_missing_inputs(
    voucher_and_partial_matches_with_coupons, settings, empty_field
):
    """
    Test match_courses_to_voucher returns correct eligible choices when there are partial matches
    """
    context = voucher_and_partial_matches_with_coupons
    voucher = context.voucher
    setattr(voucher, empty_field, "")
    settings.VOUCHER_COMPANY_ID = context.company.id
    eligible_coupons = get_eligible_coupon_choices(voucher)
    # reduce number of expected matches by the number of matches that depend on the empty search field
    assert len(eligible_coupons) == len(context.coupon_eligibility_list) - 2
    _test_eligible_coupon_version(eligible_coupons, context)


def test_exact_course_match(voucher_and_exact_match_with_coupon, settings):
    """
    Test match_courses_to_voucher returns correct eligible choices when there is an exact match
    """
    context = voucher_and_exact_match_with_coupon
    voucher = context.voucher
    settings.VOUCHER_COMPANY_ID = context.company.id
    eligible_coupons = get_eligible_coupon_choices(voucher)
    assert len(eligible_coupons) == 1
    eligible_coupon = eligible_coupons[0]
    assert eligible_coupon[1] == "{title} - starts {start_date}".format(
        title=context.exact_match.title,
        start_date=context.exact_match.start_date.strftime("%b %d, %Y"),
    )
    product_id, coupon_id = json.loads(eligible_coupon[0])
    assert product_id == context.product.id
    assert coupon_id == context.coupon_version.coupon.id


def test_voucher_upload_path(voucher_and_exact_match_with_coupon):
    """voucher_upload_path returns a unique filename based on original name"""
    voucher = voucher_and_exact_match_with_coupon.voucher
    assert (
        re.match(
            r"vouchers\/\w{8}\-\w{4}\-\w{4}\-\w{4}-\w{12}_%s" % voucher.pdf.name,
            voucher_upload_path(voucher, voucher.pdf.name),
        )
        is not None
    )
