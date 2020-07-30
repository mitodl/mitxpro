"""Tests for sheets.management.utils"""
from unittest.mock import MagicMock

import pytest
from django.core.management import CommandError
from sheets.management import utils


@pytest.fixture(name="valid_enum_rows")
def fixture_valid_enum_rows():
    """Mock rows response for tests"""
    return [
        (
            1,
            [
                "fake-purchase-order",
                "fake-coupon-name",
                "10",
                "fake-text-id",
                "fake-company",
            ],
        ),
        (
            2,
            [
                "fake-purchase-order-2",
                "fake-coupon-name-2",
                "20",
                "fake-text-id-2",
                "fake-company-2",
            ],
        ),
    ]


def test_get_assignment_sheet_by_title():
    """Test that the get_assignment_sheet_by_title works as expected"""
    mock_pygsheets_client = MagicMock(
        open_all=MagicMock(return_value=["mock-sheet-obj"])
    )
    sheet = utils.get_assignment_spreadsheet_by_title(mock_pygsheets_client, "fake")
    assert sheet == "mock-sheet-obj"


def test_get_assignment_sheet_by_title_multiple():
    """Test that the get_assignment_sheet_by_title raises an error when multiple sheets are returned"""
    mock_pygsheets_client = MagicMock(
        open_all=MagicMock(return_value=["mock-sheet-obj", "mock-second-sheet-obj"])
    )
    with pytest.raises(CommandError):
        utils.get_assignment_spreadsheet_by_title(mock_pygsheets_client, "fake")
