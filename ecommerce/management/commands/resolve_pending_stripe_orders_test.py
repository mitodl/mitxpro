"""Tests for the resolve_pending_stripe_orders command"""

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

COMMAND = "resolve_pending_stripe_orders"


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
        "ecommerce.management.commands.resolve_pending_stripe_orders.get_stripe_checkout_session_status",
        return_value={"status": status_value, "session": {}, "payment_intent": None},
    )


def test_requires_an_order_or_all():
    """The command shouldn't guess at what to operate on"""
    with pytest.raises(CommandError):
        call_command(COMMAND)


def test_rejects_order_and_all_together():
    """
    --all silently winning would let someone rescuing a single order apply
    changes to every pending one.
    """
    with pytest.raises(CommandError):
        call_command(COMMAND, order="xpro-b2c-dev-1", all=True)


def test_unknown_reference_number_is_an_error():
    """A typo in the reference number should say so, not silently do nothing"""
    with pytest.raises(CommandError):
        call_command(COMMAND, order="xpro-b2c-dev-999999")


def test_paid_session_fulfills_the_order(mocker, stuck_order):
    """The main case: Stripe took the money, we never heard, so fulfil it now"""
    _patch_status(mocker, STRIPE_CHECKOUT_STATUS_PAID)
    fulfill = mocker.patch(
        "ecommerce.management.commands.resolve_pending_stripe_orders.fulfill_stripe_order"
    )

    call_command(COMMAND, order=stuck_order.reference_number, commit=True)

    fulfill.assert_called_once_with("cs_test_123")


def test_cancelled_session_fails_the_order(mocker, stuck_order):
    """If the payment never happened, the order shouldn't sit pending forever"""
    _patch_status(mocker, STRIPE_CHECKOUT_STATUS_CANCELLED)
    cancel = mocker.patch(
        "ecommerce.management.commands.resolve_pending_stripe_orders.cancel_stripe_order"
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
        "ecommerce.management.commands.resolve_pending_stripe_orders.fulfill_stripe_order"
    )
    cancel = mocker.patch(
        "ecommerce.management.commands.resolve_pending_stripe_orders.cancel_stripe_order"
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
        "ecommerce.management.commands.resolve_pending_stripe_orders.fulfill_stripe_order"
    )

    call_command(COMMAND, order=stuck_order.reference_number)

    assert fulfill.call_count == 0
    stuck_order.refresh_from_db()
    assert stuck_order.status == Order.CREATED


def test_ignores_cybersource_and_already_finished_orders(mocker, stuck_order):
    """--all only picks up Stripe orders that are actually stuck"""
    cybersource_order = OrderFactory.create(status=Order.CREATED)
    cybersource_order.stripe_checkout_session_id = "cs_test_other"
    cybersource_order.save()
    OrderFactory.create(
        status=Order.FULFILLED,
        gateway_type=MITOL_PAYMENT_GATEWAY_STRIPE,
        stripe_checkout_session_id="cs_test_done",
    )
    patched = _patch_status(mocker, STRIPE_CHECKOUT_STATUS_PAID)
    mocker.patch(
        "ecommerce.management.commands.resolve_pending_stripe_orders.fulfill_stripe_order"
    )

    call_command(COMMAND, all=True, commit=True)

    # Only the one stuck Stripe order was looked up.
    assert patched.call_count == 1
    assert patched.call_args.args[0] == stuck_order.stripe_checkout_session_id
