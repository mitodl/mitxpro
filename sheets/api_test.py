# pylint: disable=redefined-outer-name,unused-argument
"""Sheets API tests"""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
import pytz
import pytest

from django.core.exceptions import ImproperlyConfigured
import pygsheets
from pygsheets.client import Client as PygsheetsClient
from pygsheets.spreadsheet import Spreadsheet
from pygsheets.worksheet import Worksheet
from google.oauth2.credentials import Credentials  # pylint: disable-all

from sheets.api import (
    CouponRequestRow,
    get_credentials,
    create_coupons_for_request_row,
    CouponRequestHandler,
)
from sheets.utils import coupon_request_sheet_spec, ProcessedRequest
from sheets.factories import CouponGenerationRequestFactory, GoogleApiAuthFactory
from courses.models import CourseRun
from ecommerce.models import CouponPaymentVersion


@pytest.fixture()
def coupon_req_raw_data(base_data):
    """Fixture that returns raw row data that can be parsed as a CouponRequestRow"""
    return [
        "transaction_id_1",
        "mycoupon",
        "5",
        base_data.run.courseware_id,
        "Course Run",
        "01/01/2019 01:01:01",
        "02/02/2020 02:02:02",
        base_data.company.name,
        "FALSE",
    ]


@pytest.fixture()
def pygsheets_fixtures(mocker, db, coupon_req_raw_data):
    """Set of fixtures that mock out pygsheets functionality"""
    Mock = mocker.Mock
    MagicMock = mocker.MagicMock
    google_api_auth = GoogleApiAuthFactory.create()
    # Create some fake worksheet rows, with a header row and two rows of data
    # (the second slightly different from the first)
    sheet_rows = [
        coupon_request_sheet_spec.column_headers,
        coupon_req_raw_data,
        coupon_req_raw_data,
    ]
    sheet_rows[1][0] = "another_transaction_id"
    sheet_rows[1][2] = "10"
    mocked_worksheet = MagicMock(
        spec=Worksheet, get_all_values=Mock(return_value=sheet_rows)
    )
    mocked_spreadsheet = MagicMock(spec=Spreadsheet, sheet1=mocked_worksheet)
    mocked_pygsheets_client = MagicMock(
        spec=PygsheetsClient, open_by_key=Mock(return_value=mocked_spreadsheet)
    )
    top_level_module = MagicMock(
        spec=pygsheets, authorize=Mock(return_value=mocked_pygsheets_client)
    )
    return SimpleNamespace(
        pygsheets=top_level_module,
        client=mocked_pygsheets_client,
        spreadsheet=mocked_spreadsheet,
        worksheet=mocked_worksheet,
        sheet_rows=sheet_rows,
        num_data_rows=len(sheet_rows) - 1,
        google_api_auth=google_api_auth,
    )


def test_coupon_request_row_valid(coupon_req_raw_data):
    """CouponRequestRow should take a row of raw data and parse it when it's initialized"""
    coupon_req_row = CouponRequestRow.parse_raw_data(coupon_req_raw_data)
    assert coupon_req_row.transaction_id == "transaction_id_1"
    assert coupon_req_row.coupon_name == "mycoupon"
    assert coupon_req_row.num_codes == 5
    assert coupon_req_row.product_text_id == "course-v1:some-course"
    assert coupon_req_row.product_object_cls == CourseRun
    assert coupon_req_row.activation == datetime(2019, 1, 1, 1, 1, 1, tzinfo=pytz.UTC)
    assert coupon_req_row.expiration == datetime(2020, 2, 2, 2, 2, 2, tzinfo=pytz.UTC)
    assert coupon_req_row.company_name == "MIT"
    assert coupon_req_row.processed is False


@pytest.mark.django_db
def test_get_credentials(settings):
    """
    get_credentials should construct a valid Credentials object from data and app settings.
    """
    settings.DRIVE_CLIENT_ID = "client-id"
    settings.DRIVE_CLIENT_SECRET = "client-secret"
    settings.ENVIRONMENT = "prod"
    with pytest.raises(ImproperlyConfigured):
        get_credentials()

    google_api_auth = GoogleApiAuthFactory.create()
    credentials = get_credentials()
    assert isinstance(credentials, Credentials)
    assert credentials.token == google_api_auth.access_token
    assert credentials.refresh_token == google_api_auth.refresh_token


@pytest.mark.django_db
def test_create_coupons_for_request_row(mocker, base_data, coupon_req_row):
    """
    create_coupons_for_request_row should call the 'create_coupons' coupons helper
    function and creates an object to record the processing of the coupon request.
    """
    patched_create_coupons = mocker.patch("sheets.api.create_coupons")

    coupon_gen_request = create_coupons_for_request_row(coupon_req_row)
    patched_create_coupons.assert_called_once_with(
        name=coupon_req_row.coupon_name,
        product_ids=[base_data.product_version.product.id],
        num_coupon_codes=coupon_req_row.num_codes,
        coupon_type=CouponPaymentVersion.SINGLE_USE,
        max_redemptions=1,
        company_id=base_data.company.id,
        activation_date=coupon_req_row.activation,
        expiration_date=coupon_req_row.expiration,
        payment_type=CouponPaymentVersion.PAYMENT_PO,
        payment_transaction=coupon_req_row.transaction_id,
        amount=Decimal("1.0"),
        automatic=False,
    )
    assert coupon_gen_request.completed is True


@pytest.mark.django_db
def test_create_coupons_already_complete(mocker, coupon_req_row):
    """
    create_coupons_for_request_row should log and error and return nothing if a
    request has already been completed for the request row's transaction id.
    """
    patched_log = mocker.patch("sheets.api.log")
    CouponGenerationRequestFactory.create(
        transaction_id=coupon_req_row.transaction_id, completed=True
    )

    coupon_gen_request = create_coupons_for_request_row(coupon_req_row)
    patched_log.error.assert_called_once()
    assert coupon_gen_request is None


def test_coupon_request_handler_rows(mocker, pygsheets_fixtures):
    """
    CouponRequestHandler.parsed_row_iterator should iterate through raw data in
    a worksheet, parse it as a CouponRequestRow, and return the sheet row number along
    with the CouponRequestRow object.
    """
    mocker.patch("sheets.api.pygsheets", pygsheets_fixtures.pygsheets)
    coupon_req_handler = CouponRequestHandler()
    parsed_rows = list(coupon_req_handler.parsed_row_iterator())
    assert len(parsed_rows) == pygsheets_fixtures.num_data_rows
    first_row_number, first_request_row = parsed_rows[0]
    assert first_row_number == 2
    assert first_request_row.transaction_id == pygsheets_fixtures.sheet_rows[1][0]
    second_row_number, second_request_row = parsed_rows[1]
    assert second_row_number == 3
    assert second_request_row.transaction_id == pygsheets_fixtures.sheet_rows[2][0]


def test_coupon_request_handler_create_coupons(mocker, pygsheets_fixtures):
    """
    CouponRequestHandler.create_coupons_from_sheet should iterate through the rows of the coupon request sheet, create
    coupons for the ones that are not yet processed, and return objects representing the processed rows.
    """
    mocker.patch("sheets.api.pygsheets", pygsheets_fixtures.pygsheets)
    coupon_gen_requests = CouponGenerationRequestFactory.create_batch(
        pygsheets_fixtures.num_data_rows
    )
    patched_create_coupons = mocker.patch(
        "sheets.api.create_coupons_for_request_row", side_effect=coupon_gen_requests
    )

    coupon_req_handler = CouponRequestHandler()
    processed_requests = coupon_req_handler.create_coupons_from_sheet()
    assert patched_create_coupons.call_count == pygsheets_fixtures.num_data_rows
    assert len(processed_requests) == pygsheets_fixtures.num_data_rows
    assert processed_requests[0].row_index == 2
    assert processed_requests[1].row_index == 3
    assert all(
        isinstance(processed_request.coupon_req_row, CouponRequestRow)
        for processed_request in processed_requests
    )
    assert [
        processed_request.request_id for processed_request in processed_requests
    ] == [coupon_gen_request.id for coupon_gen_request in coupon_gen_requests]


def test_coupon_request_handler_update_checkboxes(
    mocker, pygsheets_fixtures, coupon_req_row
):
    """
    CouponRequestHandler.update_coupon_request_checkboxes should use the pygsheets client to update the "processed"
    checkboxes for each request sheet row that was successfully processed.
    """
    mocker.patch("sheets.api.pygsheets", pygsheets_fixtures.pygsheets)
    processed_requests = [
        ProcessedRequest(row_index=2, coupon_req_row=coupon_req_row, request_id=1),
        ProcessedRequest(row_index=3, coupon_req_row=coupon_req_row, request_id=2),
    ]

    coupon_req_handler = CouponRequestHandler()
    coupon_req_handler.update_coupon_request_checkboxes(processed_requests)
    assert pygsheets_fixtures.worksheet.update_value.call_count == len(
        processed_requests
    )
    assert pygsheets_fixtures.worksheet.update_value.call_args_list[0][0] == (
        "I2",
        True,
    )
    assert pygsheets_fixtures.worksheet.update_value.call_args_list[1][0] == (
        "I3",
        True,
    )


def test_coupon_request_handler_write_results(
    mocker, pygsheets_fixtures, coupon_req_row
):
    """
    CouponRequestHandler.write_results_to_sheets should use the pygsheets client to
    update request sheet checkboxes and create a new assignment sheet for every row
    that was successfully processed.
    """
    mocker.patch("sheets.api.pygsheets", pygsheets_fixtures.pygsheets)
    processed_requests = [
        ProcessedRequest(row_index=2, coupon_req_row=coupon_req_row, request_id=1),
        ProcessedRequest(row_index=3, coupon_req_row=coupon_req_row, request_id=2),
    ]
    patched_update_checkboxes = mocker.patch.object(
        CouponRequestHandler, "update_coupon_request_checkboxes"
    )
    patched_create_sheet = mocker.patch.object(
        CouponRequestHandler, "create_bulk_coupon_sheet"
    )

    coupon_req_handler = CouponRequestHandler()
    coupon_req_handler.write_results_to_sheets(processed_requests)
    patched_update_checkboxes.assert_called_once_with(processed_requests)
    assert patched_create_sheet.call_count == len(processed_requests)
    assert [args[0][0] for args in patched_create_sheet.call_args_list] == [
        processed_request.coupon_req_row for processed_request in processed_requests
    ]


def test_coupon_request_handler_write_results_empty(
    mocker, pygsheets_fixtures, coupon_req_row
):
    """
    CouponRequestHandler.write_results_to_sheets should do nothing if given an empty list.
    """
    mocker.patch("sheets.api.pygsheets", pygsheets_fixtures.pygsheets)
    patched_update_checkboxes = mocker.patch.object(
        CouponRequestHandler, "update_coupon_request_checkboxes"
    )
    patched_create_sheet = mocker.patch.object(
        CouponRequestHandler, "create_bulk_coupon_sheet"
    )

    coupon_req_handler = CouponRequestHandler()
    coupon_req_handler.write_results_to_sheets([])
    patched_update_checkboxes.assert_not_called()
    patched_create_sheet.assert_not_called()
