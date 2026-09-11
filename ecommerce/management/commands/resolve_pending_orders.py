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
* --order <reference number or ID> - a single order (ex: xpro-b2c-dev-123, or 123)
* --all - every stuck order, on either gateway
* --commit - actually apply the changes

This reports what it would do and changes nothing unless --commit is passed.
Fulfilling an order enrolls the learner and emails them a receipt, and --all is
the easiest thing to type, so the safe option is the default one.
"""

import logging
import operator
from collections import defaultdict

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
from ecommerce.exceptions import ParseException
from ecommerce.models import Order

log = logging.getLogger(__name__)

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
        # Exactly one of these, enforced by argparse: naming an order and
        # also passing --all is a mistake worth refusing rather than guessing
        # at, since the two mean very different amounts of money.
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument(
            "--order",
            type=str,
            help=(
                "The order to resolve, as a reference number "
                "(ex: xpro-b2c-dev-123) or a plain order ID (ex: 123)."
            ),
        )
        target.add_argument(
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

        return orders.filter(id=self._resolve_identifier(reference_number).id)

    @staticmethod
    def _resolve_identifier(identifier):
        """
        Find the order named on the command line.

        Accepts a reference number or a bare order ID: the ID is what an
        operator reading the database has to hand, the reference number is what
        the gateway reports.
        """
        if identifier.isdigit():
            order = Order.objects.filter(id=int(identifier)).first()
        else:
            try:
                order = Order.objects.get_by_reference_number(identifier)
            except Order.DoesNotExist:
                order = None
            except ParseException as exc:
                # Raised for a reference number from another environment, or one
                # that doesn't end in an order ID. Without this it escapes as a
                # traceback instead of telling the operator what to fix.
                raise CommandError(  # noqa: TRY003
                    f"{identifier} is not a valid order reference number: {exc}"  # noqa: EM102
                ) from None

        if order is None:
            raise CommandError(f"No order found for {identifier}.")  # noqa: EM102, TRY003

        return order

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
        found = defaultdict(list)

        for start in range(0, len(reference_numbers), CYBERSOURCE_SEARCH_BATCH_SIZE):
            batch = reference_numbers[start : start + CYBERSOURCE_SEARCH_BATCH_SIZE]
            # Deliberately not PaymentGateway.find_and_get_transactions: it
            # iterates `results.items()` and then indexes the dict with the
            # resulting tuple, so it raises KeyError whenever the search
            # actually finds something. These two calls are what it wraps.
            for (
                transaction_id,
                reference_number,
                submitted,
            ) in gateway.find_transactions(batch, len(batch)):
                found[reference_number].append((submitted, transaction_id))

        for reference_number, transactions in found.items():
            detailed = []
            for submitted, transaction_id in transactions:
                _response, payload = gateway.get_transaction_details(transaction_id)
                detailed.append((submitted, _normalize_cybersource_payload(payload)))

            # An unpaid order is reused across checkout attempts, so one
            # reference number can carry several transactions -- a decline
            # followed by a successful retry is exactly what this command
            # exists to rescue. find_transactions promises no ordering, so
            # choose deliberately rather than keeping whichever arrived last:
            # an accepted transaction wins, and the most recent breaks a tie.
            # Taking the last one would mark a genuinely paid order failed.
            accepted = [
                entry
                for entry in detailed
                if entry[1].get("decision") == CYBERSOURCE_DECISION_ACCEPT
            ]
            submitted_at = operator.itemgetter(0)
            payloads[reference_number] = max(accepted or detailed, key=submitted_at)[1]

        return payloads

    def _resolve_cybersource(self, orders, *, dry_run):
        """Resolve CyberSource orders by replaying the reply we never received"""
        resolved = 0
        errors = 0

        try:
            payloads = self._find_cybersource_payloads(orders)
        except Exception:
            # The batch lookup runs before the per-order loop, so a failure
            # here -- bad gateway credentials, CyberSource unreachable -- would
            # otherwise escape as a traceback and take the Stripe orders down
            # with it. Report it and let the rest of the run continue.
            log.exception("Could not query CyberSource for pending transactions")
            self.stderr.write(
                f"Could not reach CyberSource; skipped {len(orders)} order(s). "
                "Check the MITOL_PAYMENT_GATEWAY_CYBERSOURCE_* settings."
            )
            return 0, len(orders)

        for order in orders:
            try:
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
            except Exception:
                # Keep going: with --all, one unresolvable order must not
                # strand every other stuck learner behind it.
                errors += 1
                log.exception("Failed to resolve %s", order.reference_number)
                self.stderr.write(f"{order.reference_number}: errored, skipped")

        return resolved, errors

    def _resolve_stripe(self, orders, *, dry_run):
        """Resolve Stripe orders by asking about their checkout session"""
        resolved = 0
        errors = 0

        for order in orders:
            try:
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
                    action = (
                        "fulfill" if state == STRIPE_CHECKOUT_STATUS_PAID else "fail"
                    )
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
                    self.stdout.write(
                        f"{order.reference_number}: marked failed ({state})"
                    )

                resolved += 1
            except Exception:
                errors += 1
                log.exception("Failed to resolve %s", order.reference_number)
                self.stderr.write(f"{order.reference_number}: errored, skipped")

        return resolved, errors

    def handle(self, *args, **kwargs):  # noqa: ARG002
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

        resolved, errors = self._resolve_stripe(stripe_orders, dry_run=dry_run)
        cs_resolved, cs_errors = self._resolve_cybersource(
            cybersource_orders, dry_run=dry_run
        )
        resolved += cs_resolved
        errors += cs_errors

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Would resolve {resolved} order(s). Pass --commit to apply."
                )
            )
        else:
            self.stdout.write(f"Resolved {resolved} order(s).")

        if errors:
            # Exit non-zero so a scheduled run surfaces the failures, but only
            # after everything resolvable has been dealt with.
            raise CommandError(f"{errors} order(s) could not be resolved.")  # noqa: EM102, TRY003
