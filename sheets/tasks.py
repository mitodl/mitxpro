"""Sheets app tasks"""
import json
import logging
from datetime import datetime, timedelta
from itertools import chain, repeat

from googleapiclient.errors import HttpError
from django.conf import settings
import celery

from ecommerce.models import BulkCouponAssignment
from mitxpro.celery import app
from mitxpro.utils import now_in_utc, case_insensitive_equal
from sheets import (
    api as sheets_api,
    coupon_assign_api,
    coupon_request_api,
    refund_request_api,
    deferral_request_api,
)
from sheets.constants import (
    ASSIGNMENT_SHEET_ENROLLED_STATUS,
    SHEET_TYPE_COUPON_REQUEST,
    SHEET_TYPE_ENROLL_CHANGE,
    SHEET_TYPE_COUPON_ASSIGN,
)
from sheets.utils import AssignmentRowUpdate

log = logging.getLogger(__name__)


@app.task
def handle_unprocessed_coupon_requests():
    """
    Goes through all unprocessed rows in the coupon request sheet, creates the requested
    coupons, updates the request sheet to indicate that it was processed, and creates
    the necessary coupon assignment sheets.
    """
    coupon_request_handler = coupon_request_api.CouponRequestHandler()
    results = coupon_request_handler.process_sheet()
    return results


@app.task
def handle_unprocessed_refund_requests():
    """
    Ensures that all non-legacy rows in the spreadsheet are correctly represented in the database,
    reverses/refunds enrollments if appropriate, updates the spreadsheet to reflect any changes
    made, and returns a summary of those changes.
    """
    refund_request_handler = refund_request_api.RefundRequestHandler()
    results = refund_request_handler.process_sheet()
    return results


@app.task
def handle_unprocessed_deferral_requests():
    """
    Ensures that all non-legacy rows in the spreadsheet are correctly represented in the database,
    defers user enrollments where appropriate, updates the spreadsheet to reflect any changes
    made, and returns a summary of those changes.
    """
    deferral_request_handler = deferral_request_api.DeferralRequestHandler()
    results = deferral_request_handler.process_sheet()
    return results


@app.task
def process_coupon_assignment_sheet(*, file_id, change_date=None):
    """
    Processes a single coupon assignment spreadsheet

    Args:
        file_id (str): The file id of the assignment spreadsheet (visible in the spreadsheet URL)
        change_date (str): ISO-8601-formatted string indicating the datetime when this spreadsheet
            was changed
    """
    change_dt = datetime.fromisoformat(change_date) if change_date else now_in_utc()
    bulk_assignment, _ = BulkCouponAssignment.objects.update_or_create(
        assignment_sheet_id=file_id, defaults=dict(sheet_last_modified_date=change_dt)
    )
    coupon_assignment_handler = coupon_assign_api.CouponAssignmentHandler(
        spreadsheet_id=file_id, bulk_assignment=bulk_assignment
    )
    _, num_created, num_removed = (
        coupon_assignment_handler.process_assignment_spreadsheet()
    )
    return {
        "sheet_id": file_id,
        "assignments_created": num_created,
        "assignments_removed": num_removed,
    }


def _get_scheduled_assignment_task_ids(file_id):
    """
    Gets the task ids for coupon assignment sheet processing tasks that are scheduled in the
    future and have not been executed yet.

    Args:
        file_id (str): The file id of the assignment spreadsheet (visible in the spreadsheet URL)

    Returns:
        list of str: Task ids of currently-scheduled but not-yet-executed tasks to process the
            assignment spreadsheet with the given id
    """
    task_name = process_coupon_assignment_sheet.name
    already_scheduled_task_ids = []
    # If the scheduled task name matches the 'process_coupon_assignment_sheet' task, and it was
    # provided the given file_id as a kwarg, add its task id to the list
    for scheduled in chain.from_iterable(app.control.inspect().scheduled().values()):
        task_metadata = scheduled["request"]
        if task_metadata["name"] == task_name:
            # NOTE: Celery provides metadata for scheduled tasks, and the args/kwargs passed to
            # that task are stored as serialized strings (e.g.: "{'file_id': '123'}"). Here the kwargs
            # are being parsed as JSON after coercing the string to use double-quotes.
            task_kwargs = json.loads(
                task_metadata.get("kwargs", "{}").replace("'", '"')
            )
            if task_kwargs.get("file_id") == file_id:
                already_scheduled_task_ids.append(task_metadata["id"])
    return already_scheduled_task_ids


@app.task
def schedule_coupon_assignment_sheet_handling(file_id):
    """
    Schedules a task to process the assignment sheet with the given file id after cancelling
    any currently-scheduled tasks to process the same sheet. This scheduling/canceling logic
    is intended to minimize unintended assignments in the sheet. If a user has not edited the
    spreadsheet for some period of time, it's assumed that those edits are more likely to be
    considered "final".

    Args:
        file_id (str): The file id of the assignment spreadsheet (visible in the spreadsheet URL)
    """
    # Cancel any already-scheduled tasks to process this particular assignment sheet
    already_scheduled_task_ids = _get_scheduled_assignment_task_ids(file_id)
    if already_scheduled_task_ids:
        log.warning(
            "Canceling existing task(s) for processing coupon assignment sheet (id: '%s')...",
            file_id,
        )
        app.control.revoke(already_scheduled_task_ids)
    # Schedule a new task to process this assignment sheet
    async_result = process_coupon_assignment_sheet.s(
        file_id=file_id, change_date=now_in_utc().isoformat()
    ).apply_async(
        eta=(now_in_utc() + timedelta(seconds=settings.DRIVE_WEBHOOK_ASSIGNMENT_WAIT))
    )
    return async_result.id


@app.task
def update_incomplete_assignment_delivery_statuses():
    """
    Fetches all BulkCouponAssignments that have assignments but have not yet finished delivery, then updates the
    delivery status for each depending on what has been sent.
    """
    bulk_assignments = coupon_assign_api.fetch_update_eligible_bulk_assignments()
    updated_assignments = coupon_assign_api.update_incomplete_assignment_message_statuses(
        bulk_assignments
    )
    return [
        (bulk_assignment_id, len(product_coupon_assignments))
        for bulk_assignment_id, product_coupon_assignments in updated_assignments.items()
    ]


@app.task
def set_assignment_rows_to_enrolled(sheet_update_map):
    """
    Sets the status to "enrolled" (along with status date) for the specified rows
    in a coupon assignment sheet.

    Args:
        sheet_update_map (dict): A dict of dicts that maps assignment sheet id's a dict of coupon codes
            and emails representing the rows that need to be set to enrolled.
            Example: {"sheet-id-1": {"couponcode1": "a@b.com", "couponcode2": "c@d.com"}}

    Returns:
        dict: A summary of execution results. The id of each provided sheet is mapped to the
            number of updated assignments in that sheet.
    """
    now = now_in_utc()
    result_summary = {}
    for sheet_id, assignment_code_email_dict in sheet_update_map.items():
        bulk_assignment = BulkCouponAssignment.objects.get(assignment_sheet_id=sheet_id)
        coupon_assignment_handler = coupon_assign_api.CouponAssignmentHandler(
            spreadsheet_id=sheet_id, bulk_assignment=bulk_assignment
        )
        assignment_rows = coupon_assignment_handler.parsed_rows()
        assignment_row_updates = []
        for assignment_row in assignment_rows:
            if not assignment_row.code or not assignment_row.email:
                continue
            if assignment_row.code in assignment_code_email_dict:
                redeemed_email = assignment_code_email_dict[assignment_row.code]
                alternate_email = (
                    None
                    if case_insensitive_equal(redeemed_email, assignment_row.email)
                    else redeemed_email
                )
                assignment_row_updates.append(
                    AssignmentRowUpdate(
                        row_index=assignment_row.row_index,
                        status=ASSIGNMENT_SHEET_ENROLLED_STATUS,
                        status_date=now,
                        alternate_email=alternate_email,
                    )
                )
        coupon_assignment_handler.update_sheet_with_new_statuses(
            assignment_row_updates, zero_based_index=False
        )
        result_summary[sheet_id] = len(assignment_code_email_dict)
    return result_summary


@app.task(
    autoretry_for=(HttpError,),
    retry_kwargs={"max_retries": 3, "countdown": 5},
    rate_limit="6/m",
)
def renew_file_watch(*, sheet_type, file_id):
    """
    Renews push notifications for changes to a certain spreadsheet via the Google API.
    """
    sheet_metadata = sheets_api.get_sheet_metadata_from_type(sheet_type)
    # These renewal tasks are run on a schedule and ensure that there is an unexpired file watch
    # on each sheet we want to watch. If a file watch was manually created/updated at any
    # point, this task might be run while that file watch is still unexpired. If the file
    # watch renewal was skipped, the task might not run again until after expiration. To
    # avoid that situation, the file watch is always renewed here (force=True).
    file_watch, created, _ = sheets_api.create_or_renew_sheet_file_watch(
        sheet_metadata, force=True, sheet_file_id=file_id
    )
    return {
        "type": sheet_metadata.sheet_type,
        "file_watch_channel_id": getattr(file_watch, "channel_id"),
        "file_watch_file_id": getattr(file_watch, "file_id"),
        "created": created,
    }


@app.task()
def renew_all_file_watches():
    """
    Renews push notifications for changes to all relevant spreadsheets via the Google API.
    """
    assignment_sheet_ids_to_renew = (
        coupon_assign_api.fetch_webhook_eligible_assign_sheet_ids()
    )
    sheet_type_file_id_pairs = chain(
        # The coupon request and enrollment change request sheets are singletons.
        # It's not necessary to specify their file id here.
        [(SHEET_TYPE_COUPON_REQUEST, None)],
        [(SHEET_TYPE_ENROLL_CHANGE, None)],
        zip(
            repeat(SHEET_TYPE_COUPON_ASSIGN, len(assignment_sheet_ids_to_renew)),
            assignment_sheet_ids_to_renew,
        ),
    )
    celery.group(
        *[
            renew_file_watch.s(sheet_type=sheet_type, file_id=file_id)
            for sheet_type, file_id in sheet_type_file_id_pairs
        ]
    )()
