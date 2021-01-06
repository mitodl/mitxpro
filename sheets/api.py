"""API for the Sheets app"""
import os
import json
import datetime
import pickle
import logging
from collections import namedtuple
from urllib.parse import urljoin

from django.conf import settings
from django.db import transaction
from django.core.exceptions import ImproperlyConfigured
import pygsheets

from google.oauth2.credentials import Credentials  # pylint:disable=no-name-in-module
from google.oauth2.service_account import (  # pylint:disable=no-name-in-module
    Credentials as ServiceAccountCredentials,
)
from google.auth.transport.requests import Request  # pylint:disable=no-name-in-module
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from mitxpro.utils import now_in_utc
from sheets.models import GoogleApiAuth, GoogleFileWatch, FileWatchRenewalAttempt
from sheets.constants import (
    GOOGLE_TOKEN_URI,
    REQUIRED_GOOGLE_API_SCOPES,
    GOOGLE_SERVICE_ACCOUNT_EMAIL_DOMAIN,
    GOOGLE_API_FILE_WATCH_KIND,
    GOOGLE_API_NOTIFICATION_TYPE,
    DEFAULT_GOOGLE_EXPIRE_TIMEDELTA,
    SHEET_TYPE_COUPON_REQUEST,
    SHEET_TYPE_ENROLL_CHANGE,
    WORKSHEET_TYPE_REFUND,
    SHEET_TYPE_COUPON_ASSIGN,
    SHEET_RENEWAL_RECORD_LIMIT,
)
from sheets.utils import (
    format_datetime_for_google_timestamp,
    google_timestamp_to_datetime,
    build_drive_file_email_share_request,
    CouponRequestSheetMetadata,
    RefundRequestSheetMetadata,
    CouponAssignSheetMetadata,
)
from sheets.exceptions import FailedBatchRequestException

log = logging.getLogger(__name__)

DEV_TOKEN_PATH = "localdev/google.token"
FileWatchSpec = namedtuple(
    "FileWatchSpec",
    ["sheet_metadata", "sheet_file_id", "channel_id", "handler_url", "force"],
)


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
            except:  # pylint: disable=bare-except
                log.exception(
                    "Failed to share the file with id '%s' with email '%s'",
                    file_id,
                    email_to_share,
                )


def request_file_watch(
    file_id, channel_id, handler_url, expiration=None, credentials=None
):
    """
    Sends a request to the Google API to watch for changes in a given file. If successful, this
    app will receive requests from Google when changes are made to the file.
    Ref: https://developers.google.com/drive/api/v3/reference/files/watch

    Args:
        file_id (str): The id of the file in Google Drive (can be determined from the URL)
        channel_id (str): Arbitrary string to identify the file watch being set up. This will
            be included in the header of every request Google sends to the app.
        handler_url (str): The URL stub for the xpro endpoint that should be called from Google's end when the file
            changes.
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
                "address": urljoin(settings.SITE_BASE_URL, handler_url),
                "payload": True,
                "kind": GOOGLE_API_FILE_WATCH_KIND,
                "type": GOOGLE_API_NOTIFICATION_TYPE,
                **extra_body_params,
            },
        )
        .execute()
    )


def _generate_channel_id(sheet_metadata, sheet_file_id=None, dt=None):
    """
    Generates a string channel id based on several spreadsheet attributes. The channel id is an identifier
    used in the Google file watch API.

    Args:
        sheet_metadata (SheetMetadata):
        sheet_file_id (str): The file id of the spreadsheet
        dt (Optional[datetime.datetime]): The date and time when the file watch was created

    Returns:
        str: The channel id to be used in the Google file watch API
    """
    dt = dt or now_in_utc()
    new_channel_id_segments = [
        settings.DRIVE_WEBHOOK_CHANNEL_ID,
        sheet_metadata.sheet_type,
        dt.strftime("%Y%m%d-%H%M%S"),
    ]
    if isinstance(sheet_metadata, CouponAssignSheetMetadata):
        new_channel_id_segments.insert(2, sheet_file_id)
    return "-".join(new_channel_id_segments)


def _track_file_watch_renewal(sheet_type, sheet_file_id, exception=None):
    """
    Creates a record of the attempt to update a Google file watch. This is used for
    debugging purposes as the renewal endpoint is flaky.

    Args:
        sheet_type (str): The type of spreadsheet
        sheet_file_id (str): The file id of the spreadsheet
        exception (Optional[Exception]): The exception raised when trying to renew the file watch
    """
    result = None
    result_status_code = None
    if exception is None:
        result_status_code = 200
    else:
        if isinstance(exception, HttpError):
            result_status_code = exception.resp.status
            exc_content = json.loads(exception.content.decode("utf-8"))
            if "error" in exc_content:
                result = exc_content["error"]["message"]
        if not result:
            result = str(exception)[0:300]
    FileWatchRenewalAttempt.objects.create(
        sheet_type=sheet_type,
        sheet_file_id=sheet_file_id,
        result=result,
        result_status_code=result_status_code,
    )
    # Clear out old records. We only need to keep a record of renewal attempts for debugging recent errors.
    existing_attempt_ids = (
        FileWatchRenewalAttempt.objects.filter(sheet_file_id=sheet_file_id)
        .order_by("-id")
        .values_list("id", flat=True)
    )
    if len(existing_attempt_ids) > SHEET_RENEWAL_RECORD_LIMIT:
        id_to_delete = existing_attempt_ids[SHEET_RENEWAL_RECORD_LIMIT]
        FileWatchRenewalAttempt.objects.filter(id__lte=id_to_delete).delete()


def create_or_renew_sheet_file_watch(sheet_metadata, force=False, sheet_file_id=None):
    """
    Creates or renews a file watch on a spreadsheet depending on the existence
    of other file watches and their expiration.

    Args:
        sheet_metadata (Type(sheets.utils.SheetMetadata)): The file watch metadata for the sheet
            that we want to create/renew the file watch for.
        force (bool): If True, make the file watch request and overwrite the GoogleFileWatch record
            even if an unexpired one exists.
        sheet_file_id (Optional[str]): (Optional) The id of the spreadsheet as it appears in the spreadsheet's
            URL. If the spreadsheet being watched is a singleton, this isn't necessary.

    Returns:
        (Optional[GoogleFileWatch], bool, bool): The GoogleFileWatch object (or None), a flag indicating
            whether or not it was newly created during execution, and a flag indicating
            whether or not it was updated during execution.
    """
    now = now_in_utc()
    sheet_file_id = sheet_file_id or sheet_metadata.sheet_file_id
    new_channel_id = _generate_channel_id(
        sheet_metadata, sheet_file_id=sheet_file_id, dt=now
    )
    handler_url = (
        sheet_metadata.handler_url_stub(file_id=sheet_file_id)
        if isinstance(sheet_metadata, CouponAssignSheetMetadata)
        else sheet_metadata.handler_url_stub()
    )
    min_fresh_expiration_date = now + datetime.timedelta(
        minutes=settings.DRIVE_WEBHOOK_RENEWAL_PERIOD_MINUTES
    )
    with transaction.atomic():
        file_watch, created = GoogleFileWatch.objects.select_for_update().get_or_create(
            file_id=sheet_file_id,
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
                "Current file watch in the database for %s is expired. "
                "Some file changes may have failed to trigger a push notification (%s, file id: %s)",
                sheet_metadata.sheet_name,
                file_watch,
                sheet_file_id,
            )
        expiration = now + datetime.timedelta(
            minutes=settings.DRIVE_WEBHOOK_EXPIRATION_MINUTES
        )
        try:
            resp_dict = request_file_watch(
                sheet_file_id, new_channel_id, handler_url, expiration=expiration
            )
        except HttpError as exc:
            _track_file_watch_renewal(
                sheet_metadata.sheet_type, sheet_file_id, exception=exc
            )
            return None, False, False
        else:
            _track_file_watch_renewal(sheet_metadata.sheet_type, sheet_file_id)
        log.info(
            "File watch request for push notifications on %s completed. Response: %s",
            sheet_metadata.sheet_name,
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


def get_sheet_metadata_from_type(sheet_type):
    """
    Gets sheet metadata associated with the given sheet type

    Args:
        sheet_type (str):

    Returns:
        type(sheets.utils.SheetMetadata): An object with metadata about some sheet type

    Raises:
         ValueError: Raised if there is no metadata class associated with the given sheet type
    """
    if sheet_type == SHEET_TYPE_COUPON_REQUEST:
        return CouponRequestSheetMetadata()
    elif sheet_type == SHEET_TYPE_COUPON_ASSIGN:
        return CouponAssignSheetMetadata()
    elif sheet_type in {SHEET_TYPE_ENROLL_CHANGE, WORKSHEET_TYPE_REFUND}:
        return RefundRequestSheetMetadata()
    raise ValueError(f"No sheet metadata exists matching the type '{sheet_type}'")
