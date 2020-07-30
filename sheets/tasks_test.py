"""Tests for sheets app views"""
from sheets.tasks import handle_unprocessed_coupon_requests


def test_handle_unprocessed_coupon_requests(mocker):
    """
    handle_unprocessed_coupon_requests should call a method to process the request spreadsheet
    """
    patched_req_handler = mocker.patch(
        "sheets.coupon_request_api.CouponRequestHandler", autospec=True
    )
    handle_unprocessed_coupon_requests.delay()
    patched_req_handler.return_value.process_sheet.assert_called_once()
