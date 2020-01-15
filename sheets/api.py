"""API for the Sheets app"""
import itertools
import os
import json
import datetime
from collections import defaultdict
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
from googleapiclient.discovery import build
import pygsheets
from anymail.exceptions import AnymailInvalidAddress

import ecommerce.api
from ecommerce.mail_api import send_bulk_enroll_emails
from ecommerce.models import (
    Company,
    CouponPaymentVersion,
    Coupon,
    BulkCouponAssignment,
    CouponEligibility,
    ProductCouponAssignment,
)
from mail.api import validate_email_addresses
from mail.constants import (
    MAILGUN_DELIVERED,
    MAILGUN_FAILED,
    MAILGUN_OPENED,
    MAILGUN_CLICKED,
)
from mail.exceptions import MultiEmailValidationError
from mitxpro.utils import now_in_utc, all_unique, partition, partition_to_lists
from sheets.mail_api import get_bulk_assignment_messages
from sheets.models import CouponGenerationRequest, GoogleApiAuth, GoogleFileWatch
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
    UNSENT_EMAIL_STATUSES,
    INVALID_EMAIL_STATUS,
    UNKNOWN_EMAIL_ERROR_STATUS,
)
from sheets.utils import (
    coupon_assign_sheet_spec,
    ProcessedRequest,
    FailedRequest,
    IgnoredRequest,
    AssignmentStatusMap,
    CouponRequestRow,
    CouponAssignmentRow,
    get_data_rows,
    get_enumerated_data_rows,
    spreadsheet_repr,
    format_datetime_for_google_api,
    mailgun_timestamp_to_datetime,
    build_multi_cell_update_request_body,
    ASSIGNMENT_SHEET_STATUS_COLUMN,
    format_datetime_for_sheet_formula,
    assignment_sheet_file_name,
    format_datetime_for_google_timestamp,
    google_timestamp_to_datetime,
    google_date_string_to_datetime,
    build_protected_range_request_body,
    build_drive_file_email_share_request,
)
from sheets.exceptions import (
    SheetValidationException,
    SheetUpdateException,
    SheetOutOfSyncException,
    InvalidSheetProductException,
    SheetCouponCreationException,
    SheetRowParsingException,
    FailedBatchRequestException,
)

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
            if email.endswith(GOOGLE_SERVICE_ACCOUNT_EMAIL_DOMAIN)
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

    def get_metadata_for_matching_files(self, query, file_fields="id, name"):
        """
        Fetches metadata for all Drive files that match a given query
        Args:
            query (str): The Drive files query (ref: https://developers.google.com/drive/api/v3/search-files)
            file_fields (str): Comma-separated list of file fields that should be returned in the metadata
                results (ref: https://developers.google.com/drive/api/v3/reference/files#resource)

        Returns:
            list of dict: A dict of metadata for each file that matched the given query
        """
        extra_list_params = {}
        if self.supports_team_drives:
            extra_list_params.update(
                dict(
                    corpora="teamDrive",
                    teamDriveId=settings.DRIVE_SHARED_ID,
                    supportsTeamDrives=True,
                    includeTeamDriveItems=True,
                )
            )
        return self.pygsheets_client.drive.list(
            **extra_list_params, fields="files({})".format(file_fields), q=query
        )

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

    def get_drive_file_metadata(self, file_id, fields="id, name, modifiedTime"):
        """
        Helper method to fetch metadata for some Drive file.

        Args:
           file_id (str): The file ID
           fields (str): Comma-separated list of file fields that should be returned in the metadata
                results (ref: https://developers.google.com/drive/api/v3/reference/files#resource)

        Returns:
           dict: The file metadata, which includes the specified fields.
        """
        return (
            self.pygsheets_client.drive.service.files()
            .get(
                fileId=file_id,
                fields=fields,
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
        result = self.get_drive_file_metadata(file_id=file_id, fields="appProperties")
        if result and "appProperties" in result:
            return result["appProperties"]
        return {}

    def batch_update_sheet_cells(self, sheet_id, request_objects):
        """
        Performs a batch update of targeted cells in a spreadsheet.

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


def build_drive_service(credentials=None):
    """
    Builds the Google API client Drive service for API functionality that cannot be implemented correctly
    with pygsheets.

    Args:
        credentials (google.oauth2.credentials.Credentials or None): Credentials to be used by the
            Google Drive client

    Returns:
        googleapiclient.discovery.Resource: The Drive API service. The methods available on this resource are
            defined dynamically (ref: http://googleapis.github.io/google-api-python-client/docs/dyn/drive_v3.html)
    """
    credentials = credentials or get_credentials()
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def batch_share_callback(
    request_id, response, exception
):  # pylint: disable=unused-argument
    """
    A callback function given to the Google API client's new_batch_http_request(). Called for the result
    of each individual request executed in a batch API call.
    Ref: https://developers.google.com/drive/api/v3/batch#using-client-libraries
    NOTE: If *any* of the individual share requests in the batch fail, this callback is called and passed an exception
    for *all* of the individual requests whether they contained a bad email address or not. There is no way to
    determine the specific failed emails from the arguments to this function.

    Args:
        request_id (str): The id of the individual batch request
        response (dict): The API response body if no error occurred
        exception (googleapiclient.errors.HttpError): The error, if one occurred
    """
    if exception:
        raise FailedBatchRequestException from exception


def share_drive_file_with_emails(file_id, emails_to_share, credentials=None):
    """
    Shares a Drive file with multiple recipients. First attempts to share with the list of emails via a batch request.
    If that fails, attempts to share with each email address individually. If a batch share request fails, the file is
    not shared with any of the emails, and there is no way to get reliable information about which specific emails
    failed. This function defaults to individual sharing so valid emails will still be shared to if the batch request
    fails.

    Args:
        file_id (str): The Drive file id
        emails_to_share (list of str): Email addresses that will be added as shared users for the given file
        credentials (google.oauth2.credentials.Credentials or None): Credentials to be used by the
            Google Drive client

    Returns:

    """
    if not emails_to_share:
        return
    drive_service = build_drive_service(credentials=credentials)
    batch = drive_service.new_batch_http_request()
    for email_to_share in emails_to_share:
        batch.add(
            drive_service.permissions().create(
                **build_drive_file_email_share_request(file_id, email_to_share)
            ),
            request_id=email_to_share,
            callback=batch_share_callback,
        )
    try:
        batch.execute()
    except FailedBatchRequestException:
        log.exception(
            "Failed to batch-share the spreadsheet (id: '%s'). One or more of the emails failed, "
            "so the spreadsheet was not shared with any of them. Now attempting to share individually...",
            file_id,
        )
        for email_to_share in emails_to_share:
            perm_request = drive_service.permissions().create(
                **build_drive_file_email_share_request(file_id, email_to_share)
            )
            try:
                perm_request.execute()
            except:  # pylint: disable=broad-except
                log.exception(
                    "Failed to share the file with id '%s' with email '%s'",
                    file_id,
                    email_to_share,
                )


def request_file_watch(file_id, channel_id, expiration=None, credentials=None):
    """
    Sends a request to the Google API to watch for changes in a given file. If successful, this
    app will receive requests from Google when changes are made to the file.
    Ref: https://developers.google.com/drive/api/v3/reference/files/watch

    Args:
        file_id (str): The id of the file in Google Drive (can be determined from the URL)
        channel_id (str): Arbitrary string to identify the file watch being set up. This will
            be included in the header of every request Google sends to the app.
        expiration (datetime.datetime or None): The datetime that this file watch should expire.
            Defaults to 1 hour, and cannot exceed 24 hours.
        credentials (google.oauth2.credentials.Credentials or None): Credentials to be used by the
            Google Drive client

    Returns:
        dict: The Google file watch API response
    """
    drive_service = build_drive_service(credentials=credentials)
    extra_body_params = {}
    if expiration:
        extra_body_params["expiration"] = format_datetime_for_google_timestamp(
            expiration
        )
    return (
        drive_service.files()
        .watch(
            fileId=file_id,
            supportsTeamDrives=True,
            body={
                "id": channel_id,
                "resourceId": file_id,
                "address": urljoin(
                    settings.SITE_BASE_URL,
                    reverse("handle-coupon-request-sheet-update"),
                ),
                "payload": True,
                "kind": GOOGLE_API_FILE_WATCH_KIND,
                "type": GOOGLE_API_NOTIFICATION_TYPE,
                **extra_body_params,
            },
        )
        .execute()
    )


def renew_coupon_request_file_watch(force=False):
    """
    Creates or renews a file watch on the coupon request spreadsheet depending on the existence
    of other file watches and when they expire.

    Args:
        force (bool): If True, make the file watch request and overwrite the GoogleFileWatch record
            even if an unexpired one exists.

    Returns:
        (GoogleFileWatch, bool, bool): The GoogleFileWatch object, a flag indicating
            whether or not it was newly created during execution, and a flag indicating
            whether or not it was updated during execution.
    """
    now = now_in_utc()
    min_fresh_expiration_date = now + datetime.timedelta(
        minutes=settings.DRIVE_WEBHOOK_RENEWAL_PERIOD_MINUTES
    )
    new_channel_id = "{}-{}".format(
        settings.DRIVE_WEBHOOK_CHANNEL_ID, now.strftime("%Y%m%d-%H%M%S")
    )
    with transaction.atomic():
        file_watch, created = GoogleFileWatch.objects.select_for_update().get_or_create(
            file_id=settings.COUPON_REQUEST_SHEET_ID,
            defaults=dict(
                version=1,
                channel_id=new_channel_id,
                activation_date=now,
                expiration_date=now,
            ),
        )
        if (
            not created
            and file_watch.expiration_date > min_fresh_expiration_date
            and not force
        ):
            return file_watch, False, False
        if file_watch.expiration_date < now:
            log.error(
                "Current file watch in the database is expired. Some file changes may have failed to "
                "trigger a push notification (%s)",
                file_watch,
            )
        expiration = now + datetime.timedelta(
            minutes=settings.DRIVE_WEBHOOK_EXPIRATION_MINUTES
        )
        resp_dict = request_file_watch(
            settings.COUPON_REQUEST_SHEET_ID, new_channel_id, expiration=expiration
        )
        log.info(
            "File watch request for push notifications on coupon request sheet completed. Response: %s",
            resp_dict,
        )
        file_watch.activation_date = now
        file_watch.expiration_date = google_timestamp_to_datetime(
            resp_dict["expiration"]
        )
        file_watch.channel_id = new_channel_id
        if not created:
            file_watch.version += 1
        file_watch.save()
        return file_watch, created, True


def create_coupons_for_request_row(coupon_req_row, company_id):
    """
    Creates coupons for a given request

    Args:
        coupon_req_row (sheets.utils.CouponRequestRow): A representation of a coupon request row
        company_id (int): The id of the Company on whose behalf these coupons are being created

    Returns:
        CouponPaymentVersion:
            A CouponPaymentVersion. Other instances will be created at the same time and linked via foreign keys.
    """
    return ecommerce.api.create_coupons(
        name=coupon_req_row.coupon_name,
        product_ids=[coupon_req_row.get_product_id()],
        num_coupon_codes=coupon_req_row.num_codes,
        coupon_type=CouponPaymentVersion.SINGLE_USE,
        max_redemptions=1,
        company_id=company_id,
        activation_date=coupon_req_row.activation,
        expiration_date=coupon_req_row.expiration,
        payment_type=CouponPaymentVersion.PAYMENT_PO,
        payment_transaction=coupon_req_row.purchase_order_id,
        **BULK_PURCHASE_DEFAULTS,
    )


class CouponRequestHandler:
    """Manages the processing of coupon requests from a Sheet"""

    def __init__(self):
        self.pygsheets_client = get_authorized_pygsheets_client()
        self._credentials = self.pygsheets_client.oauth
        spreadsheet = self.pygsheets_client.open_by_key(
            settings.COUPON_REQUEST_SHEET_ID
        )
        self.coupon_request_sheet = spreadsheet.sheet1

    @staticmethod
    def validate_sheet(enumerated_data_rows):
        """
        Checks the request sheet data for any data issues beyond the scope of a single row (i.e.: any row data
        that is invalid because of the data in other rows in the sheet)

        Args:
            enumerated_data_rows (iterable of (int, list of str)): Row indices paired with a list of strings
                representing the data in each row

        Returns:
            ( (iterable of (int, list of str)), list of FailedRequest ): Enumerated data rows with invalidated rows
                filtered out, paired with objects representing the rows that failed validation.
        """
        enumerated_data_rows_1, enumerated_data_rows_2 = itertools.tee(
            enumerated_data_rows
        )
        failed_row_dict = {}
        observed_coupon_names = set()
        invalid_coupon_name_row_map = defaultdict(list)
        for row_index, row_data in enumerated_data_rows_1:
            coupon_name = row_data[CouponRequestRow.COUPON_NAME_COL_INDEX].strip()
            if coupon_name in observed_coupon_names:
                invalid_coupon_name_row_map[coupon_name].append(row_index)
            else:
                observed_coupon_names.add(coupon_name)

        # If any coupon names were found on multiple rows, log a message and create a failed request
        # object for each row with a non-unique coupon name (except for the row with the first instance
        # of that name).
        for coupon_name, row_indices in invalid_coupon_name_row_map.items():
            log.error(
                "Coupon name '%s' appears %d times on the request sheet (rows: %s). Coupon name "
                "must be unique.",
                coupon_name,
                (len(row_indices) + 1),
                row_indices,
            )
            sheet_error_text = "Coupon name '{}' already exists in the sheet".format(
                coupon_name
            )
            failed_row_dict = {
                **failed_row_dict,
                **{
                    row_index: FailedRequest(
                        row_index=row_index,
                        exception=SheetValidationException(sheet_error_text),
                        sheet_error_text=sheet_error_text,
                    )
                    for row_index in row_indices
                },
            }

        valid_data_rows = filter(
            lambda index_data_tuple: index_data_tuple[0] not in failed_row_dict.keys(),
            enumerated_data_rows_2,
        )
        return valid_data_rows, list(failed_row_dict.values())

    @staticmethod
    def parse_row_and_create_coupons(row_index, row_data):
        """
        Ensures that the given request row has a database record representing the request,
        and that coupons are created for the request if necessary.

        Args:
            row_index (int): The row index according to the spreadsheet
            row_data (iterable of str): Raw unparsed row data from the spreadsheet

        Returns:
            CouponGenerationRequest, CouponRequestRow, bool: The database object representing
                the request row, the parsed row data, and a flag indicating whether or not
                the row was ignored.

        Raises:
            SheetRowParsingException: Raised if the row could not be parsed
            SheetOutOfSyncException: Raised if the data in the database record for the request
                and the data in the sheet do not agree
            SheetCouponCreationException: Raised if there was an error during coupon creation
        """
        coupon_name = row_data[CouponRequestRow.COUPON_NAME_COL_INDEX].strip()
        purchase_order_id = row_data[CouponRequestRow.PURCHASE_ORDER_COL_INDEX].strip()
        user_input_json = json.dumps(CouponRequestRow.get_user_input_columns(row_data))

        with transaction.atomic():
            coupon_gen_request, created = CouponGenerationRequest.objects.select_for_update().get_or_create(
                coupon_name=coupon_name,
                defaults=dict(
                    purchase_order_id=purchase_order_id, raw_data=user_input_json
                ),
            )
            raw_data_changed = coupon_gen_request.raw_data != user_input_json
            if raw_data_changed:
                coupon_gen_request.raw_data = user_input_json
                coupon_gen_request.save()

        coupon_req_row = CouponRequestRow.parse_raw_data(row_index, row_data)
        if coupon_req_row.date_processed:
            return coupon_gen_request, coupon_req_row, True
        if not created and coupon_gen_request.date_completed:
            raise SheetOutOfSyncException(
                coupon_gen_request=coupon_gen_request, coupon_req_row=coupon_req_row
            )
        if not created and coupon_req_row.error and not raw_data_changed:
            return coupon_gen_request, coupon_req_row, True

        company, created = Company.objects.get_or_create(
            name__iexact=coupon_req_row.company_name,
            defaults=dict(name=coupon_req_row.company_name),
        )
        if created:
            log.info("Created new Company '%s'...", coupon_req_row.company_name)
        try:
            create_coupons_for_request_row(coupon_req_row, company.id)
        except Exception as exc:
            raise SheetCouponCreationException(
                coupon_gen_request=coupon_gen_request,
                coupon_req_row=coupon_req_row,
                inner_exc=exc,
            ) from exc

        coupon_gen_request.date_completed = now_in_utc()
        coupon_gen_request.save()
        return coupon_gen_request, coupon_req_row, False

    def parse_rows_and_create_coupons(self, enumerated_data_rows):
        """
        Parses the given data rows, creates coupons for the rows that have not been processed,
        and returns information about which rows were successfully processed and which ones failed.

        Args:
            enumerated_data_rows (iterable of (int, list of str)): Row indices paired with a list of strings
                representing the data in each row

        Returns:
            (list of ProcessedRequest, list of FailedRequest, list of ProcessedRequest):
                A list of objects representing each request row that was processed,
                a list of objects representing each request row that couldn't be processed,
                and a list of objects representing each request row that is complete but doesn't say so in
                the spreadsheet.
        """
        processed_requests = []
        ignored_requests = []
        unrecorded_complete_requests = []
        valid_enumerated_data_rows, failed_requests = self.validate_sheet(
            enumerated_data_rows
        )
        for row_index, row_data in valid_enumerated_data_rows:
            try:
                coupon_gen_request, coupon_req_row, ignored = self.parse_row_and_create_coupons(
                    row_index, row_data
                )
            except SheetRowParsingException as exc:
                log.exception(
                    "Coupon request row could not be parsed (row %d)", row_index
                )
                failed_requests.append(
                    FailedRequest(
                        row_index=row_index,
                        exception=exc,
                        sheet_error_text="Row parsing error ({})".format(exc),
                    )
                )
            except SheetOutOfSyncException as exc:
                log.error(
                    "Found completed CouponGenerationRequest, but the 'Date Processed' column "
                    "in the spreadsheet is empty (purchase order id: %s)",
                    exc.coupon_req_row.purchase_order_id,
                )
                unrecorded_complete_requests.append(
                    ProcessedRequest(
                        row_index=row_index,
                        coupon_req_row=exc.coupon_req_row,
                        request_id=exc.coupon_gen_request.id,
                        date_processed=exc.coupon_gen_request.date_completed,
                    )
                )
            except SheetCouponCreationException as exc:
                log.exception("Enrollment code creation error (row %d)", row_index)
                if isinstance(exc.inner_exc, InvalidSheetProductException):
                    error_msg = "Invalid product ({})".format(exc.inner_exc)
                else:
                    error_msg = "Enrollment code creation error ({})".format(
                        exc.inner_exc
                    )
                failed_requests.append(
                    FailedRequest(
                        row_index=row_index,
                        exception=exc.inner_exc,
                        sheet_error_text=error_msg,
                    )
                )
            except Exception as exc:  # pylint: disable=broad-except
                log.exception(
                    "Unknown error while parsing row and creating coupons (row: %d)",
                    row_index,
                )
                error_msg = "Unknown error while parsing row and creating coupons"
                failed_requests.append(
                    FailedRequest(
                        row_index=row_index, exception=exc, sheet_error_text=error_msg
                    )
                )
            else:
                # We only need to report on ignored rows if the row has some error text.
                # Rows that have already been processed are also be ignored, but that is a normal
                # and unremarkable state that doesn't need to be tracked.
                if ignored and coupon_req_row.error:
                    ignored_requests.append(
                        IgnoredRequest(
                            row_index=row_index,
                            coupon_req_row=coupon_req_row,
                            reason="Row has an error and is unchanged since the last attempt.",
                        )
                    )
                elif not ignored and coupon_gen_request.date_completed:
                    processed_requests.append(
                        ProcessedRequest(
                            row_index=row_index,
                            coupon_req_row=coupon_req_row,
                            request_id=coupon_gen_request.id,
                            date_processed=coupon_gen_request.date_completed,
                        )
                    )
        return (
            processed_requests,
            failed_requests,
            ignored_requests,
            unrecorded_complete_requests,
        )

    def update_coupon_request_processed_dates(self, processed_requests):
        """
        For all processed request rows, programatically sets the "Date Processed" column value and
        blanks the error column.

        Args:
            processed_requests (list of ProcessedRequest): A list of ProcessedRequest objects
        """
        for processed_request in processed_requests:
            self.coupon_request_sheet.update_values(
                crange="{processed_col}{row_index}:{error_col}{row_index}".format(
                    processed_col=settings.SHEETS_REQ_PROCESSED_COL_LETTER,
                    error_col=settings.SHEETS_REQ_ERROR_COL_LETTER,
                    row_index=processed_request.row_index,
                ),
                values=[
                    [
                        format_datetime_for_sheet_formula(
                            processed_request.date_processed.astimezone(
                                settings.SHEETS_DATE_TIMEZONE
                            )
                        ),
                        "",
                    ]
                ],
            )

    def update_coupon_request_errors(self, failed_requests):
        """
        For all failed request rows, updates the error column to contain the error message.

        Args:
            failed_requests (list of FailedRequest): A list of FailedRequest objects
        """
        for failed_request in failed_requests:
            self.coupon_request_sheet.update_value(
                "{}{}".format(
                    settings.SHEETS_REQ_ERROR_COL_LETTER, failed_request.row_index
                ),
                failed_request.sheet_error_text,
            )

    def protect_coupon_assignment_ranges(
        self, spreadsheet_id, worksheet_id, num_data_rows
    ):
        """
        Sets the header row, the coupon code column, and the status columns to protected so that they can only be
        edited by the script or a privileged user.

        Args:
            spreadsheet_id (str): The Spreadsheet id
            worksheet_id (int): The id of the Worksheet that these ranges will be applied to
            num_data_rows (int): The number of data rows (i.e.: all rows except the header) in the sheet

        Returns:
            dict: The response body from the Google Sheets API batch update request
        """
        header_range_req = build_protected_range_request_body(
            worksheet_id=worksheet_id,
            start_row_index=0,
            num_rows=1,
            start_col_index=0,
            num_cols=coupon_assign_sheet_spec.num_columns,
            warning_only=False,
            description="Header Row",
        )
        coupon_code_range_req = build_protected_range_request_body(
            worksheet_id=worksheet_id,
            start_row_index=coupon_assign_sheet_spec.first_data_row - 1,
            num_rows=num_data_rows,
            start_col_index=0,
            num_cols=1,
            warning_only=False,
            description="Coupon Codes",
        )
        status_columns_range_req = build_protected_range_request_body(
            worksheet_id=worksheet_id,
            start_row_index=coupon_assign_sheet_spec.first_data_row - 1,
            num_rows=num_data_rows,
            start_col_index=ASSIGNMENT_SHEET_STATUS_COLUMN,
            num_cols=2,
            warning_only=True,
            description="Status Columns",
        )
        return self.pygsheets_client.sheet.batch_update(
            spreadsheet_id,
            [header_range_req, coupon_code_range_req, status_columns_range_req],
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
                "Cannot create bulk coupon sheet - No coupon codes found matching the name '%s'",
                coupon_req_row.coupon_name,
            )
            return
        # Create sheet
        spreadsheet_title = assignment_sheet_file_name(coupon_req_row)
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
        # Protect ranges of cells that should not be edited (everything besides the email column)
        self.protect_coupon_assignment_ranges(
            spreadsheet_id=bulk_coupon_sheet.id,
            worksheet_id=worksheet.id,
            num_data_rows=len(coupon_codes),
        )
        # Share
        if settings.SHEETS_ADMIN_EMAILS:
            share_drive_file_with_emails(
                file_id=bulk_coupon_sheet.id,
                emails_to_share=settings.SHEETS_ADMIN_EMAILS,
                credentials=self._credentials,
            )
        return bulk_coupon_sheet

    def create_and_update_sheets(self, processed_requests):
        """
        Updates the coupon request sheet and creates a coupon assignment sheet for every successfully
        processed coupon request.

        Args:
            processed_requests (list of ProcessedRequest): List of ProcessedRequest objects

        Returns:
            list of pygsheets.Spreadsheet: Spreadsheet objects representing the spreadsheets that were
                created
        """
        # Set processed dates
        self.update_coupon_request_processed_dates(processed_requests)
        # Write new assignment sheets with coupon codes
        return [
            self.create_coupon_assignment_sheet(processed_request.coupon_req_row)
            for processed_request in processed_requests
        ]

    def process_sheet(self, limit_row_index=None):
        """
        Attempts to process the coupon request Sheet. This involves parsing rows in the spreadsheet,
        creating coupons, creating coupon assignment Sheets for rows that were successfully processed, and
        updating the coupon request Sheet with information about what succeeded and what failed.

        Args:
            limit_row_index (int or None): The row index of the specific coupon request Sheet row that
                should be processed. If None, this function will attempt to process all unprocessed rows
                in the Sheet.

        Returns:
            dict: A dictionary indicating the results of processing the coupon request Sheet
        """
        enumerated_data_rows = get_enumerated_data_rows(
            self.coupon_request_sheet, limit_row_index=limit_row_index
        )
        processed_requests, failed_requests, ignored_requests, unrecorded_complete_requests = self.parse_rows_and_create_coupons(
            enumerated_data_rows
        )
        results = {}
        if processed_requests:
            new_spreadsheets = self.create_and_update_sheets(processed_requests)
            results["processed_requests"] = {
                "rows": [
                    processed_request.row_index
                    for processed_request in processed_requests
                ],
                "assignment_sheets": [
                    spreadsheet.title for spreadsheet in new_spreadsheets
                ],
            }
        if failed_requests:
            self.update_coupon_request_errors(failed_requests)
            results["failed_request_rows"] = [
                request.row_index for request in failed_requests
            ]
        if ignored_requests:
            log.warning(
                "Ignored request rows in the coupon request sheet: %s",
                [
                    (req.row_index, req.coupon_req_row.purchase_order_id, req.reason)
                    for req in ignored_requests
                ],
            )
            results["ignored_request_rows"] = [
                request.row_index for request in ignored_requests
            ]
        if unrecorded_complete_requests:
            self.update_coupon_request_processed_dates(unrecorded_complete_requests)
            results["synced_request_rows"] = [
                request.row_index for request in unrecorded_complete_requests
            ]
        return results


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
                data_rows, start=coupon_assign_sheet_spec.first_data_row
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

    def process_assignment_spreadsheet(self, worksheet, bulk_assignment, last_modified):
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
