"""
Tests for hubspot tasks
"""
# pylint: disable=redefined-outer-name
from datetime import datetime
from unittest.mock import ANY

import pytest
import pytz

from faker import Faker

from ecommerce.factories import ProductFactory, OrderFactory, LineFactory
from hubspot.api import (
    make_contact_sync_message,
    make_product_sync_message,
    make_deal_sync_message,
    make_line_item_sync_message,
)
from hubspot.factories import HubspotErrorCheckFactory
from hubspot.models import HubspotErrorCheck
from hubspot.tasks import (
    sync_contact_with_hubspot,
    HUBSPOT_SYNC_URL,
    sync_product_with_hubspot,
    sync_deal_with_hubspot,
    sync_line_item_with_hubspot,
    check_hubspot_api_errors,
)
from users.factories import UserFactory

pytestmark = [pytest.mark.django_db]

fake = Faker()

error_response_json = {
    "results": [
        {
            "portalId": 5_890_463,
            "objectType": "CONTACT",
            "integratorObjectId": "16",
            "changeOccurredTimestamp": 1_558_727_887_000,
            "errorTimestamp": 1_558_727_887_000,
            "type": "UNKNOWN_ERROR",
            "details": 'Error performing[CREATE] CONTACT[16] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-13T12:05:53.602759Z was not a valid long.","error":"INVALID_LONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"fcde9e27-6e3b-4b3b-83c2-f6bd01289685","requestId":"8ede7b56-8269-4a5c-b2ea-a48a2dd9cd5d',
            "status": "OPEN",
        },
        {
            "portalId": 5_890_463,
            "objectType": "CONTACT",
            "integratorObjectId": "55",
            "changeOccurredTimestamp": 1_558_382_138_000,
            "errorTimestamp": 1_558_382_138_000,
            "type": "UNKNOWN_ERROR",
            "details": 'Error performing[CREATE] CONTACT[55] for portal 5890463, error was [5890463] create/update by email failed - java.util.concurrent.CompletionException: com.hubspot.properties.exceptions.InvalidProperty: {"validationResults":[{"isValid":false,"message":"2019-05-21T17:32:43.135139Z was not a valid long.","error":"INVALID_LONG","name":"createdate"}],"status":"error","message":"Property values were not valid","correlationId":"51274e2f-d839-4476-a077-eba7a38d3786","requestId":"9c1f2ded-78da-41a2-a607-568acfbd908f',
            "status": "OPEN",
        },
    ]
}


@pytest.fixture
def mock_logger(mocker):
    """ Mock the logger """
    yield mocker.patch("hubspot.tasks.log.exception")


@pytest.fixture
def mock_hubspot_request(mocker):
    """Mock the send hubspot request method"""
    yield mocker.patch("hubspot.tasks.send_hubspot_request", autospec=True)


@pytest.fixture
def mock_hubspot_errors(mocker):
    """Mock the get_sync_errors API call"""
    yield mocker.patch("hubspot.tasks.get_sync_errors")


def test_sync_contact_with_hubspot(mock_hubspot_request):
    """Test that send_hubspot_request is called properly for a CONTACT sync"""
    user = UserFactory.create()
    sync_contact_with_hubspot(user.id)
    body = [make_contact_sync_message(user.id)]
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "CONTACT", HUBSPOT_SYNC_URL, "PUT", body=body
    )


def test_sync_product_with_hubspot(mock_hubspot_request):
    """Test that send_hubspot_request is called properly for a PRODUCT sync"""
    product = ProductFactory.create()
    sync_product_with_hubspot(product.id)
    body = [make_product_sync_message(product.id)]
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "PRODUCT", HUBSPOT_SYNC_URL, "PUT", body=body
    )


def test_sync_deal_with_hubspot(mock_hubspot_request):
    """Test that send_hubspot_request is called properly for a DEAL sync"""
    order = OrderFactory.create()
    sync_deal_with_hubspot(order.id)
    body = [make_deal_sync_message(order.id)]
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "DEAL", HUBSPOT_SYNC_URL, "PUT", body=body
    )


def test_sync_line_item_with_hubspot(mock_hubspot_request):
    """Test that send_hubspot_request is called properly for a LINE_ITEM sync"""
    line = LineFactory.create()
    sync_line_item_with_hubspot(line.id)
    body = [make_line_item_sync_message(line.id)]
    body[0]["changeOccurredTimestamp"] = ANY
    mock_hubspot_request.assert_called_once_with(
        "LINE_ITEM", HUBSPOT_SYNC_URL, "PUT", body=body
    )


def test_sync_errors_first_run(mock_hubspot_errors, mock_logger):
    """Test that HubspotErrorCheck is created on 1st run and nothing is logged"""
    mock_hubspot_errors.return_value.json.side_effect = [
        error_response_json,
        {"results": []},
    ]
    assert HubspotErrorCheck.objects.count() == 0
    check_hubspot_api_errors()
    assert HubspotErrorCheck.objects.count() == 1
    assert mock_hubspot_errors.call_count == 1
    assert mock_logger.call_count == 0


def test_sync_errors_new_errors(mock_hubspot_errors, mock_logger):
    """Test that errors more recent than last checked_on date are logged"""
    last_check = HubspotErrorCheckFactory.create(
        checked_on=datetime(2015, 1, 1, tzinfo=pytz.utc)
    )
    mock_hubspot_errors.return_value.json.side_effect = [
        error_response_json,
        {"results": []},
    ]
    check_hubspot_api_errors()
    assert mock_hubspot_errors.call_count == 2
    assert mock_logger.call_count == len(error_response_json.get("results"))
    assert HubspotErrorCheck.objects.first().checked_on > last_check.checked_on


def test_sync_errors_some_errors(mock_hubspot_errors, mock_logger):
    """Test that errors less recent than last checked_on date are not logged"""
    last_check = HubspotErrorCheckFactory.create(
        checked_on=datetime(2019, 5, 22, tzinfo=pytz.utc)
    )
    mock_hubspot_errors.return_value.json.side_effect = [
        error_response_json,
        {"results": []},
    ]
    check_hubspot_api_errors()
    assert mock_hubspot_errors.call_count == 1
    assert mock_logger.call_count == 1
    assert HubspotErrorCheck.objects.first().checked_on > last_check.checked_on
