"""
Parses specific coupon request rows, creates coupons, and updates/creates relevant Sheets
to reflect the processed request.
"""
from django.core.management import BaseCommand, CommandError

from mitxpro.utils import now_in_utc
from sheets.api import CouponRequestHandler, create_coupons_for_request_row
from sheets.management.utils import get_matching_request_row
from sheets.utils import ProcessedRequest


class Command(BaseCommand):
    """
    Parses specific coupon request rows, creates coupons, and updates/creates relevant Sheets
    to reflect the processed request.
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
        if not options["row"] and not options["po_id"]:
            raise CommandError("Need to specify -r/--row, -p/--po-id, or both")

        coupon_request_handler = CouponRequestHandler()
        # Raise exception if the row was already processed and the 'force' flag wasn't added
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
        self.stdout.write("Creating coupons...")
        coupon_gen_request = create_coupons_for_request_row(matching_req_row)
        if not coupon_gen_request:
            raise CommandError(
                "Failed to create coupons for the given request row ({})".format(
                    row_summary
                )
            )

        # Update the coupon request sheet, and create the new sheet with coupon codes to be assigned
        self.stdout.write(
            "Updating coupon request sheet and creating new coupon assignment sheet..."
        )
        processed_request = ProcessedRequest(
            row_index=matching_row_index,
            coupon_req_row=matching_req_row,
            request_id=coupon_gen_request.id,
            date_processed=now_in_utc(),
        )
        coupon_request_handler.write_results_to_sheets([processed_request])

        self.stdout.write(
            self.style.SUCCESS(
                "Coupon generation succeeded.\n{}, CouponGenerationRequest id: {}".format(
                    row_summary, coupon_gen_request.id
                )
            )
        )
