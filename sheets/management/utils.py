"""Sheets app management command utils"""
from django.core.management import CommandError

from sheets.coupon_assign_api import CouponAssignmentHandler


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
