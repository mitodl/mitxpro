"""Coupon request API tests"""

import os
from types import SimpleNamespace

import pytest
from pygsheets import Spreadsheet, Worksheet
from pygsheets.client import Client as PygsheetsClient
from pygsheets.drive import DriveAPIWrapper
from pygsheets.sheet import SheetAPIWrapper

from courses.factories import CourseRunFactory
from ecommerce.factories import ProductVersionFactory
from ecommerce.models import Company, Coupon
from sheets.coupon_request_api import CouponRequestHandler, CouponRequestRow
from sheets.factories import GoogleApiAuthFactory
from sheets.models import CouponGenerationRequest
from sheets.utils import ResultType


@pytest.fixture
def courseware_objects():
    """Database objects that CSV data depends on"""
    run = CourseRunFactory.create(courseware_id="course-v1:edX+DemoX+Demo_Course")
    ProductVersionFactory.create(product__content_object=run)


@pytest.fixture
def request_csv_rows(settings, courseware_objects):
    """Fake coupon request spreadsheet data rows (loaded from CSV)"""
    fake_request_csv_filepath = os.path.join(  # noqa: PTH118
        settings.BASE_DIR, "sheets/resources/coupon_requests.csv"
    )
    with open(fake_request_csv_filepath) as f:  # noqa: PTH123
        # Return all rows except for the header
        return [line.split(",") for i, line in enumerate(f.readlines()) if i > 0]


@pytest.fixture
def pygsheets_fixtures(mocker, db, request_csv_rows):
    """Patched functions for pygsheets client functionality"""
    Mock = mocker.Mock
    MagicMock = mocker.MagicMock
    google_api_auth = GoogleApiAuthFactory.create()
    patched_get_data_rows = mocker.patch(
        "sheets.sheet_handler_api.get_data_rows", return_value=request_csv_rows
    )
    mocked_worksheet = MagicMock(spec=Worksheet, get_all_values=Mock(return_value=[]))
    mocked_spreadsheet = MagicMock(
        spec=Spreadsheet, sheet1=mocked_worksheet, id="abc123"
    )
    mocked_pygsheets_client = MagicMock(
        spec=PygsheetsClient,
        oauth=Mock(),
        open_by_key=Mock(return_value=mocked_spreadsheet),
        drive=MagicMock(spec=DriveAPIWrapper),
        sheet=MagicMock(spec=SheetAPIWrapper),
        create=Mock(return_value=mocked_spreadsheet),
    )
    mocker.patch(
        "sheets.coupon_request_api.get_authorized_pygsheets_client",
        return_value=mocked_pygsheets_client,
    )
    return SimpleNamespace(
        client=mocked_pygsheets_client,
        spreadsheet=mocked_spreadsheet,
        worksheet=mocked_worksheet,
        google_api_auth=google_api_auth,
        patched_get_data_rows=patched_get_data_rows,
    )


@pytest.fixture
def patched_sheets_api(mocker):
    """Patches for sheets API functions that use the Drive/Sheets APIs"""
    share_drive_file = mocker.patch(
        "sheets.coupon_request_api.share_drive_file_with_emails", return_value=None
    )
    create_file_watch = mocker.patch(
        "sheets.coupon_request_api.create_or_renew_sheet_file_watch", return_value=None
    )
    return SimpleNamespace(
        share_drive_file=share_drive_file, create_file_watch=create_file_watch
    )


def test_full_sheet_process(
    db, pygsheets_fixtures, patched_sheets_api, request_csv_rows
):
    """
    CouponRequestHandler.process_sheet should parse rows, create relevant objects in the database, and report
    on results
    """
    handler = CouponRequestHandler()
    result = handler.process_sheet()
    expected_processed_rows = {6, 8}
    expected_failed_rows = {5, 7}
    assert ResultType.PROCESSED.value in result
    assert set(result[ResultType.PROCESSED.value]) == expected_processed_rows, (
        f"Rows {expected_processed_rows!s} as defined in coupon_requests.csv should be processed"
    )
    assert ResultType.FAILED.value in result
    assert set(result[ResultType.FAILED.value]) == expected_failed_rows, (
        f"Rows {expected_failed_rows!s} as defined in coupon_requests.csv should fail"
    )
    # A CouponGenerationRequest should be created for each row that wasn't ignored and did not fail full sheet
    # validation (CSV has 1 row that should fail validation, hence the 1)
    assert CouponGenerationRequest.objects.all().count() == (
        len(expected_processed_rows) + len(expected_failed_rows) - 1
    )
    # The correct number of coupons should have been created for each processed row
    processed_rows = [
        CouponRequestRow.parse_raw_data(i, row_data)
        for i, row_data in enumerate(request_csv_rows, start=2)
        if i in expected_processed_rows
    ]
    expected_coupons = sum(row.num_codes for row in processed_rows)
    assert Coupon.objects.all().count() == expected_coupons
    # Sheets API should have been used to create an assignment sheet and share it
    assert patched_sheets_api.create_file_watch.call_count == len(
        expected_processed_rows
    )
    assert patched_sheets_api.share_drive_file.call_count == len(
        expected_processed_rows
    )
    # New companies should have been created during the processing
    assert list(Company.objects.order_by("name").values_list("name", flat=True)) == [
        "MIT",
        "MIT Open Learning",
    ]
