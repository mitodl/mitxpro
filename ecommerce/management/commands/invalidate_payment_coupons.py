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


class Command(BaseCommand):
    """
    Disables coupons in the system.
    """

    help = "Disables coupons in the system."  # noqa: A003

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
            msg = "Please specify a payment to deactivate or a code file to process."
            raise CommandError(msg)

        if kwargs["payment"] is not None:
            try:
                payment = CouponPayment.objects.filter(name=kwargs["payment"]).get()
            except Exception:  # noqa: BLE001
                msg = f"Payment name {kwargs['payment']} not found or ambiguous."
                raise CommandError(msg)  # noqa: B904, TRY200

            codes = Coupon.objects.filter(enabled=True, payment=payment).all()
        else:
            try:
                with open(kwargs["codefile"]) as file:  # noqa: PTH123
                    procCodes = []

                    for line in file:
                        procCodes.append(line.strip())  # noqa: PERF401
            except Exception as e:  # noqa: BLE001
                msg = f"Specified file {kwargs['codefile']} could not be opened: {e}"
                raise CommandError(msg)  # noqa: B904, TRY200

            codes = Coupon.objects.filter(coupon_code__in=procCodes, enabled=True).all()

        if len(codes) == 0:
            msg = "No codes found."
            raise CommandError(msg)

        for code in codes:
            code.enabled = False

        Coupon.objects.bulk_update(codes, ["enabled"])

        self.stdout.write(f"Disabled {len(codes)} codes successfully.")
