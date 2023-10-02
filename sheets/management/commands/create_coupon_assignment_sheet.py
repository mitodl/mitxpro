"""
Creates a coupon assignment Sheet for some row in the coupon request Sheet if one doesn't exist already.
"""  # noqa: INP001, E501
from django.core.management import BaseCommand, CommandError
from pygsheets.exceptions import SpreadsheetNotFound

from sheets.coupon_request_api import CouponRequestHandler, CouponRequestRow
from sheets.models import CouponGenerationRequest
from sheets.utils import assignment_sheet_file_name, spreadsheet_repr


class Command(BaseCommand):
    """
    Creates a coupon assignment Sheet for some row in the coupon request Sheet if one doesn't exist already.
    """  # noqa: E501

    help = __doc__  # noqa: A003

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        parser.add_argument(
            "-r", "--row", type=int, help="Row number in the request Sheet"
        )

    def handle(
        self, *args, **options  # noqa: ARG002
    ):  # pylint:disable=missing-docstring  # noqa: ARG002, RUF100
        if not options["row"]:
            msg = "Need to specify -r/--row"
            raise CommandError(msg)

        row_index = options["row"]
        coupon_request_handler = CouponRequestHandler()
        # Raise exception if the row was already processed and the 'force' flag wasn't added  # noqa: E501
        row_data = coupon_request_handler.worksheet.get_row(options["row"])
        coupon_req_row = CouponRequestRow.parse_raw_data(row_index, row_data)
        coupon_gen_request = CouponGenerationRequest.objects.filter(
            coupon_name=coupon_req_row.coupon_name
        ).first()
        if coupon_gen_request is None:
            msg = (
                "No coupon generation request found for coupon name '{}'. This coupon"
                " request has probably not been processed yet.".format(
                    coupon_req_row.coupon_name
                )
            )
            raise CommandError(msg)

        spreadsheet_file_name = assignment_sheet_file_name(coupon_req_row)
        try:
            coupon_request_handler.pygsheets_client.open(spreadsheet_file_name)
        except SpreadsheetNotFound:
            already_exists = False
        else:
            already_exists = True
        if already_exists:
            msg = (
                "A spreadsheet already exists with the file name that would be created"  # noqa: E501, RUF100, UP032
                " for this request ({})".format(spreadsheet_file_name)
            )
            raise CommandError(msg)

        spreadsheet = coupon_request_handler.create_assignment_sheet(coupon_req_row)
        self.stdout.write(
            self.style.SUCCESS(
                f"Coupon assignment Sheet created ({spreadsheet_repr(spreadsheet)})"
            )
        )
