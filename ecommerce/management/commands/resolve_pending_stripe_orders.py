"""
Resolves Stripe orders that are stuck in the created state.

Stripe tells us a payment succeeded by webhook, and that webhook can fail to
arrive: the app might have been down, the endpoint misconfigured, or Stripe's
retries exhausted. When that happens the learner has paid and the order sits in
`created` forever, because nothing else retries.

This asks Stripe what actually happened to the order and makes our records
match -- fulfilling it if the payment went through, failing it if it didn't, and
leaving it alone if the payment is still in flight.

Arguments:
* --order <reference number> - a single order (ex: xpro-b2c-dev-123)
* --all - every stuck Stripe order
* --commit - actually apply the changes

This reports what it would do and changes nothing unless --commit is passed.
Fulfilling an order enrolls the learner and emails them a receipt, and --all is
the easiest thing to type, so the safe option is the default one.
"""

from django.core.management import BaseCommand, CommandError
from mitol.payment_gateway.constants import MITOL_PAYMENT_GATEWAY_STRIPE

from ecommerce.api import (
    cancel_stripe_order,
    fulfill_stripe_order,
    get_stripe_checkout_session_status,
)
from ecommerce.constants import (
    STRIPE_CHECKOUT_STATUS_CANCELLED,
    STRIPE_CHECKOUT_STATUS_ERROR,
    STRIPE_CHECKOUT_STATUS_PAID,
    STRIPE_CHECKOUT_STATUS_PENDING,
)
from ecommerce.models import Order


class Command(BaseCommand):
    """
    Resolves Stripe orders whose webhook never arrived.
    """

    help = "Resolves Stripe orders that are stuck in the created state."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--order",
            type=str,
            help="The order reference number to resolve (ex: xpro-b2c-dev-123).",
            required=False,
        )

        parser.add_argument(
            "--all", action="store_true", help="Resolve all stuck Stripe orders."
        )

        parser.add_argument(
            "--commit",
            action="store_true",
            help="Apply the changes. Without this the command only reports.",
        )

    def get_orders(self, reference_number, *, process_all):
        """
        Find the orders to work on.

        Only Stripe orders still in `created` with a checkout session recorded
        can be resolved: without the session ID there is nothing to ask Stripe
        about.
        """
        orders = Order.objects.filter(
            status=Order.CREATED,
            gateway_type=MITOL_PAYMENT_GATEWAY_STRIPE,
            stripe_checkout_session_id__isnull=False,
        ).exclude(stripe_checkout_session_id="")

        if process_all:
            return orders

        try:
            order = Order.objects.get_by_reference_number(reference_number)
        except Order.DoesNotExist:
            raise CommandError(  # noqa: B904
                f"No order found with reference number {reference_number}."  # noqa: EM102
            )

        return orders.filter(id=order.id)

    def handle(self, *args, **kwargs):  # noqa: ARG002
        if bool(kwargs["all"]) == bool(kwargs["order"]):
            # Refuse both cases. Silently letting --all win when an order was
            # also named would apply changes to every pending order when the
            # operator meant one of them.
            raise CommandError(  # noqa: TRY003
                "Specify either an order reference number or --all, not both."  # noqa: EM101
            )

        dry_run = not kwargs["commit"]
        orders = self.get_orders(kwargs["order"], process_all=kwargs["all"])

        if not orders:
            # Nothing stuck is the healthy state, not a failure -- exiting
            # non-zero here would make this unusable on a schedule. A named
            # order that doesn't exist is a different matter and still errors,
            # in get_orders.
            self.stdout.write("No stuck Stripe orders found.")
            return

        resolved = 0
        for order in orders:
            session_id = order.stripe_checkout_session_id
            status_info = get_stripe_checkout_session_status(session_id)
            state = status_info["status"]

            if state == STRIPE_CHECKOUT_STATUS_PENDING:
                # A delayed payment method that hasn't cleared yet. Stripe will
                # still send async_payment_succeeded, so leave it be.
                self.stdout.write(
                    f"{order.reference_number}: payment still in progress, leaving alone"
                )
                continue

            if dry_run:
                action = "fulfill" if state == STRIPE_CHECKOUT_STATUS_PAID else "fail"
                self.stdout.write(
                    f"{order.reference_number}: would {action} (Stripe says {state})"
                )
                resolved += 1
                continue

            if state == STRIPE_CHECKOUT_STATUS_PAID:
                fulfill_stripe_order(session_id)
                self.stdout.write(
                    self.style.SUCCESS(f"{order.reference_number}: fulfilled")
                )
            elif state in (
                STRIPE_CHECKOUT_STATUS_CANCELLED,
                STRIPE_CHECKOUT_STATUS_ERROR,
            ):
                cancel_stripe_order(session_id, reason=f"resolved from {state}")
                self.stdout.write(f"{order.reference_number}: marked failed ({state})")

            resolved += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Would resolve {resolved} order(s). Pass --commit to apply."
                )
            )
        else:
            self.stdout.write(f"Resolved {resolved} order(s).")
