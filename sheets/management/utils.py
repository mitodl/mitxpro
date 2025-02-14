"""Sheets app management command utils"""

from sheets.coupon_assign_api import CouponAssignmentHandler
from sheets.exceptions import CouponAssignmentError
from sheets.api import ExpandedSheetsClient, get_authorized_pygsheets_client
from sheets.utils import google_date_string_to_datetime, spreadsheet_repr
from ecommerce.models import BulkCouponAssignment

def get_assignment_spreadsheet_by_title(pygsheets_client, title):
    """
    Fetches a coupon assignment spreadsheet object that matches the full or partial title provided.
    Raises an exception if the given title doesn't match exactly one spreadsheet in the bulk
    assignment Drive folder.

    Args:
        pygsheets_client (pygsheets.client.Client): An authorized pygsheets Client object
        title (str): A full or partial spreadsheet title

    Returns:
        pygsheets.spreadsheet.Spreadsheet: A pygsheets spreadsheet object
    """
    matching_spreadsheets = pygsheets_client.open_all(
        "{base_query} and name contains '{title}'".format(  # noqa: UP032
            base_query=CouponAssignmentHandler.ASSIGNMENT_SHEETS_QUERY, title=title
        )
    )
    if len(matching_spreadsheets) != 1:
        raise CouponAssignmentError(
            f"There should be 1 coupon assignment sheet that matches the given title ('{title}'). "  # noqa: EM102
            f"{len(matching_spreadsheets)} were found."
        )
    return matching_spreadsheets[0]


def assign_coupons_from_spreadsheet(use_sheet_id: bool, value: str, force: bool = False):
    """
    Fetches and processes a coupon assignment spreadsheet using either the sheet ID or title.

    Args:
        use_sheet_id (bool): If True, 'value' represents the spreadsheet ID; otherwise, it represents the title.
        value (str): The spreadsheet ID or title.

    Returns:
        dict: A dictionary containing the result of the processing.
    """

    if not value:
        raise CouponAssignmentError("Spreadsheet identifier (ID or Title) is required.")
    
    pygsheets_client = get_authorized_pygsheets_client()

    # Fetch the correct spreadsheet
    if use_sheet_id:
        spreadsheet = pygsheets_client.open_by_key(value)
    else:
        spreadsheet = get_assignment_spreadsheet_by_title(pygsheets_client, value)

    expanded_sheets_client = ExpandedSheetsClient(pygsheets_client)
    metadata = expanded_sheets_client.get_drive_file_metadata(
        file_id=spreadsheet.id, fields="modifiedTime"
    )
    sheet_last_modified = google_date_string_to_datetime(metadata["modifiedTime"])

    bulk_assignment, created = BulkCouponAssignment.objects.get_or_create(
        assignment_sheet_id=spreadsheet.id
    )

    if (
        bulk_assignment.sheet_last_modified_date
        and sheet_last_modified <= bulk_assignment.sheet_last_modified_date
        and not force
    ):
        raise CouponAssignmentError(
            f"Spreadsheet is unchanged since last processed ({spreadsheet_repr(spreadsheet)}, last modified: {sheet_last_modified.isoformat()})."
        )

    coupon_assignment_handler = CouponAssignmentHandler(
        spreadsheet_id=spreadsheet.id, bulk_assignment=bulk_assignment
    )

    bulk_assignment, num_created, num_removed = coupon_assignment_handler.process_assignment_spreadsheet()
    bulk_assignment.sheet_last_modified_date = sheet_last_modified
    bulk_assignment.save()

    return spreadsheet_repr(spreadsheet), num_created, num_removed, bulk_assignment.id
