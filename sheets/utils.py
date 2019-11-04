"""Sheets app util functions"""
from collections import namedtuple
from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse

from sheets.constants import (
    GOOGLE_AUTH_URI,
    GOOGLE_TOKEN_URI,
    GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
)


def generate_google_client_config():
    """Helper method to generate Google client config based on app settings"""
    return {
        "web": {
            "client_id": settings.DRIVE_CLIENT_ID,
            "client_secret": settings.DRIVE_CLIENT_SECRET,
            "project_id": settings.DRIVE_API_PROJECT_ID,
            "redirect_uris": [
                urljoin(settings.SITE_BASE_URL, reverse("complete-google-auth"))
            ],
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_TOKEN_URI,
            "auth_provider_x509_cert_url": GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
        }
    }


SpreadsheetSpec = namedtuple(
    "SpreadsheetSpec",
    ["first_data_row", "last_data_column", "num_columns", "column_headers"],
)
coupon_request_sheet_spec = SpreadsheetSpec(
    first_data_row=2, last_data_column="I", num_columns=9, column_headers=[]
)
coupon_assign_sheet_spec = SpreadsheetSpec(
    first_data_row=2,
    last_data_column="B",
    num_columns=2,
    column_headers=["Coupon Code", "Email (Assignee)"],
)
ProcessedRequest = namedtuple(
    "ProcessedRequest", ["row_index", "coupon_req_row", "request_id"]
)


def get_data_rows(worksheet, include_tailing_empty=False):
    """
    Yields the data rows of a spreadsheet that has a header row

    Args:
        worksheet (pygsheets.worksheet.Worksheet): Worksheet object

    Yields:
        list of str: List of cell values in a given row
    """
    row_iter = iter(
        worksheet.get_all_values(
            include_tailing_empty=include_tailing_empty,
            include_tailing_empty_rows=False,
        )
    )
    try:
        # Skip header row
        next(row_iter)
    except StopIteration:
        return
    yield from row_iter


def spreadsheet_repr(spreadsheet):
    """
    Returns a simple string representation of a Spreadsheet object

    Args:
        spreadsheet (pygsheets.spreadsheet.Spreadsheet):

    Returns:
        str: String representation of the spreadsheet
    """
    return "'{}', id: {}".format(spreadsheet.title, spreadsheet.id)


def format_date(dt):
    """
    String-ifies a datetime value in the format expected by Google APIs

    Args:
        dt (datetime.datetime):

    Returns:
        str: The datetime formatted for use in a Google API request
    """
    return dt.isoformat()
