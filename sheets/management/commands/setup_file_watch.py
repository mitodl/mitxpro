"""
Makes a request to receive push notifications when the coupon request Sheet is updated.
"""
from django.core.management import BaseCommand

from googleapiclient.errors import HttpError

from sheets.api import (
    renew_sheet_file_watch,
    request_file_watch,
    get_sheet_metadata_from_type,
)
from sheets.constants import SHEET_TYPE_COUPON_REQUEST, SHEET_TYPE_ENROLL_CHANGE


class Command(BaseCommand):
    """
    Makes a request to receive push notifications when a spreadsheet is updated.
    """

    help = __doc__

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
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
        parser.add_argument(
            "-s",
            "--sheet",
            default=SHEET_TYPE_COUPON_REQUEST,
            choices=[SHEET_TYPE_COUPON_REQUEST, SHEET_TYPE_ENROLL_CHANGE],
            help="The sheet that will have a file watch configured (default: '%(default)s')",
        )

    def handle(
        self, *args, **options
    ):  # pylint:disable=missing-docstring,too-many-branches
        sheet_metadata = get_sheet_metadata_from_type(options["sheet"])
        try:
            file_watch, created, updated = renew_sheet_file_watch(
                sheet_metadata, force=options["force"]
            )
        except HttpError as exc:
            self.stdout.write(
                self.style.ERROR(
                    "Request to create/renew file watch for {} failed.\nResponse [{}]: {}".format(
                        sheet_metadata.sheet_name, exc.resp["status"], exc
                    )
                )
            )
            exit(1)
        else:
            if created:
                desc = "created"
            elif updated:
                desc = "updated"
            else:
                desc = "found (unexpired)"
            self.stdout.write(
                self.style.SUCCESS(
                    "{} file watch {}.\n{}".format(
                        sheet_metadata.sheet_name, desc, file_watch
                    )
                )
            )

            if not created and not updated and options["confirm"]:
                self.stdout.write(
                    self.style.WARNING(
                        "\n--confirm flag provided, so an API request will now be made to create a file watch "
                        "that matches the file watch record in the database..."
                    )
                )
                try:
                    resp_dict = request_file_watch(
                        sheet_metadata.sheet_file_id,
                        file_watch.channel_id,
                        sheet_metadata.handler_url_stub,
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
