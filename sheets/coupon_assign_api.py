"""Coupon assignment API"""
import logging
from collections import defaultdict

from django.conf import settings
from django.db import transaction

import ecommerce.api
from ecommerce.mail_api import send_bulk_enroll_emails
from ecommerce.models import (
    CouponEligibility,
    ProductCouponAssignment,
    BulkCouponAssignment,
)
from mail.api import validate_email_addresses
from mail.constants import (
    MAILGUN_DELIVERED,
    MAILGUN_FAILED,
    MAILGUN_OPENED,
    MAILGUN_CLICKED,
)
from mail.exceptions import MultiEmailValidationError
from mitxpro.utils import (
    now_in_utc,
    all_unique,
    partition_to_lists,
    partition,
    item_at_index_or_none,
)
from sheets.api import get_authorized_pygsheets_client, ExpandedSheetsClient
from sheets.constants import (
    ASSIGNMENT_SHEET_PREFIX,
    ASSIGNMENT_MESSAGES_COMPLETED_KEY,
    GOOGLE_API_TRUE_VAL,
    ASSIGNMENT_MESSAGES_COMPLETED_DATE_KEY,
    GOOGLE_DATE_TIME_FORMAT,
    INVALID_EMAIL_STATUS,
    UNSENT_EMAIL_STATUSES,
    ASSIGNMENT_SHEET_ENROLLED_STATUS,
)
from sheets.exceptions import (
    SheetValidationException,
    SheetUpdateException,
    SheetRowParsingException,
)
from sheets.mail_api import get_bulk_assignment_messages
from sheets.utils import (
    format_datetime_for_google_api,
    build_multi_cell_update_request_body,
    format_datetime_for_sheet_formula,
    get_data_rows,
    google_date_string_to_datetime,
    spreadsheet_repr,
    mailgun_timestamp_to_datetime,
    parse_sheet_datetime_str,
    assign_sheet_metadata,
)

log = logging.getLogger(__name__)


class CouponAssignmentRow:
    """Represents a row of a coupon assignment sheet"""

    def __init__(
        self, row_index, code, assignee_email, status, status_date
    ):  # pylint: disable=too-many-arguments
        self.row_index = row_index
        self.code = code
        self.email = assignee_email
        self.status = status
        self.status_date = status_date

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
            return cls(
                row_index=row_index,
                code=raw_row_data[0],
                assignee_email=item_at_index_or_none(raw_row_data, 1),
                status=item_at_index_or_none(raw_row_data, 2),
                status_date=item_at_index_or_none(raw_row_data, 3),
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
        self._sheet_id_map = {}

    def add_assignment_rows(self, bulk_assignment, assignment_rows):
        """
        Adds information about coupon assignment rows from a coupon assignment Sheet

        Args:
            bulk_assignment (BulkCouponAssignment): A BulkCouponAssignment object
            assignment_rows (iterable of CouponAssignmentRow): Objects representing rows in an assignment Sheet
        """
        self._sheet_id_map[bulk_assignment.id] = bulk_assignment.assignment_sheet_id
        for assignment_row in assignment_rows:
            if assignment_row.email:
                self._assignment_map[bulk_assignment.id][
                    (assignment_row.code, assignment_row.email)
                ] = {
                    "row_index": assignment_row.row_index,
                    "new_status": None,
                    "new_status_date": None,
                    "existing_status": assignment_row.status,
                    "existing_status_date": parse_sheet_datetime_str(
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

    def __init__(self):
        self.pygsheets_client = get_authorized_pygsheets_client()
        self.expanded_sheets_client = ExpandedSheetsClient(self.pygsheets_client)

    def _set_spreadsheet_completed(self, file_id, completed_dt=None):
        """
        Sets spreadsheet metadata to indicate that all coupon assignments have been completed and enrollment
        messages have all been sent.

        Args:
            file_id (str): The spreadsheet ID
            completed_dt (datetime.datetime or None): A datetime indicating completion date (defaults to UTC now)

        Returns:
            dict: Google Drive API results from the files.update endpoint
        """
        date_str = format_datetime_for_google_api(completed_dt or now_in_utc())
        return self.expanded_sheets_client.update_spreadsheet_properties(
            file_id,
            {
                ASSIGNMENT_MESSAGES_COMPLETED_KEY: GOOGLE_API_TRUE_VAL,
                ASSIGNMENT_MESSAGES_COMPLETED_DATE_KEY: date_str,
            },
        )

    def fetch_incomplete_sheet_metadata(self):
        """
        Yields assignment spreadsheet metadata for sheets that indicate that they have not yet been completed
        and should still be considered for processing.

        Yields:
            dict: An metadata dict for an assignment spreadsheet whose keys match the
                `FILE_METADATA_FIELDS` property value
        """
        incomplete_assignment_sheet_metadata = self.expanded_sheets_client.get_metadata_for_matching_files(
            query="{} and {}".format(
                self.ASSIGNMENT_SHEETS_QUERY, self.INCOMPLETE_SHEETS_QUERY_TERM
            ),
            file_fields=self.FILE_METADATA_FIELDS,
        )
        yield from incomplete_assignment_sheet_metadata

    def fetch_assignment_sheet(self, sheet_id):
        """
        Helper method to fetch a Spreadsheet object via pygsheets and return it along with
        the worksheet where coupon assignments are made

        Args:
            sheet_id (str): A coupon assignment spreadsheet id

        Returns:
            (pygsheets.spreadsheet.Spreadsheet, pygsheets.worksheet.Worksheet): A Spreadsheet
                object paired with a Worksheet object
        """
        spreadsheet = self.pygsheets_client.open_by_key(sheet_id)
        return spreadsheet, spreadsheet.sheet1

    def update_sheet_with_new_statuses(
        self, sheet_id, status_date_rows, zero_based_indices=True
    ):
        """
        Updates the relevant cells of a coupon assignment Sheet with message statuses and dates.

        Args:
            sheet_id (str): The spreadsheet id
            status_date_rows (iterable of (int, str, datetime.datetime): An iterable of row indices
                (indicating the Sheet row, zero-based) paired with the message status and the date
                of that status change.
            zero_based_indices (bool): True indicates that the row indices being passed in are zero-based. False
                indicates that the row indices are 1-based and need to be adjusted for the API call.

        Returns:
            dict: Google API response body
        """
        index_adjust = 0 if zero_based_indices else 1
        return self.expanded_sheets_client.batch_update_sheet_cells(
            sheet_id=sheet_id,
            request_objects=[
                build_multi_cell_update_request_body(
                    row_index=row_index - index_adjust,
                    column_index=assign_sheet_metadata.STATUS_COL,
                    values=[
                        {"userEnteredValue": {"stringValue": status}},
                        {
                            "userEnteredValue": {
                                "formulaValue": format_datetime_for_sheet_formula(
                                    status_date.astimezone(
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
                for row_index, status, status_date in status_date_rows
            ],
        )

    def get_sheet_rows(self, worksheet):
        """
        Returns an iterable of raw row data in a coupon assignment sheet with None filled
        in for any empty columns.

        Args:
            worksheet (pygsheets.worksheet.Worksheet): A coupon assignment worksheet

        Returns:
            iterable of (str, str, str, str): A matrix of raw row data from the sheet
        """
        data_rows = list(get_data_rows(worksheet))
        coupon_codes = [row[0] for row in data_rows]
        if not coupon_codes:
            raise SheetValidationException("No data found in coupon assignment Sheet")
        elif not all_unique(coupon_codes):
            raise SheetValidationException(
                "All coupon codes in the Sheet must be unique"
            )
        return (
            CouponAssignmentRow.parse_raw_data(
                row_index=row_index, raw_row_data=row_data
            )
            for row_index, row_data in enumerate(
                data_rows, start=assign_sheet_metadata.first_data_row
            )
        )

    def assignment_sheet_row_iter(self, bulk_assignments):
        """
        Generator for data rows in Sheets associated with bulk assignments

        Args:
            bulk_assignments (iterable of BulkCouponAssignment):

        Yields:
            (BulkCouponAssignment, iterable of (str, str, str, str)): A bulk coupon assignment object paired with a
                matrix of data rows in the coupon assignment Sheet associated with that object
        """
        for bulk_assignment in bulk_assignments:
            _, worksheet = self.fetch_assignment_sheet(
                bulk_assignment.assignment_sheet_id
            )
            yield bulk_assignment, self.get_sheet_rows(worksheet)

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
        existing_assignment_qet, desired_assignments
    ):
        """
        Returns coupon assignments that should be created and existing coupon assignments that should be deleted.

        Args:
            existing_assignment_qet (django.db.models.query.QuerySet): Queryset of existing ProductCouponAssignments
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
        for existing_assignment in existing_assignment_qet.all():
            assignment_tuple = (
                existing_assignment.email,
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

    def report_invalid_emails(self, sheet_id, assignment_rows, invalid_emails):
        """
        Updates the status column for each row in an assignment sheet with an invalid email

        Args:
            sheet_id (str): An assignment spreadsheet id
            assignment_rows (iterable of CouponAssignmentRow): The parsed rows in the given assignment sheet
            invalid_emails (set of str): Email addresses that failed validation
        """
        now = now_in_utc()
        status_date_rows = [
            (row.row_index, INVALID_EMAIL_STATUS, now)
            for row in assignment_rows
            if row.email in invalid_emails
        ]
        self.update_sheet_with_new_statuses(
            sheet_id=sheet_id,
            status_date_rows=status_date_rows,
            zero_based_indices=False,
        )

    def process_assignment_spreadsheet(
        self, worksheet, bulk_assignment, last_modified
    ):  # pylint: disable=too-many-locals
        """
        Ensures that there are product coupon assignments for every filled-in row in a coupon assignment Spreadsheet,
        and sets some metadata to reflect the state of the bulk assignment.

        In more detail:
        1) Creates a bulk assignment record if one doesn't exist
        2) Gets valid assignment rows from the Sheet
        3) Creates new product coupon assignments, removes assignments that were created before
           but no longer exist in the sheet, and updates bulk assignment status
        4) Send emails to all recipients of newly-created ProductCouponAssignments

        Args:
            worksheet (pygsheets.worksheet.Worksheet):
            bulk_assignment (BulkCouponAssignment): The BulkCouponAssignment that is tracking the
                status of the assignments in this worksheet
            last_modified (datetime.datetime): The datetime when the spreadsheet was last modified

        Returns:
            (BulkCouponAssignment, int, int): The bulk coupon assignment created/updated paired with
                the number of ProductCouponAssignments created and the number deleted
        """
        created_assignments, invalid_emails, num_assignments_removed = [], set(), 0
        assignment_rows = list(self.get_sheet_rows(worksheet))

        # Determine what assignments need to be created and deleted
        desired_assignments = self.get_desired_coupon_assignments(assignment_rows)
        if bulk_assignment.assignments_started_date:
            existing_assignment_qet = bulk_assignment.assignments
            existing_assignment_count = existing_assignment_qet.count()
            assignments_to_create, assignment_ids_to_remove = self.get_assignments_to_create_and_remove(
                existing_assignment_qet, desired_assignments
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
            _, created_assignments = ecommerce.api.bulk_assign_product_coupons(
                assignments_to_create, bulk_assignment=bulk_assignment
            )
            bulk_assignment.assignment_sheet_last_modified = last_modified
            if not bulk_assignment.assignments_started_date and created_assignments:
                bulk_assignment.assignments_started_date = now_in_utc()
            bulk_assignment.save()

        # Send messages if any assignments were created
        if created_assignments:
            send_bulk_enroll_emails(bulk_assignment.id, created_assignments)
        # Update the sheet if any emails failed validation
        if invalid_emails:
            self.report_invalid_emails(
                bulk_assignment.assignment_sheet_id, assignment_rows, invalid_emails
            )

        return bulk_assignment, len(created_assignments), num_assignments_removed

    def process_assignment_spreadsheets(self):
        """
        Processes all as-yet-incomplete coupon assignment spreadsheets

        Returns:
            list of (str, str): Spreadsheet ids paired with spreadsheet titles for all successfully-processed
                assignment sheets
        """
        processed = []
        for spreadsheet_metadata in self.fetch_incomplete_sheet_metadata():
            sheet_id = spreadsheet_metadata["id"]
            sheet_last_modified = google_date_string_to_datetime(
                spreadsheet_metadata["modifiedTime"]
            )
            bulk_assignment, created = BulkCouponAssignment.objects.get_or_create(
                assignment_sheet_id=sheet_id,
                defaults=dict(assignment_sheet_last_modified=sheet_last_modified),
            )
            if (
                not created
                and bulk_assignment.assignment_sheet_last_modified
                and bulk_assignment.assignment_sheet_last_modified
                >= sheet_last_modified
            ):
                log.info(
                    "Spreadsheet is unchanged since last scan (%s). Skipping...",
                    spreadsheet_repr(spreadsheet_metadata=spreadsheet_metadata),
                )
                continue

            spreadsheet, worksheet = self.fetch_assignment_sheet(sheet_id)
            log.info("Processing spreadsheet (%s)...", spreadsheet_repr(spreadsheet))
            try:
                self.process_assignment_spreadsheet(
                    worksheet, bulk_assignment, last_modified=sheet_last_modified
                )
            except SheetValidationException:
                log.exception(
                    "Spreadsheet has invalid data for processing - %s",
                    spreadsheet_repr(spreadsheet),
                )
            except SheetUpdateException:
                log.exception(
                    "All relevant coupons have been assigned and messages have been sent, "
                    "but failed to update the spreadsheet properties to indicate status "
                    "- %s",
                    spreadsheet_repr(spreadsheet),
                )
            except:  # pylint: disable=bare-except
                log.exception(
                    "Unexpected error while processing spreadsheet - %s",
                    spreadsheet_repr(spreadsheet),
                )
            else:
                processed.append((spreadsheet.id, spreadsheet.title))
        return processed

    def build_assignment_status_map(self, bulk_assignments, earliest_date=None):
        """
        Builds an object that tracks the relationship between bulk coupon assignments, the Sheets they represent,
        and the enrollment email statuses for their individual assignments (e.g.: "delivered", "failed").

        Args:
            bulk_assignments (iterable of BulkCouponAssignment):
            earliest_date (datetime.datetime or None): The lower date bound for Mailgun messages to search
                for. If None, this will be calculated from the given bulk assignments.

        Returns:
            AssignmentStatusMap: The assignment delivery map
        """
        earliest_date = earliest_date or min(
            assignment.assignments_started_date for assignment in bulk_assignments
        )
        assignment_status_map = AssignmentStatusMap()

        # Initialize the map of coupon assignment deliveries starting with the data in each
        # coupon assignment Sheet.
        for bulk_assignment, assignment_rows in self.assignment_sheet_row_iter(
            bulk_assignments
        ):
            assignment_status_map.add_assignment_rows(bulk_assignment, assignment_rows)

        # Loop through bulk coupon assignment emails from the Mailgun API and fill in the
        # delivery or failure date for any matching coupon assignments in the map.
        relevant_events = {
            MAILGUN_DELIVERED,
            MAILGUN_FAILED,
            MAILGUN_OPENED,
            MAILGUN_CLICKED,
        }
        message_iter = filter(
            lambda bulk_assignment_message: bulk_assignment_message.event
            in relevant_events,
            get_bulk_assignment_messages(begin=earliest_date, end=now_in_utc()),
        )
        for message in message_iter:
            assignment_status_map.add_potential_event_date(
                message.bulk_assignment_id,
                message.coupon_code,
                message.email,
                event_type=message.event,
                event_date=mailgun_timestamp_to_datetime(message.timestamp),
            )

        return assignment_status_map

    def update_coupon_delivery_statuses(self, assignment_status_map):
        """
        Updates the relevant database records and spreadsheet cells depending on the coupon message statuses in the
        assignment status map.

        Args:
            assignment_status_map (AssignmentStatusMap): The assignment status map to use for updating the
                database and Sheet

        Returns:
            dict: Bulk assignment ids mapped to a list of all product coupon assignments that were updated that
                bulk assignment
        """
        updated_assignments = {}
        for bulk_assignment_id in assignment_status_map.bulk_assignment_ids:
            # Update product coupon assignment statuses and dates in database
            updated_assignments[bulk_assignment_id] = []
            product_coupon_assignments = ProductCouponAssignment.objects.filter(
                bulk_assignment_id=bulk_assignment_id
            ).select_related("product_coupon__coupon")
            for assignment in product_coupon_assignments:
                new_status, new_status_date = assignment_status_map.get_new_status_and_date(
                    bulk_assignment_id,
                    assignment.product_coupon.coupon.coupon_code,
                    assignment.email,
                )
                if (
                    new_status
                    and new_status_date
                    and (
                        new_status != assignment.message_status
                        or new_status_date != assignment.message_status_date
                    )
                ):
                    assignment.message_status = new_status
                    assignment.message_status_date = new_status_date
                    assignment.updated_on = now_in_utc()
                    updated_assignments[bulk_assignment_id].append(assignment)
            ProductCouponAssignment.objects.bulk_update(
                updated_assignments[bulk_assignment_id],
                fields=["message_status", "message_status_date", "updated_on"],
            )

            # Set the BulkCouponAssignment to complete if every coupon has been assigned and
            # all of the coupon messages have been delivered.
            spreadsheet_id = assignment_status_map.get_sheet_id(bulk_assignment_id)
            unsent_assignments_exist = any(
                assignment.message_status in UNSENT_EMAIL_STATUSES
                for assignment in product_coupon_assignments
            )
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
                    self._set_spreadsheet_completed(spreadsheet_id, now)
                except Exception:  # pylint: disable=broad-except
                    log.exception(
                        "The BulkCouponAssignment has been updated to indicate that message delivery is complete, "
                        "but the request to update spreadsheet properties to indicate this status failed "
                        "(spreadsheet id: %s)",
                        spreadsheet_id,
                    )

            # Update delivery dates in Sheet
            if assignment_status_map.has_new_statuses(bulk_assignment_id):
                self.update_sheet_with_new_statuses(
                    spreadsheet_id,
                    assignment_status_map.get_status_date_rows(bulk_assignment_id),
                    zero_based_indices=False,
                )

        return updated_assignments

    def update_incomplete_assignment_message_statuses(self):
        """
        Fetches all BulkCouponAssignments that have one or more undelivered coupon assignments, and
        attempts to update the message status for each in the database and spreadsheet.

        Returns:
            dict: Bulk assignment ids mapped to a list of all product coupon assignments that were updated that
                bulk assignment
        """
        bulk_assignments = (
            BulkCouponAssignment.objects.exclude(assignment_sheet_id=None)
            .exclude(assignments_started_date=None)
            .filter(message_delivery_completed_date=None)
            .order_by("assignments_started_date")
            .prefetch_related("assignments")
        )
        if not bulk_assignments.exists():
            return {}
        earliest_date = bulk_assignments[0].assignments_started_date
        assignment_status_map = self.build_assignment_status_map(
            bulk_assignments, earliest_date=earliest_date
        )
        updated_assignments = self.update_coupon_delivery_statuses(
            assignment_status_map
        )
        return updated_assignments
