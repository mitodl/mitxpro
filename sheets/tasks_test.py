"""Tests for sheets app views"""

import pytest

from sheets.tasks import (
    _get_scheduled_assignment_task_ids,
    handle_unprocessed_coupon_requests,
)


def test_handle_unprocessed_coupon_requests(mocker):
    """
    handle_unprocessed_coupon_requests should call a method to process the request spreadsheet
    """
    patched_req_handler = mocker.patch(
        "sheets.coupon_request_api.CouponRequestHandler", autospec=True
    )
    handle_unprocessed_coupon_requests.delay()
    patched_req_handler.return_value.process_sheet.assert_called_once()


@pytest.mark.parametrize("same_name", [True, False])
@pytest.mark.parametrize("same_id", [True, False])
def test_get_scheduled_assignment_task_ids(mocker, same_name, same_id):
    """The expected task ids should be returned"""
    mock_app_control = mocker.patch("sheets.tasks.app.control")
    file_id = "correct_file_id" if same_id else "different_id"
    task_name = (
        "sheets.tasks.process_coupon_assignment_sheet"
        if same_name
        else "sheets.tasks.other_sheet"
    )
    task_id = "123-456-7890"
    mock_app_control.inspect.return_value.scheduled.return_value.values.return_value = [
        [
            {
                "request": {
                    "id": task_id,
                    "name": task_name,
                    "args": [],
                    "kwargs": {
                        "file_id": file_id,
                        "change_date": "2023-02-06T21:35:11.280503+00:00",
                    },
                }
            }
        ]
    ]
    assert _get_scheduled_assignment_task_ids("correct_file_id") == (
        [task_id] if (same_name and same_id) else []
    )
