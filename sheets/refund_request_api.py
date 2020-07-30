"""Enrollment refund API"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from courses.api import deactivate_program_enrollment, deactivate_run_enrollment
from courses.constants import ENROLL_CHANGE_STATUS_REFUNDED
from courses.models import CourseRunEnrollment, ProgramEnrollment
from courses.utils import is_program_text_id
from ecommerce.models import Order
from mitxpro.utils import now_in_utc
from sheets.constants import (
    REFUND_SHEET_ORDER_TYPE_PAID,
    REFUND_SHEET_ORDER_TYPE_FULL_COUPON,
    GOOGLE_API_TRUE_VAL,
)
from sheets.sheet_handler_api import EnrollmentChangeRequestHandler
from sheets.exceptions import SheetRowParsingException
from sheets.models import RefundRequest
from sheets.utils import (
    ResultType,
    RowResult,
    clean_sheet_value,
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
                refund_processor=raw_row_data[refund_sheet_metadata.PROCESSOR_COL],
                refund_complete_date=parse_sheet_date_only_str(
                    raw_row_data[refund_sheet_metadata.COMPLETED_DATE_COL]
                ),
                errors=raw_row_data[refund_sheet_metadata.ERROR_COL],
                skip_row=(
                    raw_row_data[refund_sheet_metadata.SKIP_ROW_COL]
                    == GOOGLE_API_TRUE_VAL
                ),
            )
        except Exception as exc:
            raise SheetRowParsingException(str(exc)) from exc


class RefundRequestHandler(EnrollmentChangeRequestHandler):
    """Manages the processing of refund requests from a spreadsheet"""

    def __init__(self):
        super().__init__(
            worksheet_id=settings.REFUND_REQUEST_WORKSHEET_ID,
            start_row=settings.SHEETS_REFUND_FIRST_ROW,
            sheet_metadata=refund_sheet_metadata,
            request_model_cls=RefundRequest,
        )

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
        user = User.objects.get(email__iexact=refund_req_row.learner_email)
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
            deactivated_enrollment, _ = deactivate_program_enrollment(
                enrollment, change_status=ENROLL_CHANGE_STATUS_REFUNDED
            )
        else:
            deactivated_enrollment = deactivate_run_enrollment(
                enrollment, change_status=ENROLL_CHANGE_STATUS_REFUNDED
            )
        # When #1838 is completed, this logic can be removed
        if deactivated_enrollment is None:
            raise Exception("Enrollment change failed in edX")
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
                row_object=None,
                result_type=ResultType.FAILED,
                message="Parsing failure: {}".format(str(exc)),
            )
        is_unchanged_error_row = (
            refund_req_row.errors and not request_created and not request_updated
        )
        if is_unchanged_error_row:
            return RowResult(
                row_index=row_index,
                row_db_record=refund_request,
                row_object=None,
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
                row_object=None,
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
                row_object=None,
                result_type=ResultType.FAILED,
                message=message,
            )

        self.reverse_order_and_enrollments(order, enrollment)
        refund_request.date_completed = now_in_utc()
        refund_request.save()
        return RowResult(
            row_index=row_index,
            row_db_record=refund_request,
            row_object=refund_req_row,
            result_type=ResultType.PROCESSED,
            message=None,
        )
