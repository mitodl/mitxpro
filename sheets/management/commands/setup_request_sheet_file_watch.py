"""
Makes a request to receive push notifications when the coupon request Sheet is updated.
"""
from django.core.management import BaseCommand
from django.conf import settings

from googleapiclient.errors import HttpError

from sheets.api import renew_coupon_request_file_watch, request_file_watch


class Command(BaseCommand):
    """
    Makes a request to receive push notifications when the coupon request Sheet is updated.
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

    def handle(self, *args, **options):  # pylint:disable=missing-docstring
        try:
            file_watch, created, updated = renew_coupon_request_file_watch(
                force=options["force"]
            )
        except HttpError as exc:
            self.stdout.write(
                self.style.ERROR(
                    "File watch request failed.\nResponse [{}]: {}".format(
                        exc.resp["status"], exc
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
                    "Coupon request sheet file watch {}.\n{}".format(desc, file_watch)
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
                        settings.COUPON_REQUEST_SHEET_ID,
                        file_watch.channel_id,
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
