"""
Parses deferral request row(s), creates/deactivates enrollments as necessary, and updates the spreadsheet
to reflect the processed request(s).
"""

from django.core.management import BaseCommand

from sheets.deferral_request_api import DeferralRequestHandler


class Command(BaseCommand):
    """
    Parses deferral request row(s), creates/deactivates enrollments as necessary, and updates the spreadsheet
    to reflect the processed request(s).
    """

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "-r", "--row", type=int, help="Row number in the deferral request Sheet"
        )

    def handle(self, *args, **options):  # noqa: ARG002
        defer_request_handler = DeferralRequestHandler()
        self.stdout.write("Handling deferrals and updating spreadsheet...")
        results = defer_request_handler.process_sheet(
            limit_row_index=options.get("row", None)
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Deferral sheet successfully processed.\n{results}"  # noqa: UP032
            )
        )
