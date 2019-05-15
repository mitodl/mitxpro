"""
Tests for ecommerce tasks
"""
# pylint: disable=redefined-outer-name
from unittest.mock import ANY

import pytest

from faker import Faker

from ecommerce.factories import ProductFactory, OrderFactory, LineFactory
from ecommerce.hubspot_api import (
    make_contact_sync_message,
    make_product_sync_message,
    make_deal_sync_message,
    make_line_item_sync_message,
)
from ecommerce.tasks import (
    sync_contact_with_hubspot,
    HUBSPOT_SYNC_URL,
    sync_product_with_hubspot,
    sync_deal_with_hubspot,
    sync_line_item_with_hubspot,
)
from users.factories import UserFactory

fake = Faker()


@pytest.fixture
def mock_hubspot_request(mocker):
    """Mock the send hubspot request method"""
    yield mocker.patch("ecommerce.tasks.send_hubspot_request")


@pytest.mark.django_db
def test_sync_contact_with_hubspot(mock_hubspot_request):
    """Test that send_hubspot_request is called properly for a CONTACT sync"""
    user = UserFactory.create()
    sync_contact_with_hubspot(user.id)
    body = [make_contact_sync_message(user.id)]
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "CONTACT", HUBSPOT_SYNC_URL, "PUT", body=body
    )


@pytest.mark.django_db
def test_sync_product_with_hubspot(mock_hubspot_request):
    """Test that send_hubspot_request is called properly for a PRODUCT sync"""
    product = ProductFactory.create()
    sync_product_with_hubspot(product.id)
    body = [make_product_sync_message(product.id)]
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "PRODUCT", HUBSPOT_SYNC_URL, "PUT", body=body
    )


@pytest.mark.django_db
def test_sync_deal_with_hubspot(mock_hubspot_request):
    """Test that send_hubspot_request is called properly for a DEAL sync"""
    order = OrderFactory.create()
    sync_deal_with_hubspot(order.id)
    body = [make_deal_sync_message(order.id)]
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "DEAL", HUBSPOT_SYNC_URL, "PUT", body=body
    )


@pytest.mark.django_db
def test_sync_line_item_with_hubspot(mock_hubspot_request):
    """Test that send_hubspot_request is called properly for a LINE_ITEM sync"""
    line = LineFactory.create()
    sync_line_item_with_hubspot(line.id)
    body = [make_line_item_sync_message(line.id)]
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "LINE_ITEM", HUBSPOT_SYNC_URL, "PUT", body=body
    )
