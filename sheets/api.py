import re
import pickle
import datetime
import pytz
import itertools
from collections import namedtuple
from decimal import Decimal
import logging

from django.conf import settings
from django.db import transaction
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import gspread

from courses.models import CourseRun, Program
from courses.constants import CONTENT_TYPE_MODEL_COURSERUN, CONTENT_TYPE_MODEL_PROGRAM
from ecommerce.api import create_coupons
from ecommerce.models import Company, CouponPaymentVersion, Coupon
from sheets.models import GoogleToken, CouponGenerationRequest

log = logging.getLogger(__name__)

SHEET_DATE_FORMAT = "%m/%d/%Y %H:%M:%S"
BULK_PURCHASE_DEFAULTS = dict(
    amount=Decimal("1.0"),
    automatic=False
)
API_CLIENT_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

SpreadsheetSpec = namedtuple(
    "SpreadsheetSpec", ["first_data_row", "last_data_column", "num_columns", "column_headers"]
)
coupon_request_sheet_spec = SpreadsheetSpec(
    first_data_row=2,
    last_data_column="I",
    num_columns=9,
    column_headers=[],
)
coupon_assign_sheet_spec = SpreadsheetSpec(
    first_data_row=2,
    last_data_column="B",
    num_columns=2,
    column_headers=["Coupon Code", "Email (Assignee)"],
)
ProcessedRequest = namedtuple("ProcessedRequest", ["row_index", "coupon_gen_row", "request_id"])


class CouponGenRow:
    PROCESSED_COLUMN = "I"

    def __init__(self, raw_row_data):
        self.transaction_id = raw_row_data[0]
        self.coupon_name = raw_row_data[1]
        self.num_codes = int(raw_row_data[2])
        self.product_text_id = raw_row_data[3]
        self.product_object_cls = self.get_product_model_cls(raw_row_data[4])
        self.activation = self.parse_raw_date_str(raw_row_data[5])
        self.expiration = self.parse_raw_date_str(raw_row_data[6])
        self.company_name = raw_row_data[7]
        self.processed = raw_row_data[8].lower() == "true"

    @staticmethod
    def parse_raw_date_str(raw_date_str):
        return datetime.datetime.strptime(raw_date_str, SHEET_DATE_FORMAT).astimezone(pytz.UTC)

    @staticmethod
    def get_product_model_cls(product_type):
        simplified_product_type = re.sub(r"\s", "", product_type.lower())
        if simplified_product_type == CONTENT_TYPE_MODEL_COURSERUN:
            return CourseRun
        elif simplified_product_type == CONTENT_TYPE_MODEL_PROGRAM:
            return Program
        raise ValueError

    def get_product_ids(self):
        product_object = (
            self.product_object_cls.objects
                .live()
                .with_text_id(self.product_text_id)
                .prefetch_related("products")
                .first()
        )
        product = product_object.products.first()
        return [product.id]


class GSpreadCredentials:
    def __init__(self, google_token):
        self._creds = get_valid_google_creds()
        self.access_token = self._creds.token

    def refresh(self, http):
        self._creds = get_valid_google_creds()
        self.access_token = self._creds.token


def get_valid_google_creds():
    with transaction.atomic():
        token = GoogleToken.objects.select_for_update().first()
        creds = pickle.loads(token.value)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token.value = pickle.dumps(creds)
            token.save()
    assert creds and creds.valid
    return creds


def get_gspread_client_from_pickled_token():
    google_token = GoogleToken.objects.first()
    gspread_creds = GSpreadCredentials(google_token)
    return gspread.authorize(gspread_creds)


def gen_data_rows(worksheet):
    row_iter = iter(worksheet.get_all_values())
    # Skip header row
    next(row_iter)
    yield from row_iter


class CouponRequestHandler:
    def __init__(self):
        self.gspread_client = get_gspread_client_from_pickled_token()
        spreadsheet = self.gspread_client.open_by_key(settings.COUPON_GENERATION_SHEET_ID)
        self.coupon_request_sheet = spreadsheet.sheet1

    def create_coupons_from_sheet(self):
        coupon_gen_rows = (
            CouponGenRow(row_data) for row_data in gen_data_rows(self.coupon_request_sheet)
        )
        for row_index, coupon_gen_row in enumerate(coupon_gen_rows, start=2):
            if coupon_gen_row.processed:
                continue
            with transaction.atomic():
                coupon_gen_request, created = CouponGenerationRequest.objects.select_for_update().get_or_create(
                    transaction_id=coupon_gen_row.transaction_id
                )
                if not created and coupon_gen_request.completed:
                    continue
                create_coupons(
                    name=coupon_gen_row.coupon_name,
                    product_ids=coupon_gen_row.get_product_ids(),
                    num_coupon_codes=coupon_gen_row.num_codes,
                    coupon_type=CouponPaymentVersion.SINGLE_USE,
                    # ???
                    max_redemptions=coupon_gen_row.num_codes,
                    company_id=Company.objects.get(name=coupon_gen_row.company_name).id,
                    activation_date=coupon_gen_row.activation,
                    expiration_date=coupon_gen_row.expiration,
                    payment_type=CouponPaymentVersion.PAYMENT_PO,
                    payment_transaction=coupon_gen_row.transaction_id,
                    **BULK_PURCHASE_DEFAULTS,
                )
                coupon_gen_request.completed = True
                coupon_gen_request.save()
                yield ProcessedRequest(
                    row_index=row_index,
                    coupon_gen_row=coupon_gen_row,
                    request_id=coupon_gen_request.id
                )

    def update_coupon_request_sheet(self, processed_requests):
        update_cells = []
        for processed_request in processed_requests:
            processed_cell = self.coupon_request_sheet.acell(
                "{}{}".format(CouponGenRow.PROCESSED_COLUMN, processed_request.row_index)
            )
            processed_cell.value = True
            update_cells.append(processed_cell)
        self.coupon_request_sheet.update_cells(update_cells)

    def move_file_to_folder(self, file_id, to_folder_id, from_folder_id=None):
        from_folder_id = from_folder_id or settings.BASE_DRIVE_FOLDER_ID
        url = "https://www.googleapis.com/drive/v3/files/{}".format(file_id)
        return self.gspread_client.request(
            "patch",
            url,
            params={
                "addParents": to_folder_id,
                "removeParents": from_folder_id,
            },
            json={}
        )

    def create_bulk_coupon_sheet(self, coupon_gen_row):
        # Get coupon codes created by the request
        coupon_codes = (
            Coupon.objects
            .filter(payment__name=coupon_gen_row.coupon_name)
            .values_list("coupon_code", flat=True)
        )
        if not coupon_codes:
            return
        # Create sheet
        spreadsheet_title = "Bulk Coupons - {} {}".format(
            coupon_gen_row.transaction_id,
            coupon_gen_row.company_name
        )
        bulk_coupon_sheet = self.gspread_client.create(spreadsheet_title)
        worksheet = bulk_coupon_sheet.sheet1
        # Add headers
        header_cells = worksheet.range("A1:{}1".format(coupon_assign_sheet_spec.last_data_column))
        for i, header_text in enumerate(coupon_assign_sheet_spec.column_headers):
            header_cells[i].value = header_text
        worksheet.update_cells(header_cells)
        # Write data to body of worksheet
        coupon_code_cells = worksheet.range("A{}:A{}".format(
            coupon_assign_sheet_spec.first_data_row,
            len(coupon_codes) + coupon_assign_sheet_spec.first_data_row
        ))
        for i, coupon_code in enumerate(coupon_codes):
            coupon_code_cells[i].value = coupon_code
        worksheet.update_cells(coupon_code_cells)
        # Move to desired drive folder
        if settings.SHEETS_OUTPUT_FOLDER_ID:
            self.move_file_to_folder(bulk_coupon_sheet.id, to_folder_id=settings.SHEETS_OUTPUT_FOLDER_ID)
        # Share
        for email in settings.SHEETS_ADMIN_EMAILS:
            bulk_coupon_sheet.share(email, perm_type="user", role="writer")

        return bulk_coupon_sheet

    def write_results_to_sheets(self, processed_requests):
        # Set checkboxes
        processed_requests_1, processed_requests_2 = itertools.tee(processed_requests)
        self.update_coupon_request_sheet(processed_requests_1)
        # Write new sheets with codes
        for processed_request in processed_requests_2:
            self.create_bulk_coupon_sheet(processed_request.coupon_gen_row)
