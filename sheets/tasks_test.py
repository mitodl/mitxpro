"""Tests for sheets app views"""
from mitxpro.utils import now_in_utc
from sheets.tasks import handle_unprocessed_coupon_requests
from sheets.utils import ProcessedRequest


def test_handle_unprocessed_coupon_requests(mocker, coupon_req_row):
    """
    handle_unprocessed_coupon_requests should go through all unprocessed rows in a sheet, create coupons,
    and update/create sheets
    """
    patched_req_handler = mocker.patch("sheets.api.CouponRequestHandler", autospec=True)
    dummy_processed_requests = [
        ProcessedRequest(
            row_index=1,
            coupon_req_row=coupon_req_row,
            request_id=1,
            date_processed=now_in_utc(),
        ),
        ProcessedRequest(
            row_index=2,
            coupon_req_row=coupon_req_row,
            request_id=2,
            date_processed=now_in_utc(),
        ),
    ]
    patched_req_handler.return_value.parse_rows_and_create_coupons.return_value = (
        dummy_processed_requests
    )

    handle_unprocessed_coupon_requests.delay()
    patched_req_handler.assert_called_once()
    patched_req_handler.return_value.process_sheet.assert_called_once()
