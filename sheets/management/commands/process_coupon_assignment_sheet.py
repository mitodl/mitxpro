"""
Fetches a coupon assignment spreadsheet, parses it, creates product coupon assignments
based on the sheet data, and sends a message to all recipients who received a coupon assignment.
"""

from django.core.management import BaseCommand, CommandError

from sheets.management.utils import assign_coupons_from_spreadsheet
from sheets.exceptions import CouponAssignmentError


class Command(BaseCommand):
    """
    Fetches a coupon assignment spreadsheet, parses it, creates product coupon assignments
    based on the sheet data, and sends a message to all recipients who received a coupon assignment.
    """

    help = __doc__

    def add_arguments(self, parser):
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
                "Process coupon assignment sheet even if the file is unchanged since the last time it was processed."
            ),
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):  # noqa: ARG002
        sheet_id = options.get("id")
        title = options.get("title")

        if not sheet_id and not title:
            raise CommandError("Need to provide --id or --title")  # noqa: EM101

        use_sheet_id = bool(sheet_id)
        value = sheet_id if use_sheet_id else title

        try:
            spreadsheet, num_created, num_removed, bulk_assignment_id = (
                assign_coupons_from_spreadsheet(
                    use_sheet_id=use_sheet_id, value=value, force=options.get("force")
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully processed coupon assignment sheet ({spreadsheet}).\n"
                    f"{num_created} individual coupon assignment(s) added, {num_removed} deleted "
                    f"(BulkCouponAssignment id: {bulk_assignment_id})."
                )
            )

        except CouponAssignmentError as e:
            raise CommandError(str(e))

        except Exception as e:
            raise CommandError(f"An unexpected error occurred: {e}")
