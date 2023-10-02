"""
Parses coupon request row(s), creates coupons, and updates/creates relevant Sheets
to reflect the processed request(s).
"""  # noqa: INP001
from django.core.management import BaseCommand

from sheets.coupon_request_api import CouponRequestHandler


class Command(BaseCommand):
    """
    Parses coupon request row(s), creates coupons, and updates/creates relevant Sheets
    to reflect the processed request(s).
    """

    help = __doc__  # noqa: A003

    def add_arguments(self, parser):  # pylint:disable=missing-docstring
        parser.add_argument(
            "-r", "--row", type=int, help="Row number in the request Sheet"
        )

    def handle(
        self, *args, **options  # noqa: ARG002
    ):  # pylint:disable=missing-docstring  # noqa: ARG002, RUF100
        coupon_request_handler = CouponRequestHandler()
        self.stdout.write("Creating coupons and creating/updating Sheets...")
        results = coupon_request_handler.process_sheet(
            limit_row_index=options.get("row", None)
        )
        self.stdout.write(
            self.style.SUCCESS(f"Coupon generation succeeded.\n{results}")
        )
