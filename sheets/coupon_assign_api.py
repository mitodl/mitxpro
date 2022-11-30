# pylint: disable=too-many-lines
"""Coupon assignment API"""
import logging
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils.functional import cached_property

import ecommerce.api
from ecommerce.mail_api import send_bulk_enroll_emails
from ecommerce.models import (
    CouponEligibility,
    ProductCouponAssignment,
    BulkCouponAssignment,
)
from mail.api import validate_email_addresses
from mail.constants import MAILGUN_DELIVERED
from mail.exceptions import MultiEmailValidationError
from mitxpro.utils import (
    now_in_utc,
    all_unique,
    partition_to_lists,
    partition,
    item_at_index_or_none,
    case_insensitive_equal,
)
from sheets.api import get_authorized_pygsheets_client, ExpandedSheetsClient
from sheets.constants import (
    ASSIGNMENT_SHEET_PREFIX,
    ASSIGNMENT_MESSAGES_COMPLETED_KEY,
    GOOGLE_API_TRUE_VAL,
    ASSIGNMENT_MESSAGES_COMPLETED_DATE_KEY,
    GOOGLE_DATE_TIME_FORMAT,
    ASSIGNMENT_SHEET_INVALID_STATUS,
    UNSENT_EMAIL_STATUSES,
    ASSIGNMENT_SHEET_ENROLLED_STATUS,
    GOOGLE_SHEET_FIRST_ROW,
    RELEVANT_ASSIGNMENT_EMAIL_EVENTS,
    ASSIGNMENT_SHEET_MAX_AGE_DAYS,
    ASSIGNMENT_SHEET_ASSIGNED_STATUS,
    ASSIGNMENT_SHEET_EMAIL_RETRY_MINUTES,
)
from sheets.exceptions import SheetValidationException, SheetRowParsingException
from sheets.mail_api import get_bulk_assignment_messages
from sheets.utils import (
    format_datetime_for_google_api,
    build_multi_cell_update_request_body,
    format_datetime_for_sheet_formula,
    get_data_rows,
    mailgun_timestamp_to_datetime,
    parse_sheet_datetime_str,
    assign_sheet_metadata,
    AssignmentRowUpdate,
)

log = logging.getLogger(__name__)


class CouponAssignmentRow:
    """Represents a row of a coupon assignment sheet"""

    def __init__(
        self, row_index, code, assignee_email, status, status_date, enrolled_email
    ):  # pylint: disable=too-many-arguments
        self.row_index = row_index
        self.code = code
        self.email = assignee_email
        self.status = status
        self.status_date = status_date
        self.enrolled_email = enrolled_email

    @classmethod
    def parse_raw_data(cls, row_index, raw_row_data):
        """
        Parses raw row data

        Args:
            row_index (int): The row index according to the spreadsheet (not zero-based)
            raw_row_data (list of str): The raw row data

        Returns:
            CouponAssignmentRow: The parsed data row

        Raises:
            SheetRowParsingException: Raised if the row could not be parsed
        """
        try:
            raw_email = item_at_index_or_none(
                raw_row_data, assign_sheet_metadata.ASSIGNED_EMAIL_COL
            )
            email = None if not raw_email else raw_email.lower()
            return cls(
                row_index=row_index,
                code=raw_row_data[assign_sheet_metadata.ENROLL_CODE_COL],
                assignee_email=email,
                status=item_at_index_or_none(
                    raw_row_data, assign_sheet_metadata.STATUS_COL
                ),
                status_date=item_at_index_or_none(
                    raw_row_data, assign_sheet_metadata.STATUS_DATE_COL
                ),
                enrolled_email=item_at_index_or_none(
                    raw_row_data, assign_sheet_metadata.ENROLLED_EMAIL_COL
                ),
            )
        except Exception as exc:
            raise SheetRowParsingException(str(exc)) from exc


class AssignmentStatusMap:
    """
    Manages the relationship between bulk coupon assignments, the rows in their spreadsheets, and the status of
    their coupon assignment messages according to Mailgun
    """

    def __init__(self):
        self._assignment_map = defaultdict(dict)
        self._unassigned_code_map = defaultdict(int)

    def add_assignment_rows(self, bulk_assignment, assignment_rows):
        """
        Adds information about coupon assignment rows from a coupon assignment Sheet

        Args:
            bulk_assignment (BulkCouponAssignment): A BulkCouponAssignment object
            assignment_rows (List[CouponAssignmentRow]): Objects representing rows in an assignment Sheet
        """
        for assignment_row in assignment_rows:
            if assignment_row.email:
                self._assignment_map[bulk_assignment.id][assignment_row.code] = {
                    "row_index": assignment_row.row_index,
                    "email": assignment_row.email,
                    "new_status": None,
                    "new_status_date": None,
                    "existing_status": assignment_row.status,
                    "existing_status_date": parse_sheet_datetime_str(
                        assignment_row.status_date
                    ),
                    "delivery_date": None,
                    "alternate_email": None,
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
        assignment_dict = self._assignment_map.get(bulk_assignment_id, {}).get(code)
        if not assignment_dict:
            return
        # Set a flag if we see a Mailgun event for the delivery of this enrollment code email
        if event_type == MAILGUN_DELIVERED:
            self._assignment_map[bulk_assignment_id][code]["delivery_date"] = event_date
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
            self._assignment_map[bulk_assignment_id][code].update(
                {"new_status": None, "new_status_date": None, "alternate_email": None}
            )
        else:
            alternate_email = (
                recipient_email
                if not case_insensitive_equal(recipient_email, assignment_dict["email"])
                else None
            )
            self._assignment_map[bulk_assignment_id][code].update(
                {
                    "new_status": event_type,
                    "new_status_date": event_date,
                    "alternate_email": alternate_email,
                }
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

    def get_row_update(self, bulk_assignment_id, code):
        """
        Returns an object representing the row of the spreadsheet with the specified coupon code (or None if
        the row does not have a new status)

        Args:
            bulk_assignment_id (int):
            code (str): Coupon code

        Returns:
            AssignmentRowUpdate: An object representing a row of the spreadsheet that needs to be updated (or None if
                the row does not have a new status)
        """
        message_data = self._assignment_map[bulk_assignment_id].get(code)
        return (
            AssignmentRowUpdate(
                row_index=message_data["row_index"],
                status=message_data["new_status"],
                status_date=message_data["new_status_date"],
                alternate_email=message_data["alternate_email"],
            )
            if message_data and message_data["new_status"] is not None
            else None
        )

    def get_row_updates(self, bulk_assignment_id):
        """
        Returns a row object for each coupon assignment that has a new status in the given bulk assignment

        Args:
            bulk_assignment_id (int):

        Returns:
            Iterable[AssignmentRowUpdate]: An iterable of objects representing a row of the spreadsheet that needs
                to be updated.
        """
        return (
            AssignmentRowUpdate(
                row_index=message_data["row_index"],
                status=message_data["new_status"],
                status_date=message_data["new_status_date"],
                alternate_email=message_data["alternate_email"],
            )
            for message_data in self._assignment_map[bulk_assignment_id].values()
            if message_data["new_status"] is not None
        )

    def get_message_delivery_date(self, bulk_assignment_id, code):
        """
        Returns the delivery datetime if an enrollment code email has been sent for the given bulk assignment
        enrollment code.

        Args:
            bulk_assignment_id (int):
            code (str): Coupon code

        Returns:
            datetime.datetime or None: The datetime when the enrollment code message for this code was sent
        """
        message_data = self._assignment_map[bulk_assignment_id].get(code)
        return False if message_data is None else message_data["delivery_date"]

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
            Iterable[int]: BulkCouponAssignment ids
        """
        return self._assignment_map.keys()


def fetch_webhook_eligible_assign_sheet_ids():
    """
    Fetches the file ids of coupon assignment sheets with enough recent activity that they can
    have a file watch created/renewed.

    Returns:
        iterable of str: File ids for assignment sheets that can have a file watch created/renewed
    """
    min_last_activity_date = now_in_utc() - timedelta(
        days=settings.DRIVE_WEBHOOK_ASSIGNMENT_MAX_AGE_DAYS
    )
    return (
        BulkCouponAssignment.objects.exclude(assignment_sheet_id=None)
        .exclude(assignments_started_date=None, created_on__lt=min_last_activity_date)
        .filter(
            message_delivery_completed_date=None,
            last_assignment_date__gte=min_last_activity_date,
        )
        .values_list("assignment_sheet_id", flat=True)
    )


def update_product_coupon_assignments(bulk_assignment_id, assignment_status_map):
    """
    Updates the message fields of product coupon assignments in the database if they have new statuses according
    to the assignment status map.

    Args:
        bulk_assignment_id (int): ID of a BulkCouponAssignment record
        assignment_status_map (AssignmentStatusMap): An object representing the status of messages sent for
            bulk coupon assignments.

    Returns:
        List[ProductCouponAssignment]: Product coupon assignments that were updated
    """
    updated_assignments = []
    product_coupon_assignments = ProductCouponAssignment.objects.filter(
        bulk_assignment_id=bulk_assignment_id
    ).select_related("product_coupon__coupon")
    for assignment in product_coupon_assignments:
        updated_row = assignment_status_map.get_row_update(
            bulk_assignment_id, assignment.product_coupon.coupon.coupon_code
        )
        if updated_row is not None:
            assignment.message_status = updated_row.status
            assignment.message_status_date = updated_row.status_date
            assignment.updated_on = now_in_utc()
            if updated_row.alternate_email is not None:
                assignment.email = updated_row.alternate_email
            updated_assignments.append(assignment)
    ProductCouponAssignment.objects.bulk_update(
        updated_assignments,
        fields=["message_status", "message_status_date", "updated_on"],
    )
    return updated_assignments


def fetch_update_eligible_bulk_assignments():
    """
    Fetches bulk assignment records that should be considered for a message status update

    Returns:
        List[BulkCouponAssignment]: Bulk assignment records that should be considered for a message status update
    """
    now = now_in_utc()
    min_last_assignment_date = now - timedelta(days=ASSIGNMENT_SHEET_MAX_AGE_DAYS)
    # Fetch all bulk assignments that are eligible to have message statuses updated
    return list(
        BulkCouponAssignment.objects.exclude(assignment_sheet_id=None)
        .exclude(assignments_started_date=None)
        .filter(
            message_delivery_completed_date=None,
            last_assignment_date__gt=min_last_assignment_date,
        )
        .order_by("assignments_started_date")
        .prefetch_related("assignments")
    )


def find_bulk_assignment_messages(assignment_status_map, earliest_message_date=None):
    """
    Builds an object that tracks the relationship between bulk coupon assignments, the Sheets they represent,
    and the enrollment email statuses for their individual assignments (e.g.: "delivered", "failed").

    Args:
        assignment_status_map (AssignmentStatusMap): An object representing the status of messages sent for
            bulk coupon assignments.
        earliest_message_date (datetime.datetime): The earliest date that should be considered for Mailgun messages
            that are being queried.

    Returns:
        AssignmentStatusMap: The assignment status map with updated message statuses
    """
    # Loop through bulk coupon assignment emails from the Mailgun API and fill in the
    # delivery or failure date for any matching coupon assignments in the map.
    message_iter = filter(
        lambda bulk_assignment_message: bulk_assignment_message.event
        in RELEVANT_ASSIGNMENT_EMAIL_EVENTS,
        get_bulk_assignment_messages(begin=earliest_message_date, end=now_in_utc()),
    )
    for message in message_iter:
        assignment_status_map.add_potential_event_date(
            message.bulk_assignment_id,
            message.coupon_code,
            recipient_email=message.email,
            event_type=message.event,
            event_date=mailgun_timestamp_to_datetime(message.timestamp),
        )
    return assignment_status_map


def update_incomplete_assignment_message_statuses(bulk_assignments):
    """
    For each bulk assignment record passed in, attempts to update the message status for each individual assignment in
    the database and spreadsheet.

    Args:
        bulk_assignments (List[BulkCouponAssignment]):

    Returns:
        dict: Bulk assignment ids mapped to a list of all product coupon assignments that were updated
    """
    if not bulk_assignments:
        return {}
    # We only need to fetch Mailgun messages as far back as the earliest assignment date of all the bulk assignments.
    earliest_date = bulk_assignments[0].assignments_started_date
    assignment_status_map = AssignmentStatusMap()
    assignment_sheet_handlers = {}
    updated_assignment_map = {}
    # Loop through bulk assignments, load the spreadsheets associated with them, and add the data rows to a map.
    for bulk_assignment in bulk_assignments:
        coupon_assign_handler = CouponAssignmentHandler(
            spreadsheet_id=bulk_assignment.assignment_sheet_id,
            bulk_assignment=bulk_assignment,
        )
        assignment_sheet_handlers[bulk_assignment.id] = coupon_assign_handler
        assignment_status_map.add_assignment_rows(
            bulk_assignment, assignment_rows=coupon_assign_handler.parsed_rows()
        )
    # Query Mailgun for bulk assignment messages and match them to the spreadsheet rows in the map.
    assignment_status_map = find_bulk_assignment_messages(
        assignment_status_map, earliest_message_date=earliest_date
    )
    # For coupon assignment that has a new status according to Mailgun, update the sheets and the database records
    # to reflect those new statuses.
    for bulk_assignment in bulk_assignments:
        coupon_assign_handler = assignment_sheet_handlers[bulk_assignment.id]
        updated_assignment_map[
            bulk_assignment.id
        ] = coupon_assign_handler.update_coupon_delivery_statuses(assignment_status_map)

    return updated_assignment_map


def _validate_assignment_row(parsed_row, assignment, delivery_date):
    """
    Returns information about an update that needs to be made to an out-of-sync assignment sheet row.

    Args:
        parsed_row (CouponAssignmentRow):
        assignment (ProductCouponAssignment):
        delivery_date (Optional[datetime.datetime]): The datetime when the enrollment code email was sent

    Returns:
        Optional[AssignmentRowUpdate]:
            An object indicating a row update that needs to be made to the assignment sheet (or None if no update needs
            to be made)
    """
    if (
        assignment
        and assignment.redeemed is True
        and parsed_row.status != ASSIGNMENT_SHEET_ENROLLED_STATUS
    ):
        # The enrollment code assignment was redeemed, but the spreadsheet row doesn't have
        # the "enrolled" status
        return AssignmentRowUpdate(
            row_index=parsed_row.row_index,
            status=ASSIGNMENT_SHEET_ENROLLED_STATUS,
            status_date=assignment.updated_on,
            alternate_email=assignment.email
            if assignment.original_email is not None
            else None,
        )
    elif assignment and not parsed_row.status:
        # An assignment was created, but the spreadsheet row has no status
        if delivery_date is not None:
            # The enrollment code was emailed, so the row should have a status like "delivered"/"opened"/etc.
            status = MAILGUN_DELIVERED
            status_date = delivery_date
        else:
            # The enrollment code was not emailed, so the row should have the "assigned" status
            status = ASSIGNMENT_SHEET_ASSIGNED_STATUS
            status_date = assignment.created_on
        return AssignmentRowUpdate(
            row_index=parsed_row.row_index,
            status=status,
            status_date=status_date,
            alternate_email=None,
        )
    return None


def _validate_assignment_delivery(parsed_row, assignment, delivery_date):
    """
    Returns True if the email for the given enrollment code was never sent, and it's old enough that we
    would expect it to have been sent.

    Args:
        parsed_row (CouponAssignmentRow):
        assignment (ProductCouponAssignment):
        delivery_date (Optional[datetime.datetime]): The datetime when the enrollment code email was sent

    Returns:
        bool: True if the email for the given enrollment code was never sent, and it's old enough that we
            would expect it to have been sent
    """
    return (
        assignment
        and delivery_date is None
        and parsed_row.status in {None, ASSIGNMENT_SHEET_ASSIGNED_STATUS}
        and (
            assignment.updated_on
            + timedelta(minutes=ASSIGNMENT_SHEET_EMAIL_RETRY_MINUTES)
        )
        < now_in_utc()
    )


class CouponAssignmentHandler:
    """Manages the processing of coupon assignments from Sheet data"""

    ASSIGNMENT_SHEETS_QUERY = (
        '"{folder_id}" in parents and '
        'name contains "{name_prefix}" and '
        "trashed != true".format(
            folder_id=settings.DRIVE_OUTPUT_FOLDER_ID,
            name_prefix=ASSIGNMENT_SHEET_PREFIX,
        )
    )
    INCOMPLETE_SHEETS_QUERY_TERM = 'not appProperties has {{key="{completed_key}" and value="{completed_value}"}}'.format(
        completed_key=ASSIGNMENT_MESSAGES_COMPLETED_KEY,
        completed_value=GOOGLE_API_TRUE_VAL,
    )
    FILE_METADATA_FIELDS = "id, name, modifiedTime, appProperties"

    def __init__(self, spreadsheet_id, bulk_assignment):
        self.pygsheets_client = get_authorized_pygsheets_client()
        self.expanded_sheets_client = ExpandedSheetsClient(self.pygsheets_client)
        self.spreadsheet = self.pygsheets_client.open_by_key(spreadsheet_id)
        self.bulk_assignment = bulk_assignment

    @cached_property
    def worksheet(self):
        """
        Returns the correct Worksheet object for this spreadsheet

        Returns:
             pygsheets.worksheet.Worksheet: The Worksheet object
        """
        # By default, the first worksheet of the spreadsheet should be used
        return self.spreadsheet.sheet1

    def get_enumerated_rows(self):
        """
        Yields enumerated data rows of a spreadsheet (excluding header row(s))

        Yields:
            Tuple[int, List[str]]: Row index (according to the Google Sheet, NOT zero-indexed) paired with the list
                of strings representing the data in each column of the row
        """
        yield from enumerate(
            get_data_rows(self.worksheet, include_trailing_empty=False),
            start=GOOGLE_SHEET_FIRST_ROW + 1,
        )

    def parsed_rows(self):
        """
        Returns a list of parsed row data

        Returns:
            List[CouponAssignmentRow]: List of parsed row data from the sheet
        """
        data_rows = list(get_data_rows(self.worksheet))
        coupon_codes = [row[0] for row in data_rows]
        if not coupon_codes:
            raise SheetValidationException("No data found in coupon assignment Sheet")
        if not all_unique(coupon_codes):
            raise SheetValidationException(
                "All coupon codes in the Sheet must be unique"
            )
        return [
            CouponAssignmentRow.parse_raw_data(
                row_index=row_index, raw_row_data=row_data
            )
            for row_index, row_data in enumerate(
                data_rows, start=assign_sheet_metadata.first_data_row
            )
        ]

    def set_spreadsheet_completed(self, completed_dt=None):
        """
        Sets spreadsheet metadata to indicate that all coupon assignments have been completed and enrollment
        messages have all been sent.

        Args:
            completed_dt (datetime.datetime or None): A datetime indicating completion date (defaults to UTC now)

        Returns:
            dict: Google Drive API results from the files.update endpoint
        """
        date_str = format_datetime_for_google_api(completed_dt or now_in_utc())
        return self.expanded_sheets_client.update_spreadsheet_properties(
            self.spreadsheet.id,
            {
                ASSIGNMENT_MESSAGES_COMPLETED_KEY: GOOGLE_API_TRUE_VAL,
                ASSIGNMENT_MESSAGES_COMPLETED_DATE_KEY: date_str,
            },
        )

    def get_out_of_sync_sheet_data(self):
        """
        Compares assignment sheet rows to enrollment records in the database and message delivery data in Mailgun.
        Returns data for any rows that (a) are out of sync, or (b) were never sent an enrollment code email.

        Returns:
            Tuple[List[AssignmentRowUpdate], List[ProductCouponAssignment]]:
                A tuple containing a list of row updates that need to be made to the assignment sheet, paired with a
                list of assigned product coupons for which an email should have been sent.
        """
        parsed_rows = self.parsed_rows()
        earliest_message_date = self.bulk_assignment.assignments_started_date
        assignment_status_map = AssignmentStatusMap()
        assignment_status_map.add_assignment_rows(
            self.bulk_assignment, assignment_rows=parsed_rows
        )
        assignment_status_map = find_bulk_assignment_messages(
            assignment_status_map, earliest_message_date=earliest_message_date
        )

        assignment_dict = {
            assignment.product_coupon.coupon.coupon_code: assignment
            for assignment in ProductCouponAssignment.objects.filter(
                bulk_assignment=self.bulk_assignment
            ).select_related("product_coupon__coupon")
        }
        row_updates = []
        unsent_assignments = []
        for parsed_row in parsed_rows:
            code = parsed_row.code
            assignment = assignment_dict.get(code, None)
            delivery_date = assignment_status_map.get_message_delivery_date(
                self.bulk_assignment.id, code
            )
            row_update = _validate_assignment_row(parsed_row, assignment, delivery_date)
            if row_update:
                row_updates.append(row_update)
                continue
            needs_enrollment_email = _validate_assignment_delivery(
                parsed_row, assignment, delivery_date
            )
            if needs_enrollment_email:
                unsent_assignments.append(assignment)

        return row_updates, unsent_assignments

    def report_invalid_emails(self, assignment_rows, invalid_emails):
        """
        Updates the status column for each row in an assignment sheet with an invalid email

        Args:
            assignment_rows (iterable of CouponAssignmentRow): The parsed rows in the given assignment sheet
            invalid_emails (set of str): Email addresses that failed validation
        """
        now = now_in_utc()

        row_updates = [
            AssignmentRowUpdate(
                row_index=row.row_index,
                status=ASSIGNMENT_SHEET_INVALID_STATUS,
                status_date=now,
                alternate_email=None,
            )
            for row in assignment_rows
            if row.email in {email.lower() for email in invalid_emails}
        ]
        self.update_sheet_with_new_statuses(
            row_updates=row_updates, zero_based_index=False
        )

    def update_sheet_with_new_statuses(self, row_updates, zero_based_index=False):
        """
        Updates the relevant cells of a coupon assignment Sheet with message statuses and dates.

        Args:
            row_updates (iterable of AssignmentRowUpdate): An iterable of objects representing the possibly-updated
                row data
            zero_based_index (bool): True if the row index is 0-based, False if the row index in 1-based

        Returns:
            list(dict): The bodies of the Google API responses
        """
        index_increment = 0 if zero_based_index else -1
        responses = []
        resp = self.expanded_sheets_client.batch_update_sheet_cells(
            sheet_id=self.spreadsheet.id,
            request_objects=[
                build_multi_cell_update_request_body(
                    row_index=row_update.row_index + index_increment,
                    column_index=assign_sheet_metadata.STATUS_COL,
                    values=[
                        {"userEnteredValue": {"stringValue": row_update.status}},
                        {
                            "userEnteredValue": {
                                "formulaValue": format_datetime_for_sheet_formula(
                                    row_update.status_date.astimezone(
                                        settings.SHEETS_DATE_TIMEZONE
                                    )
                                )
                            },
                            "userEnteredFormat": {
                                "numberFormat": {"type": GOOGLE_DATE_TIME_FORMAT}
                            },
                        },
                    ],
                )
                for row_update in row_updates
            ],
        )
        responses.append(resp)
        alt_email_row_updates = [
            row_update
            for row_update in row_updates
            if row_update.alternate_email is not None
        ]
        if alt_email_row_updates:
            responses.append(
                self.update_sheet_with_alternate_emails(
                    alt_email_row_updates, zero_based_index=zero_based_index
                )
            )
        return responses

    def update_sheet_with_alternate_emails(self, row_updates, zero_based_index=False):
        """
        Updates the relevant cells of a coupon assignment Sheet with emails that users enrolled with (if different from
        the email that was originally entered for the assignment).

        Args:
            row_updates (iterable of AssignmentRowUpdate): An iterable of objects representing rows in the
                spreadsheet that need to be updated
            zero_based_index (bool): True if the row index is 0-based, False if the row index in 1-based

        Returns:
            dict: Google API response body
        """
        index_increment = 0 if zero_based_index else -1
        return self.expanded_sheets_client.batch_update_sheet_cells(
            sheet_id=self.spreadsheet.id,
            request_objects=[
                build_multi_cell_update_request_body(
                    row_index=row_update.row_index + index_increment,
                    column_index=assign_sheet_metadata.ENROLLED_EMAIL_COL,
                    values=[
                        {
                            "userEnteredValue": {
                                "stringValue": row_update.alternate_email
                            }
                        }
                    ],
                )
                for row_update in row_updates
            ],
        )

    def report_assigned_codes(self, assignment_rows, created_assignments):
        """
        Updates the status column for each row in an assignment sheet that was successfully assigned.
        Args:
            assignment_rows (List[CouponAssignmentRow]): The parsed rows in the given assignment sheet
            created_assignments (List[ProductCouponAssignment]): Newly-created product coupon assignments
        """
        row_updates = []
        # Map the code and email pair to the date it was created. This will allow us to find matching assignments and
        # set the status date correctly.
        assignment_creation_dict = {
            (
                assignment.product_coupon.coupon.coupon_code,
                assignment.email.lower(),
            ): assignment.created_on
            for assignment in created_assignments
        }
        for row in assignment_rows:
            if not row.email:
                continue
            code_email_tuple = (row.code, row.email.lower())
            if code_email_tuple in assignment_creation_dict:
                row_updates.append(
                    AssignmentRowUpdate(
                        row_index=row.row_index,
                        status=ASSIGNMENT_SHEET_ASSIGNED_STATUS,
                        status_date=assignment_creation_dict[code_email_tuple],
                        alternate_email=None,
                    )
                )
        self.update_sheet_with_new_statuses(
            row_updates=row_updates, zero_based_index=False
        )

    @classmethod
    def get_desired_coupon_assignments(cls, assignment_rows):
        """
        Parses coupon assignment sheet data to get desired coupon assignments. Only rows with both a non-empty coupon
        code and email are considered.

        Args:
            assignment_rows (iterable of CouponAssignmentRow):

        Returns:
            set of (str, int): A set of emails paired with the product coupon (CouponEligibility)
                id's that should be assigned to them.
        """
        valid_rows = [row for row in assignment_rows if row.code and row.email]
        product_coupon_tuples = CouponEligibility.objects.filter(
            coupon__coupon_code__in=[row.code for row in valid_rows]
        ).values_list("coupon__coupon_code", "id")
        if len(product_coupon_tuples) != len(valid_rows):
            raise SheetValidationException(
                "Mismatch between the number of matching product coupons and the number of coupon "
                "codes listed in the Sheet. There may be an invalid coupon code in the Sheet."
            )
        product_coupon_dict = dict(product_coupon_tuples)
        return set((row.email, product_coupon_dict[row.code]) for row in valid_rows)

    @staticmethod
    def get_assignments_to_create_and_remove(
        existing_assignment_qset, desired_assignments
    ):
        """
        Returns coupon assignments that should be created and existing coupon assignments that should be deleted.

        Args:
            existing_assignment_qset (django.db.models.query.QuerySet): Queryset of existing ProductCouponAssignments
            desired_assignments (set of (str, int)): A set of emails paired with the product coupon (CouponEligibility)
                id's that should be assigned to them. This represents the complete set of assignments that should exist
                in the database, including previously-existing assignments.

        Returns:
            ( set of (str, int), iterable of int ):
                A set of (email, product coupon id) tuples, which indicate new assignments we want to create,
                paired with an iterable of ProductCouponAssignment id's that should be deleted.
        """
        existing_tuple_set = set()
        assignments_to_remove = []
        # Based on existing ProductCouponAssignments, figure out which assignments should be
        # created and which ones do not exist in the desired assignments and should therefore be removed.
        for existing_assignment in existing_assignment_qset.all():
            assignment_tuple = (
                existing_assignment.email.lower(),
                existing_assignment.product_coupon_id,
            )
            if assignment_tuple in desired_assignments:
                existing_tuple_set.add(assignment_tuple)
            else:
                assignments_to_remove.append(existing_assignment)
        tuple_set_to_create = desired_assignments - existing_tuple_set

        if assignments_to_remove:
            # Remove any assignments that have already been redeemed from the list of assignments to remove/delete.
            # If they have been redeemed already, we can't delete them.
            assignments_to_remove, already_redeemed_assignments = partition_to_lists(
                assignments_to_remove, lambda assignment: assignment.redeemed
            )
            if already_redeemed_assignments:
                log.error(
                    "Cannot remove ProductCouponAssignments that are already redeemed - "
                    "The following assignments will not be removed: %s",
                    list(already_redeemed_assignments),
                )
                # If any of the assignments we want to create have the same product coupon as one
                # of these already-redeemed assignments, filter them out and log an error.
                product_coupon_ids = set(
                    assignment.product_coupon_id
                    for assignment in already_redeemed_assignments
                )
                adjusted_create_iter, cannot_create_iter = partition(
                    tuple_set_to_create,
                    lambda assignment_tuple: assignment_tuple[1] in product_coupon_ids,
                )
                tuple_set_to_create = set(adjusted_create_iter)
                if cannot_create_iter:
                    log.error(
                        "Cannot create ProductCouponAssignments for codes that have already been redeemed. "
                        "The following assignments will be not be created: %s",
                        list(cannot_create_iter),
                    )

        return (
            tuple_set_to_create,
            [assignment.id for assignment in assignments_to_remove],
        )

    def update_coupon_delivery_statuses(self, assignment_status_map):
        """
        Updates product coupon assignment records and their corresponding rows in the spreadsheet based on the
        contents of the assigment status map.

        Args:
            assignment_status_map (AssignmentStatusMap): An object representing the status of messages sent for
                bulk coupon assignments.

        Returns:
            List[ProductCouponAssignment]: Product coupon assignment objects that were updated
        """
        bulk_assignment_id = self.bulk_assignment.id

        # Update product coupon assignment statuses and dates in database
        updated_assignments = update_product_coupon_assignments(
            bulk_assignment_id, assignment_status_map
        )

        # Set the BulkCouponAssignment to complete if every coupon has been assigned and
        # all of the coupon messages have been delivered.
        unsent_assignments_exist = ProductCouponAssignment.objects.filter(
            bulk_assignment_id=self.bulk_assignment.id,
            message_status__in=UNSENT_EMAIL_STATUSES,
        ).exists()
        if (
            not unsent_assignments_exist
            and not assignment_status_map.has_unassigned_codes(bulk_assignment_id)
        ):
            now = now_in_utc()
            BulkCouponAssignment.objects.filter(id=bulk_assignment_id).update(
                message_delivery_completed_date=now, updated_on=now
            )
            # Update spreadsheet metadata to reflect the status
            try:
                self.set_spreadsheet_completed(now)
            except Exception:  # pylint: disable=broad-except
                log.exception(
                    "The BulkCouponAssignment has been updated to indicate that message delivery is complete, "
                    "but the request to update spreadsheet properties to indicate this status failed "
                    "(spreadsheet id: %s)",
                    self.spreadsheet.id,
                )

        # Update delivery dates in Sheet
        if assignment_status_map.has_new_statuses(bulk_assignment_id):
            row_updates = assignment_status_map.get_row_updates(bulk_assignment_id)
            self.update_sheet_with_new_statuses(row_updates, zero_based_index=False)

        return updated_assignments

    def process_assignment_spreadsheet(self):  # pylint: disable=too-many-locals
        """
        Ensures that there are product coupon assignments for every filled-in row in a coupon assignment Spreadsheet,
        and sets some metadata to reflect the state of the bulk assignment.

        In more detail:
        1) Gets valid assignment rows from the Sheet
        2) Creates new product coupon assignments, removes assignments that were created before
           but no longer exist in the sheet, and updates bulk assignment status
        3) Send emails to all recipients of newly-created ProductCouponAssignments

        Returns:
            (BulkCouponAssignment, int, int): The bulk coupon assignment created/updated paired with
                the number of ProductCouponAssignments created and the number deleted
        """
        created_assignments, invalid_emails, num_assignments_removed = [], set(), 0
        assignment_rows = self.parsed_rows()

        # Determine what assignments need to be created and deleted
        desired_assignments = self.get_desired_coupon_assignments(assignment_rows)
        if self.bulk_assignment.assignments_started_date:
            existing_assignment_qset = self.bulk_assignment.assignments
            existing_assignment_count = existing_assignment_qset.count()
            assignments_to_create, assignment_ids_to_remove = self.get_assignments_to_create_and_remove(
                existing_assignment_qset, desired_assignments
            )
        else:
            assignments_to_create = desired_assignments
            assignment_ids_to_remove = []
            existing_assignment_count = 0

        # Delete assignments as necessary
        if assignment_ids_to_remove:
            num_assignments_removed, _ = ProductCouponAssignment.objects.filter(
                id__in=assignment_ids_to_remove
            ).delete()
            existing_assignment_count -= num_assignments_removed

        # Validate emails before assignment so we can filter out and report on any bad emails
        try:
            validate_email_addresses(
                (assignment_tuple[0] for assignment_tuple in assignments_to_create)
            )
        except MultiEmailValidationError as exc:
            invalid_emails = exc.invalid_emails
            assignments_to_create = (
                assignment_tuple
                for assignment_tuple in assignments_to_create
                if assignment_tuple[0] not in invalid_emails
            )

        # Create ProductCouponAssignments and update the BulkCouponAssignment record to reflect the progress
        with transaction.atomic():
            bulk_assignment = BulkCouponAssignment.objects.select_for_update().get(
                id=self.bulk_assignment.id
            )
            _, created_assignments = ecommerce.api.bulk_assign_product_coupons(
                assignments_to_create, bulk_assignment=bulk_assignment
            )
            if created_assignments or num_assignments_removed:
                now = now_in_utc()
                if not bulk_assignment.assignments_started_date and created_assignments:
                    bulk_assignment.assignments_started_date = now
                bulk_assignment.last_assignment_date = now
                bulk_assignment.updated_on = now
                bulk_assignment.save()
                self.bulk_assignment = bulk_assignment

        # Send messages if any assignments were created
        if created_assignments:
            send_bulk_enroll_emails(self.bulk_assignment.id, created_assignments)
            self.report_assigned_codes(assignment_rows, created_assignments)

        # Update the sheet if any emails failed validation
        if invalid_emails:
            self.report_invalid_emails(assignment_rows, invalid_emails)

        return self.bulk_assignment, len(created_assignments), num_assignments_removed
