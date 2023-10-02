"""
Parses refund request row(s), reverses orders/enrollments, and updates the spreadsheet
to reflect the processed request(s).
"""  # noqa: INP001
from django.core.management import BaseCommand

from sheets.refund_request_api import RefundRequestHandler


class Command(BaseCommand):
    """
    Parses refund request row(s), reverses orders/enrollments, and updates the spreadsheet
    to reflect the processed request(s).
    """  # noqa: E501

    help = __doc__  # noqa: A003

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        parser.add_argument(
            "-r", "--row", type=int, help="Row number in the refund request Sheet"
        )

    def handle(
        self, *args, **options  # noqa: ARG002
    ):  # pylint:disable=missing-docstring  # noqa: ARG002, RUF100
        refund_request_handler = RefundRequestHandler()
        self.stdout.write("Handling refunds and updating spreadsheet...")
        results = refund_request_handler.process_sheet(
            limit_row_index=options.get("row", None)
        )
        self.stdout.write(
            self.style.SUCCESS(f"Refund sheet successfully processed.\n{results}")
        )
