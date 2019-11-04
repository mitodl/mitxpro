"""
Fetches a coupon assignment spreadsheet, parses it, creates product coupon assignments
based on the sheet data, and sends a message to all recipients who received a coupon assignment.
"""
from django.core.management import BaseCommand, CommandError

from sheets.api import CouponAssignmentHandler
from sheets.constants import ASSIGNMENT_COMPLETED_KEY, GOOGLE_API_TRUE_VAL
from sheets.utils import spreadsheet_repr


class Command(BaseCommand):
    """
    Fetches a coupon assignment spreadsheet, parses it, creates product coupon assignments
    based on the sheet data, and sends a message to all recipients who received a coupon assignment.
    """

    help = __doc__

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "-i",
            "--id",
            type=str,
            help="The spreadsheet ID (can be found in the sheet's URL)",
        )
        group.add_argument(
            "-t",
            "--title",
            type=str,
            help="The title of the spreadsheet (should match exactly one sheet)",
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Process coupon assignment sheet even if file properties indicate that it was already processed",
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):  # pylint:disable=missing-docstring
        if not options["id"] and not options["title"]:
            raise CommandError("Need to provide --id or --title")

        coupon_assignment_handler = CouponAssignmentHandler()
        pygsheets_client = coupon_assignment_handler.pygsheets_client

        # Fetch the correct spreadsheet
        if options["id"]:
            spreadsheet = pygsheets_client.open_by_key(options["id"])
        else:
            matching_spreadsheets = pygsheets_client.open_all(
                "{base_query} and name contains '{title}'".format(
                    base_query=coupon_assignment_handler.ASSIGNMENT_SHEETS_QUERY,
                    title=options["title"],
                )
            )
            if len(matching_spreadsheets) != 1:
                raise CommandError(
                    "There should be 1 coupon assignment sheet that matches the given title ('{}'). "
                    "{} were found.".format(
                        options["title"], len(matching_spreadsheets)
                    )
                )
            spreadsheet = matching_spreadsheets[0]

        # Check file properties to make sure this sheet wasn't already processed
        if not options["force"]:
            sheet_properties = coupon_assignment_handler.get_sheet_properties(
                spreadsheet.id
            )
            if sheet_properties.get(ASSIGNMENT_COMPLETED_KEY) == GOOGLE_API_TRUE_VAL:
                raise CommandError(
                    "Spreadsheet properties indicate that all assignments have already been completed (%s). "
                    "Add the '-f/--force' flag to process it anyway."
                    % (spreadsheet_repr(spreadsheet))
                )

        # Process the sheet
        self.stdout.write(
            "Found spreadsheet ({}). Processing...".format(
                spreadsheet_repr(spreadsheet)
            )
        )
        coupon_assignment_handler.process_assignment_spreadsheet(spreadsheet)

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully processed coupon assignment sheet ({})".format(
                    spreadsheet_repr(spreadsheet)
                )
            )
        )
