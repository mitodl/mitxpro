"""Tests for the resolve_pending_orders command"""

from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from mitol.payment_gateway.constants import MITOL_PAYMENT_GATEWAY_STRIPE

from ecommerce.constants import (
    STRIPE_CHECKOUT_STATUS_CANCELLED,
    STRIPE_CHECKOUT_STATUS_PAID,
    STRIPE_CHECKOUT_STATUS_PENDING,
)
from ecommerce.factories import LineFactory, OrderFactory
from ecommerce.models import Order

pytestmark = pytest.mark.django_db

COMMAND = "resolve_pending_orders"


@pytest.fixture
def stuck_order():
    """An order whose webhook never arrived: paid at Stripe, still `created` here"""
    order = OrderFactory.create(
        status=Order.CREATED,
        gateway_type=MITOL_PAYMENT_GATEWAY_STRIPE,
        stripe_checkout_session_id="cs_test_123",
    )
    LineFactory.create(order=order)
    return order


def _patch_status(mocker, status_value):
    """Make Stripe report a given state for the session"""
    return mocker.patch(
        "ecommerce.management.commands.resolve_pending_orders.get_stripe_checkout_session_status",
        return_value={"status": status_value, "session": {}, "payment_intent": None},
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({}, id="neither"),
        pytest.param({"order": "xpro-b2c-dev-1", "all": True}, id="both"),
    ],
)
def test_requires_exactly_one_of_order_or_all(kwargs):
    """
    The command shouldn't guess at what to operate on, and letting --all
    silently win would apply changes to every pending order when the operator
    named a single one.
    """
    with pytest.raises(CommandError):
        call_command(COMMAND, **kwargs)


def test_unknown_reference_number_is_an_error():
    """A typo in the reference number should say so, not silently do nothing"""
    with pytest.raises(CommandError):
        call_command(COMMAND, order="xpro-b2c-dev-999999")


def test_nothing_stuck_is_not_an_error():
    """
    Nothing stuck is the healthy state. Exiting non-zero would make this
    unusable on a schedule.
    """
    call_command(COMMAND, all=True)


def test_paid_session_fulfills_the_order(mocker, stuck_order):
    """The main case: Stripe took the money, we never heard, so fulfil it now"""
    _patch_status(mocker, STRIPE_CHECKOUT_STATUS_PAID)
    fulfill = mocker.patch(
        "ecommerce.management.commands.resolve_pending_orders.fulfill_stripe_order"
    )

    call_command(COMMAND, order=stuck_order.reference_number, commit=True)

    fulfill.assert_called_once_with("cs_test_123")


def test_cancelled_session_fails_the_order(mocker, stuck_order):
    """If the payment never happened, the order shouldn't sit pending forever"""
    _patch_status(mocker, STRIPE_CHECKOUT_STATUS_CANCELLED)
    cancel = mocker.patch(
        "ecommerce.management.commands.resolve_pending_orders.cancel_stripe_order"
    )

    call_command(COMMAND, order=stuck_order.reference_number, commit=True)

    assert cancel.call_count == 1


def test_pending_payment_is_left_alone(mocker, stuck_order):
    """
    A delayed payment that hasn't cleared is not stuck -- Stripe will still send
    async_payment_succeeded, so the command must not pre-empt it.
    """
    _patch_status(mocker, STRIPE_CHECKOUT_STATUS_PENDING)
    fulfill = mocker.patch(
        "ecommerce.management.commands.resolve_pending_orders.fulfill_stripe_order"
    )
    cancel = mocker.patch(
        "ecommerce.management.commands.resolve_pending_orders.cancel_stripe_order"
    )

    call_command(COMMAND, order=stuck_order.reference_number, commit=True)

    assert fulfill.call_count == 0
    assert cancel.call_count == 0


def test_reports_without_changing_anything_by_default(mocker, stuck_order):
    """
    Fulfilling enrolls a learner and emails them a receipt, so the command
    reports and stops unless --commit is passed.
    """
    _patch_status(mocker, STRIPE_CHECKOUT_STATUS_PAID)
    fulfill = mocker.patch(
        "ecommerce.management.commands.resolve_pending_orders.fulfill_stripe_order"
    )

    call_command(COMMAND, order=stuck_order.reference_number)

    assert fulfill.call_count == 0
    stuck_order.refresh_from_db()
    assert stuck_order.status == Order.CREATED


def test_ignores_already_finished_orders(mocker, stuck_order):
    """
    --all picks up stuck orders on both gateways, and nothing that has already
    reached a final state.
    """
    cybersource_order = OrderFactory.create(status=Order.CREATED)
    OrderFactory.create(
        status=Order.FULFILLED,
        gateway_type=MITOL_PAYMENT_GATEWAY_STRIPE,
        stripe_checkout_session_id="cs_test_done",
    )
    OrderFactory.create(status=Order.FULFILLED)
    patched = _patch_status(mocker, STRIPE_CHECKOUT_STATUS_PAID)
    mocker.patch(
        "ecommerce.management.commands.resolve_pending_orders.fulfill_stripe_order"
    )
    gateway = _patch_cybersource(mocker, [])

    call_command(COMMAND, all=True, commit=True)

    # Only the stuck Stripe order was looked up at Stripe.
    assert patched.call_count == 1
    assert patched.call_args.args[0] == stuck_order.stripe_checkout_session_id
    # And only the stuck CyberSource order was searched for.
    assert gateway.find_transactions.call_args.args[0] == [
        cybersource_order.reference_number
    ]


@pytest.fixture
def cybersource_stuck_order():
    """
    An order whose merchant POST never arrived: paid at CyberSource, still
    `created` here. CyberSource is the model default, so nothing to set.
    """
    order = OrderFactory.create(status=Order.CREATED)
    LineFactory.create(order=order)
    return order


def _library_payload(refno, reason_code):
    """
    A payload shaped the way the payment gateway library actually returns it.

    Note `decision` carries the numeric reason code, not a word -- that is what
    the library does, and it is why the command has to normalize it. A test
    using a tidy {"decision": "ACCEPT"} payload would pass against code that
    marks every paid order failed.
    """
    return {
        "decision": reason_code,
        "reason_code": reason_code,
        "req_reference_number": refno,
        "req_card_type": "",
        "req_card_number": "",
    }


def _patch_cybersource(mocker, transactions, payload=None):
    """
    Stand in for the CyberSource gateway.

    `transactions` is what the search returns: (transaction id, reference
    number, submitted at) rows, the same shape find_transactions produces.
    """
    gateway = mocker.Mock()
    gateway.find_transactions.return_value = transactions
    gateway.get_transaction_details.return_value = (mocker.Mock(), payload)
    mocker.patch(
        "ecommerce.management.commands.resolve_pending_orders.PaymentGateway.get_gateway_class",
        return_value=gateway,
    )
    return gateway


def test_paid_cybersource_transaction_fulfills_the_order(
    mocker, cybersource_stuck_order
):
    """
    The CyberSource equivalent of the main case: the money was taken, the
    merchant POST never landed, so replay it now.
    """
    refno = cybersource_stuck_order.reference_number
    _patch_cybersource(
        mocker,
        [["7883514374536923204011", refno, "2026-09-02"]],
        _library_payload(refno, "100"),
    )
    fulfill = mocker.patch(
        "ecommerce.management.commands.resolve_pending_orders.fulfill_order"
    )

    call_command(COMMAND, order=refno, commit=True)

    fulfill.assert_called_once()
    replayed = fulfill.call_args.args[0]
    assert replayed["req_reference_number"] == refno
    # The library's "100" must arrive at fulfill_order as the word it expects,
    # or determine_order_status_change fails a paid order.
    assert replayed["decision"] == "ACCEPT"
    assert replayed["reason_code"] == "100"


def test_declined_cybersource_transaction_still_replays(
    mocker, cybersource_stuck_order
):
    """
    A declined payment is resolved too: fulfill_order records the receipt and
    moves the order to failed, so it stops sitting in `created`.
    """
    refno = cybersource_stuck_order.reference_number
    _patch_cybersource(
        mocker,
        [["788351437453692320401", refno, "2026-09-02"]],
        _library_payload(refno, "203"),
    )
    fulfill = mocker.patch(
        "ecommerce.management.commands.resolve_pending_orders.fulfill_order"
    )

    call_command(COMMAND, order=refno, commit=True)

    fulfill.assert_called_once()
    assert fulfill.call_args.args[0]["decision"] == "DECLINE"


def test_cybersource_order_with_no_transaction_is_left_alone(
    mocker, cybersource_stuck_order
):
    """
    No transaction means the learner never paid -- an abandoned checkout, which
    looks identical to a stuck order in our own database. Don't touch it.
    """
    _patch_cybersource(mocker, [])
    fulfill = mocker.patch(
        "ecommerce.management.commands.resolve_pending_orders.fulfill_order"
    )

    call_command(COMMAND, order=cybersource_stuck_order.reference_number, commit=True)

    fulfill.assert_not_called()


def test_cybersource_dry_run_reports_the_right_action(mocker, cybersource_stuck_order):
    """
    Without --commit the command reports and leaves the order alone -- and
    the report has to say "fulfill" for a paid order, not "fail".
    """
    refno = cybersource_stuck_order.reference_number
    _patch_cybersource(
        mocker,
        [["7883514374536923204011", refno, "2026-09-02"]],
        _library_payload(refno, "100"),
    )
    fulfill = mocker.patch(
        "ecommerce.management.commands.resolve_pending_orders.fulfill_order"
    )
    out = StringIO()

    call_command(COMMAND, order=refno, stdout=out)

    fulfill.assert_not_called()
    cybersource_stuck_order.refresh_from_db()
    assert cybersource_stuck_order.status == Order.CREATED
    assert f"{refno}: would fulfill" in out.getvalue()


def test_does_not_use_the_broken_library_helper(mocker, cybersource_stuck_order):
    """
    PaymentGateway.find_and_get_transactions raises KeyError as soon as the
    search finds anything, so this command must not call it.
    """
    refno = cybersource_stuck_order.reference_number
    gateway = _patch_cybersource(
        mocker,
        [["7883514374536923204011", refno, "2026-09-02"]],
        _library_payload(refno, "100"),
    )
    mocker.patch("ecommerce.management.commands.resolve_pending_orders.fulfill_order")

    call_command(COMMAND, order=refno, commit=True)

    gateway.find_and_get_transactions.assert_not_called()
    gateway.find_transactions.assert_called_once()
