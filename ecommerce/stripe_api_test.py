"""Tests for the Stripe payment gateway integration"""

import decimal

import pytest

from ecommerce.api import (
    _generate_cybersource_sa_payload,
    _generate_stripe_cart_items,
    cancel_stripe_order,
    fulfill_stripe_order,
    get_gateway_type_for_user,
    get_stripe_checkout_session_status,
    start_stripe_checkout,
    stripe_data_to_receipt_data,
)
from ecommerce.constants import (
    STRIPE_CHECKOUT_STATUS_CANCELLED,
    STRIPE_CHECKOUT_STATUS_ERROR,
    STRIPE_CHECKOUT_STATUS_PAID,
    STRIPE_CHECKOUT_STATUS_PENDING,
)
from ecommerce.factories import LineFactory, OrderFactory
from ecommerce.models import Order
from mitol.payment_gateway.constants import (
    MITOL_PAYMENT_GATEWAY_CYBERSOURCE,
    MITOL_PAYMENT_GATEWAY_STRIPE,
)

pytestmark = pytest.mark.django_db


def _checkout_session(**kwargs):
    """Build a Stripe checkout session payload for tests"""
    session = {
        "id": "cs_test_123",
        "object": "checkout.session",
        "status": "complete",
        "payment_status": "paid",
        "client_reference_id": None,
        "amount_total": 10000,
        "currency": "usd",
        "customer_details": {"email": "learner@example.com"},
        "total_details": {"amount_tax": 0},
        "metadata": {},
        "payment_intent": {
            "id": "pi_test_123",
            "status": "succeeded",
            "latest_charge": {
                "id": "ch_test_123",
                "payment_method_details": {"card": {"brand": "visa", "last4": "4242"}},
            },
        },
    }
    session.update(kwargs)
    return session


@pytest.fixture
def order_with_line():
    """An order with a single line, as B2C orders always have"""
    order = OrderFactory.create(status=Order.CREATED)
    LineFactory.create(order=order)
    return order


class TestGatewaySelection:
    """The per-user gateway choice"""

    @pytest.mark.parametrize(
        ("flag_enabled", "configured_default", "expected"),
        [
            # The flag wins whenever it is on.
            (True, MITOL_PAYMENT_GATEWAY_CYBERSOURCE, MITOL_PAYMENT_GATEWAY_STRIPE),
            (True, MITOL_PAYMENT_GATEWAY_STRIPE, MITOL_PAYMENT_GATEWAY_STRIPE),
            # Otherwise the configured default decides, so a deployment (or a
            # local setup with no PostHog) can force one gateway.
            (False, MITOL_PAYMENT_GATEWAY_STRIPE, MITOL_PAYMENT_GATEWAY_STRIPE),
            (
                False,
                MITOL_PAYMENT_GATEWAY_CYBERSOURCE,
                MITOL_PAYMENT_GATEWAY_CYBERSOURCE,
            ),
        ],
    )
    def test_gateway_selection(
        self, mocker, user, settings, flag_enabled, configured_default, expected
    ):
        """The flag chooses the gateway, falling back to the configured default"""
        settings.ECOMMERCE_DEFAULT_PAYMENT_GATEWAY = configured_default
        mocker.patch("ecommerce.api.is_enabled", return_value=flag_enabled)

        assert get_gateway_type_for_user(user) == expected

    def test_flag_is_evaluated_per_user(self, mocker, user):
        """The user's ID is passed to the flag so rollout can be gradual"""
        patched = mocker.patch("ecommerce.api.is_enabled", return_value=False)

        get_gateway_type_for_user(user)

        assert patched.call_args.kwargs["opt_unique_id"] == str(user.id)


class TestCartMapping:
    """Mapping an order onto the gateway's cart items"""

    def test_total_matches_cybersource(self, order_with_line):
        """
        The amount sent to Stripe must equal the amount CyberSource would have
        been sent for the same order. This is the invariant that stops the
        migration from charging people a different price.
        """
        cybersource_payload = _generate_cybersource_sa_payload(
            order=order_with_line,
            receipt_url="http://example.com/receipt",
            cancel_url="http://example.com/cancel",
            ip_address="127.0.0.1",
        )
        cart_items = _generate_stripe_cart_items(order_with_line)
        stripe_total = sum(
            (decimal.Decimal(item.unitprice) + decimal.Decimal(item.taxable))
            * item.quantity
            for item in cart_items
        ).quantize(decimal.Decimal("0.01"))

        assert stripe_total == decimal.Decimal(cybersource_payload["amount"])

    def test_tax_is_passed_separately(self, order_with_line):
        """Tax we calculated is handed over as `taxable`, not folded into the price"""
        order_with_line.tax_rate = decimal.Decimal("10.0000")
        order_with_line.save()

        cart_items = _generate_stripe_cart_items(order_with_line)

        assert len(cart_items) == 1
        assert cart_items[0].taxable > 0
        expected_tax = (
            decimal.Decimal(cart_items[0].unitprice) * decimal.Decimal("0.10")
        ).quantize(decimal.Decimal("0.01"))
        assert cart_items[0].taxable == expected_tax

    def test_quantity_is_not_multiplied(self, order_with_line):
        """
        Quantity stays at 1: order totals are computed from the unit price
        without it, so multiplying here would overcharge.
        """
        line = order_with_line.lines.first()
        line.quantity = 3
        line.save()

        cart_items = _generate_stripe_cart_items(order_with_line)

        assert all(item.quantity == 1 for item in cart_items)


class TestCheckoutPayload:
    """What the checkout API hands back to the frontend"""

    def test_payload_carries_the_reference_number(self, mocker, order_with_line):
        """
        The checkout page tags its GTM purchase event with `reference_number`.
        A Stripe session calls it `client_reference_id`, so we add the key the
        frontend already reads -- CyberSource's payload has it too.
        """
        mocker.patch(
            "ecommerce.api.PaymentGateway.start_payment",
            return_value={
                "payload": {"id": "cs_test_123", "client_reference_id": "x"},
                "url": "https://checkout.stripe.com/c/pay/cs_test_123",
                "method": "GET",
            },
        )

        response = start_stripe_checkout(
            order=order_with_line,
            receipt_url="http://example.com/receipt",
            cancel_url="http://example.com/cancel",
        )

        assert (
            response["payload"]["reference_number"] == order_with_line.reference_number
        )


class TestSupersededSessions:
    """Starting checkout again on the same order"""

    def test_previous_session_is_expired(self, mocker, order_with_line):
        """
        An unpaid order is reused across attempts, so a learner who goes back
        and starts again gets a second session. Both would stay payable, which
        is a route to being charged twice.
        """
        order_with_line.stripe_checkout_session_id = "cs_test_old"
        order_with_line.save()
        mocker.patch(
            "ecommerce.api.PaymentGateway.start_payment",
            return_value={
                "payload": {"id": "cs_test_new"},
                "url": "https://checkout.stripe.com/c/pay/cs_test_new",
                "method": "GET",
            },
        )
        expire = mocker.patch("ecommerce.api.expire_stripe_checkout_session")

        start_stripe_checkout(
            order=order_with_line,
            receipt_url="http://example.com/receipt",
            cancel_url="http://example.com/cancel",
        )

        expire.assert_called_once_with("cs_test_old")
        order_with_line.refresh_from_db()
        assert order_with_line.stripe_checkout_session_id == "cs_test_new"

    def test_swap_reads_the_stored_session_not_the_instance(
        self, mocker, order_with_line
    ):
        """
        The previous session must come from the database under the lock, not
        from the in-memory instance: a stale instance would expire an already
        superseded session and leave the truly-previous one payable.
        """
        # Simulate another checkout having landed after this instance was read.
        Order.objects.filter(id=order_with_line.id).update(
            stripe_checkout_session_id="cs_test_concurrent"
        )
        # The in-memory instance still says None.
        assert order_with_line.stripe_checkout_session_id is None

        mocker.patch(
            "ecommerce.api.PaymentGateway.start_payment",
            return_value={
                "payload": {"id": "cs_test_new"},
                "url": "https://checkout.stripe.com/c/pay/cs_test_new",
                "method": "GET",
            },
        )
        expire = mocker.patch("ecommerce.api.expire_stripe_checkout_session")

        start_stripe_checkout(
            order=order_with_line,
            receipt_url="http://example.com/receipt",
            cancel_url="http://example.com/cancel",
        )

        # It expired what was actually stored, not what the instance believed.
        expire.assert_called_once_with("cs_test_concurrent")

    def test_nothing_to_expire_on_a_first_attempt(self, mocker, order_with_line):
        """No previous session means nothing to retire"""
        mocker.patch(
            "ecommerce.api.PaymentGateway.start_payment",
            return_value={
                "payload": {"id": "cs_test_new"},
                "url": "https://checkout.stripe.com/c/pay/cs_test_new",
                "method": "GET",
            },
        )
        expire = mocker.patch("ecommerce.api.expire_stripe_checkout_session")

        start_stripe_checkout(
            order=order_with_line,
            receipt_url="http://example.com/receipt",
            cancel_url="http://example.com/cancel",
        )

        assert expire.call_count == 0


class TestSessionStatus:
    """Collapsing a checkout session into a single state"""

    @pytest.mark.parametrize(
        ("session_kwargs", "expected"),
        [
            ({}, STRIPE_CHECKOUT_STATUS_PAID),
            (
                {"payment_status": "no_payment_required"},
                STRIPE_CHECKOUT_STATUS_PAID,
            ),
            (
                {
                    "payment_status": "unpaid",
                    "payment_intent": {"id": "pi", "status": "processing"},
                },
                STRIPE_CHECKOUT_STATUS_PENDING,
            ),
            (
                {"status": "expired", "payment_status": "unpaid"},
                STRIPE_CHECKOUT_STATUS_CANCELLED,
            ),
            (
                {
                    "payment_status": "unpaid",
                    "payment_intent": {"id": "pi", "status": "requires_payment_method"},
                },
                STRIPE_CHECKOUT_STATUS_ERROR,
            ),
        ],
    )
    def test_status_is_derived_from_session_and_intent(
        self, mocker, session_kwargs, expected
    ):
        """
        `checkout.session.completed` alone doesn't mean paid: for delayed
        payment methods the session completes while the PaymentIntent is still
        processing, so both are considered.
        """
        session = _checkout_session(**session_kwargs)
        gateway = mocker.patch("ecommerce.api.PaymentGateway.get_gateway_class")
        gateway.return_value.stripe_client.v1.checkout.sessions.retrieve.return_value = session

        result = get_stripe_checkout_session_status("cs_test_123")

        assert result["status"] == expected


class TestReceiptMapping:
    """Translating Stripe data into the receipt keys the app already reads"""

    def test_writes_existing_req_keys(self):
        """The receipt page and email read req_* keys, so we write those"""
        session = _checkout_session(
            client_reference_id="xpro-b2c-dev-1",
            amount_total=12345,
            total_details={"amount_tax": 345},
        )

        receipt_data = stripe_data_to_receipt_data(session, session["payment_intent"])

        assert receipt_data["req_reference_number"] == "xpro-b2c-dev-1"
        assert receipt_data["req_amount"] == "123.45"
        assert receipt_data["req_card_number"] == "xxxxxxxxxxxx4242"
        # The serializer looks brands up in CYBERSOURCE_CARD_TYPES by code.
        assert receipt_data["req_card_type"] == "001"
        assert receipt_data["req_tax_amount"] == "3.45"
        assert receipt_data["req_bill_to_email"] == "learner@example.com"
        assert receipt_data["decision"] == "ACCEPT"

    @pytest.mark.parametrize(
        ("payment_method_details", "expected_method", "expected_card"),
        [
            (
                {"type": "card", "card": {"brand": "visa", "last4": "4242"}},
                "card",
                "xxxxxxxxxxxx4242",
            ),
            # ACH is enabled for learners, so the receipt must not claim "card".
            (
                {"type": "us_bank_account", "us_bank_account": {"last4": "6789"}},
                "us_bank_account",
                "",
            ),
        ],
    )
    def test_payment_method_is_taken_from_the_charge(
        self, payment_method_details, expected_method, expected_card
    ):
        """The receipt records what the learner actually paid with"""
        session = _checkout_session(
            payment_intent={
                "id": "pi_test_123",
                "status": "succeeded",
                "latest_charge": {
                    "id": "ch_test_123",
                    "payment_method_details": payment_method_details,
                },
            }
        )

        receipt_data = stripe_data_to_receipt_data(session, session["payment_intent"])

        assert receipt_data["req_payment_method"] == expected_method
        assert receipt_data["req_card_number"] == expected_card

    def test_keeps_the_raw_stripe_objects(self):
        """Nothing Stripe told us is thrown away"""
        session = _checkout_session()

        receipt_data = stripe_data_to_receipt_data(session, session["payment_intent"])

        assert receipt_data["stripe_checkout_session"] == session
        assert receipt_data["stripe_payment_intent"]["id"] == "pi_test_123"


class TestReceiptSerialization:
    """The receipt page and email have to keep working unchanged"""

    def test_card_brand_survives_into_the_receipt(self, order_with_line):
        """
        `OrderReceiptSerializer` looks the card type up in
        CYBERSOURCE_CARD_TYPES by numeric code, so a raw Stripe brand like
        "visa" would silently drop off the receipt.
        """
        from ecommerce.models import Receipt
        from ecommerce.serializers import OrderReceiptSerializer

        session = _checkout_session(
            client_reference_id=order_with_line.reference_number
        )
        receipt_data = stripe_data_to_receipt_data(session, session["payment_intent"])
        Receipt.objects.create(data=receipt_data, order=order_with_line)

        serialized = OrderReceiptSerializer(order_with_line).data

        assert serialized["receipt"]["card_type"] == "Visa"
        assert serialized["receipt"]["card_number"] == "xxxxxxxxxxxx4242"


class TestReceiptDecision:
    """The stored decision has to match what actually happened"""

    @pytest.mark.parametrize(
        ("checkout_status", "expected_decision"),
        [
            (STRIPE_CHECKOUT_STATUS_PAID, "ACCEPT"),
            (STRIPE_CHECKOUT_STATUS_CANCELLED, "CANCEL"),
            (STRIPE_CHECKOUT_STATUS_ERROR, "DECLINE"),
        ],
    )
    def test_decision_reflects_the_outcome(self, checkout_status, expected_decision):
        """
        A receipt is stored for failures too, so recording ACCEPT on a failed
        payment would leave contradictory records behind.
        """
        session = _checkout_session()

        receipt_data = stripe_data_to_receipt_data(
            session, session["payment_intent"], checkout_status=checkout_status
        )

        assert receipt_data["decision"] == expected_decision


class TestFulfillment:
    """Fulfilling an order from a webhook"""

    @staticmethod
    def _patch_status(mocker, order, status_value):
        """Patch the session lookup to return a given state for this order"""
        session = _checkout_session(client_reference_id=order.reference_number)
        return mocker.patch(
            "ecommerce.api.get_stripe_checkout_session_status",
            return_value={
                "status": status_value,
                "session": session,
                "payment_intent": session["payment_intent"],
            },
        )

    def test_paid_session_fulfills(self, order_with_line, mocker):
        """A paid session fulfils the order and sends the receipt"""
        mocker.patch("ecommerce.api.complete_order")
        mocker.patch("ecommerce.api.sync_hubspot_deal")
        send_receipt = mocker.patch("ecommerce.api.send_ecommerce_order_receipt")

        self._patch_status(mocker, order_with_line, STRIPE_CHECKOUT_STATUS_PAID)

        fulfill_stripe_order("cs_test_123")

        order_with_line.refresh_from_db()
        assert order_with_line.status == Order.FULFILLED
        assert send_receipt.call_count == 1

    def test_pending_session_does_not_fulfill(self, order_with_line, mocker):
        """
        A delayed payment that hasn't cleared leaves the order alone -- we wait
        for checkout.session.async_payment_succeeded instead of enrolling
        someone whose bank transfer might still fail.
        """
        complete = mocker.patch("ecommerce.api.complete_order")
        mocker.patch("ecommerce.api.sync_hubspot_deal")

        self._patch_status(mocker, order_with_line, STRIPE_CHECKOUT_STATUS_PENDING)

        fulfill_stripe_order("cs_test_123")

        order_with_line.refresh_from_db()
        assert order_with_line.status == Order.CREATED
        assert complete.call_count == 0

    def test_failed_session_marks_order_failed(self, order_with_line, mocker):
        """A payment that didn't go through fails the order"""
        mocker.patch("ecommerce.api.complete_order")
        mocker.patch("ecommerce.api.sync_hubspot_deal")

        self._patch_status(mocker, order_with_line, STRIPE_CHECKOUT_STATUS_ERROR)

        fulfill_stripe_order("cs_test_123")

        order_with_line.refresh_from_db()
        assert order_with_line.status == Order.FAILED

    def test_redelivered_failure_does_not_pile_up_receipts(
        self, order_with_line, mocker
    ):
        """
        FAILED is terminal too: a failed order is never reused, so a
        redelivered failure event must not write another receipt each time.
        """
        from ecommerce.models import Receipt

        mocker.patch("ecommerce.api.complete_order")
        mocker.patch("ecommerce.api.sync_hubspot_deal")

        with_status = self._patch_status(
            mocker, order_with_line, STRIPE_CHECKOUT_STATUS_ERROR
        )
        fulfill_stripe_order("cs_test_123")
        fulfill_stripe_order("cs_test_123")
        assert with_status.call_count == 2

        order_with_line.refresh_from_db()
        assert order_with_line.status == Order.FAILED
        assert Receipt.objects.filter(order=order_with_line).count() == 1

    def test_duplicate_delivery_is_a_no_op(self, order_with_line, mocker):
        """
        Stripe delivers events at least once and retries anything that isn't a
        2xx, so a repeat delivery must not enroll the learner twice or raise.
        """
        complete = mocker.patch("ecommerce.api.complete_order")
        mocker.patch("ecommerce.api.sync_hubspot_deal")
        send_receipt = mocker.patch("ecommerce.api.send_ecommerce_order_receipt")

        self._patch_status(mocker, order_with_line, STRIPE_CHECKOUT_STATUS_PAID)

        fulfill_stripe_order("cs_test_123")
        fulfill_stripe_order("cs_test_123")

        order_with_line.refresh_from_db()
        assert order_with_line.status == Order.FULFILLED
        assert complete.call_count == 1
        assert send_receipt.call_count == 1

    def test_crm_failure_does_not_block_enrollment(self, order_with_line, mocker):
        """
        A HubSpot outage must not stop the learner being enrolled. The order is
        committed as fulfilled before this point, so an exception here would
        make Stripe retry, and the retry short-circuits on the already-fulfilled
        order -- leaving someone who paid without their enrollment.
        """
        complete = mocker.patch("ecommerce.api.complete_order")
        mocker.patch("ecommerce.api.send_ecommerce_order_receipt")
        mocker.patch(
            "ecommerce.api.sync_hubspot_deal", side_effect=Exception("hubspot down")
        )

        self._patch_status(mocker, order_with_line, STRIPE_CHECKOUT_STATUS_PAID)

        fulfill_stripe_order("cs_test_123")

        order_with_line.refresh_from_db()
        assert order_with_line.status == Order.FULFILLED
        assert complete.call_count == 1

    def test_unknown_reference_is_handled(self, mocker):
        """A session for an order we don't have doesn't blow up the webhook"""
        session = _checkout_session(client_reference_id="xpro-b2c-dev-999999")
        mocker.patch(
            "ecommerce.api.get_stripe_checkout_session_status",
            return_value={
                "status": STRIPE_CHECKOUT_STATUS_PAID,
                "session": session,
                "payment_intent": None,
            },
        )

        assert fulfill_stripe_order("cs_test_123") is None


class TestCancellation:
    """Expired and failed sessions"""

    def test_expired_session_fails_the_order(self, order_with_line):
        """An expired checkout session marks the order failed"""
        order_with_line.stripe_checkout_session_id = "cs_test_123"
        order_with_line.save()

        cancel_stripe_order("cs_test_123", reason="checkout.session.expired")

        order_with_line.refresh_from_db()
        assert order_with_line.status == Order.FAILED

    def test_does_not_touch_a_fulfilled_order(self, order_with_line):
        """A late failure event can't undo a fulfilled order"""
        order_with_line.stripe_checkout_session_id = "cs_test_123"
        order_with_line.status = Order.FULFILLED
        order_with_line.save()

        cancel_stripe_order("cs_test_123")

        order_with_line.refresh_from_db()
        assert order_with_line.status == Order.FULFILLED
