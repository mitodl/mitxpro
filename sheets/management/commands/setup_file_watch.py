"""
Makes a request to receive push notifications when xPro spreadsheets are updated
"""
from django.core.management import BaseCommand
from googleapiclient.errors import HttpError

from sheets.api import (
    create_or_renew_sheet_file_watch,
    request_file_watch,
    get_sheet_metadata_from_type,
)
from sheets.coupon_assign_api import fetch_webhook_eligible_assign_sheet_ids
from sheets.constants import (
    SHEET_TYPE_COUPON_REQUEST,
    SHEET_TYPE_COUPON_ASSIGN,
    SHEET_TYPE_ENROLL_CHANGE,
)


class Command(BaseCommand):
    """
    Makes a request to receive push notifications when xPro spreadsheets are updated
    """

    help = __doc__

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        parser.add_argument(
            "-s",
            "--sheet",
            default=SHEET_TYPE_COUPON_REQUEST,
            choices=[
                SHEET_TYPE_COUPON_REQUEST,
                SHEET_TYPE_ENROLL_CHANGE,
                SHEET_TYPE_COUPON_ASSIGN,
            ],
            help="The sheet that will have a file watch configured (default: '%(default)s')",
        )
        parser.add_argument(
            "--sheet-id",
            help=(
                "(Optional) The id for the spreadsheet as it appears in the spreadsheet URL. "
                f"Only relevant for coupon assignment sheets. If sheet type '{SHEET_TYPE_COUPON_ASSIGN}' "
                "is specified and no file id is provided, file watches will be set up/renewed for all "
                "eligible assignment sheets."
            ),
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--confirm",
            action="store_true",
            help=(
                "Make the request to create the file watch via API even if our local file watch "
                "record is unexpired. Uses the same dates and channel ID as the existing record."
            ),
        )
        group.add_argument(
            "--force",
            action="store_true",
            help=(
                "Make the request to create a new file watch via API and overwrite any existing "
                "file watch record."
            ),
        )

    def handle(
        self, *args, **options
    ):  # pylint:disable=missing-docstring,too-many-branches
        sheet_metadata = get_sheet_metadata_from_type(options["sheet"])
        if options["sheet"] == SHEET_TYPE_COUPON_ASSIGN:
            file_ids = (
                [options["sheet_id"]]
                if options["sheet_id"]
                else fetch_webhook_eligible_assign_sheet_ids()
            )
        else:
            file_ids = [None]

        file_watch_results = []
        for file_id in file_ids:
            try:
                file_watch, created, updated = create_or_renew_sheet_file_watch(
                    sheet_metadata, force=options["force"], sheet_file_id=file_id
                )
                file_watch_results.append((file_watch, created, updated))
            except HttpError as exc:
                self.stdout.write(
                    self.style.ERROR(
                        "Request to create/renew file watch for {} failed.\nResponse [{}]: {}".format(
                            sheet_metadata.sheet_name, exc.resp["status"], exc
                        )
                    )
                )

        for file_watch, created, updated in file_watch_results:
            if created:
                desc = "created"
            elif updated:
                desc = "updated"
            else:
                desc = "found (unexpired)"
            self.stdout.write(
                self.style.SUCCESS(
                    "{} file watch {}.".format(sheet_metadata.sheet_name, desc)
                )
            )
            self.stdout.write(str(file_watch))
            if created or updated or not options["confirm"]:
                continue

            self.stdout.write(
                self.style.WARNING(
                    "\n--confirm flag provided, so an API request will now be made to create a file watch "
                    "that matches the file watch record in the database..."
                )
            )
            try:
                resp_dict = request_file_watch(
                    file_id=file_watch.file_id,
                    channel_id=file_watch.channel_id,
                    handler_url=sheet_metadata.handler_url_stub(
                        file_id=(
                            file_watch.file_id
                            if options["sheet"] == SHEET_TYPE_COUPON_ASSIGN
                            else None
                        )
                    ),
                    expiration=file_watch.expiration_date,
                )
            except HttpError as exc:
                existing_channel_id_message = "Channel id {} not unique".format(
                    file_watch.channel_id
                )
                if existing_channel_id_message in str(exc):
                    self.stdout.write(
                        self.style.SUCCESS(
                            "The file watch with channel id {} already exists.".format(
                                file_watch.channel_id
                            )
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR("Request failed: {}".format(exc))
                    )
                    exit(1)
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "New file watch successfully created via API.\n Response: {}".format(
                            resp_dict
                        )
                    )
                )
