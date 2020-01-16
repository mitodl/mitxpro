"""
Creates a coupon assignment Sheet for some row in the coupon request Sheet if one doesn't exist already.
"""
from django.core.management import BaseCommand, CommandError
from pygsheets.exceptions import SpreadsheetNotFound

from sheets.coupon_request_api import CouponRequestHandler
from sheets.management.utils import get_matching_request_row
from sheets.models import CouponGenerationRequest
from sheets.utils import spreadsheet_repr, assignment_sheet_file_name


class Command(BaseCommand):
    """
    Creates a coupon assignment Sheet for some row in the coupon request Sheet if one doesn't exist already.
    """

    help = __doc__

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        parser.add_argument(
            "-r", "--row", type=int, help="Row number in the request Sheet"
        )
        parser.add_argument("-c", "--coupon-name", type=str, help="Coupon Name")

    def handle(self, *args, **options):  # pylint:disable=missing-docstring
        if not options["row"] and not options["coupon_name"]:
            raise CommandError("Need to specify -r/--row, -c/--coupon-name, or both")

        coupon_request_handler = CouponRequestHandler()
        # Raise exception if the row was already processed and the 'force' flag wasn't added
        _, matching_req_row = get_matching_request_row(
            coupon_request_handler,
            row=options["row"],
            coupon_name=options["coupon_name"],
        )
        coupon_gen_request = CouponGenerationRequest.objects.filter(
            coupon_name=matching_req_row.coupon_name
        ).first()
        if coupon_gen_request is None:
            raise CommandError(
                "No coupon generation request found for coupon name '{}'. "
                "This coupon request has probably not been processed yet.".format(
                    matching_req_row.coupon_name
                )
            )

        spreadsheet_file_name = assignment_sheet_file_name(matching_req_row)
        try:
            coupon_request_handler.pygsheets_client.open(spreadsheet_file_name)
        except SpreadsheetNotFound:
            already_exists = False
        else:
            already_exists = True
        if already_exists:
            raise CommandError(
                "A spreadsheet already exists with the file name that would be created for this request ({})".format(
                    spreadsheet_file_name
                )
            )

        spreadsheet = coupon_request_handler.create_coupon_assignment_sheet(
            matching_req_row
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Coupon assignment Sheet created ({})".format(
                    spreadsheet_repr(spreadsheet)
                )
            )
        )
