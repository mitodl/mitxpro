# pylint: disable=redefined-outer-name,unused-argument
"""Sheets API tests"""

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
import pytest
import pytz

from django.core.exceptions import ImproperlyConfigured
import pygsheets
from pygsheets.client import Client as PygsheetsClient
from pygsheets.drive import DriveAPIWrapper
from pygsheets.sheet import SheetAPIWrapper
from pygsheets.spreadsheet import Spreadsheet
from pygsheets.worksheet import Worksheet
from google.oauth2.credentials import Credentials  # pylint: disable-all

from mitxpro.utils import now_in_utc
from sheets.api import (
    get_credentials,
    create_coupons_for_request_row,
    CouponRequestHandler,
)
from sheets.constants import (
    GOOGLE_SERVICE_ACCOUNT_EMAIL_DOMAIN,
    REQUIRED_GOOGLE_API_SCOPES,
)
from sheets.exceptions import SheetOutOfSyncException, InvalidSheetProductException
from sheets.utils import (
    coupon_request_sheet_spec,
    ProcessedRequest,
    format_datetime_for_sheet_formula,
    CouponRequestRow,
    get_enumerated_data_rows,
    FailedRequest,
)
from sheets.factories import CouponGenerationRequestFactory, GoogleApiAuthFactory
from ecommerce.models import CouponPaymentVersion, Company


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
    sheet_rows[1][0] = "another_purchase_order_id"
    sheet_rows[1][2] = "10"
    mocked_worksheet = MagicMock(
        spec=Worksheet, get_all_values=Mock(return_value=sheet_rows)
    )
    mocked_spreadsheet = MagicMock(spec=Spreadsheet, sheet1=mocked_worksheet)
    mocked_pygsheets_client = MagicMock(
        spec=PygsheetsClient,
        open_by_key=Mock(return_value=mocked_spreadsheet),
        drive=MagicMock(spec=DriveAPIWrapper),
        sheet=MagicMock(spec=SheetAPIWrapper),
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


@pytest.mark.django_db
def test_get_credentials_service_account(mocker, settings):
    """
    get_credentials should construct a valid Credentials object from app settings using Service Account auth
    """
    patched_svc_account_creds = mocker.patch("sheets.api.ServiceAccountCredentials")
    settings.DRIVE_SERVICE_ACCOUNT_CREDS = '{"credentials": "json"}'
    settings.SHEETS_ADMIN_EMAILS = ["abc@example.com"]
    # An exception should be raised if service account auth is being used, but no service account email
    # is included in the list of emails to share spreadsheets with.
    with pytest.raises(ImproperlyConfigured):
        get_credentials()

    settings.SHEETS_ADMIN_EMAILS.append(
        "service-account@mitxpro.{}".format(GOOGLE_SERVICE_ACCOUNT_EMAIL_DOMAIN)
    )
    creds = get_credentials()

    patched_svc_account_creds.from_service_account_info.assert_called_once_with(
        {"credentials": "json"}, scopes=REQUIRED_GOOGLE_API_SCOPES
    )
    assert creds == patched_svc_account_creds.from_service_account_info.return_value


@pytest.mark.django_db
def test_get_credentials_personal_auth(settings):
    """
    get_credentials should construct a valid Credentials object from data and app settings using personal
    OAuth credentials if Service Account auth is not being used
    """
    settings.DRIVE_SERVICE_ACCOUNT_CREDS = None
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
        payment_transaction=coupon_req_row.purchase_order_id,
        amount=Decimal("1.0"),
        automatic=False,
    )
    assert coupon_gen_request.completed is True


@pytest.mark.django_db
def test_create_coupons_already_complete(mocker, coupon_req_row):
    """
    create_coupons_for_request_row should raise an exception if a
    request has already been completed for the request row's transaction id.
    """
    patched_log = mocker.patch("sheets.api.log")
    CouponGenerationRequestFactory.create(
        purchase_order_id=coupon_req_row.purchase_order_id, completed=True
    )
    with pytest.raises(SheetOutOfSyncException):
        create_coupons_for_request_row(coupon_req_row)
    patched_log.error.assert_called_once()


def test_coupon_request_handler_create_coupons(mocker, pygsheets_fixtures):
    """
    CouponRequestHandler.create_coupons_from_rows should iterate through the given rows of data, create
    coupons for the ones that are not yet processed, and return objects representing the row results.
    """
    mocker.patch("sheets.api.pygsheets", pygsheets_fixtures.pygsheets)
    coupon_gen_requests = CouponGenerationRequestFactory.create_batch(
        pygsheets_fixtures.num_data_rows
    )
    patched_create_coupons = mocker.patch(
        "sheets.api.create_coupons_for_request_row", side_effect=coupon_gen_requests
    )

    coupon_req_handler = CouponRequestHandler()
    enumerated_rows = get_enumerated_data_rows(coupon_req_handler.coupon_request_sheet)
    processed_requests, failed_requests, _ = coupon_req_handler.create_coupons_from_rows(
        enumerated_rows
    )
    assert patched_create_coupons.call_count == pygsheets_fixtures.num_data_rows
    assert len(processed_requests) == pygsheets_fixtures.num_data_rows
    assert len(failed_requests) == 0
    assert processed_requests[0].row_index == 2
    assert processed_requests[1].row_index == 3
    assert all(
        isinstance(processed_request.coupon_req_row, CouponRequestRow)
        for processed_request in processed_requests
    )
    assert [
        processed_request.request_id for processed_request in processed_requests
    ] == [coupon_gen_request.id for coupon_gen_request in coupon_gen_requests]


def test_coupon_request_handler_coupon_failures(
    mocker, pygsheets_fixtures, coupon_req_row
):
    """
    CouponRequestHandler.create_coupons_from_rows should return objects representing row failures
    if data rows can't be parsed or coupons can't be created.
    """
    mocker.patch("sheets.api.pygsheets", pygsheets_fixtures.pygsheets)
    patched_log = mocker.patch("sheets.api.log")
    patched_row_parse = mocker.patch.object(
        CouponRequestRow,
        "parse_raw_data",
        side_effect=[
            IndexError("Parsing failure"),
            coupon_req_row,
            coupon_req_row,
            coupon_req_row,
        ],
    )
    patched_create_coupons = mocker.patch(
        "sheets.api.create_coupons_for_request_row",
        side_effect=[
            Company.DoesNotExist(),
            InvalidSheetProductException(),
            ValueError("Coupon creation failure"),
        ],
    )
    coupon_req_handler = CouponRequestHandler()
    enumerated_rows = enumerate([["mock", "row", "data"]] * 4, start=2)
    processed_requests, failed_requests, _ = coupon_req_handler.create_coupons_from_rows(
        enumerated_rows
    )
    assert len(failed_requests) == 4
    assert patched_log.error.call_count == 4
    assert patched_row_parse.call_count == 4
    # create_coupons_for_request_row should not be called if the row fails parsing
    assert patched_create_coupons.call_count == 3
    expected_exception_types = [
        IndexError,
        Company.DoesNotExist,
        InvalidSheetProductException,
        ValueError,
    ]
    exceptions = [failed_request.exception for failed_request in failed_requests]
    assert all(
        isinstance(exception, expected_exception_type)
        for exception, expected_exception_type in zip(
            exceptions, expected_exception_types
        )
    )


def test_coupon_request_handler_update_processed(
    mocker, settings, pygsheets_fixtures, coupon_req_row
):
    """
    CouponRequestHandler.update_coupon_request_processed_dates should use the pygsheets client to update the "processed"
    checkboxes for each request sheet row that was successfully processed.
    """
    tz_new_york = pytz.timezone("America/New_York")
    settings.SHEETS_DATE_TIMEZONE = tz_new_york
    mocker.patch("sheets.api.pygsheets", pygsheets_fixtures.pygsheets)
    processed_dates = [now_in_utc(), now_in_utc() - timedelta(days=1)]
    processed_requests = [
        ProcessedRequest(
            row_index=2,
            coupon_req_row=coupon_req_row,
            request_id=1,
            date_processed=processed_dates[0],
        ),
        ProcessedRequest(
            row_index=3,
            coupon_req_row=coupon_req_row,
            request_id=2,
            date_processed=processed_dates[1],
        ),
    ]

    coupon_req_handler = CouponRequestHandler()
    coupon_req_handler.update_coupon_request_processed_dates(processed_requests)
    assert pygsheets_fixtures.worksheet.update_values.call_count == len(
        processed_requests
    )
    pygsheets_fixtures.worksheet.update_values.assert_any_call(
        crange="H2:I2",
        values=[
            [
                format_datetime_for_sheet_formula(
                    processed_dates[0].astimezone(tz_new_york)
                ),
                "",
            ]
        ],
    )
    pygsheets_fixtures.worksheet.update_values.assert_any_call(
        crange="H3:I3",
        values=[
            [
                format_datetime_for_sheet_formula(
                    processed_dates[1].astimezone(tz_new_york)
                ),
                "",
            ]
        ],
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
        ProcessedRequest(
            row_index=2,
            coupon_req_row=coupon_req_row,
            request_id=1,
            date_processed=now_in_utc(),
        ),
        ProcessedRequest(
            row_index=3,
            coupon_req_row=coupon_req_row,
            request_id=2,
            date_processed=now_in_utc(),
        ),
    ]
    patched_update_checkboxes = mocker.patch.object(
        CouponRequestHandler, "update_coupon_request_processed_dates"
    )
    patched_create_sheet = mocker.patch.object(
        CouponRequestHandler, "create_coupon_assignment_sheet"
    )

    coupon_req_handler = CouponRequestHandler()
    coupon_req_handler.create_and_update_sheets(processed_requests)
    patched_update_checkboxes.assert_called_once_with(processed_requests)
    assert patched_create_sheet.call_count == len(processed_requests)
    assert [args[0][0] for args in patched_create_sheet.call_args_list] == [
        processed_request.coupon_req_row for processed_request in processed_requests
    ]


def test_process_sheet(mocker, pygsheets_fixtures):
    """
    CouponRequestHandler.process_sheet should create coupons for all relevant rows, appropriately handle
    rows that succeeded and failed, and return some results.
    """
    mocker.patch("sheets.api.pygsheets", pygsheets_fixtures.pygsheets)
    patched_get_rows = mocker.patch(
        "sheets.api.get_enumerated_data_rows", return_value=[(1, ["fake", "row"])]
    )
    processed_requests = [
        ProcessedRequest(
            row_index=2, coupon_req_row=mocker.Mock(), request_id=2, date_processed=None
        ),
        ProcessedRequest(
            row_index=3, coupon_req_row=mocker.Mock(), request_id=3, date_processed=None
        ),
    ]
    failed_request = FailedRequest(
        row_index=4, exception=Exception("error"), error_text="bad"
    )
    unrecorded_complete_request = ProcessedRequest(
        row_index=5,
        coupon_req_row=mocker.Mock(),
        request_id=5,
        date_processed=now_in_utc(),
    )
    patched_create_coupons_from_rows = mocker.patch.object(
        CouponRequestHandler,
        "create_coupons_from_rows",
        return_value=(
            processed_requests,
            [failed_request],
            [unrecorded_complete_request],
        ),
    )
    patched_create_and_update_sheets = mocker.patch.object(
        CouponRequestHandler,
        "create_and_update_sheets",
        return_value=[mocker.Mock(title="new spreadsheet")],
    )
    patched_update_coupon_request_errors = mocker.patch.object(
        CouponRequestHandler, "update_coupon_request_errors"
    )
    patched_update_coupon_request_processed_dates = mocker.patch.object(
        CouponRequestHandler, "update_coupon_request_processed_dates"
    )

    coupon_req_handler = CouponRequestHandler()
    results = coupon_req_handler.process_sheet()

    patched_get_rows.assert_called_once_with(
        coupon_req_handler.coupon_request_sheet, limit_row_index=None
    )
    patched_create_coupons_from_rows.assert_called_once_with(
        patched_get_rows.return_value
    )
    patched_create_and_update_sheets.assert_called_once_with(processed_requests)
    patched_update_coupon_request_errors.assert_called_once_with([failed_request])
    patched_update_coupon_request_processed_dates.assert_called_once_with(
        [unrecorded_complete_request]
    )
    assert results == {
        "processed_requests": {
            "rows": [2, 3],
            "assignment_sheets": ["new spreadsheet"],
        },
        "failed_request_rows": [4],
        "synced_request_rows": [5],
    }
