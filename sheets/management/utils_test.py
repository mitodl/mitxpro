"""Tests for sheets.management.utils"""

from unittest.mock import MagicMock, patch

import pytest
from django.core.management import CommandError
from datetime import timedelta

from sheets.management import utils
from mitxpro.utils import now_in_utc

from sheets.management.utils import assign_coupons_from_spreadsheet, CouponAssignmentError
from ecommerce.factories import BulkCouponAssignmentFactory


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
    with pytest.raises(CouponAssignmentError):
        utils.get_assignment_spreadsheet_by_title(mock_pygsheets_client, "fake")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "use_sheet_id, value, force, sheet_modified_offset, existing_modified_offset, expect_error, force_processing",
    [
        (True, "sheet-id-123", False, timedelta(days=-1), timedelta(days=-2), False, True),  # Valid, modified after last
        (False, "fake-title", False, timedelta(days=-2), timedelta(days=-1), True, False),  # No modification
        (True, "sheet-id-123", True, timedelta(days=-2), timedelta(days=-1), False, True),  # Forced processing
        (False, "", False, None, None, True, False),  # Missing value should raise an error
    ],
)
@patch("sheets.management.utils.get_authorized_pygsheets_client")
@patch("sheets.management.utils.get_assignment_spreadsheet_by_title")
@patch("sheets.management.utils.google_date_string_to_datetime")
@patch("sheets.management.utils.CouponAssignmentHandler")
def test_assign_coupons_from_spreadsheet(
    mock_coupon_assignment_handler,
    mock_google_date_string_to_datetime,
    mock_get_assignment_sheet_by_title,
    mock_get_authorized_pygsheets_client,
    use_sheet_id,
    value,
    force,
    sheet_modified_offset,
    existing_modified_offset,
    expect_error,
    force_processing,
):
    """Test assign_coupons_from_spreadsheet with different conditions."""

    # Mock authorized pygsheets client
    mock_pygsheets_client = MagicMock()
    mock_get_authorized_pygsheets_client.return_value = mock_pygsheets_client

    # Mock spreadsheet
    mock_spreadsheet = MagicMock()

    # Title and ID should be assigned to assert the returning value of assign_coupons_from_spreadsheet
    mock_spreadsheet.title = "fake-title" 
    mock_spreadsheet.id = "sheet-id-123"

    if use_sheet_id:
        mock_pygsheets_client.open_by_key.return_value = mock_spreadsheet
    else:
        mock_get_assignment_sheet_by_title.return_value = mock_spreadsheet

    # Mock modification time
    sheet_last_modified = now_in_utc() + sheet_modified_offset if sheet_modified_offset else None
    mock_google_date_string_to_datetime.return_value = sheet_last_modified

    bulk_assignment = BulkCouponAssignmentFactory.create(
        assignment_sheet_id="sheet-id-123",
        sheet_last_modified_date = now_in_utc() + existing_modified_offset if existing_modified_offset else None
    )

    if expect_error:
        with pytest.raises(CouponAssignmentError):
            assign_coupons_from_spreadsheet(use_sheet_id, value, force)
    else:
        mock_process_assignment = mock_coupon_assignment_handler.return_value.process_assignment_spreadsheet
        mock_process_assignment.return_value = (bulk_assignment, 5, 2)

        result = assign_coupons_from_spreadsheet(use_sheet_id, value, force)
        if force_processing:
            assert result == ("'fake-title', id: sheet-id-123", 5, 2, bulk_assignment.id)
            mock_process_assignment.assert_called_once()
        else:
            mock_process_assignment.assert_not_called()
