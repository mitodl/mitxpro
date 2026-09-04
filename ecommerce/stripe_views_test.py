"""Tests for the Stripe webhook endpoint

These cover the public boundary itself -- signature rejection and event
routing -- which the API-level tests can't catch.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from ecommerce.constants import (
    STRIPE_EVENT_CHECKOUT_SESSION_ASYNC_PAYMENT_FAILED,
    STRIPE_EVENT_CHECKOUT_SESSION_ASYNC_PAYMENT_SUCCEEDED,
    STRIPE_EVENT_CHECKOUT_SESSION_COMPLETED,
    STRIPE_EVENT_CHECKOUT_SESSION_EXPIRED,
)

pytestmark = pytest.mark.django_db


class FakeEventData:
    def __init__(self, session):
        self.object = session


class FakeEvent:
    """Stands in for a stripe.Event, which is not a plain dict"""

    def __init__(self, event_type, session_id="cs_test_123"):
        self.id = "evt_test_123"
        self.type = event_type
        self.data = FakeEventData({"id": session_id})


def _patch_validation(mocker, event):
    return mocker.patch(
        "ecommerce.views.PaymentGateway.validate_processor_response",
        return_value=event,
    )


def test_invalid_signature_is_rejected(client, mocker):
    """An unsigned or wrongly-signed payload must not reach fulfillment"""
    mocker.patch(
        "ecommerce.views.PaymentGateway.validate_processor_response",
        side_effect=Exception("bad signature"),
    )
    fulfill = mocker.patch("ecommerce.views.fulfill_stripe_order")

    resp = client.post(reverse("stripe-webhook"), {}, content_type="application/json")

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert fulfill.call_count == 0


@pytest.mark.parametrize(
    "event_type",
    [
        STRIPE_EVENT_CHECKOUT_SESSION_COMPLETED,
        STRIPE_EVENT_CHECKOUT_SESSION_ASYNC_PAYMENT_SUCCEEDED,
    ],
)
def test_fulfillment_events_are_routed(client, mocker, event_type):
    """Both the immediate and the delayed success events fulfil"""
    _patch_validation(mocker, FakeEvent(event_type))
    fulfill = mocker.patch("ecommerce.views.fulfill_stripe_order")
    mocker.patch("ecommerce.views.cancel_stripe_order")

    resp = client.post(reverse("stripe-webhook"), {}, content_type="application/json")

    assert resp.status_code == status.HTTP_200_OK
    fulfill.assert_called_once_with("cs_test_123")


@pytest.mark.parametrize(
    "event_type",
    [
        STRIPE_EVENT_CHECKOUT_SESSION_EXPIRED,
        STRIPE_EVENT_CHECKOUT_SESSION_ASYNC_PAYMENT_FAILED,
    ],
)
def test_cancellation_events_are_routed(client, mocker, event_type):
    """Expiry and delayed failure both fail the order"""
    _patch_validation(mocker, FakeEvent(event_type))
    mocker.patch("ecommerce.views.fulfill_stripe_order")
    cancel = mocker.patch("ecommerce.views.cancel_stripe_order")

    resp = client.post(reverse("stripe-webhook"), {}, content_type="application/json")

    assert resp.status_code == status.HTTP_200_OK
    assert cancel.call_count == 1


def test_unhandled_events_return_200(client, mocker):
    """
    Anything we don't act on still gets a 200 -- returning an error would have
    Stripe retry an event we were never going to process.
    """
    _patch_validation(mocker, FakeEvent("payment_intent.created"))
    fulfill = mocker.patch("ecommerce.views.fulfill_stripe_order")
    cancel = mocker.patch("ecommerce.views.cancel_stripe_order")

    resp = client.post(reverse("stripe-webhook"), {}, content_type="application/json")

    assert resp.status_code == status.HTTP_200_OK
    assert fulfill.call_count == 0
    assert cancel.call_count == 0


def test_event_without_a_session_id_is_ignored(client, mocker):
    """A malformed event shouldn't 500 and make Stripe retry it forever"""
    event = FakeEvent(STRIPE_EVENT_CHECKOUT_SESSION_COMPLETED)
    event.data.object = {}
    _patch_validation(mocker, event)
    fulfill = mocker.patch("ecommerce.views.fulfill_stripe_order")

    resp = client.post(reverse("stripe-webhook"), {}, content_type="application/json")

    assert resp.status_code == status.HTTP_200_OK
    assert fulfill.call_count == 0
