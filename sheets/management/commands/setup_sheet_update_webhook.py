"""
Makes a request to receive push notifications from the
"""
from urllib.parse import urljoin

from django.core.management import BaseCommand
from django.conf import settings
from django.urls import reverse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from sheets.api import get_credentials

NOTIFICATION_TYPE = "webhook"
FILE_WATCH_KIND = "api#channel"


class DriveClient:
    """Google Drive API Client"""
    def __init__(self):
        creds = get_credentials()
        self._drive_resource = build('drive', 'v3', credentials=creds)

    @property
    def files_service(self):
        """Returns the Files API service"""
        return self._drive_resource.files()

    def request_file_watch(self, file_id, channel_id):
        """
        Executes the request to watch for changes made to a specific file in Drive. If successful, Drive will
        make requests to our webhook when changes are made to the given file.
        """
        return self.files_service.watch(
            fileId=file_id,
            body={
                "id": channel_id,
                "address": urljoin(settings.SITE_BASE_URL, reverse("handle-coupon-request-sheet-update")),
                "payload": True,
                "kind": FILE_WATCH_KIND,
                "type": NOTIFICATION_TYPE,
            }
        ).execute()


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        parser.add_argument(
            "-i",
            "--override-sheet-id",
            type=str,
            help="Sheet ID to use instead of the coupon generation sheet ID in settings",
        )

    def handle(self, *args, **options):  # pylint:disable=missing-docstring
        client = DriveClient()
        try:
            watch_response = client.request_file_watch(
                file_id=options["override_sheet_id"] or settings.COUPON_REQUEST_SHEET_ID,
                channel_id=settings.DRIVE_WEBHOOK_CHANNEL_ID
            )
        except HttpError as exc:
            self.stdout.write(self.style.ERROR(
                "File watch request failed.\nResponse [{}]: {}".format(exc.resp["status"], exc)
            ))
        else:
            self.stdout.write(self.style.SUCCESS("File watch request succeeded.\nResponse: {}".format(watch_response)))

