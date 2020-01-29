"""Sheets app management command utils"""
from django.core.management import CommandError

from sheets.coupon_assign_api import CouponAssignmentHandler
from sheets.utils import get_enumerated_data_rows
from sheets.coupon_request_api import CouponRequestRow


def get_matching_request_row(coupon_request_handler, row=None, coupon_name=None):
    """
    Gets a matching row from the coupon request Sheet, or raises an exception if the parameters don't match
    exactly one row.

    Args:
        coupon_request_handler (sheets.coupon_request_api.CouponRequestHandler):
        row (int or None): Row index
        coupon_name (str or None): Coupon name

    Returns:
        (int, sheets.coupon_request_api.CouponRequestRow): The row index and an object representation of the matching row
    """
    matching_rows = []
    # Scan the sheet to find rows that match the given conditions
    enumerated_data_rows = get_enumerated_data_rows(
        coupon_request_handler.coupon_request_sheet
    )
    for row_index, row_data in enumerated_data_rows:
        if row and row != row_index:
            continue
        try:
            coupon_req_row = CouponRequestRow.parse_raw_data(row_index, row_data)
        except:  # pylint: disable=bare-except
            continue
        if coupon_name and coupon_name != coupon_req_row.coupon_name:
            continue
        matching_rows.append((row_index, coupon_req_row))

    # Raise exception if no rows match or if multiple rows match
    if len(matching_rows) != 1:
        param_summary = []
        if row:
            param_summary.append("Row number == {}".format(row))
        if coupon_name:
            param_summary.append("Coupon name == {}".format(coupon_name))
        error_text = (
            "Could not find a matching row ({})"
            if len(matching_rows) == 0
            else "Found multiple matching rows ({})"
        )
        raise CommandError(error_text.format(", ".join(param_summary)))

    return matching_rows[0]


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
        "{base_query} and name contains '{title}'".format(
            base_query=CouponAssignmentHandler.ASSIGNMENT_SHEETS_QUERY, title=title
        )
    )
    if len(matching_spreadsheets) != 1:
        raise CommandError(
            "There should be 1 coupon assignment sheet that matches the given title ('{}'). "
            "{} were found.".format(title, len(matching_spreadsheets))
        )
    return matching_spreadsheets[0]
