"""
Compares assignment sheet rows to enrollment records in the database and message delivery data in Mailgun.
If the data in the sheet does not match, a request is sent to update/"sync" the sheet data.
"""
from django.core.management import BaseCommand, CommandError

from ecommerce.mail_api import send_bulk_enroll_emails
from ecommerce.models import BulkCouponAssignment
from sheets.api import get_authorized_pygsheets_client
from sheets.coupon_assign_api import CouponAssignmentHandler
from sheets.management.utils import get_assignment_spreadsheet_by_title


class Command(BaseCommand):
    """
    Compares assignment sheet rows to enrollment records in the database and message delivery data in Mailgun.
    If the data in the sheet does not match, a request is sent to update/"sync" the sheet data.
    """

    help = __doc__

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--id", type=int, help="The BulkCouponAssignment ID")
        group.add_argument(
            "--sheet-id", type=str, help="The coupon assignment Sheet ID"
        )
        group.add_argument(
            "-t",
            "--title",
            type=str,
            help="The title of the coupon assignment Sheet (should match exactly one sheet)",
        )
        parser.add_argument(
            "--skip-confirm",
            action="store_true",
            help="Skip the confirmation step for sending enrollment code emails that should have been sent",
        )
        super().add_arguments(parser)

    def handle(
        self, *args, **options
    ):  # pylint:disable=missing-docstring,too-many-locals
        if not any([options["id"], options["sheet_id"], options["title"]]):
            raise CommandError("Need to provide --id, --sheet-id, or --title")

        if options["id"]:
            qset_kwargs = dict(id=options["id"])
        elif options["sheet_id"]:
            qset_kwargs = dict(assignment_sheet_id=options["sheet_id"])
        else:
            pygsheets_client = get_authorized_pygsheets_client()
            spreadsheet = get_assignment_spreadsheet_by_title(
                pygsheets_client, options["title"]
            )
            qset_kwargs = dict(assignment_sheet_id=spreadsheet.id)

        bulk_assignment = BulkCouponAssignment.objects.get(**qset_kwargs)
        coupon_assignment_handler = CouponAssignmentHandler(
            spreadsheet_id=bulk_assignment.assignment_sheet_id,
            bulk_assignment=bulk_assignment,
        )
        (
            row_updates,
            unsent_assignments,
        ) = coupon_assignment_handler.get_out_of_sync_sheet_data()

        if len(row_updates) == 0 and len(unsent_assignments) == 0:
            self.stdout.write(
                self.style.WARNING(
                    "Spreadsheet data appears to be synced. No updates needed. Exiting..."
                )
            )
            return

        row_update_results, message_delivery_results = "", ""
        if row_updates:
            coupon_assignment_handler.update_sheet_with_new_statuses(
                row_updates=row_updates
            )
            row_update_summary = "\n".join(
                [
                    "Row: {}, Status: {}".format(
                        row_update.row_index, row_update.status
                    )
                    for row_update in row_updates
                ]
            )
            row_update_results = (
                "Request sent to the Google API to update {} row(s):\n{}".format(
                    len(row_updates), row_update_summary
                )
            )

        if unsent_assignments and not options["skip_confirm"]:
            user_input = input(
                "{} users(s) will be sent an enrollment code email:\n"
                "{}\n"
                "Enter 'y' to confirm and send the emails, or any other key to skip this step: ".format(
                    len(unsent_assignments),
                    "\n".join(
                        [
                            f"  {assignment.email} (code: {assignment.product_coupon.coupon.coupon_code})"
                            for assignment in unsent_assignments
                        ]
                    ),
                )
            )
            if user_input.lower() != "y":
                unsent_assignments = []

        if unsent_assignments:
            send_bulk_enroll_emails(bulk_assignment.id, unsent_assignments)
            message_delivery_results = (
                f"{len(unsent_assignments)} enrollment code email(s) sent."
            )

        summary = "\n\n".join(
            list(filter(None, [row_update_results, message_delivery_results]))
        )
        self.stdout.write(self.style.SUCCESS(summary))
