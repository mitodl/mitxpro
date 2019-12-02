"""
Parses coupon request row(s), creates coupons, and updates/creates relevant Sheets
to reflect the processed request(s).
"""
from django.core.management import BaseCommand, CommandError

from sheets.api import CouponRequestHandler
from sheets.management.utils import get_matching_request_row


class Command(BaseCommand):
    """
    Parses coupon request row(s), creates coupons, and updates/creates relevant Sheets
    to reflect the processed request(s).
    """

    help = __doc__

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        parser.add_argument(
            "-r", "--row", type=int, help="Row number in the request Sheet"
        )
        parser.add_argument("-p", "--po-id", type=str, help="Purchase Order ID")
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Process request row even if the 'processed' column is set to checked/true",
        )

    def handle(self, *args, **options):  # pylint:disable=missing-docstring
        coupon_request_handler = CouponRequestHandler()
        matching_row_index = None

        # Raise exception if the row was already processed and the 'force' flag wasn't added
        if options["row"] or options["po_id"]:
            matching_row_index, matching_req_row = get_matching_request_row(
                coupon_request_handler, row=options["row"], po_id=options["po_id"]
            )
            if matching_req_row.date_processed is not None and not options["force"]:
                raise CommandError(
                    "The sheet indicates that the matching row has already been processed. "
                    "Add the -f/--force flag to process it anyway."
                )

            row_summary = "purchase order id: {}, row: {}".format(
                matching_req_row.purchase_order_id, matching_row_index
            )
            self.stdout.write("Found matching row ({})".format(row_summary))

        # Create coupons
        self.stdout.write("Creating coupons and creating/updating Sheets...")
        results = coupon_request_handler.process_sheet(
            limit_row_index=matching_row_index
        )

        self.stdout.write(
            self.style.SUCCESS("Coupon generation succeeded.\n{}".format(results))
        )
