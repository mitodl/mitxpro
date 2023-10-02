"""
Updates the database records and coupon assignment Sheet associated with a bulk coupon assignment record depending
on what messages were delivered, failed delivery, etc.
"""  # noqa: INP001, E501
from django.core.management import BaseCommand, CommandError

from ecommerce.models import BulkCouponAssignment
from sheets.api import get_authorized_pygsheets_client
from sheets.coupon_assign_api import update_incomplete_assignment_message_statuses
from sheets.management.utils import get_assignment_spreadsheet_by_title


class Command(BaseCommand):
    """
    Updates the database records and coupon assignment Sheet associated with a bulk coupon assignment record depending
    on what messages were delivered, failed delivery, etc.
    """  # noqa: E501

    help = __doc__  # noqa: A003

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
            help=(
                "The title of the coupon assignment Sheet (should match exactly one"
                " sheet)"
            ),
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help=(
                "Update message status even if the record indicates that all messages"
                " were already delivered"
            ),
        )
        super().add_arguments(parser)

    def handle(
        self, *args, **options  # noqa: ARG002
    ):  # pylint:disable=missing-docstring  # noqa: ARG002, RUF100
        if not any([options["id"], options["sheet_id"], options["title"]]):
            msg = "Need to provide --id, --sheet-id, or --title"
            raise CommandError(msg)

        if options["id"]:
            qset_kwargs = {"id": options["id"]}
        elif options["sheet_id"]:
            qset_kwargs = {"assignment_sheet_id": options["sheet_id"]}
        else:
            pygsheets_client = get_authorized_pygsheets_client()
            spreadsheet = get_assignment_spreadsheet_by_title(
                pygsheets_client, options["title"]
            )
            qset_kwargs = {"assignment_sheet_id": spreadsheet.id}

        bulk_assignment = BulkCouponAssignment.objects.get(**qset_kwargs)
        self.stdout.write(
            "Updating bulk coupon assignment ({}, {})...".format(
                bulk_assignment.id, bulk_assignment.assignment_sheet_id
            )
        )

        updated_assignments = update_incomplete_assignment_message_statuses(
            [bulk_assignment]
        )
        update_count = len(updated_assignments.get(bulk_assignment.id, []))
        if update_count:
            self.stdout.write(
                self.style.SUCCESS(
                    "Successfully updated message status for bulk coupon assignment "
                    f"({update_count} individual status(es) added/updated)."
                )
            )
        else:
            self.stdout.write(self.style.WARNING("No message status changes detected."))
