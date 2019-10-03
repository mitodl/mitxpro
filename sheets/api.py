import re
import pickle
import datetime
import pytz
from collections import namedtuple
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from courses.models import CourseRun, Program
from courses.constants import CONTENT_TYPE_MODEL_COURSERUN, CONTENT_TYPE_MODEL_PROGRAM
from ecommerce.api import create_coupons
from ecommerce.models import Company, CouponPaymentVersion
from sheets.models import GoogleToken
from sheets.utils import namedtuple_from_array

SHEET_DATE_FORMAT = "%m/%d/%Y %H:%M:%S"
BULK_PURCHASE_DEFAULTS = dict(
    amount=Decimal("1.0"),
    automatic=False
)

SpreadsheetSpec = namedtuple("SpreadsheetSpec", ["first_data_row", "last_data_column"])

coupon_gen_sheet_spec = SpreadsheetSpec(
    first_data_row=2,
    last_data_column="G"
)
CouponGenerationRow = namedtuple(
    "CouponGenerationRow", [
        "trans_id",
        "coupon_name",
        "num_codes",
        "product_text_id",
        "product_type",
        "expires",
        "company"
    ]
)


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


def get_full_data_range(spreadsheet_spec):
    return "A{}:{}".format(spreadsheet_spec.first_data_row, spreadsheet_spec.last_data_column)


class SheetsClient:
    def __init__(self):
        self.service = self._get_service()

    @staticmethod
    def _get_service():
        creds = get_valid_google_creds()
        return build('sheets', 'v4', credentials=creds).spreadsheets()

    def read_rows(self, spreadsheet_id, spreadsheet_spec):
        result = self.service.values().get(
            spreadsheetId=spreadsheet_id,
            range=get_full_data_range(spreadsheet_spec)
        ).execute()
        row_arrays = result.get("values", [])
        yield from row_arrays


def get_coupon_gen_rows():
    sheets = SheetsClient()
    coupon_rows = sheets.read_rows(
        settings.COUPON_GENERATION_SHEET_ID,
        coupon_gen_sheet_spec
    )
    return [
        namedtuple_from_array(CouponGenerationRow, coupon_row)
        for coupon_row in coupon_rows
    ]


def get_product_model_cls(product_type_str):
    simplified = re.sub(r"\s", "", product_type_str.lower())
    if simplified == CONTENT_TYPE_MODEL_COURSERUN:
        return CourseRun
    elif simplified == CONTENT_TYPE_MODEL_PROGRAM:
        return Program
    raise ValueError


def get_product_ids(coupon_gen_row):
    product_model_cls = get_product_model_cls(coupon_gen_row.product_type)
    product_object = (
        product_model_cls.objects
        .live()
        .with_text_id(coupon_gen_row.product_text_id)
        .prefetch_related("products")
        .first()
    )
    product = product_object.products.first()
    return [product.id]


def create_coupons_from_row(coupon_gen_row):
    return create_coupons(
        name=coupon_gen_row.coupon_name,
        product_ids=get_product_ids(coupon_gen_row),
        num_coupon_codes=int(coupon_gen_row.num_codes),
        coupon_type=CouponPaymentVersion.SINGLE_USE,
        # ???
        max_redemptions=int(coupon_gen_row.num_codes),
        company_id=Company.objects.get(name=coupon_gen_row.company).id,
        expiration_date=datetime.datetime.strptime(coupon_gen_row.expires, SHEET_DATE_FORMAT).astimezone(pytz.UTC),
        payment_type=CouponPaymentVersion.PAYMENT_PO,
        payment_transaction=coupon_gen_row.trans_id,
        **BULK_PURCHASE_DEFAULTS,
    )
