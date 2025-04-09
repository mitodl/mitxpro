"""Tests for sheets.management.utils"""

import pytest

from unittest.mock import MagicMock

from sheets.management import utils
from sheets.management.utils import CouponAssignmentError


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
    """Test that the get_assignment_sheet_by_title returns the exact match"""
    mock_sheet = MagicMock()
    mock_sheet.title = "fake"
    mock_pygsheets_client = MagicMock(
        open_all=MagicMock(return_value=[mock_sheet])
    )
    sheet = utils.get_assignment_spreadsheet_by_title(mock_pygsheets_client, "fake")
    assert sheet == mock_sheet


def test_get_assignment_sheet_by_title_multiple():
    """Test that get_assignment_sheet_by_title raises an error when multiple exact title matches exist"""
    mock_sheet1 = MagicMock()
    mock_sheet1.title = "fake"
    mock_sheet2 = MagicMock()
    mock_sheet2.title = "fake"
    mock_pygsheets_client = MagicMock(
        open_all=MagicMock(return_value=[mock_sheet1, mock_sheet2])
    )
    with pytest.raises(CouponAssignmentError, match="There should be 1 coupon assignment sheet"):
        utils.get_assignment_spreadsheet_by_title(mock_pygsheets_client, "fake")


def test_get_assignment_sheet_by_title_no_exact_match():
    """Test that get_assignment_sheet_by_title raises an error when no exact title match is found"""
    mock_sheet1 = MagicMock()
    mock_sheet1.title = "fake-not"
    mock_pygsheets_client = MagicMock(
        open_all=MagicMock(return_value=[mock_sheet1])
    )
    with pytest.raises(CouponAssignmentError, match="There should be 1 coupon assignment sheet"):
        utils.get_assignment_spreadsheet_by_title(mock_pygsheets_client, "fake")