"""
Parses refund request row(s), reverses orders/enrollments, and updates the spreadsheet
to reflect the processed request(s).
"""
from django.core.management import BaseCommand

from sheets.refund_request_api import RefundRequestHandler


class Command(BaseCommand):
    """
    Parses refund request row(s), reverses orders/enrollments, and updates the spreadsheet
    to reflect the processed request(s).
    """

    help = __doc__

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        parser.add_argument(
            "-r", "--row", type=int, help="Row number in the refund request Sheet"
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Process refund request row even if the completed date column is non-empty",
        )

    def handle(self, *args, **options):  # pylint:disable=missing-docstring
        refund_request_handler = RefundRequestHandler()
        self.stdout.write("Handling refunds and updating spreadsheet...")
        results = refund_request_handler.process_sheet(
            limit_row_index=options.get("row", None)
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Refund sheet successfully processed.\n{}".format(results)
            )
        )
