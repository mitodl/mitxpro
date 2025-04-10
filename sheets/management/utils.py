"""Sheets app management command utils"""

from sheets.coupon_assign_api import CouponAssignmentHandler
from sheets.exceptions import CouponAssignmentError


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
    exact_match_sheets = [
        sheet for sheet in matching_spreadsheets if sheet.title == title
    ]
    if len(exact_match_sheets) != 1:
        raise CouponAssignmentError(
            f"There should be 1 coupon assignment sheet that matches the given title ('{title}'). "  # noqa: EM102
            f"{len(exact_match_sheets)} were found."
        )
    return exact_match_sheets[0]
