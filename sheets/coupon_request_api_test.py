# pylint: disable=redefined-outer-name,unused-argument
"""Coupon request API tests"""

import copy
import json
from decimal import Decimal
from datetime import timedelta
from types import SimpleNamespace

import pytest
import pytz
from pygsheets import Worksheet, Spreadsheet
from pygsheets.client import Client as PygsheetsClient
from pygsheets.drive import DriveAPIWrapper
from pygsheets.sheet import SheetAPIWrapper

from ecommerce.models import CouponPaymentVersion, Company
from mitxpro.utils import now_in_utc
from sheets.coupon_request_api import (
    create_coupons_for_request_row,
    CouponRequestHandler,
)
from sheets.exceptions import (
    SheetRowParsingException,
    SheetCouponCreationException,
    InvalidSheetProductException,
    SheetOutOfSyncException,
)
from sheets.factories import CouponGenerationRequestFactory, GoogleApiAuthFactory
from sheets.models import CouponGenerationRequest
from sheets.utils import (
    get_enumerated_data_rows,
    CouponRequestRow,
    ProcessedRequest,
    format_datetime_for_sheet_formula,
    FailedRequest,
    IgnoredRequest,
    coupon_request_sheet_spec,
)


@pytest.fixture()
def pygsheets_fixtures(mocker, db, coupon_req_raw_data):
    """Set of fixtures that mock out pygsheets functionality"""
    Mock = mocker.Mock
    MagicMock = mocker.MagicMock
    google_api_auth = GoogleApiAuthFactory.create()
    # Create some fake worksheet rows, with a header row and two rows of data
    # (the second slightly different from the first)
    sheet_rows = [coupon_request_sheet_spec.column_headers, coupon_req_raw_data]
    added_row = list(coupon_req_raw_data)
    added_row[0] = "another_purchase_order_id"
    added_row[1] = "another_coupon_id"
    added_row[2] = "10"
    sheet_rows.append(added_row)
    mocked_worksheet = MagicMock(
        spec=Worksheet, get_all_values=Mock(return_value=sheet_rows)
    )
    mocked_spreadsheet = MagicMock(spec=Spreadsheet, sheet1=mocked_worksheet)
    mocked_pygsheets_client = MagicMock(
        spec=PygsheetsClient,
        oauth=Mock(),
        open_by_key=Mock(return_value=mocked_spreadsheet),
        drive=MagicMock(spec=DriveAPIWrapper),
        sheet=MagicMock(spec=SheetAPIWrapper),
    )
    mocker.patch(
        "sheets.coupon_request_api.get_authorized_pygsheets_client",
        return_value=mocked_pygsheets_client,
    )
    return SimpleNamespace(
        client=mocked_pygsheets_client,
        spreadsheet=mocked_spreadsheet,
        worksheet=mocked_worksheet,
        sheet_rows=sheet_rows,
        num_data_rows=len(sheet_rows) - 1,
        google_api_auth=google_api_auth,
    )


@pytest.mark.django_db
def test_create_coupons_for_request_row(mocker, base_data, coupon_req_row):
    """
    create_coupons_for_request_row should call the 'create_coupons' coupons helper
    function and creates an object to record the processing of the coupon request.
    """
    patched_create_coupons = mocker.patch("ecommerce.api.create_coupons")
    fake_company_id = 123
    create_coupons_for_request_row(coupon_req_row, company_id=fake_company_id)
    patched_create_coupons.assert_called_once_with(
        name=coupon_req_row.coupon_name,
        product_ids=[base_data.product_version.product.id],
        num_coupon_codes=coupon_req_row.num_codes,
        coupon_type=CouponPaymentVersion.SINGLE_USE,
        max_redemptions=1,
        company_id=fake_company_id,
        activation_date=coupon_req_row.activation,
        expiration_date=coupon_req_row.expiration,
        payment_type=CouponPaymentVersion.PAYMENT_PO,
        payment_transaction=coupon_req_row.purchase_order_id,
        amount=Decimal("1.0"),
        automatic=False,
    )


def test_parse_rows_and_create_coupons(mocker, pygsheets_fixtures):
    """
    CouponRequestHandler.parse_rows_and_create_coupons should iterate through the given rows of data, create
    coupons for the ones that are not yet processed, and return objects representing the row results.
    """
    patched_create_coupons = mocker.patch(
        "sheets.coupon_request_api.create_coupons_for_request_row"
    )

    coupon_req_handler = CouponRequestHandler()
    enumerated_rows = get_enumerated_data_rows(coupon_req_handler.coupon_request_sheet)
    processed_requests, failed_requests, _, _ = coupon_req_handler.parse_rows_and_create_coupons(
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
    request_ids = [
        processed_request.request_id for processed_request in processed_requests
    ]
    coupon_gen_request_ids = CouponGenerationRequest.objects.filter(
        id__in=request_ids
    ).values_list("id", flat=True)
    assert len(coupon_gen_request_ids) == pygsheets_fixtures.num_data_rows
    assert set(coupon_gen_request_ids) == set(request_ids)


def test_parse_and_create_other_responses(
    mocker, pygsheets_fixtures, coupon_req_row
):  # pylint: disable=too-many-locals
    """
    CouponRequestHandler.parse_rows_and_create_coupons should return objects representing row failures
    if data rows can't be parsed or coupons can't be created.
    """
    patched_log = mocker.patch("sheets.coupon_request_api.log")
    row_with_error_text = copy.copy(coupon_req_row)
    row_with_error_text.error = "Row error"
    incomplete_request = CouponGenerationRequestFactory.create(date_completed=None)
    complete_request = CouponGenerationRequestFactory.create(
        date_completed=now_in_utc()
    )
    parse_and_create_side_effects = [
        SheetRowParsingException(),
        SheetCouponCreationException(
            incomplete_request, coupon_req_row, inner_exc=InvalidSheetProductException()
        ),
        SheetCouponCreationException(
            incomplete_request, coupon_req_row, inner_exc=ValueError()
        ),
        ValueError("Unexpected value error"),
        SheetOutOfSyncException(incomplete_request, coupon_req_row),
        # Rows with error text that were passed over should be included in results as ignored rows
        (incomplete_request, row_with_error_text, True),
        # Completed rows that were ignored should NOT be included in results as ignored rows
        (complete_request, coupon_req_row, True),
    ]
    patched_parse_row_and_create_coupons = mocker.patch(
        "sheets.coupon_request_api.CouponRequestHandler.parse_row_and_create_coupons",
        side_effect=parse_and_create_side_effects,
    )
    row_count = len(parse_and_create_side_effects)

    coupon_req_handler = CouponRequestHandler()
    enumerated_rows = enumerate(
        [["order{}".format(i), "coupon{}".format(i)] for i in range(row_count)], start=2
    )
    processed_reqs, failed_reqs, ignored_reqs, unrecorded_reqs = coupon_req_handler.parse_rows_and_create_coupons(
        enumerated_rows
    )

    assert patched_parse_row_and_create_coupons.call_count == row_count
    assert len(processed_reqs) == 0
    # All but the last 3 calls to 'parse_row_and_create_coupons' should be counted as failed requests
    assert len(failed_reqs) == (row_count - 3)
    assert len(ignored_reqs) == 1
    assert len(unrecorded_reqs) == 1
    assert patched_log.exception.call_count == len(failed_reqs)


def test_parse_row_raw_data_update(mocker, pygsheets_fixtures, coupon_req_raw_data):
    """
    CouponRequestHandler.parse_row_and_create_coupons should update the `raw_data` property for a
    CouponGenerationRequest if the actual data in the row is different.
    """
    mocker.patch("sheets.coupon_request_api.create_coupons_for_request_row")
    raw_row_data = copy.copy(coupon_req_raw_data)
    raw_data_for_gen_request = json.dumps(
        CouponRequestRow.get_user_input_columns(raw_row_data)
    )
    coupon_gen_request = CouponGenerationRequestFactory.create(
        coupon_name=raw_row_data[CouponRequestRow.COUPON_NAME_COL_INDEX],
        raw_data=raw_data_for_gen_request,
    )

    raw_row_data[3] = "updated column value"
    coupon_req_handler = CouponRequestHandler()
    _, _, _ = coupon_req_handler.parse_row_and_create_coupons(
        row_index=1, row_data=raw_row_data
    )
    coupon_gen_request.refresh_from_db()
    assert coupon_gen_request.raw_data != raw_data_for_gen_request
    assert coupon_gen_request.raw_data == json.dumps(
        CouponRequestRow.get_user_input_columns(raw_row_data)
    )


def test_parse_row_already_processed(
    mocker, settings, pygsheets_fixtures, coupon_req_raw_data
):
    """
    CouponRequestHandler.parse_row_and_create_coupons should return ignored=True and skip coupon creation
    if a request row indicates that it has already been processed.
    """
    patched_create_coupons = mocker.patch(
        "sheets.coupon_request_api.create_coupons_for_request_row"
    )
    now = now_in_utc()
    row_data = copy.copy(coupon_req_raw_data)
    row_data[settings.SHEETS_REQ_PROCESSED_COL] = now.strftime(
        settings.SHEETS_DATE_FORMAT
    )

    coupon_req_handler = CouponRequestHandler()
    _, coupon_req_row, ignored = coupon_req_handler.parse_row_and_create_coupons(
        row_index=1, row_data=row_data
    )
    assert ignored is True
    assert (
        coupon_req_row.purchase_order_id
        == row_data[CouponRequestRow.PURCHASE_ORDER_COL_INDEX]
    )
    patched_create_coupons.assert_not_called()


def test_parse_row_unchanged_error(
    mocker, settings, pygsheets_fixtures, coupon_req_raw_data
):
    """
    CouponRequestHandler.parse_row_and_create_coupons should return ignored=True and skip coupon creation
    if a request row has an error and the row data is unchanged from our data in the database.
    """
    patched_create_coupons = mocker.patch(
        "sheets.coupon_request_api.create_coupons_for_request_row"
    )
    raw_row_data = copy.copy(coupon_req_raw_data)
    raw_row_data[settings.SHEETS_REQ_ERROR_COL] = "Error"
    existing_coupon_gen_request = CouponGenerationRequestFactory.create(
        coupon_name=raw_row_data[CouponRequestRow.COUPON_NAME_COL_INDEX],
        raw_data=json.dumps(CouponRequestRow.get_user_input_columns(raw_row_data)),
    )

    coupon_req_handler = CouponRequestHandler()
    coupon_gen_request, _, ignored = coupon_req_handler.parse_row_and_create_coupons(
        row_index=1, row_data=raw_row_data
    )
    assert ignored is True
    assert coupon_gen_request == existing_coupon_gen_request
    patched_create_coupons.assert_not_called()


@pytest.mark.django_db
def test_parse_row_new_company(mocker, pygsheets_fixtures, coupon_req_raw_data):
    """
    CouponRequestHandler.parse_row_and_create_coupons should create a Company by the name
    indicated in the request row if it doesn't exist yet.
    """
    patched_create_coupons = mocker.patch(
        "sheets.coupon_request_api.create_coupons_for_request_row"
    )
    new_company_name = "New Company"
    row_data = copy.copy(coupon_req_raw_data)
    row_data[4] = new_company_name
    coupon_req_handler = CouponRequestHandler()
    _, _, _ = coupon_req_handler.parse_row_and_create_coupons(
        row_index=1, row_data=row_data
    )
    patched_create_coupons.assert_called_once()
    assert Company.objects.filter(name=new_company_name).exists() is True


def test_update_processed(settings, pygsheets_fixtures, coupon_req_row):
    """
    CouponRequestHandler.update_coupon_request_processed_dates should use the pygsheets client to update the "processed"
    checkboxes for each request sheet row that was successfully processed.
    """
    tz_new_york = pytz.timezone("America/New_York")
    settings.SHEETS_DATE_TIMEZONE = tz_new_york
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
        crange="I2:J2",
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
        crange="I3:J3",
        values=[
            [
                format_datetime_for_sheet_formula(
                    processed_dates[1].astimezone(tz_new_york)
                ),
                "",
            ]
        ],
    )


def test_write_results_to_sheets(mocker, pygsheets_fixtures, coupon_req_row):
    """
    CouponRequestHandler.write_results_to_sheets should use the pygsheets client to
    update request sheet checkboxes and create a new assignment sheet for every row
    that was successfully processed.
    """
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
    patched_get_rows = mocker.patch(
        "sheets.coupon_request_api.get_enumerated_data_rows",
        return_value=[(1, ["fake", "row"])],
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
        row_index=4, exception=Exception("error"), sheet_error_text="bad"
    )
    ignored_request = IgnoredRequest(
        row_index=5, coupon_req_row=mocker.Mock(), reason="Ignored"
    )
    unrecorded_complete_request = ProcessedRequest(
        row_index=6,
        coupon_req_row=mocker.Mock(),
        request_id=6,
        date_processed=now_in_utc(),
    )
    patched_parse_rows_and_create_coupons = mocker.patch.object(
        CouponRequestHandler,
        "parse_rows_and_create_coupons",
        return_value=(
            processed_requests,
            [failed_request],
            [ignored_request],
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
    patched_parse_rows_and_create_coupons.assert_called_once_with(
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
        "ignored_request_rows": [5],
        "synced_request_rows": [6],
    }
