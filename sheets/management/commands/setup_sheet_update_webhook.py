"""
Makes a request to receive push notifications when the coupon request Sheet is updated.
"""
from django.core.management import BaseCommand
from django.conf import settings
from googleapiclient.errors import HttpError

from sheets.api import get_authorized_pygsheets_client, ExpandedSheetsClient


class Command(BaseCommand):
    """
    Makes a request to receive push notifications when the coupon request Sheet is updated.
    """

    help = __doc__

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        parser.add_argument(
            "-i",
            "--override-sheet-id",
            type=str,
            help="Sheet ID to use instead of the coupon generation sheet ID in settings",
        )

    def handle(self, *args, **options):  # pylint:disable=missing-docstring
        expanded_sheets_client = ExpandedSheetsClient(get_authorized_pygsheets_client())
        try:
            watch_response = expanded_sheets_client.request_file_watch(
                file_id=options["override_sheet_id"]
                or settings.COUPON_REQUEST_SHEET_ID,
                channel_id=settings.DRIVE_WEBHOOK_CHANNEL_ID,
            )
        except HttpError as exc:
            self.stdout.write(
                self.style.ERROR(
                    "File watch request failed.\nResponse [{}]: {}".format(
                        exc.resp["status"], exc
                    )
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "File watch request succeeded.\nResponse: {}".format(watch_response)
                )
            )
