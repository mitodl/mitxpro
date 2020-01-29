"""Enrollment refund API"""
import json
import operator as op
import logging

from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from courses.api import deactivate_program_enrollment, deactivate_run_enrollment
from courses.constants import ENROLL_CHANGE_STATUS_REFUNDED
from courses.models import CourseRunEnrollment, ProgramEnrollment
from courses.utils import is_program_text_id
from ecommerce.models import Order
from mitxpro.utils import group_into_dict, now_in_utc
from sheets.api import get_authorized_pygsheets_client
from sheets.constants import (
    REFUND_SHEET_ORDER_TYPE_PAID,
    REFUND_SHEET_ORDER_TYPE_FULL_COUPON,
    REFUND_SHEET_PROCESSOR_NAME,
    GOOGLE_API_TRUE_VAL,
)
from sheets.exceptions import SheetRowParsingException
from sheets.models import RefundRequest
from sheets.utils import (
    ResultType,
    RowResult,
    clean_sheet_value,
    get_data_rows_after_start,
    format_datetime_for_sheet_formula,
    parse_sheet_date_only_str,
    refund_sheet_metadata,
)

log = logging.getLogger(__name__)
User = get_user_model()


class RefundRequestRow:  # pylint: disable=too-many-instance-attributes
    """Represents a row of the refund request sheet"""

    def __init__(
        self,
        row_index,
        response_id,
        request_date,
        learner_email,
        zendesk_ticket_no,
        requester_email,
        product_id,
        order_id,
        order_type,
        finance_email,
        finance_approve_date,
        finance_notes,
        refund_processor,
        refund_complete_date,
        errors,
        skip_row,
    ):  # pylint: disable=too-many-arguments,too-many-locals
        self.row_index = row_index
        self.response_id = response_id
        self.request_date = request_date
        self.learner_email = learner_email
        self.zendesk_ticket_no = zendesk_ticket_no
        self.requester_email = requester_email
        self.product_id = product_id
        self.order_id = order_id
        self.order_type = order_type
        self.finance_email = finance_email
        self.finance_approve_date = finance_approve_date
        self.finance_notes = finance_notes
        self.refund_processor = refund_processor
        self.refund_complete_date = refund_complete_date
        self.errors = errors
        self.skip_row = skip_row

    @classmethod
    def parse_raw_data(cls, row_index, raw_row_data):
        """
        Parses raw row data

        Args:
            row_index (int): The row index according to the spreadsheet (not zero-based)
            raw_row_data (list of str): The raw row data

        Raises:
            SheetRowParsingException: Raised if the row could not be parsed
        """
        raw_row_data = list(map(clean_sheet_value, raw_row_data))
        try:
            return cls(
                row_index=row_index,
                response_id=int(
                    raw_row_data[refund_sheet_metadata.FORM_RESPONSE_ID_COL]
                ),
                request_date=raw_row_data[1],
                learner_email=raw_row_data[2],
                zendesk_ticket_no=raw_row_data[3],
                requester_email=raw_row_data[4],
                product_id=raw_row_data[5],
                order_id=int(raw_row_data[6]),
                order_type=raw_row_data[7],
                finance_email=raw_row_data[8],
                finance_approve_date=parse_sheet_date_only_str(raw_row_data[9]),
                finance_notes=raw_row_data[10],
                refund_processor=raw_row_data[
                    refund_sheet_metadata.REFUND_PROCESSOR_COL
                ],
                refund_complete_date=parse_sheet_date_only_str(
                    raw_row_data[refund_sheet_metadata.REFUND_COMPLETED_DATE_COL]
                ),
                errors=raw_row_data[refund_sheet_metadata.ERROR_COL],
                skip_row=(
                    raw_row_data[refund_sheet_metadata.SKIP_ROW_COL]
                    == GOOGLE_API_TRUE_VAL
                ),
            )
        except Exception as exc:
            raise SheetRowParsingException(str(exc)) from exc


class RefundRequestHandler:
    """Manages the processing of refund requests from a spreadsheet"""

    def __init__(self):
        self.pygsheets_client = get_authorized_pygsheets_client()
        spreadsheet = self.pygsheets_client.open_by_key(
            settings.ENROLLMENT_CHANGE_SHEET_ID
        )
        self.refund_request_sheet = spreadsheet.worksheet(
            "id", value=settings.REFUND_REQUEST_WORKSHEET_ID
        )

    def get_non_legacy_rows(self):
        """
        Fetches raw data rows in the refund request sheet, excluding "legacy" rows.
        In other words, just the rows that have been created since we started automatically processing
        refund requests from the spreadsheet.

        Returns:
            iterable of (int, iterable of (str)): Enumerated raw data rows in the refund request sheet,
                excluding "legacy" rows
        """
        return enumerate(
            get_data_rows_after_start(
                self.refund_request_sheet,
                start_row=settings.SHEETS_REFUND_FIRST_ROW,
                start_col=1,
                end_col=refund_sheet_metadata.num_columns,
            ),
            start=settings.SHEETS_REFUND_FIRST_ROW,
        )

    def update_row_completed_dates(self, row_results):
        """
        For all successfully-processed rows, programatically sets the completion date column and
        blanks the error column.

        Args:
            row_results (iterable of RowResult): Objects representing the results of processing a row
        """
        for row_result in row_results:
            self.refund_request_sheet.update_values(
                crange="{processor_col}{row_index}:{error_col}{row_index}".format(
                    processor_col=refund_sheet_metadata.REFUND_PROCESSOR_COL_LETTER,
                    error_col=refund_sheet_metadata.ERROR_COL_LETTER,
                    row_index=row_result.row_index,
                ),
                values=[
                    [
                        REFUND_SHEET_PROCESSOR_NAME,
                        format_datetime_for_sheet_formula(
                            row_result.row_db_record.date_completed.astimezone(
                                settings.SHEETS_DATE_TIMEZONE
                            )
                        ),
                        "",
                    ]
                ],
            )

    def update_row_errors(self, failed_row_results):
        """
        For all rows that could not be processed, sets the error column value to an error message.

        Args:
            failed_row_results (iterable of RowResult): Objects representing the results of processing a row
        """
        for row_result in failed_row_results:
            self.refund_request_sheet.update_value(
                "{}{}".format(
                    refund_sheet_metadata.ERROR_COL_LETTER, row_result.row_index
                ),
                row_result.message,
            )

    @staticmethod
    def get_or_create_request(row_data):
        """
        Ensures that an object exists in the database that represents the given refund request, and
        that it reflects the correct state based on the data in the spreadsheet row.

        Args:
            row_data (list of str): Raw data from a row in the spreadsheet

        Returns:
            (RefundRequest, bool, bool): A tuple containing an object representing the refund request,
                a flag that indicates whether or not it was newly created, and a flag that indicates
                whether or not it was updated.
        """
        form_response_id = int(
            row_data[refund_sheet_metadata.FORM_RESPONSE_ID_COL].strip()
        )
        user_input_json = json.dumps(
            refund_sheet_metadata.get_form_input_columns(row_data)
        )
        with transaction.atomic():
            refund_request, created = RefundRequest.objects.select_for_update().get_or_create(
                form_response_id=form_response_id,
                defaults=dict(raw_data=user_input_json),
            )
            raw_data_changed = refund_request.raw_data != user_input_json
            if raw_data_changed:
                refund_request.raw_data = user_input_json
                refund_request.save()
        return refund_request, created, raw_data_changed

    @staticmethod
    def get_order_objects(refund_req_row):
        """
        Fetches all of the database objects relevant to this refund request

        Args:
            refund_req_row (RefundRequestRow): An object representing a row in the spreadsheet

        Returns:
            (Order, ProgramEnrollment or CourseRunEnrollment): The order and enrollment associated
                with this refund request.
        """
        user = User.objects.get(email=refund_req_row.learner_email)
        order = Order.objects.get(id=refund_req_row.order_id, purchaser=user)
        if is_program_text_id(refund_req_row.product_id):
            enrollment = ProgramEnrollment.all_objects.get(
                order=order, program__readable_id=refund_req_row.product_id
            )
        else:
            enrollment = CourseRunEnrollment.all_objects.get(
                order=order, run__courseware_id=refund_req_row.product_id
            )
        return order, enrollment

    @staticmethod
    def reverse_order_and_enrollments(order, enrollment):
        """
        Sets the state of the given order and enrollment(s) to reflect that they have
        been refunded and are no longer active

        Args:
            order (Order):
            enrollment (ProgramEnrollment or CourseRunEnrollment):
        """
        if isinstance(enrollment, ProgramEnrollment):
            deactivate_program_enrollment(
                enrollment, change_status=ENROLL_CHANGE_STATUS_REFUNDED
            )
        else:
            deactivate_run_enrollment(
                enrollment, change_status=ENROLL_CHANGE_STATUS_REFUNDED
            )
        order.status = Order.REFUNDED
        order.save_and_log(acting_user=None)

    @staticmethod
    def is_ready_for_reversal(refund_req_row):
        """
        Returns True if the state of given row indicates that the refund request can be processed
        and the order/enrollments can be reversed.

        Args:
            refund_req_row (RefundRequestRow): The parsed refund request row

        Returns:
            bool: True if the order/enrollments associated with this row can be reversed
        """
        if refund_req_row.refund_complete_date is not None:
            return False
        return (
            # A request is ready to be refunded if the order was made with a full-price coupon
            # and no money was paid
            refund_req_row.order_type == REFUND_SHEET_ORDER_TYPE_FULL_COUPON
            or (
                # A request is also ready to be refunded if the order was completed with some payment,
                # and a member of the finance team has manually filled in certain columns in the request
                # spreadsheet indicating that the payment was refunded via our ecommerce provider.
                refund_req_row.order_type == REFUND_SHEET_ORDER_TYPE_PAID
                and refund_req_row.finance_email is not None
                and refund_req_row.finance_approve_date is not None
            )
        )

    def process_row(
        self, row_index, row_data
    ):  # pylint: disable=too-many-return-statements
        """
        Ensures that the given spreadsheet row is correctly represented in the database,
        attempts to parse it, reverses/refunds the given enrollment if appropriate, and returns the
        result of processing the row.

        Args:
            row_index (int): The row index according to the spreadsheet
            row_data (list of str): The raw data of the given spreadsheet row

        Returns:
            RowResult or None: An object representing the results of processing the row, or None if
                nothing needs to be done with this row.
        """
        refund_request, request_created, request_updated = self.get_or_create_request(
            row_data
        )
        try:
            refund_req_row = RefundRequestRow.parse_raw_data(row_index, row_data)
        except SheetRowParsingException as exc:
            return RowResult(
                row_index=row_index,
                row_db_record=refund_request,
                result_type=ResultType.FAILED,
                message="Parsing failure: {}".format(str(exc)),
            )
        if refund_req_row.skip_row:
            return

        is_unchanged_error_row = (
            refund_req_row.errors is not None
            and not request_created
            and not request_updated
        )
        if is_unchanged_error_row:
            return RowResult(
                row_index=row_index,
                row_db_record=refund_request,
                result_type=ResultType.IGNORED,
                message=None,
            )
        elif (
            refund_request.date_completed
            and refund_req_row.refund_complete_date is None
        ):
            return RowResult(
                row_index=row_index,
                row_db_record=refund_request,
                result_type=ResultType.OUT_OF_SYNC,
                message=None,
            )

        if not self.is_ready_for_reversal(refund_req_row):
            return

        try:
            order, enrollment = self.get_order_objects(refund_req_row)
        except ObjectDoesNotExist as exc:
            if isinstance(exc, User.DoesNotExist):
                message = "User with email '{}' not found".format(
                    refund_req_row.learner_email
                )
            elif isinstance(exc, Order.DoesNotExist):
                message = "Order with id {} and purchaser '{}' not found".format(
                    refund_req_row.order_id, refund_req_row.learner_email
                )
            elif isinstance(
                exc, (ProgramEnrollment.DoesNotExist, CourseRunEnrollment.DoesNotExist)
            ):
                message = "Program/Course run enrollment does not exist for product '{}' and order {}".format(
                    refund_req_row.product_id, refund_req_row.order_id
                )
            else:
                raise
            return RowResult(
                row_index=row_index,
                row_db_record=refund_request,
                result_type=ResultType.FAILED,
                message=message,
            )

        self.reverse_order_and_enrollments(order, enrollment)
        refund_request.date_completed = now_in_utc()
        refund_request.save()
        return RowResult(
            row_index=row_index,
            row_db_record=refund_request,
            result_type=ResultType.PROCESSED,
            message=None,
        )

    def update_sheet_from_results(self, row_results):
        """
        Helper method that updates the relevant spreadsheet cells based on the row results, logs any
        necessary messages, and returns a summary of the changes made

        Args:
            row_results (iterable of RowResult): Objects representing the results of processing rows

        Returns:
            dict: Row results grouped into a dict with the result types as keys
        """
        row_result_dict = group_into_dict(
            row_results, key_fn=op.attrgetter("result_type")
        )
        processed_row_results = row_result_dict.get(ResultType.PROCESSED, [])
        if processed_row_results:
            self.update_row_completed_dates(processed_row_results)
        failed_row_results = row_result_dict.get(ResultType.FAILED, [])
        if failed_row_results:
            self.update_row_errors(failed_row_results)
        out_of_sync_row_results = row_result_dict.get(ResultType.OUT_OF_SYNC, [])
        if out_of_sync_row_results:
            log.warning(
                "Rows found without a completed date, but local records indicate that they were completed: %s",
                [row_result.row_index for row_result in out_of_sync_row_results],
            )
            self.update_row_completed_dates(out_of_sync_row_results)
        ignored_row_results = row_result_dict.get(ResultType.IGNORED, [])
        if ignored_row_results:
            log.warning(
                "Ignored request rows in the enrollment refund sheet: %s",
                [row_result.row_index for row_result in ignored_row_results],
            )
        return row_result_dict

    def process_sheet(self, limit_row_index=None):
        """
        Ensures that all non-legacy rows in the spreadsheet are correctly represented in the database,
        reverses/refunds enrollments if appropriate, updates the spreadsheet to reflect any changes
        made, and returns a summary of those changes.

        Args:
            limit_row_index (int or None): The row index of the specific coupon request Sheet row that
                should be processed. If None, this function will attempt to process all unprocessed rows
                in the Sheet.

        Returns:
            dict: A summary of the changes made while processing the refund request sheet
        """
        if limit_row_index is None:
            enumerated_data_rows = self.get_non_legacy_rows()
        else:
            enumerated_data_rows = [
                (limit_row_index, self.refund_request_sheet.get_row(limit_row_index))
            ]
        completed_form_response_ids = set(
            RefundRequest.objects.exclude(date_completed=None).values_list(
                "form_response_id", flat=True
            )
        )
        row_results = []
        for row_index, row_data in enumerated_data_rows:
            form_response_id = int(
                row_data[refund_sheet_metadata.FORM_RESPONSE_ID_COL].strip()
            )
            completed_date_str = row_data[
                refund_sheet_metadata.REFUND_COMPLETED_DATE_COL
            ].strip()
            if form_response_id in completed_form_response_ids and completed_date_str:
                continue
            row_result = None
            try:
                row_result = self.process_row(row_index, row_data)
            except Exception as exc:  # pylint: disable=broad-except
                row_result = RowResult(
                    row_index=row_index,
                    row_db_record=None,
                    result_type=ResultType.FAILED,
                    message="Unknown error: {}".format(str(exc)),
                )
            finally:
                if row_result:
                    row_results.append(row_result)

        if not row_results:
            return {}
        row_result_dict = self.update_sheet_from_results(row_results)
        return {
            result_type.value: [row_result.row_index for row_result in row_results]
            for result_type, row_results in row_result_dict.items()
        }
