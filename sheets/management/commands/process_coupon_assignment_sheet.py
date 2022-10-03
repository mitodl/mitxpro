"""
Fetches a coupon assignment spreadsheet, parses it, creates product coupon assignments
based on the sheet data, and sends a message to all recipients who received a coupon assignment.
"""
from django.core.management import BaseCommand, CommandError

from ecommerce.models import BulkCouponAssignment
from sheets.api import get_authorized_pygsheets_client, ExpandedSheetsClient
from sheets.coupon_assign_api import CouponAssignmentHandler
from sheets.utils import spreadsheet_repr, google_date_string_to_datetime
from sheets.management.utils import get_assignment_spreadsheet_by_title


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
            help="The coupon assignment Sheet ID (can be found in the sheet's URL)",
        )
        group.add_argument(
            "-t",
            "--title",
            type=str,
            help="The title of the coupon assignment Sheet (should match exactly one sheet)",
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help=(
                "Process coupon assignment sheet even if the file is unchanged since the last time it was processed.",
            ),
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):  # pylint:disable=missing-docstring
        if not options["id"] and not options["title"]:
            raise CommandError("Need to provide --id or --title")

        pygsheets_client = get_authorized_pygsheets_client()
        # Fetch the correct spreadsheet
        if options["id"]:
            spreadsheet = pygsheets_client.open_by_key(options["id"])
        else:
            spreadsheet = get_assignment_spreadsheet_by_title(
                pygsheets_client, options["title"]
            )
        # Process the sheet
        self.stdout.write(
            "Found spreadsheet ({}). Processing...".format(
                spreadsheet_repr(spreadsheet)
            )
        )

        expanded_sheets_client = ExpandedSheetsClient(pygsheets_client)
        metadata = expanded_sheets_client.get_drive_file_metadata(
            file_id=spreadsheet.id, fields="modifiedTime"
        )
        sheet_last_modified = google_date_string_to_datetime(metadata["modifiedTime"])
        bulk_assignment, created = BulkCouponAssignment.objects.update_or_create(
            assignment_sheet_id=spreadsheet.id,
            defaults=dict(sheet_last_modified_date=sheet_last_modified),
        )
        if (
            not created
            and sheet_last_modified <= bulk_assignment.sheet_last_modified_date
            and not options["force"]
        ):
            raise CommandError(
                "Spreadsheet is unchanged since it was last processed (%s, last modified: %s). "
                "Add the '-f/--force' flag to process it anyway."
                % (spreadsheet_repr(spreadsheet), sheet_last_modified.isoformat())
            )

        coupon_assignment_handler = CouponAssignmentHandler(
            spreadsheet_id=spreadsheet.id, bulk_assignment=bulk_assignment
        )
        (
            bulk_assignment,
            num_created,
            num_removed,
        ) = coupon_assignment_handler.process_assignment_spreadsheet()

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully processed coupon assignment sheet ({}).\n"
                "{} individual coupon assignment(s) added, {} deleted (BulkCouponAssignment id: {}).".format(
                    spreadsheet_repr(spreadsheet),
                    num_created,
                    num_removed,
                    bulk_assignment.id,
                )
            )
        )
