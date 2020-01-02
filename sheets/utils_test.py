"""Sheets app util function tests"""
from datetime import datetime
import copy

import pytz
from pygsheets.worksheet import Worksheet

from sheets.constants import (
    GOOGLE_AUTH_URI,
    GOOGLE_TOKEN_URI,
    GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
)
from sheets import utils
from sheets.utils import CouponRequestRow


def test_generate_google_client_config(settings):
    """generate_google_client_config should return a dict with expected values"""
    settings.DRIVE_CLIENT_ID = "some-id"
    settings.DRIVE_CLIENT_SECRET = "some-secret"
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
    sheet_rows = [["HEADER 1", "HEADER 2"]] + non_header_rows
    mocked_worksheet = mocker.MagicMock(
        spec=Worksheet, get_all_values=mocker.Mock(return_value=sheet_rows)
    )
    data_rows = list(utils.get_data_rows(mocked_worksheet))
    assert data_rows == non_header_rows


def test_get_enumerated_data_rows(mocker):
    """
    enumerated_data_rows should return each row index paired with the raw data in the row for all rows after the
    header row. It should also limit the rows returned if requested.
    """
    non_header_rows = [
        ["row 1 - column 1", "row 1 - column 2"],
        ["row 2 - column 1", "row 2 - column 2"],
    ]
    sheet_rows = [["HEADER 1", "HEADER 2"]] + non_header_rows
    mocked_worksheet = mocker.MagicMock(
        spec=Worksheet, get_all_values=mocker.Mock(return_value=sheet_rows)
    )
    enumerated_data_rows = list(utils.get_enumerated_data_rows(mocked_worksheet))
    assert enumerated_data_rows == [
        (2, ["row 1 - column 1", "row 1 - column 2"]),
        (3, ["row 2 - column 1", "row 2 - column 2"]),
    ]
    enumerated_data_rows = list(
        utils.get_enumerated_data_rows(mocked_worksheet, limit_row_index=3)
    )
    assert enumerated_data_rows == [(3, ["row 2 - column 1", "row 2 - column 2"])]


def test_coupon_request_row_valid(settings, coupon_req_raw_data):
    """CouponRequestRow should take a row of raw data and parse it when it's initialized"""
    row_index = 2
    raw_data = copy.copy(coupon_req_raw_data)
    coupon_req_row = CouponRequestRow.parse_raw_data(row_index, raw_data)
    assert coupon_req_row.row_index == 2
    assert coupon_req_row.purchase_order_id == "purchase_order_id_1"
    assert coupon_req_row.coupon_name == "mycoupon"
    assert coupon_req_row.num_codes == 5
    assert coupon_req_row.product_text_id == "course-v1:some-course"
    assert coupon_req_row.company_name == "MIT"
    assert coupon_req_row.activation == datetime(2019, 1, 1, 1, 1, 1, tzinfo=pytz.UTC)
    assert coupon_req_row.expiration == datetime(2020, 2, 2, 2, 2, 2, tzinfo=pytz.UTC)
    assert coupon_req_row.date_processed is None
    # If any of the date columns at the end of the row are blank, our Sheets client returns a row
    # with those values cut off completely from the array. Ensure that the row can be parsed without those indices.
    truncated_raw_data = raw_data[0:5]
    coupon_req_row = CouponRequestRow.parse_raw_data(row_index, truncated_raw_data)
    assert coupon_req_row.activation is None
    assert coupon_req_row.expiration is None
    # Ensure that the "Date Processed" and "Error" columns can be parsed if they exists in the row array.
    raw_data[settings.SHEETS_REQ_PROCESSED_COL] = "03/03/2021 03:03:03"
    raw_data[settings.SHEETS_REQ_ERROR_COL] = "Error"
    coupon_req_row = CouponRequestRow.parse_raw_data(row_index, raw_data)
    assert coupon_req_row.date_processed == datetime(
        2021, 3, 3, 3, 3, 3, tzinfo=pytz.UTC
    )
    assert coupon_req_row.error == "Error"
