"""Sheets app util function tests"""

from pygsheets.worksheet import Worksheet

from sheets import utils
from sheets.constants import (
    GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
    GOOGLE_AUTH_URI,
    GOOGLE_TOKEN_URI,
)
from unittest.mock import MagicMock, patch

import pytest
from datetime import timedelta

from mitxpro.utils import now_in_utc
from ecommerce.factories import BulkCouponAssignmentFactory
from sheets.exceptions import CouponAssignmentError


def test_generate_google_client_config(settings):
    """generate_google_client_config should return a dict with expected values"""
    settings.DRIVE_CLIENT_ID = "some-id"
    settings.DRIVE_CLIENT_SECRET = "some-secret"  # noqa: S105
    settings.DRIVE_API_PROJECT_ID = "some-project-id"
    settings.SITE_BASE_URL = "http://example.com"
    assert utils.generate_google_client_config() == {
        "web": {
            "client_id": "some-id",
            "client_secret": "some-secret",
            "project_id": "some-project-id",
            "redirect_uris": ["http://example.com/api/sheets/auth-complete/"],
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_TOKEN_URI,
            "auth_provider_x509_cert_url": GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
        }
    }


def test_get_data_rows(mocker):
    """get_data_rows should return each row of a worksheet data after the first row (i.e.: the header row)"""
    non_header_rows = [
        ["row 1 - column 1", "row 1 - column 2"],
        ["row 2 - column 1", "row 2 - column 2"],
    ]
    sheet_rows = [["HEADER 1", "HEADER 2"]] + non_header_rows  # noqa: RUF005
    mocked_worksheet = mocker.MagicMock(
        spec=Worksheet, get_all_values=mocker.Mock(return_value=sheet_rows)
    )
    data_rows = list(utils.get_data_rows(mocked_worksheet))
    assert data_rows == non_header_rows


@pytest.mark.django_db
@pytest.mark.parametrize(
    "use_sheet_id, value, force, sheet_modified_offset, existing_modified_offset, expect_error, force_processing",
    [
        (
            True,
            "sheet-id-123",
            False,
            timedelta(days=-1),
            timedelta(days=-2),
            False,
            True,
        ),  # Valid, modified after last
        (
            False,
            "fake-title",
            False,
            timedelta(days=-2),
            timedelta(days=-1),
            True,
            False,
        ),  # No modification
        (
            True,
            "sheet-id-123",
            True,
            timedelta(days=-2),
            timedelta(days=-1),
            False,
            True,
        ),  # Forced processing
        (
            False,
            "",
            False,
            None,
            None,
            True,
            False,
        ),  # Missing value should raise an error
    ],
)
@patch("sheets.api.get_authorized_pygsheets_client")
@patch("sheets.management.utils.get_assignment_spreadsheet_by_title")
@patch("sheets.utils.google_date_string_to_datetime")
@patch("sheets.coupon_assign_api.CouponAssignmentHandler")
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

    mock_pygsheets_client = MagicMock()
    mock_get_authorized_pygsheets_client.return_value = mock_pygsheets_client

    mock_spreadsheet = MagicMock()

    # Title and ID should be assigned to assert the returning value of assign_coupons_from_spreadsheet
    mock_spreadsheet.title = "fake-title"
    mock_spreadsheet.id = "sheet-id-123"

    if use_sheet_id:
        mock_pygsheets_client.open_by_key.return_value = mock_spreadsheet
    else:
        mock_get_assignment_sheet_by_title.return_value = mock_spreadsheet

    sheet_last_modified = (
        now_in_utc() + sheet_modified_offset if sheet_modified_offset else None
    )
    mock_google_date_string_to_datetime.return_value = sheet_last_modified

    bulk_assignment = BulkCouponAssignmentFactory.create(
        assignment_sheet_id="sheet-id-123",
        sheet_last_modified_date=now_in_utc() + existing_modified_offset
        if existing_modified_offset
        else None,
    )

    if expect_error:
        with pytest.raises(CouponAssignmentError):
            utils.assign_coupons_from_spreadsheet(use_sheet_id, value, force)
    else:
        mock_process_assignment = (
            mock_coupon_assignment_handler.return_value.process_assignment_spreadsheet
        )
        mock_process_assignment.return_value = (bulk_assignment, 5, 2)

        result = utils.assign_coupons_from_spreadsheet(use_sheet_id, value, force)
        if force_processing:
            assert result == (
                "'fake-title', id: sheet-id-123",
                5,
                2,
                bulk_assignment.id,
            )
            mock_process_assignment.assert_called_once()
        else:
            mock_process_assignment.assert_not_called()
