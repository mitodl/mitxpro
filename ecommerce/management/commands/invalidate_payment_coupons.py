"""
Disables coupons in a batch, either by parsing a CSV file or by iterating
through a coupon payment. 
"""

from django.core.management import BaseCommand, CommandError

from ecommerce.models import CouponPayment, Coupon


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

    def handle(self, *args, **kwargs):
        if (
            "payment" not in kwargs
            or "codefile" not in kwargs
            or kwargs["payment"] == ""
            or kwargs["codefile"] == ""
        ):
            raise CommandError(
                "Please specify a payment to deactivate or a code file to process."
            )

        if kwargs["payment"] is not None:
            try:
                payment = CouponPayment.objects.filter(name=kwargs["payment"]).get()
            except Exception:
                raise CommandError(
                    f"Payment name {kwargs['payment']} not found or ambiguous."
                )

            codes = Coupon.objects.filter(enabled=True, payment=payment).all()
        else:
            try:
                with open(kwargs["codefile"], "r") as file:
                  procCodes = []

                  for line in file:
                      procCodes.append(line.strip())
            except Exception as e:
                raise CommandError(f"Specified file {kwargs['codefile']} could not be opened: {e}")

            codes = Coupon.objects.filter(coupon_code__in=procCodes, enabled=True).all()

        if len(codes) == 0:
            raise CommandError("No codes found.")

        for code in codes:
            self.stdout.write(f"Disabling code {code.coupon_code}")
            code.enabled = False
            code.save()

        self.stdout.write(f"Disabled {len(codes)} successfully.")
