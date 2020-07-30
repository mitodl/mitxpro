"""Enrollment deferral API"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from courses.api import defer_enrollment
from courses.models import CourseRunEnrollment, CourseRun
from mitxpro.utils import now_in_utc
from sheets.constants import GOOGLE_API_TRUE_VAL
from sheets.sheet_handler_api import EnrollmentChangeRequestHandler
from sheets.exceptions import SheetRowParsingException
from sheets.models import DeferralRequest
from sheets.utils import (
    ResultType,
    RowResult,
    clean_sheet_value,
    parse_sheet_date_only_str,
    deferral_sheet_metadata,
)

log = logging.getLogger(__name__)
User = get_user_model()


class DeferralRequestRow:  # pylint: disable=too-many-instance-attributes
    """Represents a row of the deferral request sheet"""

    def __init__(
        self,
        row_index,
        response_id,
        request_date,
        learner_email,
        zendesk_ticket_no,
        requester_email,
        from_courseware_id,
        to_courseware_id,
        deferral_processor,
        deferral_complete_date,
        errors,
        skip_row,
    ):  # pylint: disable=too-many-arguments,too-many-locals
        self.row_index = row_index
        self.response_id = response_id
        self.request_date = request_date
        self.learner_email = learner_email
        self.zendesk_ticket_no = zendesk_ticket_no
        self.requester_email = requester_email
        self.from_courseware_id = from_courseware_id
        self.to_courseware_id = to_courseware_id
        self.deferral_processor = deferral_processor
        self.deferral_complete_date = deferral_complete_date
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
                    raw_row_data[deferral_sheet_metadata.FORM_RESPONSE_ID_COL]
                ),
                request_date=raw_row_data[1],
                learner_email=raw_row_data[2],
                zendesk_ticket_no=raw_row_data[3],
                requester_email=raw_row_data[4],
                from_courseware_id=raw_row_data[5],
                to_courseware_id=raw_row_data[6],
                deferral_processor=raw_row_data[deferral_sheet_metadata.PROCESSOR_COL],
                deferral_complete_date=parse_sheet_date_only_str(
                    raw_row_data[deferral_sheet_metadata.COMPLETED_DATE_COL]
                ),
                errors=raw_row_data[deferral_sheet_metadata.ERROR_COL],
                skip_row=(
                    raw_row_data[deferral_sheet_metadata.SKIP_ROW_COL]
                    == GOOGLE_API_TRUE_VAL
                ),
            )
        except Exception as exc:
            raise SheetRowParsingException(str(exc)) from exc


class DeferralRequestHandler(EnrollmentChangeRequestHandler):
    """Manages the processing of enrollment deferral requests from a spreadsheet"""

    def __init__(self):
        super().__init__(
            worksheet_id=settings.DEFERRAL_REQUEST_WORKSHEET_ID,
            start_row=settings.SHEETS_DEFERRAL_FIRST_ROW,
            sheet_metadata=deferral_sheet_metadata,
            request_model_cls=DeferralRequest,
        )

    def process_row(
        self, row_index, row_data
    ):  # pylint: disable=too-many-return-statements
        """
        Ensures that the given spreadsheet row is correctly represented in the database,
        attempts to parse it, defers the given enrollment if appropriate, and returns the
        result of processing the row.

        Args:
            row_index (int): The row index according to the spreadsheet
            row_data (list of str): The raw data of the given spreadsheet row

        Returns:
            RowResult or None: An object representing the results of processing the row, or None if
                nothing needs to be done with this row.
        """
        deferral_request, request_created, request_updated = self.get_or_create_request(
            row_data
        )
        try:
            deferral_req_row = DeferralRequestRow.parse_raw_data(row_index, row_data)
        except SheetRowParsingException as exc:
            return RowResult(
                row_index=row_index,
                row_db_record=deferral_request,
                row_object=None,
                result_type=ResultType.FAILED,
                message="Parsing failure: {}".format(str(exc)),
            )
        is_unchanged_error_row = (
            deferral_req_row.errors and not request_created and not request_updated
        )
        if is_unchanged_error_row:
            return RowResult(
                row_index=row_index,
                row_db_record=deferral_request,
                row_object=None,
                result_type=ResultType.IGNORED,
                message=None,
            )
        elif (
            deferral_request.date_completed
            and deferral_req_row.deferral_complete_date is None
        ):
            return RowResult(
                row_index=row_index,
                row_db_record=deferral_request,
                row_object=None,
                result_type=ResultType.OUT_OF_SYNC,
                message=None,
            )

        if deferral_req_row.from_courseware_id == deferral_req_row.to_courseware_id:
            return RowResult(
                row_index=row_index,
                row_db_record=deferral_request,
                row_object=None,
                result_type=ResultType.FAILED,
                message="'from' and 'to' ids are identical",
            )
        try:
            user = User.objects.get(email__iexact=deferral_req_row.learner_email)
            from_enrollment, to_enrollment = defer_enrollment(
                user,
                from_courseware_id=deferral_req_row.from_courseware_id,
                to_courseware_id=deferral_req_row.to_courseware_id,
            )
            # When #1838 is completed, this logic can be removed
            if not from_enrollment and not to_enrollment:
                raise Exception("edX enrollment change failed")
        except ObjectDoesNotExist as exc:
            if isinstance(exc, CourseRunEnrollment.DoesNotExist):
                message = "'from' course run enrollment does not exist ({})".format(
                    deferral_req_row.from_courseware_id
                )
            elif isinstance(exc, CourseRun.DoesNotExist):
                message = "'to' course run does not exist ({})".format(
                    deferral_req_row.to_courseware_id
                )
            elif isinstance(exc, User.DoesNotExist):
                message = "User '{}' does not exist".format(
                    deferral_req_row.learner_email
                )
            else:
                message = str(exc)
            return RowResult(
                row_index=row_index,
                row_db_record=deferral_request,
                row_object=None,
                result_type=ResultType.FAILED,
                message=message,
            )
        except ValidationError as exc:
            return RowResult(
                row_index=row_index,
                row_db_record=deferral_request,
                row_object=None,
                result_type=ResultType.FAILED,
                message="Invalid deferral: {}".format(exc),
            )

        deferral_request.date_completed = now_in_utc()
        deferral_request.save()
        return RowResult(
            row_index=row_index,
            row_db_record=deferral_request,
            row_object=deferral_req_row,
            result_type=ResultType.PROCESSED,
            message=None,
        )
