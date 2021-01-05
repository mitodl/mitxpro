"""Sheets app util functions"""
import datetime
import email.utils
from collections import namedtuple
from urllib.parse import urljoin, quote_plus
from enum import Enum
import pytz

from django.conf import settings
from django.urls import reverse

from mitxpro.utils import matching_item_index
from sheets.constants import (
    GOOGLE_AUTH_URI,
    GOOGLE_TOKEN_URI,
    GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
    ASSIGNMENT_SHEET_PREFIX,
    GOOGLE_SHEET_FIRST_ROW,
    GOOGLE_SERVICE_ACCOUNT_EMAIL_DOMAIN,
    SHEETS_VALUE_REQUEST_PAGE_SIZE,
    SHEET_TYPE_COUPON_REQUEST,
    WORKSHEET_TYPE_REFUND,
    SHEET_TYPE_COUPON_ASSIGN,
    WORKSHEET_TYPE_DEFERRAL,
    SHEET_TYPE_ENROLL_CHANGE,
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


def get_column_letter(column_index):
    """
    Returns the spreadsheet column letter that corresponds to a given index (e.g.: 0 -> 'A', 3 -> 'D')

    Args:
        column_index (int):

    Returns:
        str: The column index expressed as a letter
    """
    if column_index > 25:
        raise ValueError("Cannot generate a column letter past 'Z'")
    uppercase_a_ord = ord("A")
    return chr(column_index + uppercase_a_ord)


class SheetMetadata:
    """Metadata for a type of Google Sheet that this app interacts with"""

    sheet_type = None
    sheet_name = None
    worksheet_type = None
    worksheet_name = None
    first_data_row = None
    non_input_column_indices = set()
    num_columns = 0

    @property
    def form_input_column_indices(self):
        """
        Returns indices of columns that contain data entered by a user in a form

        Returns:
            set: Indices of columns that contain data entered by a user in a form
        """
        return set(range(self.num_columns)).difference(self.non_input_column_indices)

    def handler_url_stub(self, file_id=None):
        """
        Returns the URL that Google should send requests to when a change is made to a watched
        spreadsheet.

        Args:
            file_id (str): (Optional) The id of the spreadsheet as it appears in the spreadsheet's URL.
                If the spreadsheet being watched is a singleton, this isn't necessary.

        Returns:
            str: The URL that Google will send file watch requests to
        """
        params = dict(sheet=quote_plus(self.sheet_type))
        if file_id:
            params["fileId"] = file_id
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        return "{}?{}".format(reverse("handle-watched-sheet-update"), param_str)

    def get_form_input_columns(self, row_data):
        """
        Returns a list of column values for columns that contain data entered by a user in a form
        (i.e.: no auto-generated values, or values entered by this app)

        Args:
            row_data (iterable): Cell values from a row in a sheet

        Returns:
            list: Values for columns that contain data entered by a user in a form
        """
        return [
            col for i, col in enumerate(row_data) if i in self.form_input_column_indices
        ]


class SingletonSheetMetadata(SheetMetadata):
    """
    Metadata for a type of Google Sheet that this app interacts with, and of which only one should exist
    """

    sheet_file_id = None


class CouponRequestSheetMetadata(
    SingletonSheetMetadata
):  # pylint: disable=too-many-instance-attributes
    """Metadata for the coupon request spreadsheet"""

    PURCHASE_ORDER_COL_INDEX = 0
    COUPON_NAME_COL_INDEX = 1
    PROCESSED_COL = settings.SHEETS_REQ_PROCESSED_COL
    ERROR_COL = settings.SHEETS_REQ_ERROR_COL
    SKIP_ROW_COL = ERROR_COL + 1

    def __init__(self):  # pylint: disable=too-many-instance-attributes
        self.sheet_type = SHEET_TYPE_COUPON_REQUEST
        self.sheet_name = "Coupon Request sheet"
        self.first_data_row = GOOGLE_SHEET_FIRST_ROW + 1
        self.non_input_column_indices = settings.SHEETS_REQ_CALCULATED_COLUMNS
        self.num_columns = self.ERROR_COL + 1
        self.sheet_file_id = settings.COUPON_REQUEST_SHEET_ID

        self.PROCESSED_COL_LETTER = get_column_letter(self.PROCESSED_COL)
        self.ERROR_COL_LETTER = get_column_letter(self.ERROR_COL)


class RefundRequestSheetMetadata(
    SingletonSheetMetadata
):  # pylint: disable=too-many-instance-attributes
    """Metadata for the refund request spreadsheet"""

    FORM_RESPONSE_ID_COL = 0

    PROCESSOR_COL = settings.SHEETS_REFUND_PROCESSOR_COL
    COMPLETED_DATE_COL = settings.SHEETS_REFUND_COMPLETED_DATE_COL
    ERROR_COL = settings.SHEETS_REFUND_ERROR_COL
    SKIP_ROW_COL = settings.SHEETS_REFUND_SKIP_ROW_COL

    def __init__(self):
        self.sheet_type = SHEET_TYPE_ENROLL_CHANGE
        self.sheet_name = "Enrollment Change Request sheet"
        self.worksheet_type = WORKSHEET_TYPE_REFUND
        self.worksheet_name = "Refunds"
        self.first_data_row = settings.SHEETS_REFUND_FIRST_ROW
        self.num_columns = self.SKIP_ROW_COL + 1
        self.non_input_column_indices = set(
            # Response ID column
            [self.FORM_RESPONSE_ID_COL]
            +
            # Every column from the finance columns to the end of the row
            list(range(8, self.num_columns))
        )
        self.sheet_file_id = settings.ENROLLMENT_CHANGE_SHEET_ID

        self.PROCESSOR_COL_LETTER = get_column_letter(self.PROCESSOR_COL)
        self.ERROR_COL_LETTER = get_column_letter(self.ERROR_COL)


class DeferralRequestSheetMetadata(
    SingletonSheetMetadata
):  # pylint: disable=too-many-instance-attributes
    """Metadata for the deferral request spreadsheet"""

    FORM_RESPONSE_ID_COL = 0
    PROCESSOR_COL = 7
    COMPLETED_DATE_COL = 8
    ERROR_COL = 9
    SKIP_ROW_COL = 10

    def __init__(self):
        self.sheet_type = SHEET_TYPE_ENROLL_CHANGE
        self.sheet_name = "Enrollment Change Request sheet"
        self.worksheet_type = WORKSHEET_TYPE_DEFERRAL
        self.worksheet_name = "Deferrals"
        self.first_data_row = settings.SHEETS_DEFERRAL_FIRST_ROW
        self.num_columns = self.SKIP_ROW_COL + 1
        self.non_input_column_indices = set(
            # Response ID column
            [self.FORM_RESPONSE_ID_COL]
            +
            # Every column from the finance columns to the end of the row
            list(range(self.PROCESSOR_COL, self.num_columns))
        )
        self.sheet_file_id = settings.ENROLLMENT_CHANGE_SHEET_ID

        self.PROCESSOR_COL_LETTER = get_column_letter(self.PROCESSOR_COL)
        self.ERROR_COL_LETTER = get_column_letter(self.ERROR_COL)


class CouponAssignSheetMetadata(
    SheetMetadata
):  # pylint: disable=too-many-instance-attributes
    """Metadata for a coupon assignment spreadsheet"""

    def __init__(self):
        self.sheet_type = SHEET_TYPE_COUPON_ASSIGN
        self.sheet_name = "Coupon Assignment sheet"
        self.first_data_row = GOOGLE_SHEET_FIRST_ROW + 1
        self.column_headers = [
            "Coupon Code",
            "Email (Assignee)",
            "Status",
            "Status Date",
            "Enrollment URL",
            "Enrolled Email",
        ]
        self.non_input_column_indices = {0, 2, 3}
        self.num_columns = len(self.column_headers)

        self.ENROLL_CODE_COL = matching_item_index(self.column_headers, "Coupon Code")
        self.ASSIGNED_EMAIL_COL = matching_item_index(
            self.column_headers, "Email (Assignee)"
        )
        self.STATUS_COL = matching_item_index(self.column_headers, "Status")
        self.STATUS_DATE_COL = matching_item_index(self.column_headers, "Status Date")
        self.ENROLL_URL_COL = matching_item_index(self.column_headers, "Enrollment URL")
        self.ENROLLED_EMAIL_COL = matching_item_index(
            self.column_headers, "Enrolled Email"
        )
        self.LAST_COL_LETTER = get_column_letter(self.num_columns - 1)


request_sheet_metadata = CouponRequestSheetMetadata()
refund_sheet_metadata = RefundRequestSheetMetadata()
deferral_sheet_metadata = DeferralRequestSheetMetadata()
assign_sheet_metadata = CouponAssignSheetMetadata()


class ResultType(Enum):
    """Enum of possible row results"""

    IGNORED = "ignored"
    FAILED = "failed"
    OUT_OF_SYNC = "out_of_sync"
    PROCESSED = "processed"

    def __lt__(self, other):
        return self.value < other.value  # pylint: disable=comparison-with-callable


RowResult = namedtuple(
    "RowResult", ["row_index", "row_db_record", "row_object", "message", "result_type"]
)
ProcessedRequest = namedtuple(
    "ProcessedRequest", ["row_index", "coupon_req_row", "request_id", "date_processed"]
)
FailedRequest = namedtuple(
    "FailedRequest", ["row_index", "exception", "sheet_error_text"]
)
IgnoredRequest = namedtuple("IgnoredRequest", ["row_index", "coupon_req_row", "reason"])
AssignmentRowUpdate = namedtuple(
    "AssignmentRowUpdate", ["row_index", "status", "status_date", "alternate_email"]
)


def assignment_sheet_file_name(coupon_req_row):
    """
    Generates the filename for a coupon assignment Sheet

    Args:
        coupon_req_row (sheets.coupon_request_api.CouponRequestRow):

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


def get_data_rows_after_start(
    worksheet,
    start_row,
    start_col,
    end_col,
    page_size=SHEETS_VALUE_REQUEST_PAGE_SIZE,
    **kwargs,
):
    """
    Yields the data rows of a spreadsheet starting with a given row and spanning a given column range
    until empty rows are encountered.

    Args:
        worksheet (pygsheets.worksheet.Worksheet): Worksheet object
        start_row (int): Zero-based index of the first row for which you want data returned
        start_col (int): Zero-based index of the start of the column range
        end_col (int):  Zero-based index of the end of the column range
        page_size (int): The number of rows to fetch per individual API request
        kwargs (dict): Option params to pass along to pygsheets.worksheet.Worksheet.get_values

    Yields:
        list of str: List of cell values in a given row
    """
    request_count = 0
    values = []
    while request_count == 0 or (values and len(values) == page_size):
        end_row = start_row + page_size - 1
        values = worksheet.get_values(
            start=(start_row, start_col),
            end=(end_row, end_col),
            include_tailing_empty=True,
            include_tailing_empty_rows=False,
            returnas="matrix",
            **kwargs,
        )
        request_count += 1
        yield from values
        start_row = end_row + 1


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


def clean_sheet_value(value):
    """
    Takes a spreadsheet cell value and returns a cleaned version

    Args:
        value (str): A raw spreadsheet cell value

    Returns:
        str or None: A string with whitespace stripped, or None if the resulting value was an empty string
    """
    stripped = value.strip()
    return None if stripped == "" else stripped


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


def _parse_sheet_date_str(date_str, date_format):
    """
    Parses a string that represents a date/datetime and returns the UTC datetime (or None)

    Args:
        date_str (str): The date/datetime string
        date_format (str): The strptime-compatible format string that the string is expected to match

    Returns:
        datetime.datetime or None: The parsed datetime (in UTC) or None
    """
    if not date_str:
        return None
    dt = datetime.datetime.strptime(date_str, date_format).astimezone(
        settings.SHEETS_DATE_TIMEZONE
    )
    return dt if settings.SHEETS_DATE_TIMEZONE == pytz.UTC else dt.astimezone(pytz.UTC)


def parse_sheet_datetime_str(datetime_str):
    """
    Parses a string that represents a datetime and returns the UTC datetime (or None)

    Args:
        datetime_str (str): The datetime string

    Returns:
        datetime.datetime or None: The parsed datetime (in UTC) or None
    """
    return _parse_sheet_date_str(datetime_str, settings.SHEETS_DATE_FORMAT)


def parse_sheet_date_only_str(date_str):
    """
    Parses a string that represents a date and returns the UTC datetime (or None)

    Args:
        date_str (str): The datetime string

    Returns:
        datetime.datetime or None: The parsed datetime (in UTC) or None
    """
    return _parse_sheet_date_str(date_str, settings.SHEETS_DATE_ONLY_FORMAT)


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
    return datetime.datetime.fromtimestamp(timestamp_in_seconds, pytz.UTC)


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
    return datetime.datetime.fromtimestamp(timestamp, pytz.UTC)


def build_multi_cell_update_request_body(
    row_index, column_index, values, worksheet_id=0
):
    """
    Builds a dict for use in the body of a Google Sheets API batch update request

    Args:
        row_index (int): The index of the cell row that should be updated (starting with 0)
        column_index (int): The index of the first cell column that should be updated (starting with 0)
        values (list of dict): The updates to be performed
        worksheet_id (int):

    Returns:
        dict: A single update request object for use in a Google Sheets API batch update request
    """
    return {
        "updateCells": {
            "range": {
                "sheetId": worksheet_id,
                "startRowIndex": row_index,
                "endRowIndex": row_index + 1,
                "startColumnIndex": column_index,
                "endColumnIndex": column_index + len(values),
            },
            "rows": [{"values": values}],
            "fields": "*",
        }
    }


def build_protected_range_request_body(
    start_row_index,
    num_rows,
    start_col_index,
    num_cols,
    worksheet_id=0,
    warning_only=False,
    description=None,
):  # pylint: disable=too-many-arguments
    """
    Builds a request body that will be sent to the Google Sheets API to create a protected range on a spreadsheet.

    Args:
        start_row_index (int): The zero-based index of the row of the range that will be protected
        num_rows (int): The number of rows that this range will span
        start_col_index (int): The zero-based index of the column of the range that will be protected
        num_cols (int): The number of columns that this range will span
        worksheet_id (int): The worksheet id in the given spreadsheet (the first worksheet id is always 0)
        warning_only (bool): If True, the range will be editable, but will display a warning/confirmation dialog
            before edits are accepted
        description (str or None): An optional description for the protected range

    Returns:
        dict: A request body that will be sent to the Google Sheets API to create a protected range
    """
    extra_params = {} if description is None else {"description": description}
    return {
        "addProtectedRange": {
            "protectedRange": {
                "range": {
                    "sheetId": worksheet_id,
                    "startRowIndex": start_row_index,
                    "endRowIndex": start_row_index + num_rows,
                    "startColumnIndex": start_col_index,
                    "endColumnIndex": start_col_index + num_cols,
                },
                "warningOnly": warning_only,
                **extra_params,
            }
        }
    }


def build_drive_file_email_share_request(file_id, email_to_share):
    """
    Builds the body of a Drive file share request

    Args:
        file_id (str): The file id of the Drive file being shared
        email_to_share (str): The email of the user to whom the file will be shared

    Returns:
        dict: A dictionary of parameters for the body of a share request
    """
    added_kwargs = (
        {"sendNotificationEmail": False}
        if email_to_share.endswith(GOOGLE_SERVICE_ACCOUNT_EMAIL_DOMAIN)
        else {}
    )
    return dict(
        fileId=file_id,
        body={"type": "user", "role": "writer", "emailAddress": email_to_share},
        fields="id",
        supportsTeamDrives=True,
        **added_kwargs,
    )
