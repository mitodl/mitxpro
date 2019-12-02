"""
Makes a request to receive push notifications when the coupon request Sheet is updated.
"""
from django.core.management import BaseCommand
from googleapiclient.errors import HttpError

from sheets.api import renew_coupon_request_file_watch


class Command(BaseCommand):
    """
    Makes a request to receive push notifications when the coupon request Sheet is updated.
    """

    help = __doc__

    def handle(self, *args, **options):  # pylint:disable=missing-docstring
        try:
            file_watch, created, updated = renew_coupon_request_file_watch()
        except HttpError as exc:
            self.stdout.write(
                self.style.ERROR(
                    "File watch request failed.\nResponse [{}]: {}".format(
                        exc.resp["status"], exc
                    )
                )
            )
        else:
            if created:
                desc = "created"
            elif updated:
                desc = "updated"
            else:
                desc = "found (unexpired)"
            self.stdout.write(
                self.style.SUCCESS(
                    "Coupon request sheet file watch {}:\n{}".format(desc, file_watch)
                )
            )
