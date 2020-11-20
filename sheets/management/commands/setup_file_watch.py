"""
Makes a request to receive push notifications when xPro spreadsheets are updated
"""
from collections import namedtuple
import sys

from django.core.management import BaseCommand
from googleapiclient.errors import HttpError

from sheets.api import (
    create_or_renew_sheet_file_watch,
    request_file_watch,
    get_sheet_metadata_from_type,
)
from sheets.coupon_assign_api import fetch_webhook_eligible_assign_sheet_ids
from sheets.constants import VALID_SHEET_TYPES, SHEET_TYPE_COUPON_ASSIGN
from sheets.models import FileWatchRenewalAttempt

SheetMap = namedtuple("SheetMap", ["metadata", "file_ids"])
FileWatchResult = namedtuple(
    "FileWatchResult", ["file_watch", "metadata", "created", "updated"]
)


class Command(BaseCommand):
    """
    Makes a request to receive push notifications when xPro spreadsheets are updated
    """

    help = __doc__

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        parser.add_argument(
            "-s",
            "--sheet-type",
            choices=VALID_SHEET_TYPES,
            help=(
                "(Optional) The type of sheet that should have a file watch configured. "
                "Leave blank to renew all sheet types."
            ),
            required=False,
        )
        parser.add_argument(
            "--sheet-id",
            help=(
                "(Optional) The id for the spreadsheet as it appears in the spreadsheet URL. "
                f"Only relevant for coupon assignment sheets. If sheet type '{SHEET_TYPE_COUPON_ASSIGN}' "
                "is specified and no file id is provided, file watches will be set up/renewed for all "
                "eligible assignment sheets."
            ),
            required=False,
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
    ):  # pylint:disable=missing-docstring,too-many-branches,too-many-locals

        sheet_dict = {}

        # Build a map of sheets that should be renewed (and specific file IDs if applicable)
        if options["sheet_type"]:
            sheet_dict[options["sheet_type"]] = SheetMap(
                metadata=get_sheet_metadata_from_type(options["sheet_type"]),
                file_ids=[None],
            )
        else:
            for sheet_type in VALID_SHEET_TYPES:
                sheet_dict[sheet_type] = SheetMap(
                    metadata=get_sheet_metadata_from_type(sheet_type), file_ids=[None]
                )
        if SHEET_TYPE_COUPON_ASSIGN in sheet_dict:
            file_ids = (
                [options["sheet_id"]]
                if options["sheet_id"]
                else fetch_webhook_eligible_assign_sheet_ids()
            )
            if file_ids:
                sheet_dict[SHEET_TYPE_COUPON_ASSIGN] = SheetMap(
                    metadata=get_sheet_metadata_from_type(SHEET_TYPE_COUPON_ASSIGN),
                    file_ids=file_ids,
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "No assignment sheets were found that are eligible to renew. Skipping assignment sheets..."
                    )
                )
                del sheet_dict[SHEET_TYPE_COUPON_ASSIGN]

        # Make requests to renew the file watches for the given sheets and record the results
        file_watch_results = []
        for sheet_type, sheet_map in sheet_dict.items():
            for file_id in sheet_map.file_ids:
                file_watch, created, updated = create_or_renew_sheet_file_watch(
                    sheet_map.metadata, force=options["force"], sheet_file_id=file_id
                )
                file_watch_results.append(
                    FileWatchResult(
                        file_watch=file_watch,
                        metadata=sheet_map.metadata,
                        created=created,
                        updated=updated,
                    )
                )

        # Output the results, and post-process if necessary
        for file_watch_result in file_watch_results:
            file_watch = file_watch_result.file_watch
            if file_watch is None:
                renewal_attempt = (
                    FileWatchRenewalAttempt.objects.filter().order_by("-id").first()
                )
                error_msg = (
                    ""
                    if renewal_attempt is None
                    else "\n[{}] {}".format(
                        renewal_attempt.result_status_code, renewal_attempt.result
                    )
                )
                self.style.ERROR(
                    "Failed to create/update file watch.{}".format(error_msg)
                )
                continue
            if file_watch_result.created:
                desc = "created"
            elif file_watch_result.updated:
                desc = "updated"
            else:
                desc = "found (unexpired)"
            file_id_desc = ""
            if file_watch_result.metadata.sheet_type == SHEET_TYPE_COUPON_ASSIGN:
                file_id_desc = " (file id: {})".format(file_watch.file_id)

            self.stdout.write(
                self.style.SUCCESS(
                    "{} file watch {}{}.".format(
                        file_watch_result.metadata.sheet_name, desc, file_id_desc
                    )
                )
            )
            self.stdout.write(str(file_watch))
            if (
                file_watch_result.created
                or file_watch_result.updated
                or not options["confirm"]
            ):
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
                    handler_url=file_watch_result.metadata.handler_url_stub(
                        file_id=(
                            file_watch.file_id
                            if file_watch_result.metadata.sheet_type
                            == SHEET_TYPE_COUPON_ASSIGN
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
                    sys.exit(1)
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "New file watch successfully created via API.\n Response: {}".format(
                            resp_dict
                        )
                    )
                )
