"""Sheets app tasks"""
from googleapiclient.errors import HttpError

from mitxpro.celery import app
from sheets import api


@app.task
def handle_unprocessed_coupon_requests():
    """
    Goes through all unprocessed rows in the coupon request sheet, creates the requested
    coupons, updates the request sheet to indicate that it was processed, and creates
    the necessary coupon assignment sheets.
    """
    coupon_request_handler = api.CouponRequestHandler()
    results = coupon_request_handler.process_sheet()
    return results


@app.task
def handle_incomplete_coupon_assignments():
    """
    Processes all as-yet-incomplete coupon assignment spreadsheets
    """
    coupon_assignment_handler = api.CouponAssignmentHandler()
    processed_spreadsheet_metadata = (
        coupon_assignment_handler.process_assignment_spreadsheets()
    )
    return processed_spreadsheet_metadata


@app.task
def update_incomplete_assignment_delivery_statuses():
    """
    Fetches all BulkCouponAssignments that have assignments but have not yet finished delivery, then updates the
    delivery status for each depending on what has been sent.
    """
    coupon_assignment_handler = api.CouponAssignmentHandler()
    updated_assignments = (
        coupon_assignment_handler.update_incomplete_assignment_message_statuses()
    )
    return [
        (bulk_assignment_id, len(product_coupon_assignments))
        for bulk_assignment_id, product_coupon_assignments in updated_assignments.items()
    ]


@app.task(autoretry_for=(HttpError,), retry_kwargs={"max_retries": 3, "countdown": 5})
def renew_file_watches():
    """
    Renews push notifications for changes to certain files via the Google API.
    """
    file_watch, created = api.renew_coupon_request_file_watch()
    return file_watch.id, file_watch.channel_id, created
