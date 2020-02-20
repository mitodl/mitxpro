"""Tests for sheets.management.utils"""
from unittest.mock import MagicMock

import copy
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


@pytest.fixture(name="patched_get_enum_rows", autouse=True)
def fixture_patched_get_enum_rows(mocker, valid_enum_rows):
    """patched get_enumrated_data_rows method"""
    return mocker.patch(
        "sheets.management.utils.get_enumerated_data_rows", return_value=valid_enum_rows
    )


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


def test_get_matching_request_row():
    """Test that the get_matching_request_row method works as expected"""
    row_idx, row_obj = utils.get_matching_request_row(
        MagicMock(), coupon_name="fake-coupon-name-2"
    )
    assert row_idx == 2
    assert row_obj.coupon_name == "fake-coupon-name-2"
    assert row_obj.company_name == "fake-company-2"
    assert row_obj.activation is None
    assert row_obj.expiration is None
    assert row_obj.date_processed is None
    assert row_obj.num_codes == 20
    assert row_obj.purchase_order_id == "fake-purchase-order-2"
    assert row_obj.product_text_id == "fake-text-id-2"


def test_get_matching_request_row_with_row_id():
    """Test that the get_matching_request_row method works as expected when given a row id"""
    row_idx, row_obj = utils.get_matching_request_row(MagicMock(), row=2)
    assert row_idx == 2
    assert row_obj.coupon_name == "fake-coupon-name-2"
    assert row_obj.company_name == "fake-company-2"
    assert row_obj.activation is None
    assert row_obj.expiration is None
    assert row_obj.date_processed is None
    assert row_obj.num_codes == 20
    assert row_obj.purchase_order_id == "fake-purchase-order-2"
    assert row_obj.product_text_id == "fake-text-id-2"


def test_get_matching_request_row_duplicates(patched_get_enum_rows, valid_enum_rows):
    """Test that the get_matching_request_row raises exception on duplicate matched rows"""
    bad_data = copy.copy(valid_enum_rows)
    bad_data[0] = (bad_data[1][0], bad_data[0][1])
    patched_get_enum_rows.return_value = bad_data
    with pytest.raises(CommandError):
        utils.get_matching_request_row(MagicMock(), row=1)


def test_get_matching_request_row_duplicate_coupon_name(
    patched_get_enum_rows, valid_enum_rows
):
    """Test that the get_matching_request_row raises exception on duplicate matched rows"""
    bad_data = copy.copy(valid_enum_rows)
    bad_data[1] = (bad_data[1][0], bad_data[0][1])
    patched_get_enum_rows.return_value = bad_data
    with pytest.raises(CommandError):
        utils.get_matching_request_row(MagicMock(), coupon_name="fake-coupon-name")


def test_get_matching_request_row_invalid_data(patched_get_enum_rows, valid_enum_rows):
    """Test that the get_matching_request_row method ignores invalid data"""
    bad_data = copy.copy(valid_enum_rows)
    bad_data[0] = (100, [])
    patched_get_enum_rows.return_value = bad_data
    with pytest.raises(CommandError):
        utils.get_matching_request_row(MagicMock(), row=100)
