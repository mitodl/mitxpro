"""
Disables coupons in a batch, either by reading a file or by iterating through a
coupon payment.

Codes that are already disabled will not be re-disabled, and any invalid codes
will be skipped.

Arguments:
* --file <filename> - a filename to read codes from (one per line, no header)
* --payment <payment name> - a CouponPayment to iterate through

You must specify one of these options. Specifying --payment will take precedence
over --file.
"""

from django.core.management import BaseCommand, CommandError

from ecommerce.models import Coupon, CouponPayment

from ecommerce.utils import deactivate_coupons

class Command(BaseCommand):
    """
    Disables coupons in the system.
    """

    help = "Disables coupons in the system."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--payment",
            "-p",
            nargs="?",
            type=str,
            help="The payment to iterate through.",
            dest="payment",
        )

        parser.add_argument(
            "--file",
            "-f",
            nargs="?",
            type=str,
            help="File of codes to process.",
            dest="codefile",
        )

    def handle(self, *args, **kwargs):  # noqa: ARG002
        if not kwargs["payment"] and not kwargs["codefile"]:
            raise CommandError(
                "Please specify a payment to deactivate or a code file to process."  # noqa: EM101
            )

        if kwargs["payment"] is not None:
            try:
                payment = CouponPayment.objects.filter(name=kwargs["payment"]).get()
            except Exception:  # noqa: BLE001
                raise CommandError(  # noqa: B904
                    f"Payment name {kwargs['payment']} not found or ambiguous."  # noqa: EM102
                )

            codes = Coupon.objects.filter(enabled=True, payment=payment).all()
        else:
            try:
                # Note: open() defaults to read mode ("r")
                with open(kwargs["codefile"]) as file:  # noqa: PTH123
                    procCodes = [line.strip() for line in file]
            except Exception as e:  # noqa: BLE001
                raise CommandError(  # noqa: B904
                    f"Specified file {kwargs['codefile']} could not be opened: {e}"  # noqa: EM102
                )

            codes = Coupon.objects.filter(coupon_code__in=procCodes, enabled=True).all()

        if len(codes) == 0:
            raise CommandError("No codes found.")  # noqa: EM101

        deactivate_coupons(codes, Coupon)

        self.stdout.write(f"Disabled {len(codes)} codes successfully.")
