"""Tests for utils.py"""
import json
from datetime import datetime
from unittest.mock import patch

import pytest
import pytz

from voucher.factories import VoucherFactory
from voucher.utils import read_pdf, get_current_voucher, get_eligible_coupon_choices

pytestmark = [pytest.mark.django_db]


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
            "course_title_input": "Model-Based  Systems Engineering: Documentation and Analysis",
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


@patch("voucher.utils.log")
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


# Test match_courses_to_voucher
def test_no_course_matches(voucher_and_user):
    """
    Test match_courses_to_voucher return an empty queryset on no course matches
    """
    voucher = voucher_and_user.voucher
    assert len(get_eligible_coupon_choices(voucher)) == 0


@patch("voucher.utils.log")
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


@patch("voucher.utils.log")
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


def test_partial_course_matches(voucher_and_partial_matches_with_coupons, settings):
    """
    Test match_courses_to_voucher returns correct eligible choices when there are partial matches
    """
    context = voucher_and_partial_matches_with_coupons
    voucher = context.voucher
    settings.VOUCHER_COMPANY_ID = context.company.id
    eligible_coupons = get_eligible_coupon_choices(voucher)
    assert len(eligible_coupons) == len(context.coupon_eligibility_list)
    product_ids = [product.id for product in context.products]
    coupon_ids = [
        coupon_version.coupon.id for coupon_version in context.coupon_versions
    ]
    titles = [match.title for match in context.partial_matches]
    for eligible_coupon in eligible_coupons:
        product_id, coupon_id = json.loads(eligible_coupon[0])
        assert product_id in product_ids
        assert coupon_id in coupon_ids
        assert eligible_coupon[1] in titles


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
    assert eligible_coupon[1] == context.exact_match.title
    product_id, coupon_id = json.loads(eligible_coupon[0])
    assert product_id == context.product.id
    assert coupon_id == context.coupon_version.coupon.id
