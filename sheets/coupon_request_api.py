"""Coupon request API"""
import itertools
import json
from decimal import Decimal
import logging

from django.conf import settings
from django.db import transaction
from django.utils.functional import cached_property

import ecommerce.api
from ecommerce.models import Company, Coupon, CouponPaymentVersion, BulkCouponAssignment
from ecommerce.utils import make_checkout_url
from mitxpro.utils import now_in_utc, item_at_index_or_none, item_at_index_or_blank
from sheets.api import (
    get_authorized_pygsheets_client,
    share_drive_file_with_emails,
    create_or_renew_sheet_file_watch,
)
from sheets.constants import GOOGLE_API_TRUE_VAL
from sheets.exceptions import SheetRowParsingException
from sheets.models import CouponGenerationRequest
from sheets.sheet_handler_api import SheetHandler
from sheets.utils import (
    RowResult,
    format_datetime_for_sheet_formula,
    build_protected_range_request_body,
    assignment_sheet_file_name,
    parse_sheet_datetime_str,
    request_sheet_metadata,
    assign_sheet_metadata,
    ResultType,
    get_column_letter,
)

log = logging.getLogger(__name__)

BULK_PURCHASE_DEFAULTS = dict(amount=Decimal("1.0"), automatic=False)


def create_coupons_for_request_row(row, company_id):
    """
    Creates coupons for a given request

    Args:
        row (sheets.coupon_request_api.CouponRequestRow): A representation of a coupon request row
        company_id (int): The id of the Company on whose behalf these coupons are being created

    Returns:
        CouponPaymentVersion:
            A CouponPaymentVersion. Other instances will be created at the same time and linked via foreign keys.
    """
    product_program_run_map = (
        {row.product.id: row.program_run.id} if row.program_run else None
    )
    return ecommerce.api.create_coupons(
        name=row.coupon_name,
        product_ids=[row.product.id],
        num_coupon_codes=row.num_codes,
        coupon_type=CouponPaymentVersion.SINGLE_USE,
        max_redemptions=1,
        company_id=company_id,
        activation_date=row.activation,
        expiration_date=row.expiration,
        payment_type=CouponPaymentVersion.PAYMENT_PO,
        payment_transaction=row.purchase_order_id,
        product_program_run_map=product_program_run_map,
        **BULK_PURCHASE_DEFAULTS,
    )


class CouponRequestRow:  # pylint: disable=too-many-instance-attributes
    """Represents a row of a coupon request sheet"""

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
        errors,
        skip_row,
        requester,
    ):  # pylint: disable=too-many-arguments,too-many-locals
        self.row_index = row_index
        self.purchase_order_id = purchase_order_id
        self.coupon_name = coupon_name
        self.num_codes = num_codes
        self.product_text_id = product_text_id
        self.company_name = company_name
        self.activation = activation
        self.expiration = expiration
        self.date_processed = date_processed
        self.errors = errors
        self.skip_row = skip_row
        self.requester = requester
        #
        product, _, program_run = ecommerce.api.get_product_from_text_id(
            self.product_text_id
        )
        self.product = product
        self.program_run = program_run

    @classmethod
    def parse_raw_data(cls, row_index, raw_row_data):
        """
        Parses raw row data

        Args:
            row_index (int): The row index according to the spreadsheet (not zero-based)
            raw_row_data (List[str]): The raw row data

        Returns:
            CouponRequestRow: The parsed data row

        Raises:
            SheetRowParsingException: Raised if the row could not be parsed
        """
        try:
            return cls(
                row_index=row_index,
                purchase_order_id=raw_row_data[
                    request_sheet_metadata.PURCHASE_ORDER_COL_INDEX
                ].strip(),
                coupon_name=raw_row_data[
                    request_sheet_metadata.COUPON_NAME_COL_INDEX
                ].strip(),
                num_codes=int(raw_row_data[2]),
                product_text_id=raw_row_data[3].strip(),
                company_name=raw_row_data[4],
                activation=parse_sheet_datetime_str(
                    item_at_index_or_none(raw_row_data, 5)
                ),
                expiration=parse_sheet_datetime_str(
                    item_at_index_or_none(raw_row_data, 6)
                ),
                date_processed=parse_sheet_datetime_str(
                    item_at_index_or_none(
                        raw_row_data, request_sheet_metadata.PROCESSED_COL
                    )
                ),
                requester=item_at_index_or_none(
                    raw_row_data, settings.SHEETS_REQ_EMAIL_COL
                ),
                errors=item_at_index_or_none(
                    raw_row_data, request_sheet_metadata.ERROR_COL
                ),
                skip_row=item_at_index_or_none(
                    raw_row_data, request_sheet_metadata.SKIP_ROW_COL
                )
                == GOOGLE_API_TRUE_VAL,
            )
        except Exception as exc:
            raise SheetRowParsingException(str(exc)) from exc


def is_row_ignored_or_complete(raw_row_data):
    """
    Returns True if the data in the given row indicates that it is complete (processed) or should be ignored

    Args:
        raw_row_data (List[str]): The raw row data

    Returns:
        bool: True if the data in the given row indicates that it is complete (processed) or should be ignored
    """
    return item_at_index_or_blank(
        raw_row_data, request_sheet_metadata.SKIP_ROW_COL
    ).strip() == GOOGLE_API_TRUE_VAL or bool(
        item_at_index_or_none(raw_row_data, request_sheet_metadata.PROCESSED_COL)
    )


class CouponRequestHandler(SheetHandler):
    """Manages the processing of coupon requests from a Sheet"""

    def __init__(self):
        self.pygsheets_client = get_authorized_pygsheets_client()
        self._credentials = self.pygsheets_client.oauth
        self.spreadsheet = self.pygsheets_client.open_by_key(
            settings.COUPON_REQUEST_SHEET_ID
        )
        self.sheet_metadata = request_sheet_metadata

    @cached_property
    def worksheet(self):
        return self.spreadsheet.sheet1

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
            num_cols=assign_sheet_metadata.num_columns,
            warning_only=False,
            description="Header Row",
        )
        coupon_code_range_req = build_protected_range_request_body(
            worksheet_id=worksheet_id,
            start_row_index=assign_sheet_metadata.first_data_row - 1,
            num_rows=num_data_rows,
            start_col_index=0,
            num_cols=1,
            warning_only=False,
            description="Coupon Codes",
        )
        status_columns_range_req = build_protected_range_request_body(
            worksheet_id=worksheet_id,
            start_row_index=assign_sheet_metadata.first_data_row - 1,
            num_rows=num_data_rows,
            start_col_index=assign_sheet_metadata.STATUS_COL,
            num_cols=2,
            warning_only=True,
            description="Status Columns",
        )
        return self.pygsheets_client.sheet.batch_update(
            spreadsheet_id,
            [header_range_req, coupon_code_range_req, status_columns_range_req],
        )

    def create_assignment_sheet(self, coupon_req_row):
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
            crange="A1:{}1".format(assign_sheet_metadata.LAST_COL_LETTER),
            values=[assign_sheet_metadata.column_headers],
        )
        # Write enrollment codes to the appropriate column of the worksheet
        last_data_row_idx = len(coupon_codes) + assign_sheet_metadata.first_data_row
        worksheet.update_values(
            crange="{enroll_col_letter}{first_data_row}:{enroll_col_letter}{last_data_row}".format(
                enroll_col_letter=get_column_letter(
                    assign_sheet_metadata.ENROLL_CODE_COL
                ),
                first_data_row=assign_sheet_metadata.first_data_row,
                last_data_row=last_data_row_idx,
            ),
            values=[[coupon_code] for coupon_code in coupon_codes],
        )
        # Write enrollment URLs to the appropriate column of the worksheet
        product_coupon_iter = zip(
            itertools.repeat(coupon_req_row.product.id, len(coupon_codes)), coupon_codes
        )
        worksheet.update_values(
            crange="{enroll_url_letter}{first_data_row}:{enroll_url_letter}{last_data_row}".format(
                enroll_url_letter=get_column_letter(
                    assign_sheet_metadata.ENROLL_URL_COL
                ),
                first_data_row=assign_sheet_metadata.first_data_row,
                last_data_row=last_data_row_idx,
            ),
            values=[
                [make_checkout_url(product_id=product_id, code=coupon_code)]
                for product_id, coupon_code in product_coupon_iter
            ],
        )

        # Adjust code and email column widths to fit coupon codes and emails
        worksheet.adjust_column_width(start=0, end=2, pixel_size=270)
        # Format header cells with bold text
        header_range = worksheet.get_values(
            start="A1",
            end="{}1".format(assign_sheet_metadata.LAST_COL_LETTER),
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
        # If it doesn't exist, create bulk coupon assignment for tracking purposes
        BulkCouponAssignment.objects.create(assignment_sheet_id=bulk_coupon_sheet.id)

        # Share
        if settings.SHEETS_ADMIN_EMAILS:
            share_drive_file_with_emails(
                file_id=bulk_coupon_sheet.id,
                emails_to_share=settings.SHEETS_ADMIN_EMAILS,
                credentials=self._credentials,
            )
        # Set up webhook to monitor changes to this new assignment sheet
        create_or_renew_sheet_file_watch(
            assign_sheet_metadata, sheet_file_id=bulk_coupon_sheet.id
        )
        return bulk_coupon_sheet

    def update_completed_rows(self, success_row_results):
        for row_result in success_row_results:
            self.worksheet.update_values(
                crange="{date_processed_col}{row_index}:{error_col}{row_index}".format(
                    date_processed_col=self.sheet_metadata.PROCESSED_COL_LETTER,
                    error_col=self.sheet_metadata.ERROR_COL_LETTER,
                    row_index=row_result.row_index,
                ),
                values=[
                    [
                        format_datetime_for_sheet_formula(
                            row_result.row_db_record.date_completed.astimezone(
                                settings.SHEETS_DATE_TIMEZONE
                            )
                        ),
                        "",
                    ]
                ],
            )

    def post_process_results(self, grouped_row_results):
        # Create assignment sheets for all newly-processed rows
        processed_row_results = grouped_row_results.get(ResultType.PROCESSED, [])
        for row_result in processed_row_results:
            self.create_assignment_sheet(row_result.row_object)

    def get_or_create_request(self, row_data):
        coupon_name = row_data[self.sheet_metadata.COUPON_NAME_COL_INDEX].strip()
        purchase_order_id = row_data[
            self.sheet_metadata.PURCHASE_ORDER_COL_INDEX
        ].strip()
        user_input_json = json.dumps(
            self.sheet_metadata.get_form_input_columns(row_data)
        )
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
        return coupon_gen_request, created, raw_data_changed

    @staticmethod
    def validate_sheet(enumerated_rows):
        enumerated_data_rows_1, enumerated_data_rows_2 = itertools.tee(enumerated_rows)
        invalid_rows = []
        observed_coupon_names = set()
        invalid_coupon_name_row_dict = {}
        for row_index, row_data in enumerated_data_rows_1:
            coupon_name = row_data[request_sheet_metadata.COUPON_NAME_COL_INDEX].strip()
            if coupon_name in observed_coupon_names:
                invalid_coupon_name_row_dict[row_index] = coupon_name
            else:
                observed_coupon_names.add(coupon_name)

        # If any coupon names were found on multiple rows, create a failed request
        # object for each row with a non-unique coupon name (except for the row with the first instance
        # of that name).
        for row_index, coupon_name in invalid_coupon_name_row_dict.items():
            sheet_error_text = "Coupon name '{}' already exists in the sheet".format(
                coupon_name
            )
            invalid_rows.append(
                RowResult(
                    row_index=row_index,
                    row_db_record=None,
                    row_object=None,
                    message=sheet_error_text,
                    result_type=ResultType.FAILED,
                )
            )

        valid_data_rows = filter(
            lambda data_row_tuple: data_row_tuple[0]
            not in invalid_coupon_name_row_dict.keys(),
            enumerated_data_rows_2,
        )
        return valid_data_rows, invalid_rows

    def filter_ignored_rows(self, enumerated_rows):
        return filter(
            # If the "ignore" column is set to TRUE for this row, or it has already been processed,
            # it should be skipped
            lambda data_row_tuple: not is_row_ignored_or_complete(data_row_tuple[1]),
            enumerated_rows,
        )

    def process_row(
        self, row_index, row_data
    ):  # pylint: disable=too-many-return-statements
        coupon_gen_request, request_created, request_updated = self.get_or_create_request(
            row_data
        )
        try:
            coupon_req_row = CouponRequestRow.parse_raw_data(row_index, row_data)
        except SheetRowParsingException as exc:
            return RowResult(
                row_index=row_index,
                row_db_record=coupon_gen_request,
                row_object=None,
                result_type=ResultType.FAILED,
                message="Parsing failure: {}".format(str(exc)),
            )
        is_unchanged_error_row = (
            coupon_req_row.errors and not request_created and not request_updated
        )
        if is_unchanged_error_row:
            return RowResult(
                row_index=row_index,
                row_db_record=coupon_gen_request,
                row_object=None,
                result_type=ResultType.IGNORED,
                message=None,
            )
        elif (
            coupon_gen_request.date_completed and coupon_req_row.date_processed is None
        ):
            return RowResult(
                row_index=row_index,
                row_db_record=coupon_gen_request,
                row_object=None,
                result_type=ResultType.OUT_OF_SYNC,
                message=None,
            )

        company, created = Company.objects.get_or_create(
            name__iexact=coupon_req_row.company_name,
            defaults=dict(name=coupon_req_row.company_name),
        )
        if created:
            log.info("Created new Company '%s'...", coupon_req_row.company_name)
        create_coupons_for_request_row(coupon_req_row, company.id)
        coupon_gen_request.date_completed = now_in_utc()
        coupon_gen_request.save()
        return RowResult(
            row_index=row_index,
            row_db_record=coupon_gen_request,
            row_object=coupon_req_row,
            result_type=ResultType.PROCESSED,
            message=None,
        )
