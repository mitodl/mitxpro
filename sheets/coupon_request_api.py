"""Coupon request API"""
import itertools
from collections import defaultdict
import json
from decimal import Decimal
import logging

from django.conf import settings
from django.db import transaction

from courses.models import CourseRun, Program
import ecommerce.api
from ecommerce.models import Company, Coupon, CouponPaymentVersion
from mitxpro.utils import now_in_utc, item_at_index_or_none
from sheets.api import (
    get_authorized_pygsheets_client,
    share_drive_file_with_emails,
    create_or_renew_sheet_file_watch,
)
from sheets.exceptions import (
    SheetOutOfSyncException,
    SheetCouponCreationException,
    SheetRowParsingException,
    InvalidSheetProductException,
    SheetValidationException,
)
from sheets.models import CouponGenerationRequest
from sheets.utils import (
    FailedRequest,
    ProcessedRequest,
    IgnoredRequest,
    format_datetime_for_sheet_formula,
    build_protected_range_request_body,
    assignment_sheet_file_name,
    get_enumerated_data_rows,
    parse_sheet_datetime_str,
    request_sheet_metadata,
    assign_sheet_metadata,
)

log = logging.getLogger(__name__)

BULK_PURCHASE_DEFAULTS = dict(amount=Decimal("1.0"), automatic=False)


def create_coupons_for_request_row(coupon_req_row, company_id):
    """
    Creates coupons for a given request

    Args:
        coupon_req_row (sheets.coupon_request_api.CouponRequestRow): A representation of a coupon request row
        company_id (int): The id of the Company on whose behalf these coupons are being created

    Returns:
        CouponPaymentVersion:
            A CouponPaymentVersion. Other instances will be created at the same time and linked via foreign keys.
    """
    product, _, program_run = ecommerce.api.get_product_from_text_id(
        coupon_req_row.product_text_id
    )
    product_program_run_map = {product.id: program_run.id} if program_run else None
    return ecommerce.api.create_coupons(
        name=coupon_req_row.coupon_name,
        product_ids=[product.id],
        num_coupon_codes=coupon_req_row.num_codes,
        coupon_type=CouponPaymentVersion.SINGLE_USE,
        max_redemptions=1,
        company_id=company_id,
        activation_date=coupon_req_row.activation,
        expiration_date=coupon_req_row.expiration,
        payment_type=CouponPaymentVersion.PAYMENT_PO,
        payment_transaction=coupon_req_row.purchase_order_id,
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
        error,
        requester=None,
    ):  # pylint: disable=too-many-arguments
        self.row_index = row_index
        self.purchase_order_id = purchase_order_id
        self.coupon_name = coupon_name
        self.num_codes = num_codes
        self.product_text_id = product_text_id
        self.company_name = company_name
        self.activation = activation
        self.expiration = expiration
        self.date_processed = date_processed
        self.error = error
        self.requester = requester

    @classmethod
    def parse_raw_data(cls, row_index, raw_row_data):
        """
        Parses raw row data

        Args:
            row_index (int): The row index according to the spreadsheet (not zero-based)
            raw_row_data (list of str): The raw row data

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
                error=item_at_index_or_none(
                    raw_row_data, request_sheet_metadata.ERROR_COL
                ),
            )
        except Exception as exc:
            raise SheetRowParsingException(str(exc)) from exc

    def get_product_id(self):
        """
        Gets the id for the most recently-created product associated with the CourseRun/Program indicated
        by this row.

        Returns:
            int: The most recently-created product ID for the object indicated by the text ID in the spreadsheet
        """
        for product_object_cls in [CourseRun, Program]:
            product_object = (
                product_object_cls.objects.live()
                .with_text_id(self.product_text_id)
                .prefetch_related("products")
                .first()
            )
            if product_object:
                break
        product = (
            None
            if not product_object
            else product_object.products.order_by("-created_on").first()
        )
        if not product_object:
            raise InvalidSheetProductException(
                "Could not find a CourseRun or Program with text id '%s'"
                % self.product_text_id
            )
        elif not product:
            raise InvalidSheetProductException(
                "No Products associated with %s" % str(product_object)
            )
        return product.id


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
            coupon_name = row_data[request_sheet_metadata.COUPON_NAME_COL_INDEX].strip()
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
        coupon_name = row_data[request_sheet_metadata.COUPON_NAME_COL_INDEX].strip()
        purchase_order_id = row_data[
            request_sheet_metadata.PURCHASE_ORDER_COL_INDEX
        ].strip()
        user_input_json = json.dumps(
            request_sheet_metadata.get_form_input_columns(row_data)
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
            crange="A1:{}1".format(assign_sheet_metadata.LAST_COL_LETTER),
            values=[assign_sheet_metadata.column_headers],
        )
        # Write data to body of worksheet
        worksheet.update_values(
            crange="A{}:A{}".format(
                assign_sheet_metadata.first_data_row,
                len(coupon_codes) + assign_sheet_metadata.first_data_row,
            ),
            values=[[coupon_code] for coupon_code in coupon_codes],
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
        if limit_row_index is None:
            enumerated_data_rows = get_enumerated_data_rows(self.coupon_request_sheet)
        else:
            enumerated_data_rows = [
                (limit_row_index, self.coupon_request_sheet.get_row(limit_row_index))
            ]
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
