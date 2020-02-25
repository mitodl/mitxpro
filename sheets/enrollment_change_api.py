"""API with general functionality for all enrollment change spreadsheets"""
import json
import operator as op
import logging

from django.conf import settings
from django.db import transaction
from django.utils.functional import cached_property

from mitxpro.utils import group_into_dict
from sheets.api import get_authorized_pygsheets_client
from sheets.constants import ENROLL_CHANGE_SHEET_PROCESSOR_NAME, GOOGLE_API_TRUE_VAL
from sheets.utils import (
    get_data_rows_after_start,
    format_datetime_for_sheet_formula,
    ResultType,
    RowResult,
)

log = logging.getLogger(__name__)


class EnrollmentChangeRequestHandler:
    """
    Manages the processing of enrollment change requests from a spreadsheet
    """

    def __init__(self, worksheet_id, start_row, sheet_metadata, request_model_cls):
        """

        Args:
            worksheet_id (int):
            start_row (int):
            sheet_metadata (Type(SheetMetadata)):
            request_model_cls (Type(EnrollmentChangeRequestModel)):
        """
        self.pygsheets_client = get_authorized_pygsheets_client()
        self.spreadsheet = self.pygsheets_client.open_by_key(
            settings.ENROLLMENT_CHANGE_SHEET_ID
        )
        self.worksheet_id = worksheet_id
        self.start_row = start_row
        self.sheet_metadata = sheet_metadata
        self.request_model_cls = request_model_cls

    @cached_property
    def worksheet(self):
        """
        Returns the correct Worksheet object for this enrollment change request sheet

        Returns:
             pygsheets.worksheet.Worksheet: The Worksheet object
        """
        return self.spreadsheet.worksheet("id", value=self.worksheet_id)

    def process_row(self, row_index, row_data):
        """
        Parses a row in an enrollment change request worksheet and takes the appropriate actions
        based on the data in the spreadsheet and in the database.

        Args:
            row_index (int): The row index according to the spreadsheet
            row_data (list of str): The raw data of the given spreadsheet row

        Returns:
            RowResult or None: An object representing the results of processing the row, or None if
                nothing needs to be done with this row.
        """
        raise NotImplementedError

    def get_non_legacy_rows(self):
        """
        Fetches raw data rows in the request sheet, excluding "legacy" rows.
        In other words, just the rows that have been created since we started automatically processing
        requests from the spreadsheet.

        Returns:
            iterable of (int, iterable of (str)): Enumerated raw data rows in the sheet,
                excluding "legacy" rows
        """
        return enumerate(
            get_data_rows_after_start(
                self.worksheet,
                start_row=self.start_row,
                start_col=1,
                end_col=self.sheet_metadata.num_columns,
            ),
            start=self.start_row,
        )

    def update_row_completed_dates(self, row_results):
        """
        For all successfully-processed rows, programatically sets the completion date column and
        blanks the error column.

        Args:
            row_results (iterable of RowResult): Objects representing the results of processing a row
        """
        for row_result in row_results:
            self.worksheet.update_values(
                crange="{processor_col}{row_index}:{error_col}{row_index}".format(
                    processor_col=self.sheet_metadata.PROCESSOR_COL_LETTER,
                    error_col=self.sheet_metadata.ERROR_COL_LETTER,
                    row_index=row_result.row_index,
                ),
                values=[
                    [
                        ENROLL_CHANGE_SHEET_PROCESSOR_NAME,
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
            self.worksheet.update_value(
                "{}{}".format(
                    self.sheet_metadata.ERROR_COL_LETTER, row_result.row_index
                ),
                row_result.message,
            )

    def get_or_create_request(self, row_data):
        """
        Ensures that an object exists in the database that represents the given enrollment change request, and
        that it reflects the correct state based on the data in the spreadsheet row.

        Args:
            row_data (list of str): Raw data from a row in the spreadsheet

        Returns:
            (Type(EnrollmentChangeRequestModel), bool, bool): A tuple containing an object representing the request,
                a flag that indicates whether or not it was newly created, and a flag that indicates
                whether or not it was updated.
        """
        form_response_id = int(
            row_data[self.sheet_metadata.FORM_RESPONSE_ID_COL].strip()
        )
        user_input_json = json.dumps(
            self.sheet_metadata.get_form_input_columns(row_data)
        )
        with transaction.atomic():
            enroll_change_request, created = self.request_model_cls.objects.select_for_update().get_or_create(
                form_response_id=form_response_id,
                defaults=dict(raw_data=user_input_json),
            )
            raw_data_changed = enroll_change_request.raw_data != user_input_json
            if raw_data_changed:
                enroll_change_request.raw_data = user_input_json
                enroll_change_request.save()
        return enroll_change_request, created, raw_data_changed

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
                "Ignored rows in %s (%s): %s",
                self.sheet_metadata.sheet_name,
                self.sheet_metadata.worksheet_name,
                [row_result.row_index for row_result in ignored_row_results],
            )
        return row_result_dict

    def should_ignore_row(self, row_data, completed_form_response_ids):
        """
        Indicates whether or not this row should be skipped entirely before attempting to parse.

        Args:
            row_data (list of str): The raw data of the given spreadsheet row
            completed_form_response_ids (set of int): Response ids of request objects in the
                database that have a non-empty `date_completed` value

        Returns:
            bool: If True, indicates that this row should be skipped before attempting to parse/process
        """
        skip_row = (
            row_data[self.sheet_metadata.SKIP_ROW_COL].strip() == GOOGLE_API_TRUE_VAL
        )
        if skip_row:
            return True
        form_response_id = int(
            row_data[self.sheet_metadata.FORM_RESPONSE_ID_COL].strip()
        )
        completed_date_str = row_data[self.sheet_metadata.COMPLETED_DATE_COL].strip()
        return form_response_id in completed_form_response_ids and completed_date_str

    def process_sheet(self, limit_row_index=None):
        """
        Ensures that all non-legacy rows in the spreadsheet are correctly represented in the database,
        changes enrollments if appropriate, updates the spreadsheet to reflect any changes
        made, and returns a summary of those changes.

        Returns:
            dict: A summary of the changes made while processing the enrollment change request sheet
        """
        if limit_row_index is None:
            enumerated_data_rows = self.get_non_legacy_rows()
        else:
            enumerated_data_rows = [
                (limit_row_index, self.worksheet.get_row(limit_row_index))
            ]
        completed_form_response_ids = set(
            self.request_model_cls.objects.exclude(date_completed=None).values_list(
                "form_response_id", flat=True
            )
        )
        row_results = []
        for row_index, row_data in enumerated_data_rows:
            if self.should_ignore_row(row_data, completed_form_response_ids):
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
