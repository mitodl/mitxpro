"""Sheets app tasks"""
from mitxpro.celery import app
from sheets.api import CouponRequestHandler, CouponAssignmentHandler


@app.task
def handle_unprocessed_coupon_requests():
    """
    Goes through all unprocessed rows in the coupon request sheet, creates the requested
    coupons, updates the request sheet to indicate that it was processed, and creates
    the necessary coupon assignment sheets.
    """
    coupon_request_handler = CouponRequestHandler()
    processed_requests = coupon_request_handler.create_coupons_from_sheet()
    coupon_request_handler.write_results_to_sheets(processed_requests)
    return [
        (
            processed_request.row_index,
            processed_request.coupon_req_row.purchase_order_id,
        )
        for processed_request in processed_requests
    ]


@app.task
def handle_incomplete_coupon_assignments():
    """
    Processes all as-yet-incomplete coupon assignment spreadsheets
    """
    coupon_assignment_handler = CouponAssignmentHandler()
    spreadsheets = coupon_assignment_handler.process_assignment_spreadsheets()
    return [(spreadsheet.id, spreadsheet.title) for spreadsheet in spreadsheets]


@app.task
def update_incomplete_assignment_delivery_statuses():
    """
    Fetches all BulkCouponAssignments that have assignments but have not yet finished delivery, then updates the
    delivery status for each depending on what has been sent.
    """
    coupon_assignment_handler = CouponAssignmentHandler()
    updated_assignments = (
        coupon_assignment_handler.update_incomplete_assignment_message_statuses()
    )
    return [
        (bulk_assignment_id, len(product_coupon_assignments))
        for bulk_assignment_id, product_coupon_assignments in updated_assignments.items()
    ]
