"""
Parses specific coupon request rows, creates coupons, and updates/creates relevant Sheets
to reflect the processed request.
"""
from django.core.management import BaseCommand, CommandError

from sheets.api import CouponRequestHandler, create_coupons_for_request_row, ProcessedRequest


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        parser.add_argument(
            "-r",
            "--row",
            type=int,
            help="Row number in the Sheet",
        )
        parser.add_argument(
            "-t",
            "--trans-id",
            type=str,
            help="Transaction ID",
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Process request row even if the 'processed' column is set to checked/true",
        )

    def handle(self, *args, **options):  # pylint:disable=missing-docstring
        if not options["row"] and not options["trans_id"]:
            raise CommandError("Need to specify -r/--row, -t/--trans-id, or both")

        coupon_request_handler = CouponRequestHandler()
        matching_rows = []
        # Scan the sheet to find rows that match the given conditions
        for row_index, coupon_req_row in coupon_request_handler.parsed_row_iterator():
            if options["row"] and options["row"] != row_index:
                continue
            if options["trans_id"] and options["trans_id"] != coupon_req_row.transaction_id:
                continue
            matching_rows.append((row_index, coupon_req_row))

        # Raise exception if no rows match or if multiple rows match
        if len(matching_rows) == 0 or len(matching_rows) > 1:
            param_summary = []
            if options["row"]:
                param_summary.append("Row number == {}".format(options["row"]))
            if options["trans_id"]:
                param_summary.append("Transaction ID == {}".format(options["trans_id"]))
            error_text = (
                "Could not find a matching row ({})"
                if len(matching_rows) == 0 else
                "Found multiple matching rows ({})"
            )
            raise CommandError(error_text.format(", ".join(param_summary)))

        # Raise exception if the row was already processed and the 'force' flag wasn't added
        matching_row_index, matching_req_row = matching_rows[0]
        if matching_req_row.processed and not options["force"]:
            raise CommandError(
                "The sheet indicates that the matching row has already been processed. "
                "Add the -f/--force flag to process it anyway."
            )

        row_summary = "transaction id: {}, row: {}".format(
            matching_req_row.transaction_id,
            matching_row_index
        )
        self.stdout.write("Found matching row ({})".format(row_summary))

        # Create coupons
        self.stdout.write("Creating coupons...")
        coupon_gen_request = create_coupons_for_request_row(matching_req_row)
        if not coupon_gen_request:
            raise CommandError(
                "Failed to create coupons for the given request row ({})".format(row_summary)
            )

        # Update the coupon request sheet, and create the new sheet with coupon codes to be assigned
        self.stdout.write("Updating coupon request sheet and creating new coupon assignment sheet...")
        processed_request = ProcessedRequest(
            row_index=matching_row_index,
            coupon_req_row=matching_req_row,
            request_id=coupon_gen_request.id
        )
        coupon_request_handler.write_results_to_sheets([processed_request])

        self.stdout.write(self.style.SUCCESS(
            "Coupon generation succeeded.\n{}, CouponGenerationRequest: {}".format(
                row_summary,
                coupon_gen_request.id
            )
        ))
