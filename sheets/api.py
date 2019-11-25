"""API for the Sheets app"""
import os
import json
import datetime
from decimal import Decimal
import pickle
import logging
from urllib.parse import urljoin

from django.conf import settings
from django.db import transaction
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

# NOTE: Due to an unresolved bug (https://github.com/PyCQA/pylint/issues/2108), the
# `google` package (and other packages without an __init__.py file) will break pylint.
# The `disable-all` rules are here until that bug is fixed.
from google.oauth2.credentials import Credentials  # pylint: disable-all
from google.oauth2.service_account import (
    Credentials as ServiceAccountCredentials,
)  # pylint: disable-all
from google.auth.transport.requests import Request  # pylint: disable-all
import pygsheets

from ecommerce.api import create_coupons, bulk_assign_product_coupons
from ecommerce.mail_api import send_bulk_enroll_emails
from ecommerce.models import (
    Company,
    CouponPaymentVersion,
    Coupon,
    BulkCouponAssignment,
    CouponEligibility,
    ProductCouponAssignment,
)
from mail.constants import (
    MAILGUN_DELIVERED,
    MAILGUN_FAILED,
    MAILGUN_OPENED,
    MAILGUN_CLICKED,
)
from mitxpro.utils import (
    now_in_utc,
    item_at_index_or_none,
    all_unique,
    partition,
    partition_to_lists,
)
from sheets.mail_api import get_bulk_assignment_messages
from sheets.models import CouponGenerationRequest, GoogleApiAuth
from sheets.constants import (
    GOOGLE_TOKEN_URI,
    REQUIRED_GOOGLE_API_SCOPES,
    ASSIGNMENT_MESSAGES_COMPLETED_KEY,
    ASSIGNMENT_MESSAGES_COMPLETED_DATE_KEY,
    ASSIGNMENT_SHEET_PREFIX,
    GOOGLE_API_TRUE_VAL,
    GOOGLE_SERVICE_ACCOUNT_EMAIL_DOMAIN,
    GOOGLE_DATE_TIME_FORMAT,
    GOOGLE_API_FILE_WATCH_KIND,
    GOOGLE_API_NOTIFICATION_TYPE,
)
from sheets.utils import (
    coupon_request_sheet_spec,
    coupon_assign_sheet_spec,
    ProcessedRequest,
    get_data_rows,
    spreadsheet_repr,
    format_datetime_for_google_api,
    mailgun_timestamp_to_datetime,
    build_multi_cell_update_request_body,
    AssignmentStatusMap,
    AssignmentRow,
    ASSIGNMENT_SHEET_STATUS_COLUMN,
    format_datetime_for_sheet_formula,
    CouponRequestRow,
    assignment_sheet_file_name,
)
from sheets.exceptions import SheetValidationException, SheetUpdateException

log = logging.getLogger(__name__)

BULK_PURCHASE_DEFAULTS = dict(amount=Decimal("1.0"), automatic=False)
DEFAULT_GOOGLE_EXPIRE_TIMEDELTA = dict(minutes=60)
DEV_TOKEN_PATH = "localdev/google.token"


def get_google_creds_from_pickled_token_file(token_file_path):
    """
    Helper method to get valid credentials from a local token file (and refresh as necessary).
    For dev use only.
    """
    with open(token_file_path, "rb") as f:
        creds = pickle.loads(f.read())
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file_path, "wb") as token:
            pickle.dump(creds, token)
    if not creds:
        raise ImproperlyConfigured("Local token file credentials are empty")
    if not creds.valid:
        raise ImproperlyConfigured("Local token file credentials are invalid")
    return creds


def get_credentials():
    """
    Gets valid Google API client credentials

    Returns:
        google.oauth2.credentials.Credentials: Credentials to be used by the Google Drive client/pygsheets/etc.

    Raises:
        ImproperlyConfigured: Raised if no credentials have been configured
    """
    if settings.DRIVE_SERVICE_ACCOUNT_CREDS:
        is_sharing_to_service_account = any(
            email
            for email in settings.SHEETS_ADMIN_EMAILS
            if GOOGLE_SERVICE_ACCOUNT_EMAIL_DOMAIN in email
        )
        if not is_sharing_to_service_account:
            raise ImproperlyConfigured(
                "If Service Account auth is being used, the SHEETS_ADMIN_EMAILS setting must "
                "include a Service Account email for spreadsheet updates/creation to work. "
                "Add the Service Account email to that setting, or remove the DRIVE_SERVICE_ACCOUNT_CREDS "
                "setting and use a different auth method."
            )
        return ServiceAccountCredentials.from_service_account_info(
            json.loads(settings.DRIVE_SERVICE_ACCOUNT_CREDS),
            scopes=REQUIRED_GOOGLE_API_SCOPES,
        )
    google_api_auth = GoogleApiAuth.objects.order_by("-updated_on").first()
    if google_api_auth:
        creds = Credentials(
            token=google_api_auth.access_token,
            refresh_token=google_api_auth.refresh_token,
            token_uri=GOOGLE_TOKEN_URI,
            client_id=settings.DRIVE_CLIENT_ID,
            client_secret=settings.DRIVE_CLIENT_SECRET,
            scopes=REQUIRED_GOOGLE_API_SCOPES,
        )
        # Proactively refresh if necessary
        needs_refresh = (
            creds.expired
            if creds.expiry
            else google_api_auth.updated_on
            < (now_in_utc() - datetime.timedelta(**DEFAULT_GOOGLE_EXPIRE_TIMEDELTA))
        )
        if needs_refresh:
            log.info("Refreshing GoogleApiAuth credentials...")
            creds.refresh(Request())
            GoogleApiAuth.objects.filter(id=google_api_auth.id).update(
                access_token=creds.token, updated_on=now_in_utc()
            )
        return creds
    # (For local development use only) You can use a locally-created token for auth.
    # This token can be created by following the Google API Python quickstart guide:
    # https://developers.google.com/sheets/api/quickstart/python.
    # A script with more helpful options than the one in that guide can be found here:
    # https://gist.github.com/gsidebo/b87abaafda3e79186c1e5f7f964074ab
    if settings.ENVIRONMENT == "dev":
        token_file_path = os.path.join(settings.BASE_DIR, DEV_TOKEN_PATH)
        if os.path.exists(token_file_path):
            return get_google_creds_from_pickled_token_file(token_file_path)
    raise ImproperlyConfigured("Authorization with Google has not been completed.")


def get_authorized_pygsheets_client():
    """
    Instantiates a pygsheets Client and authorizes it with the proper credentials.

    Returns:
        pygsheets.client.Client: The authorized Client object
    """
    credentials = get_credentials()
    pygsheets_client = pygsheets.authorize(custom_credentials=credentials)
    if settings.DRIVE_SHARED_ID:
        pygsheets_client.drive.enable_team_drive(team_drive_id=settings.DRIVE_SHARED_ID)
    return pygsheets_client


class ExpandedSheetsClient:
    """
    Helper class that executes some Drive/Sheets API requests that pygsheets doesn't directly support
    """

    def __init__(self, pygsheets_client):
        """
        Args:
            pygsheets_client (pygsheets.client.Client): An authorized pygsheets client
        """
        self.pygsheets_client = pygsheets_client
        self.supports_team_drives = bool(settings.DRIVE_SHARED_ID)

    def update_spreadsheet_properties(self, file_id, property_dict):
        """
        Sets metadata properties on the spreadsheet, which can then be
        included in queries.

        Args:
            file_id (str): The spreadsheet ID
            property_dict (dict): Dict of properties to set

        Returns:
            dict: Google Drive API response to the files.update request
        """
        return (
            self.pygsheets_client.drive.service.files()
            .update(
                fileId=file_id,
                body={"appProperties": property_dict},
                supportsTeamDrives=self.supports_team_drives,
            )
            .execute()
        )

    def get_sheet_properties(self, file_id):
        """
        Helper method to fetch the dictionary of appProperties for the given spreadsheet by its
        file ID. The Google Sheets API doesn't know about this data. Only the Drive API can access
        it, hence this helper method.

        Args:
            file_id (str): The spreadsheet ID

        Returns:
            dict: appProperties (if any) for the given sheet according to Drive
        """
        result = (
            self.pygsheets_client.drive.service.files()
            .get(
                fileId=file_id,
                fields="appProperties",
                supportsTeamDrives=self.supports_team_drives,
            )
            .execute()
        )
        if result and "appProperties" in result:
            return result["appProperties"]
        return {}

    def batch_update_sheet_cells(self, sheet_id, request_objects):
        """
        Updates the relevant cells of a coupon assignment Sheet with the email delivery dates for the assignments
        on the coupon assignments on the rows of those cells.

        Args:
            sheet_id (str): The spreadsheet id
            request_objects (list of dict): Update request objects
                (docs: https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request#Request)

        Returns:
            dict: Google API response to the spreadsheets.values.batchUpdate request
        """
        return (
            self.pygsheets_client.sheet.service.spreadsheets()
            .batchUpdate(spreadsheetId=sheet_id, body={"requests": request_objects})
            .execute()
        )

    def request_file_watch(self, file_id, channel_id):
        """
        Executes the request to watch for changes made to a specific file in Drive. If successful, Drive will
        make requests to our webhook when changes are made to the given file.

        Returns:
            dict: Google API response to a files.watch request
        """
        return (
            self.pygsheets_client.drive.service.files()
            .watch(
                fileId=file_id,
                supportsTeamDrives=self.supports_team_drives,
                body={
                    "id": channel_id,
                    "address": urljoin(
                        settings.SITE_BASE_URL,
                        reverse("handle-coupon-request-sheet-update"),
                    ),
                    "payload": True,
                    "kind": GOOGLE_API_FILE_WATCH_KIND,
                    "type": GOOGLE_API_NOTIFICATION_TYPE,
                },
            )
            .execute()
        )


def create_coupons_for_request_row(coupon_req_row):
    """
    Creates coupons for a given request

    Args:
        coupon_req_row (sheets.utils.CouponRequestRow): A representation of a coupon request row

    Returns:
        CouponGenerationRequest or None: The record of the completed coupon generation request, or None
            if the request for the given transaction id has already been completed.
    """
    with transaction.atomic():
        coupon_gen_request, created = CouponGenerationRequest.objects.select_for_update().get_or_create(
            purchase_order_id=coupon_req_row.purchase_order_id
        )
        if not created and coupon_gen_request.completed:
            log.error(
                "Found completed CouponGenerationRequest, but the 'processed' column "
                "in the spreadsheet == False (transaction id: %s)"
                % coupon_req_row.purchase_order_id
            )
            return
        create_coupons(
            name=coupon_req_row.coupon_name,
            product_ids=[coupon_req_row.get_product_id()],
            num_coupon_codes=coupon_req_row.num_codes,
            coupon_type=CouponPaymentVersion.SINGLE_USE,
            max_redemptions=1,
            company_id=Company.objects.get(name__iexact=coupon_req_row.company_name).id,
            activation_date=coupon_req_row.activation,
            expiration_date=coupon_req_row.expiration,
            payment_type=CouponPaymentVersion.PAYMENT_PO,
            payment_transaction=coupon_req_row.purchase_order_id,
            **BULK_PURCHASE_DEFAULTS,
        )
        coupon_gen_request.completed = True
        coupon_gen_request.save()
        return coupon_gen_request


class CouponRequestHandler:
    """Manages the processing of coupon requests from a Sheet"""

    def __init__(self):
        self.pygsheets_client = get_authorized_pygsheets_client()
        spreadsheet = self.pygsheets_client.open_by_key(
            settings.COUPON_REQUEST_SHEET_ID
        )
        self.coupon_request_sheet = spreadsheet.sheet1

    def parsed_row_iterator(self):
        """
        Generator for successfully-parsed rows in the coupon request sheet. Rows that fail parsing
        are logged and skipped.

        Yields:
            tuple of (int, CouponRequestRow): The row number in the sheet paired with the parsed coupon request row
        """
        enumerated_data_rows = enumerate(
            get_data_rows(self.coupon_request_sheet),
            start=coupon_request_sheet_spec.first_data_row,
        )
        for row_index, row_data in enumerated_data_rows:
            try:
                yield row_index, CouponRequestRow.parse_raw_data(row_data)
            except Exception as exc:
                log.error(
                    "Coupon request row could not be parsed (row %d). Exception: %s"
                    % row_index,
                    str(exc),
                )
                continue

    def create_coupons_from_sheet(self):
        """
        Creates coupons for all rows in the coupon request sheet that indicate that they are not yet processed.

        Returns:
            list of ProcessedRequest: A list of objects containing information about each request row that was processed.
        """
        processed_requests = []
        for row_index, coupon_req_row in self.parsed_row_iterator():
            if coupon_req_row.date_processed:
                continue
            coupon_gen_request = create_coupons_for_request_row(coupon_req_row)
            if coupon_gen_request:
                processed_requests.append(
                    ProcessedRequest(
                        row_index=row_index,
                        coupon_req_row=coupon_req_row,
                        request_id=coupon_gen_request.id,
                        date_processed=now_in_utc(),
                    )
                )
        return processed_requests

    def update_coupon_request_processed_dates(self, processed_requests):
        """
        For all processed request rows, programatically sets the "processed" column to checked/TRUE.

        Args:
            processed_requests (list of ProcessedRequest): A list of ProcessedRequest objects
        """
        for processed_request in processed_requests:
            self.coupon_request_sheet.update_value(
                "{}{}".format(
                    CouponRequestRow.DATE_PROCESSED_COLUMN, processed_request.row_index
                ),
                format_datetime_for_sheet_formula(
                    processed_request.date_processed.astimezone(
                        settings.SHEETS_DATE_TIMEZONE
                    )
                ),
            )

    def create_coupon_assignment_sheet(self, coupon_req_row):
        """
        Creates a coupon assignment sheet from a single coupon request row

        Args:
            coupon_req_row (CouponRequestRow): The coupon request row

        Returns:
            pygsheets.Spreadsheet: The Spreadsheet object representing the newly-created sheet
        """
        # Get coupon codes created by the request
        coupon_codes = Coupon.objects.filter(
            payment__name=coupon_req_row.coupon_name
        ).values_list("coupon_code", flat=True)
        if not coupon_codes:
            log.error(
                "Cannot create bulk coupon sheet - No coupon codes found matching the name '%s'"
                % coupon_req_row.coupon_name
            )
            return
        # Create sheet
        spreadsheet_title = assignment_sheet_file_name(
            coupon_req_row.purchase_order_id, coupon_req_row.company_name
        )
        create_kwargs = (
            dict(folder=settings.DRIVE_OUTPUT_FOLDER_ID)
            if settings.DRIVE_OUTPUT_FOLDER_ID
            else {}
        )
        bulk_coupon_sheet = self.pygsheets_client.create(
            spreadsheet_title, **create_kwargs
        )
        worksheet = bulk_coupon_sheet.sheet1
        # Add headers
        worksheet.update_values(
            crange="A1:{}1".format(coupon_assign_sheet_spec.last_data_column),
            values=[coupon_assign_sheet_spec.column_headers],
        )
        # Write data to body of worksheet
        worksheet.update_values(
            crange="A{}:A{}".format(
                coupon_assign_sheet_spec.first_data_row,
                len(coupon_codes) + coupon_assign_sheet_spec.first_data_row,
            ),
            values=[[coupon_code] for coupon_code in coupon_codes],
        )
        # Adjust code and email column widths to fit coupon codes and emails
        worksheet.adjust_column_width(start=0, end=2, pixel_size=270)
        # Format header cells with bold text
        header_range = worksheet.get_values(
            start="A1",
            end="{}1".format(coupon_assign_sheet_spec.last_data_column),
            returnas="range",
        )
        first_cell = header_range.cells[0][0]
        first_cell.set_text_format("bold", True)
        header_range.apply_format(first_cell)
        # Share
        for email in settings.SHEETS_ADMIN_EMAILS:
            added_kwargs = (
                {"sendNotificationEmail": False}
                if GOOGLE_SERVICE_ACCOUNT_EMAIL_DOMAIN in email
                else {}
            )
            bulk_coupon_sheet.share(email, type="user", role="writer", **added_kwargs)

        return bulk_coupon_sheet

    def write_results_to_sheets(self, processed_requests):
        """
        Updates the coupon request sheet and creates a coupon assignment sheet for every successfully
        processed coupon request.

        Args:
            processed_requests (list of ProcessedRequest): List of ProcessedRequest objects
        """
        if not processed_requests:
            return
        # Set checkboxes
        self.update_coupon_request_processed_dates(processed_requests)
        # Write new sheets with codes
        for processed_request in processed_requests:
            self.create_coupon_assignment_sheet(processed_request.coupon_req_row)


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

    def fetch_incomplete_sheets(self):
        """
        Fetches assignment Spreadsheets with metadata that indicate that they have not yet been completed
        and should still be considered for processing.

        Returns:
            list of pygsheets.spreadsheet.Spreadsheet: A list of Spreadsheets that have not been completed
        """
        return self.pygsheets_client.open_all(
            query="{} and {}".format(
                self.ASSIGNMENT_SHEETS_QUERY, self.INCOMPLETE_SHEETS_QUERY_TERM
            )
        )

    @staticmethod
    def assignment_tuple_iter(data_rows):
        """
        Validates assignment Sheet data rows and returns a "safe" iterable for the data in those rows

        Args:
            data_rows (list of lists): Matrix of raw data in the non-header rows of a Sheet

        Returns:
            iterable of (str, str, str, str): An iterable for the data rows that yields None for a given column
                if that column is empty
        """
        coupon_codes = [row[0] for row in data_rows]
        if not coupon_codes:
            raise SheetValidationException("No data found in coupon assignment Sheet")
        elif not all_unique(coupon_codes):
            raise SheetValidationException(
                "All coupon codes in the Sheet must be unique"
            )
        emails = (item_at_index_or_none(row, 1) for row in data_rows)
        statuses = (item_at_index_or_none(row, 2) for row in data_rows)
        status_dates = (item_at_index_or_none(row, 3) for row in data_rows)
        return zip(coupon_codes, emails, statuses, status_dates)

    def assignment_sheet_data_iter(self, bulk_assignments):
        """
        Generator for data rows in Sheets associated with bulk assignments

        Args:
            bulk_assignments (iterable of BulkCouponAssignment):

        Yields:
            (BulkCouponAssignment, iterable of (str, str, str, str)): A bulk coupon assignment object paired with a
                matrix of data rows in the coupon assignment Sheet associated with that object
        """
        for bulk_assignment in bulk_assignments:
            spreadsheet = self.pygsheets_client.open_by_key(
                bulk_assignment.assignment_sheet_id
            )
            worksheet = spreadsheet.sheet1
            data_rows = list(get_data_rows(worksheet))
            yield bulk_assignment, self.assignment_tuple_iter(data_rows)

    @classmethod
    def get_desired_coupon_assignments(cls, data_rows):
        """
        Parses coupon assignment sheet data to get desired coupon assignments. Only rows with both a non-empty coupon
        code and email are considered.

        Args:
            data_rows (list of lists): A matrix (list of lists) of data from a coupon assignment Worksheet

        Returns:
            set of (str, int): A set of emails paired with the product coupon (CouponEligibility)
                id's that should be assigned to them.
        """
        assignment_tuples = cls.assignment_tuple_iter(data_rows)
        valid_code_email_pairs = [
            (code, email) for code, email, _, _ in assignment_tuples if code and email
        ]
        product_coupon_tuples = CouponEligibility.objects.filter(
            coupon__coupon_code__in=[pair[0] for pair in valid_code_email_pairs]
        ).values_list("coupon__coupon_code", "id")
        if len(product_coupon_tuples) != len(valid_code_email_pairs):
            raise SheetValidationException(
                "Mismatch between the number of matching product coupons and the number of coupon "
                "codes listed in the Sheet. There may be an invalid coupon code in the Sheet."
            )
        product_coupon_dict = dict(product_coupon_tuples)
        return set(
            (valid_code_email_pair[1], product_coupon_dict[valid_code_email_pair[0]])
            for valid_code_email_pair in valid_code_email_pairs
        )

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
                    "The following assignments will not be removed: %s"
                    % str(list(already_redeemed_assignments))
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
                        "The following assignments will be not be created: %s"
                        % str(list(cannot_create_iter))
                    )

        return (
            tuple_set_to_create,
            [assignment.id for assignment in assignments_to_remove],
        )

    def process_assignment_spreadsheet(self, spreadsheet):
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
            spreadsheet (pygsheets.spreadsheet.Spreadsheet):

        Returns:
            (BulkCouponAssignment, int, int): The bulk coupon assignment created/updated paired with
                the number of ProductCouponAssignments created and the number deleted
        """
        sheet = spreadsheet.sheet1
        data_rows = list(get_data_rows(sheet))

        bulk_assignment, _ = BulkCouponAssignment.objects.get_or_create(
            assignment_sheet_id=spreadsheet.id
        )
        created_assignments, num_assignments_removed = [], 0

        # Determine what assignments need to be created and deleted
        desired_assignments = self.get_desired_coupon_assignments(data_rows)
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

        # Create ProductCouponAssignments and update the BulkCouponAssignment record to reflect the progress
        with transaction.atomic():
            _, created_assignments = bulk_assign_product_coupons(
                assignments_to_create, bulk_assignment=bulk_assignment
            )
            now = now_in_utc()
            if not bulk_assignment.assignments_started_date and created_assignments:
                bulk_assignment.assignments_started_date = now
            bulk_assignment.save()

        # Send messages if any assignments were created
        if created_assignments:
            send_bulk_enroll_emails(bulk_assignment.id, created_assignments)

        return bulk_assignment, len(created_assignments), num_assignments_removed

    def process_assignment_spreadsheets(self):
        """
        Processes all as-yet-incomplete coupon assignment spreadsheets

        Returns:
            list of pygsheets.spreadsheet.Spreadsheet: Successfully-processed spreadsheets
        """
        processed = []
        for spreadsheet in self.fetch_incomplete_sheets():
            log.info("Processing spreadsheet (%s)..." % spreadsheet_repr(spreadsheet))
            try:
                self.process_assignment_spreadsheet(spreadsheet)
            except SheetValidationException as exc:
                log.info(
                    "Spreadsheet has invalid data for processing - %s, exception: %s"
                    % (spreadsheet_repr(spreadsheet), str(exc))
                )
            except SheetUpdateException as exc:
                log.error(
                    "All relevant coupons have been assigned and messages have been sent, "
                    "but failed to update the spreadsheet properties to indicate status "
                    "- %s, exception: %s" % (spreadsheet_repr(spreadsheet), str(exc))
                )
            except Exception as exc:
                log.error(exc)
            else:
                processed.append(spreadsheet)
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
        for bulk_assignment, assignment_tuples in self.assignment_sheet_data_iter(
            bulk_assignments
        ):
            assignment_status_map.add_assignment_rows(
                bulk_assignment,
                [
                    AssignmentRow(
                        row_index=row_index,
                        coupon_code=code,
                        email=email,
                        status=status,
                        status_date=status_date,
                    )
                    for row_index, (code, email, status, status_date) in enumerate(
                        assignment_tuples, start=1
                    )
                ],
            )

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

    def update_sheet_with_new_statuses(self, sheet_id, status_date_rows):
        """
        Updates the relevant cells of a coupon assignment Sheet with message statuses and dates.

        Args:
            sheet_id (str): The spreadsheet id
            status_date_rows (iterable of (int, str, datetime.datetime): An iterable of row indices
                (indicating the Sheet row) paired with the message status and the date of that status change.

        Returns:
            dict: Google API response body
        """
        return self.expanded_sheets_client.batch_update_sheet_cells(
            sheet_id=sheet_id,
            request_objects=[
                build_multi_cell_update_request_body(
                    row_index=row_index,
                    column_index=ASSIGNMENT_SHEET_STATUS_COLUMN,
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
                assignment.message_status in {None, MAILGUN_FAILED}
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
                except Exception as exc:
                    log.error(
                        "The BulkCouponAssignment has been updated to indicate that message delivery is complete, "
                        "but the request to update spreadsheet properties to indicate this status failed."
                        "- %s, exception: %s" % (spreadsheet_id, str(exc))
                    )

            # Update delivery dates in Sheet
            if assignment_status_map.has_new_statuses(bulk_assignment_id):
                self.update_sheet_with_new_statuses(
                    spreadsheet_id,
                    assignment_status_map.get_status_date_rows(bulk_assignment_id),
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
