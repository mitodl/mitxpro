"""Tests for utils.py"""
from unittest.mock import patch

import pytest

from voucher.utils import read_pdf

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
            "BEMSID": "1234567",
            "voucher_id": "299152-01",
            "course_start_date": "04/30/2018",
            "class_module_number": "AMxB",
            "class_module_title": "Additive Manufacturing for Innovative Design and Production",
            "employee_name": "Stark, Anthony E",
        }
        assert values == expected_values


def test_pdf_parsing_domestic_offset_credits(settings):
    """Test that pdf parsing handles when the credits value is part of the course name column"""
    setup_pdf_parsing(settings)
    with open("voucher/.test/domestic_voucher_test_credits.pdf", "rb") as pdf_file:
        values = read_pdf(pdf_file)
        expected_values = {
            "BEMSID": "1234567",
            "voucher_id": "291510-03",
            "course_start_date": "04/09/2018",
            "class_module_number": "SysEngxB3",
            "class_module_title": "Model-Based  Systems Engineering: Documentation and Analysis",
            "employee_name": "Stark, Anthony E",
        }
        assert values == expected_values


def test_pdf_parsing_international(settings):
    """Test that pdf parsing correctly parses international voucher pdfs"""
    setup_pdf_parsing(settings)
    with open("voucher/.test/international_voucher.pdf", "rb") as pdf_file:
        values = read_pdf(pdf_file)
        expected_values = {
            "BEMSID": "7654321",
            "voucher_id": None,
            "course_start_date": "9-Apr-2018",
            "class_module_number": "SysEngBx3",
            "class_module_title": "Model-Based Systems Engineering",
            "employee_name": 'STEVENS, ERIK "KILLMONGER"',
        }
        assert values == expected_values


@patch("voucher.utils.log")
def test_parse_not_pdf(mock_logger, settings):
    """Test that pdf parsing correctly throws an error when handed something that isn't a PDF"""
    setup_pdf_parsing(settings)
    read_pdf("abc")
    mock_logger.error.assert_called_with("Could not parse PDF")
