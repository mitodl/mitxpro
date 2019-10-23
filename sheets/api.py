"""API for the Sheets app"""
import os
import re
import datetime
import pytz
from collections import namedtuple
from decimal import Decimal
import pickle
import logging

from django.conf import settings
from django.db import transaction
from django.core.exceptions import ImproperlyConfigured

# NOTE: Due to an unresolved bug (https://github.com/PyCQA/pylint/issues/2108), the
# `google` package (and other packages without an __init__.py file) will break pylint.
# The `disable-all` rules are here until that bug is fixed.
from google.oauth2.credentials import Credentials  # pylint: disable-all
from google.auth.transport.requests import Request  # pylint: disable-all
import pygsheets

from courses.models import CourseRun, Program
from courses.constants import CONTENT_TYPE_MODEL_COURSERUN, CONTENT_TYPE_MODEL_PROGRAM
from ecommerce.api import create_coupons
from ecommerce.models import Company, CouponPaymentVersion, Coupon
from sheets.models import CouponGenerationRequest, GoogleApiAuth
from sheets.constants import GOOGLE_TOKEN_URI, REQUIRED_GOOGLE_API_SCOPES

log = logging.getLogger(__name__)

BULK_PURCHASE_DEFAULTS = dict(amount=Decimal("1.0"), automatic=False)
DEV_TOKEN_PATH = "localdev/google.token"

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


class CouponRequestRow:
    """Represents a row of a coupon request sheet"""

    PROCESSED_COLUMN = "I"

    def __init__(
        self,
        transaction_id,
        coupon_name,
        num_codes,
        product_text_id,
        product_object_cls,
        activation,
        expiration,
        company_name,
        processed,
    ):
        self.transaction_id = transaction_id
        self.coupon_name = coupon_name
        self.num_codes = num_codes
        self.product_text_id = product_text_id
        self.product_object_cls = product_object_cls
        self.activation = activation
        self.expiration = expiration
        self.company_name = company_name
        self.processed = processed

    @classmethod
    def parse_raw_data(cls, raw_row_data):
        """
        Parses raw row data

        Args:
            raw_row_data (list of str): The raw row data

        Returns:
            CouponRequestRow: The parsed data row
        """
        return cls(
            transaction_id=raw_row_data[0],
            coupon_name=raw_row_data[1],
            num_codes=int(raw_row_data[2]),
            product_text_id=raw_row_data[3],
            product_object_cls=cls.get_product_model_cls(raw_row_data[4]),
            activation=cls.parse_raw_date_str(raw_row_data[5]),
            expiration=cls.parse_raw_date_str(raw_row_data[6]),
            company_name=raw_row_data[7],
            processed=(raw_row_data[8].lower() == "true"),
        )

    @staticmethod
    def parse_raw_date_str(raw_date_str):
        """
        Parses a string that represents a datetime and returns the datetime (or None)

        Args:
            raw_date_str (str): The datetime string

        Returns:
            datetime.datetime or None: The parsed datetime or None
        """
        return (
            datetime.datetime.strptime(
                raw_date_str, settings.COUPON_REQUEST_SHEET_DATE_FORMAT
            ).astimezone(pytz.UTC)
            if raw_date_str
            else None
        )

    @staticmethod
    def get_product_model_cls(product_type):
        """
        Given a string that represents a product type, returns the corresponding model class

        Args:
            product_type (str): String that represents a product type

        Returns:
            class: CourseRun or Program

        Raises:
            ValueError: Raised if the product type does not match either class
        """
        simplified_product_type = re.sub(r"\s", "", product_type.lower())
        if simplified_product_type == CONTENT_TYPE_MODEL_COURSERUN:
            return CourseRun
        elif simplified_product_type == CONTENT_TYPE_MODEL_PROGRAM:
            return Program
        raise ValueError(
            "Could not parse product type as course run or program (value: '{}')".format(
                product_type
            )
        )

    def get_product_ids(self):
        """
        Gets a single-item list of the first product associated with the CourseRun/Program indicated
        by this row. A list is returned so that it can be readily used by the `create_coupons` helper function.

        Returns:
            list of int: A list containing the product ID
        """
        product_object = (
            self.product_object_cls.objects.live()
            .with_text_id(self.product_text_id)
            .prefetch_related("products")
            .first()
        )
        product = product_object.products.first()
        return [product.id]


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
        # Refresh if necessary
        if creds.expired:
            creds.refresh(Request())
            GoogleApiAuth.objects.filter(id=google_api_auth.id).update(
                access_token=creds.token
            )
        return creds
    # For local development use only: you can use a locally-created token for auth.
    # This token can be created by following the Google API Python quickstart guide:
    # https://developers.google.com/sheets/api/quickstart/python.
    # A script with more helpful options than the one in that guide can be found here:
    # https://gist.github.com/gsidebo/b87abaafda3e79186c1e5f7f964074ab
    if settings.ENVIRONMENT == "dev":
        token_file_path = os.path.join(settings.BASE_DIR, DEV_TOKEN_PATH)
        if os.path.exists(token_file_path):
            return get_google_creds_from_pickled_token_file(token_file_path)
    raise ImproperlyConfigured("Authorization with Google has not been completed.")


def get_data_rows(worksheet):
    """
    Yields the data rows of a spreadsheet that has a header row

    Args:
        worksheet (pygsheets.worksheet.Worksheet): Worksheet object

    Yields:
        list of str: List of cell values in a given row
    """
    row_iter = iter(
        worksheet.get_all_values(
            include_tailing_empty=False, include_tailing_empty_rows=False
        )
    )
    # Skip header row
    next(row_iter)
    yield from row_iter


def create_coupons_for_request_row(coupon_req_row):
    """
    Creates coupons for a given request

    Args:
        coupon_req_row (CouponRequestRow): A representation of a coupon request row

    Returns:
        CouponGenerationRequest or None: The record of the completed coupon generation request, or None
            if the request for the given transaction id has already been completed.
    """
    with transaction.atomic():
        coupon_gen_request, created = CouponGenerationRequest.objects.select_for_update().get_or_create(
            transaction_id=coupon_req_row.transaction_id
        )
        if not created and coupon_gen_request.completed:
            log.error(
                "Found completed CouponGenerationRequest, but the 'processed' column "
                "in the spreadsheet == False (transaction id: %s)"
                % coupon_req_row.transaction_id
            )
            return
        create_coupons(
            name=coupon_req_row.coupon_name,
            product_ids=coupon_req_row.get_product_ids(),
            num_coupon_codes=coupon_req_row.num_codes,
            coupon_type=CouponPaymentVersion.SINGLE_USE,
            max_redemptions=1,
            company_id=Company.objects.get(name__iexact=coupon_req_row.company_name).id,
            activation_date=coupon_req_row.activation,
            expiration_date=coupon_req_row.expiration,
            payment_type=CouponPaymentVersion.PAYMENT_PO,
            payment_transaction=coupon_req_row.transaction_id,
            **BULK_PURCHASE_DEFAULTS,
        )
        coupon_gen_request.completed = True
        coupon_gen_request.save()
        return coupon_gen_request


class CouponRequestHandler:
    """Manages the processing of coupon requests from a Sheet"""

    def __init__(self):
        self._credentials = get_credentials()
        self.pygsheets_client = pygsheets.authorize(
            custom_credentials=self._credentials
        )
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
            if coupon_req_row.processed:
                continue
            coupon_gen_request = create_coupons_for_request_row(coupon_req_row)
            if coupon_gen_request:
                processed_requests.append(
                    ProcessedRequest(
                        row_index=row_index,
                        coupon_req_row=coupon_req_row,
                        request_id=coupon_gen_request.id,
                    )
                )
        return processed_requests

    def update_coupon_request_checkboxes(self, processed_requests):
        """
        For all processed request rows, programatically sets the "processed" column to checked/TRUE.

        Args:
            processed_requests (list of ProcessedRequest): A list of ProcessedRequest objects
        """
        for processed_request in processed_requests:
            self.coupon_request_sheet.update_value(
                "{}{}".format(
                    CouponRequestRow.PROCESSED_COLUMN, processed_request.row_index
                ),
                True,
            )

    def create_bulk_coupon_sheet(self, coupon_req_row):
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
        spreadsheet_title = "Bulk Coupons - {} {}".format(
            coupon_req_row.transaction_id, coupon_req_row.company_name
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
        # Share
        for email in settings.SHEETS_ADMIN_EMAILS:
            bulk_coupon_sheet.share(email, type="user", role="writer")

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
        self.update_coupon_request_checkboxes(processed_requests)
        # Write new sheets with codes
        for processed_request in processed_requests:
            self.create_bulk_coupon_sheet(processed_request.coupon_req_row)
