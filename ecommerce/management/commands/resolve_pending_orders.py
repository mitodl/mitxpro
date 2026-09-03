"""
Resolves orders that are stuck in the created state.

A gateway tells us a payment succeeded out of band -- Stripe by webhook,
CyberSource by a server-to-server POST -- and that message can fail to arrive:
the app might have been down, the endpoint misconfigured, or the retries
exhausted. When that happens the learner has paid and the order sits in
`created` forever, because nothing else retries.

Stripe retries webhooks for a while, so a stuck Stripe order means those retries
ran out. CyberSource documents no retry at all for the merchant POST, so a
single failed delivery is likely permanent. Both end up in the same place.

This asks the gateway what actually happened to the order and makes our records
match -- fulfilling it if the payment went through, failing it if it didn't, and
leaving it alone if the payment is still in flight.

Arguments:
* --order <reference number> - a single order (ex: xpro-b2c-dev-123)
* --all - every stuck order, on either gateway
* --commit - actually apply the changes

This reports what it would do and changes nothing unless --commit is passed.
Fulfilling an order enrolls the learner and emails them a receipt, and --all is
the easiest thing to type, so the safe option is the default one.
"""

from django.core.management import BaseCommand, CommandError
from django.db.models import Q
from mitol.payment_gateway.api import PaymentGateway
from mitol.payment_gateway.constants import (
    MITOL_PAYMENT_GATEWAY_CYBERSOURCE,
    MITOL_PAYMENT_GATEWAY_STRIPE,
)

from ecommerce.api import (
    cancel_stripe_order,
    fulfill_order,
    fulfill_stripe_order,
    get_stripe_checkout_session_status,
)
from ecommerce.constants import (
    CYBERSOURCE_DECISION_ACCEPT,
    CYBERSOURCE_DECISION_DECLINE,
    CYBERSOURCE_REASON_CODE_ACCEPTED,
    STRIPE_CHECKOUT_STATUS_CANCELLED,
    STRIPE_CHECKOUT_STATUS_ERROR,
    STRIPE_CHECKOUT_STATUS_PAID,
    STRIPE_CHECKOUT_STATUS_PENDING,
)
from ecommerce.models import Order

# CyberSource's search endpoint takes a batch, so ask for the orders in chunks
# rather than one request per order.
CYBERSOURCE_SEARCH_BATCH_SIZE = 20


def _normalize_cybersource_payload(payload):
    """
    Make the library's transaction payload look like a Secure Acceptance reply.

    fulfill_order decides fulfilled-vs-failed from `decision`, expecting the
    word CyberSource puts in a merchant POST ("ACCEPT", "DECLINE", ...). The
    payment gateway library builds its payload from the Transaction Details
    API instead and writes the numeric reason code into `decision` -- "100" on
    success. Passed through as-is, a paid order would compare "100" != "ACCEPT"
    and be marked failed. Derive the word from the reason code, as MITx Online
    does. The raw reason code is kept alongside.

    The same payload leaves `req_card_type` and `req_card_number` empty, so a
    receipt written from it shows no card details. That is a limit of the
    Transaction Details data the library maps, not something we can fill in.
    """
    reason_code = str(payload.get("reason_code", "")).strip()
    decision = (
        CYBERSOURCE_DECISION_ACCEPT
        if reason_code == CYBERSOURCE_REASON_CODE_ACCEPTED
        else CYBERSOURCE_DECISION_DECLINE
    )
    return {**payload, "decision": decision}


class Command(BaseCommand):
    """
    Resolves orders whose payment confirmation never arrived.
    """

    help = "Resolves orders that are stuck in the created state."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--order",
            type=str,
            help="The order reference number to resolve (ex: xpro-b2c-dev-123).",
            required=False,
        )

        parser.add_argument(
            "--all", action="store_true", help="Resolve all stuck orders."
        )

        parser.add_argument(
            "--commit",
            action="store_true",
            help="Apply the changes. Without this the command only reports.",
        )

    def get_orders(self, reference_number, *, process_all):
        """
        Find the orders to work on.

        Only orders still in `created` are candidates. Stripe orders addtionally
        need a checkout session recorded: without that ID there is nothing to
        ask Stripe about. CyberSource orders are looked up by reference number,
        so they need nothing extra.
        """
        # `__in=[None, ""]` would not match NULL in SQL, so spell the two
        # empty cases out.
        stripe_without_session = Q(gateway_type=MITOL_PAYMENT_GATEWAY_STRIPE) & (
            Q(stripe_checkout_session_id__isnull=True)
            | Q(stripe_checkout_session_id="")
        )
        orders = Order.objects.filter(status=Order.CREATED).exclude(
            stripe_without_session
        )

        if process_all:
            return orders

        try:
            order = Order.objects.get_by_reference_number(reference_number)
        except Order.DoesNotExist:
            raise CommandError(  # noqa: B904
                f"No order found with reference number {reference_number}."  # noqa: EM102
            )

        return orders.filter(id=order.id)

    def _find_cybersource_payloads(self, orders):
        """
        Ask CyberSource what happened to each order.

        Returns a dict of reference number to the CyberSource-shaped payload,
        which is the same shape the merchant POST would have delivered. Orders
        with no transaction found are left out: the learner reached the payment
        page and never paid, which is an abandoned checkout rather than a stuck
        order, and is indistinguishable from one in our own database.
        """
        payloads = {}
        if not orders:
            return payloads

        gateway = PaymentGateway.get_gateway_class(MITOL_PAYMENT_GATEWAY_CYBERSOURCE)
        reference_numbers = [order.reference_number for order in orders]

        for start in range(0, len(reference_numbers), CYBERSOURCE_SEARCH_BATCH_SIZE):
            batch = reference_numbers[start : start + CYBERSOURCE_SEARCH_BATCH_SIZE]
            # Deliberately not PaymentGateway.find_and_get_transactions: it
            # iterates `results.items()` and then indexes the dict with the
            # resulting tuple, so it raises KeyError whenever the search
            # actually finds something. These two calls are what it wraps.
            for (
                transaction_id,
                reference_number,
                _submitted,
            ) in gateway.find_transactions(batch, len(batch)):
                _response, payload = gateway.get_transaction_details(transaction_id)
                payloads[reference_number] = _normalize_cybersource_payload(payload)

        return payloads

    def _resolve_cybersource(self, orders, *, dry_run):
        """Resolve CyberSource orders by replaying the reply we never received"""
        resolved = 0
        payloads = self._find_cybersource_payloads(orders)

        for order in orders:
            payload = payloads.get(order.reference_number)

            if payload is None:
                self.stdout.write(
                    f"{order.reference_number}: no CyberSource transaction, "
                    "likely an abandoned checkout, leaving alone"
                )
                continue

            decision = payload.get("decision")

            if dry_run:
                action = (
                    "fulfill" if decision == CYBERSOURCE_DECISION_ACCEPT else "fail"
                )
                self.stdout.write(
                    f"{order.reference_number}: would {action} "
                    f"(CyberSource says {decision})"
                )
                resolved += 1
                continue

            # fulfill_order is the same path the merchant POST takes: it records
            # the receipt, moves the order to fulfilled or failed based on the
            # decision, and enrolls the learner when it succeeded.
            fulfill_order(payload)

            if decision == CYBERSOURCE_DECISION_ACCEPT:
                self.stdout.write(
                    self.style.SUCCESS(f"{order.reference_number}: fulfilled")
                )
            else:
                self.stdout.write(
                    f"{order.reference_number}: marked failed ({decision})"
                )

            resolved += 1

        return resolved

    def _resolve_stripe(self, orders, *, dry_run):
        """Resolve Stripe orders by asking about their checkout session"""
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

        return resolved

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
            self.stdout.write("No stuck orders found.")
            return

        stripe_orders = [
            order
            for order in orders
            if order.gateway_type == MITOL_PAYMENT_GATEWAY_STRIPE
        ]
        cybersource_orders = [
            order
            for order in orders
            if order.gateway_type != MITOL_PAYMENT_GATEWAY_STRIPE
        ]

        resolved = self._resolve_stripe(stripe_orders, dry_run=dry_run)
        resolved += self._resolve_cybersource(cybersource_orders, dry_run=dry_run)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Would resolve {resolved} order(s). Pass --commit to apply."
                )
            )
        else:
            self.stdout.write(f"Resolved {resolved} order(s).")
