"""Sheets app util functions"""
import datetime
import email.utils
from collections import namedtuple, defaultdict
from urllib.parse import urljoin
import pytz

from django.conf import settings
from django.urls import reverse

from courses.models import CourseRun, Program
from mitxpro.utils import item_at_index_or_none

from sheets.constants import (
    GOOGLE_AUTH_URI,
    GOOGLE_TOKEN_URI,
    GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
    ASSIGNMENT_SHEET_PREFIX,
    GOOGLE_SHEET_FIRST_ROW,
    ASSIGNMENT_SHEET_ENROLLED_STATUS,
)
from sheets.exceptions import InvalidSheetProductException, SheetRowParsingException


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
    [
        "first_data_row",
        "last_data_column",
        "calculated_column_indices",
        "num_columns",
        "column_headers",
    ],
)
coupon_request_sheet_spec = SpreadsheetSpec(
    first_data_row=GOOGLE_SHEET_FIRST_ROW + 1,
    last_data_column=settings.SHEETS_REQ_ERROR_COL_LETTER,
    calculated_column_indices={
        settings.SHEETS_REQ_PROCESSED_COL,
        settings.SHEETS_REQ_ERROR_COL,
    },
    num_columns=settings.SHEETS_REQ_ERROR_COL,
    column_headers=[],
)
coupon_assign_sheet_spec = SpreadsheetSpec(
    first_data_row=GOOGLE_SHEET_FIRST_ROW + 1,
    last_data_column="D",
    calculated_column_indices={0, 2, 3},
    num_columns=4,
    column_headers=["Coupon Code", "Email (Assignee)", "Status", "Status Date"],
)
ASSIGNMENT_SHEET_STATUS_COLUMN = next(
    (
        i
        for i, header in enumerate(coupon_assign_sheet_spec.column_headers)
        if header == "Status"
    )
)
ProcessedRequest = namedtuple(
    "ProcessedRequest", ["row_index", "coupon_req_row", "request_id", "date_processed"]
)
FailedRequest = namedtuple(
    "FailedRequest", ["row_index", "exception", "sheet_error_text"]
)
IgnoredRequest = namedtuple("IgnoredRequest", ["row_index", "coupon_req_row", "reason"])
AssignmentRow = namedtuple(
    "AssignmentRow", ["row_index", "coupon_code", "email", "status", "status_date"]
)


class CouponRequestRow:  # pylint: disable=too-many-instance-attributes
    """Represents a row of a coupon request sheet"""

    PURCHASE_ORDER_COL_INDEX = 0

    def __init__(
        self,
        row_index,
        purchase_order_id,
        coupon_name,
        num_codes,
        product_text_id,
        company_name,
        activation,
        expiration,
        date_processed,
        error,
    ):  # pylint: disable=too-many-arguments
        self.row_index = row_index
        self.purchase_order_id = purchase_order_id
        self.coupon_name = coupon_name
        self.num_codes = num_codes
        self.product_text_id = product_text_id
        self.company_name = company_name
        self.activation = activation
        self.expiration = expiration
        self.date_processed = date_processed
        self.error = error

    @classmethod
    def parse_raw_data(cls, row_index, raw_row_data):
        """
        Parses raw row data

        Args:
            row_index (int): The row index according to the spreadsheet (not zero-based)
            raw_row_data (list of str): The raw row data

        Returns:
            CouponRequestRow: The parsed data row

        Raises:
            SheetRowParsingException: Raised if the row could not be parsed
        """
        try:
            return cls(
                row_index=row_index,
                purchase_order_id=raw_row_data[cls.PURCHASE_ORDER_COL_INDEX].strip(),
                coupon_name=raw_row_data[1].strip(),
                num_codes=int(raw_row_data[2]),
                product_text_id=raw_row_data[3].strip(),
                company_name=raw_row_data[4],
                activation=parse_sheet_date_str(item_at_index_or_none(raw_row_data, 5)),
                expiration=parse_sheet_date_str(item_at_index_or_none(raw_row_data, 6)),
                date_processed=parse_sheet_date_str(
                    item_at_index_or_none(
                        raw_row_data, settings.SHEETS_REQ_PROCESSED_COL
                    )
                ),
                error=item_at_index_or_none(
                    raw_row_data, settings.SHEETS_REQ_ERROR_COL
                ),
            )
        except Exception as exc:
            raise SheetRowParsingException from exc

    @classmethod
    def get_user_input_columns(cls, raw_row_data):
        """
        Returns a list of column data that were entered via user input (as opposed to
        calculated columns that the user does not control)

        Args:
            raw_row_data (iterable of str): The raw row data

        Returns:
            list of str: The row data containing only columns with user-entered values
        """
        return [
            col
            for i, col in enumerate(raw_row_data)
            if i not in coupon_request_sheet_spec.calculated_column_indices
        ]

    def get_product_id(self):
        """
        Gets the id for the most recently-created product associated with the CourseRun/Program indicated
        by this row.

        Returns:
            int: The most recently-created product ID for the object indicated by the text ID in the spreadsheet
        """
        for product_object_cls in [CourseRun, Program]:
            product_object = (
                product_object_cls.objects.live()
                .with_text_id(self.product_text_id)
                .prefetch_related("products")
                .first()
            )
            if product_object:
                break
        product = (
            None
            if not product_object
            else product_object.products.order_by("-created_on").first()
        )
        if not product_object:
            raise InvalidSheetProductException(
                "Could not find a CourseRun or Program with text id '%s'"
                % self.product_text_id
            )
        elif not product:
            raise InvalidSheetProductException(
                "No Products associated with %s" % str(product_object)
            )
        return product.id


def assignment_sheet_file_name(coupon_req_row):
    """
    Generates the filename for a coupon assignment Sheet

    Args:
        coupon_req_row (CouponRequestRow):

    Returns:
        str: File name for a coupon assignment Sheet
    """
    return " - ".join(
        [
            ASSIGNMENT_SHEET_PREFIX,
            coupon_req_row.company_name,
            coupon_req_row.purchase_order_id,
            coupon_req_row.product_text_id,
        ]
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
                    "existing_status_date": parse_sheet_date_str(
                        assignment_row.status_date
                    ),
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
        # The "enrolled" status is set by the app when a user redeems a bulk enrollment coupon
        # and is considered the end of the bulk enrollment flow. It should not be overwritten by any
        # other status.
        if assignment_dict["existing_status"] == ASSIGNMENT_SHEET_ENROLLED_STATUS:
            return

        if (
            assignment_dict["existing_status"]
            and assignment_dict["existing_status_date"]
            and event_type == assignment_dict["existing_status"]
            and event_date == assignment_dict["existing_status_date"]
        ):
            self._assignment_map[bulk_assignment_id][(code, recipient_email)].update(
                {"new_status": None, "new_status_date": None}
            )
        else:
            self._assignment_map[bulk_assignment_id][(code, recipient_email)].update(
                {"new_status": event_type, "new_status_date": event_date}
            )

    def get_new_status_and_date(self, bulk_assignment_id, code, recipient_email):
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


def get_data_rows(worksheet, include_trailing_empty=False):
    """
    Yields the data rows of a spreadsheet that has a header row

    Args:
        worksheet (pygsheets.worksheet.Worksheet): Worksheet object
        include_trailing_empty (bool): Whether to include empty trailing cells/values after last non-zero value

    Yields:
        list of str: List of cell values in a given row
    """
    row_iter = iter(
        worksheet.get_all_values(
            # These param names are a typo in the pygsheets library
            include_tailing_empty=include_trailing_empty,
            include_tailing_empty_rows=False,
        )
    )
    try:
        # Skip header row
        next(row_iter)
    except StopIteration:
        return
    yield from row_iter


def get_enumerated_data_rows(
    worksheet, limit_row_index=None, include_trailing_empty=False
):
    """
    Yields enumerated data rows of a spreadsheet that has a header row (with an option to limit the results
    by row index)

    Args:
        worksheet (pygsheets.worksheet.Worksheet): Worksheet object
        limit_row_index (int or None): The row index of the specific data row that
            should be used. If None, the iterable returned will include all rows.
        include_trailing_empty (bool): Whether to include empty trailing cells/values after last non-zero value

    Yields:
        (int, list of str): Row index (according to the Google Sheet, NOT zero-indexed) paired with the list
            of strings representing the data in each column of the row
    """
    enumerated_data_rows = enumerate(
        get_data_rows(worksheet, include_trailing_empty=include_trailing_empty),
        start=GOOGLE_SHEET_FIRST_ROW + 1,
    )
    if limit_row_index:
        yield from (
            (index, row)
            for index, row in enumerated_data_rows
            if index == limit_row_index
        )
    else:
        yield from enumerated_data_rows


def spreadsheet_repr(spreadsheet=None, spreadsheet_metadata=None):
    """
    Returns a simple string representation of a Spreadsheet object

    Args:
        spreadsheet (pygsheets.spreadsheet.Spreadsheet or None):
        spreadsheet_metadata (dict or None): A dict of spreadsheet metadata

    Returns:
        str: String representation of the spreadsheet
    """
    if spreadsheet:
        sheet_id, title = spreadsheet.id, spreadsheet.title
    elif spreadsheet_metadata:
        sheet_id, title = spreadsheet_metadata["id"], spreadsheet_metadata["name"]
    else:
        sheet_id, title = None, None
    if not sheet_id or not title:
        raise ValueError("Invalid spreadsheet/metadata provided")
    return "'{}', id: {}".format(title, sheet_id)


def format_datetime_for_google_api(dt):
    """
    String-ifies a datetime value in the format expected by Google APIs

    Args:
        dt (datetime.datetime):

    Returns:
        str: The datetime formatted for use in a Google API request
    """
    return dt.isoformat()


def format_datetime_for_google_timestamp(dt):
    """
    Formats a datetime for use in a Google API request that expects a timestamp
    (e.g.: file watch expiration – https://developers.google.com/drive/api/v3/reference/files/watch#request-body)

    Args:
        dt (datetime.datetime):

    Returns:
        int: The datetime formatted as a timestamp for use in a Google API request
    """
    # Google expects the timestamp to be in milliseconds, not seconds, hence the '* 1000'
    return int(dt.timestamp() * 1000)


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


def parse_sheet_date_str(date_str):
    """
    Parses a string that represents a datetime and returns the UTC datetime (or None)

    Args:
        date_str (str): The datetime string

    Returns:
        datetime.datetime or None: The parsed datetime (in UTC) or None
    """
    if not date_str:
        return None

    dt = datetime.datetime.strptime(date_str, settings.SHEETS_DATE_FORMAT).astimezone(
        settings.SHEETS_DATE_TIMEZONE
    )
    return dt if settings.SHEETS_DATE_TIMEZONE == pytz.UTC else dt.astimezone(pytz.UTC)


def google_timestamp_to_datetime(google_timestamp):
    """
    Parses a timestamp value from a Google API response as a normal datetime (UTC)

    Args:
        google_timestamp (str or int): A timestamp value from a Google API response

    Returns:
        datetime.datetime: The parsed timestamp with UTC timezone
    """
    # Google timestamps are expressed in milliseconds, hence the '/ 1000'
    timestamp_in_seconds = int(google_timestamp) / 1000
    return datetime.datetime.fromtimestamp(timestamp_in_seconds, pytz.utc)


def google_date_string_to_datetime(google_date_str):
    """
    Parses a datetime string value from a Google API response as a normal datetime (UTC)

    Args:
        google_date_str (str): A datetime string value from a Google API response

    Returns:
        datetime.datetime: The parsed timestamp with UTC timezone
    """
    return datetime.datetime.strptime(
        google_date_str, "%Y-%m-%dT%H:%M:%S.%fZ"
    ).astimezone(pytz.UTC)


def mailgun_timestamp_to_datetime(timestamp):
    """
    Parses a timestamp value from a Mailgun API response as a datetime

    Args:
        timestamp (float): A timestamp value from a Mailgun API response

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
