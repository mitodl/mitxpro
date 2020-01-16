"""
Updates the database records and coupon assignment Sheet associated with a bulk coupon assignment record depending
on what messages were delivered, failed delivery, etc.
"""
from django.core.management import BaseCommand, CommandError

from ecommerce.models import BulkCouponAssignment
from sheets.coupon_assign_api import CouponAssignmentHandler
from sheets.management.utils import get_assignment_spreadsheet_by_title


class Command(BaseCommand):
    """
    Updates the database records and coupon assignment Sheet associated with a bulk coupon assignment record depending
    on what messages were delivered, failed delivery, etc.
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
            "-f",
            "--force",
            action="store_true",
            help="Update message status even if the record indicates that all messages were already delivered",
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):  # pylint:disable=missing-docstring
        if not any([options["id"], options["sheet_id"], options["title"]]):
            raise CommandError("Need to provide --id, --sheet-id, or --title")

        coupon_assignment_handler = None
        if options["id"]:
            qset_kwargs = dict(id=options["id"])
        elif options["sheet_id"]:
            qset_kwargs = dict(assignment_sheet_id=options["sheet_id"])
        else:
            coupon_assignment_handler = CouponAssignmentHandler()
            spreadsheet = get_assignment_spreadsheet_by_title(
                coupon_assignment_handler.pygsheets_client, options["title"]
            )
            qset_kwargs = dict(assignment_sheet_id=spreadsheet.id)

        bulk_coupon_assignment = BulkCouponAssignment.objects.get(**qset_kwargs)
        self.stdout.write(
            "Updating bulk coupon assignment ({}, {})...".format(
                bulk_coupon_assignment.id, bulk_coupon_assignment.assignment_sheet_id
            )
        )
        coupon_assignment_handler = (
            coupon_assignment_handler or CouponAssignmentHandler()
        )
        assignment_status_map = coupon_assignment_handler.build_assignment_status_map(
            [bulk_coupon_assignment]
        )
        updated_assignments = coupon_assignment_handler.update_coupon_delivery_statuses(
            assignment_status_map
        )
        update_count = len(updated_assignments.get(bulk_coupon_assignment.id, []))
        if update_count:
            self.stdout.write(
                self.style.SUCCESS(
                    "Successfully updated message status for bulk coupon assignment "
                    "({} individual status(es) added/updated).".format(update_count)
                )
            )
        else:
            self.stdout.write(self.style.WARNING("No message status changes detected."))
