"""Sheets app util functions"""
import datetime
import email.utils
from collections import namedtuple, defaultdict
from urllib.parse import urljoin
import pytz

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
    last_data_column="D",
    num_columns=4,
    column_headers=["Coupon Code", "Email (Assignee)", "Status", "Status Date"],
)
ASSIGNMENT_SHEET_STATUS_COLUMN = 2
AssignmentRow = namedtuple(
    "AssignmentRow", ["row_index", "coupon_code", "email", "status", "status_date"]
)
ProcessedRequest = namedtuple(
    "ProcessedRequest", ["row_index", "coupon_req_row", "request_id"]
)


class AssignmentStatusMap:
    """
    Manages the relationship between bulk coupon assignments, the rows in their spreadsheets, and the status of
    their coupon assignment messages according to Mailgun
    """

    def __init__(self):
        self._assignment_map = defaultdict(dict)
        self._unassigned_code_map = defaultdict(int)
        self._sheet_id_map = {}

    def add_assignment_rows(self, bulk_assignment, assignment_rows):
        """
        Adds information about coupon assignment rows from a coupon assignment Sheet

        Args:
            bulk_assignment (BulkCouponAssignment): A BulkCouponAssignment object
            assignment_rows (iterable of AssignmentRow): Objects representing rows in an assignment Sheet
        """
        self._sheet_id_map[bulk_assignment.id] = bulk_assignment.assignment_sheet_id
        for assignment_row in assignment_rows:
            if assignment_row.email:
                self._assignment_map[bulk_assignment.id][
                    (assignment_row.coupon_code, assignment_row.email)
                ] = {
                    "row_index": assignment_row.row_index,
                    "new_status": None,
                    "new_status_date": None,
                    "existing_status": assignment_row.status,
                }
            else:
                self._unassigned_code_map[bulk_assignment.id] += 1

    def add_potential_event_date(
        self, bulk_assignment_id, code, recipient_email, event_type, event_date
    ):  # pylint: disable=too-many-arguments
        """
        Fills in a status (e.g.: "delivered") and the datetime when that status was logged if the given
        coupon assignment exists in the map, and the status is different from the previous status.
        Does nothing if (a) the bulk assignment id isn't in the map, (b) the code and email don't match any assignment,
        or (c) the assignment already had the given status in the spreadsheet.

        Args:
            bulk_assignment_id (int):
            code (str): Coupon code
            recipient_email (str):
            event_type (str): The event type (e.g.: "delivered", "failed")
            event_date (datetime.datetime): The datetime when the email was delivered for the given coupon assignment
        """
        assignment_dict = self._assignment_map.get(bulk_assignment_id, {}).get(
            (code, recipient_email)
        )
        if not assignment_dict:
            return
        if (
            assignment_dict["existing_status"]
            and event_type == assignment_dict["existing_status"]
        ):
            self._assignment_map[bulk_assignment_id][(code, recipient_email)].update(
                {"new_status": None, "new_status_date": None}
            )
        else:
            self._assignment_map[bulk_assignment_id][(code, recipient_email)].update(
                {"new_status": event_type, "new_status_date": event_date}
            )

    def get_updated_status_and_date(self, bulk_assignment_id, code, recipient_email):
        """
        Returns the new status and status date for the coupon assignment matching the code and email
        in the given bulk assignment

        Args:
            bulk_assignment_id (int):
            code (str): Coupon code
            recipient_email (str):

        Returns:
            (str or None, datetime.datetime or None): The new status paired with the date that
                the status was logged in Mailgun (or (None, None) if the given assignment does not
                have a new status.
        """
        message_data = self._assignment_map[bulk_assignment_id].get(
            (code, recipient_email)
        )
        return (
            (message_data["new_status"], message_data["new_status_date"])
            if message_data
            else (None, None)
        )

    def has_new_statuses(self, bulk_assignment_id):
        """
        Returns True if the given bulk assignment has any individual assignments with a new status

        Args:
            bulk_assignment_id (int):

        Returns:
            bool: True if the given bulk assignment has any individual assignments with a new status
        """
        return any(
            message_data["new_status"] is not None
            for _, message_data in self._assignment_map[bulk_assignment_id].items()
        )

    def get_status_date_rows(self, bulk_assignment_id):
        """
        Returns a row index, status, and status date for each coupon assignment with a new status in the
        given bulk assignment

        Args:
            bulk_assignment_id (int):

        Returns:
            iterable of (int, str, datetime.datetime): An iterable of row indices (indicating the Sheet row) paired
                with new status and the date of that status change
        """
        return (
            (
                message_data["row_index"],
                message_data["new_status"],
                message_data["new_status_date"],
            )
            for message_data in self._assignment_map[bulk_assignment_id].values()
            if message_data["new_status"]
        )

    def get_sheet_id(self, bulk_assignment_id):
        """
        Returns the assignment spreadsheet id associated with the given bulk assignment

        Args:
            bulk_assignment_id (int):

        Returns:
            str: The assignment spreadsheet id
        """
        return self._sheet_id_map[bulk_assignment_id]

    def has_unassigned_codes(self, bulk_assignment_id):
        """
        Returns True if any of the coupon codes in the coupon assignment Sheet have not been assigned an email

        Args:
            bulk_assignment_id (int):

        Returns:
            bool: True if any of the coupon codes in the coupon assignment Sheet have not been assigned an email
        """
        return self._unassigned_code_map[bulk_assignment_id] > 0

    @property
    def bulk_assignment_ids(self):
        """
        Returns all of the bulk assignment ids in the map

        Returns:
            iterable of int: BulkCouponAssignment ids
        """
        return self._assignment_map.keys()


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


def format_datetime_for_google_api(dt):
    """
    String-ifies a datetime value in the format expected by Google APIs

    Args:
        dt (datetime.datetime):

    Returns:
        str: The datetime formatted for use in a Google API request
    """
    return dt.isoformat()


def format_datetime_for_mailgun(dt):
    """
    String-ifies a datetime value in the format expected by the Mailgun API

    Args:
        dt (datetime.datetime):

    Returns:
        str: The datetime formatted for use in a Mailgun API request
    """
    return email.utils.format_datetime(dt)


def format_datetime_for_sheet_formula(dt):
    """
    String-ifies a datetime value in a format that will result in a valid date entry in a Google Sheets cell

    Args:
        dt (datetime.datetime):

    Returns:
        str: The datetime formatted for a Google Sheets cell value
    """
    return f"=DATE({dt.year},{dt.month},{dt.day}) + TIME({dt.hour},{dt.minute},{dt.second})"


def mailgun_timestamp_to_datetime(timestamp):
    """
    Parses a timestamp value from a Mailgun API response as a datetime

    Args:
        timestamp (str): A timestamp value from a Mailgun API response

    Returns:
        datetime.datetime: The parsed timestamp
    """
    return datetime.datetime.fromtimestamp(timestamp, pytz.utc)


def build_multi_cell_update_request_body(row_index, column_index, values):
    """
    Builds a dict for use in the body of a Google Sheets API batch update request

    Args:
        row_index (int): The index of the cell row that should be updated (starting with 0)
        column_index (int): The index of the first cell column that should be updated (starting with 0)
        values (list of dict): The updates to be performed

    Returns:
        dict: A single update request object for use in a Google Sheets API batch update request
    """
    return {
        "updateCells": {
            "range": {
                "sheetId": 0,
                "startRowIndex": row_index,
                "endRowIndex": row_index + 1,
                "startColumnIndex": column_index,
                "endColumnIndex": column_index + len(values),
            },
            "rows": [{"values": values}],
            "fields": "*",
        }
    }
