"""
Hubspot API tests
"""
# pylint: disable=redefined-outer-name
from urllib.parse import urlencode

import pytest
from faker import Faker
from django.conf import settings

from ecommerce.factories import LineFactory, ProductFactory
from hubspot.api import (
    send_hubspot_request,
    HUBSPOT_API_BASE_URL,
    make_sync_message,
    make_contact_sync_message,
    make_deal_sync_message,
    make_line_item_sync_message,
    make_product_sync_message,
    get_sync_errors,
)
from hubspot.serializers import OrderToDealSerializer, LineSerializer, ProductSerializer
from mitxpro.test_utils import any_instance_of
from users.serializers import UserSerializer

fake = Faker()


@pytest.mark.parametrize("request_method", ["GET", "PUT", "POST"])
@pytest.mark.parametrize(
    "endpoint,api_url,expected_url",
    [
        [
            "sync-errors",
            "/extensions/ecomm/v1",
            f"{HUBSPOT_API_BASE_URL}/extensions/ecomm/v1/sync-errors",
        ],
        [
            "",
            "/extensions/ecomm/v1/installs",
            f"{HUBSPOT_API_BASE_URL}/extensions/ecomm/v1/installs",
        ],
        [
            "CONTACT",
            "/extensions/ecomm/v1/sync-messages",
            f"{HUBSPOT_API_BASE_URL}/extensions/ecomm/v1/sync-messages/CONTACT",
        ],
    ],
)
def test_send_hubspot_request(mocker, request_method, endpoint, api_url, expected_url):
    """Test sending hubspot request with method = GET"""
    value = fake.pyint()
    query_params = {"param": value}

    # Include hapikey when generating url to match request call against
    full_query_params = {"param": value, "hapikey": settings.HUBSPOT_API_KEY}
    mock_request = mocker.patch(f"hubspot.api.requests.{request_method.lower()}")
    url_params = urlencode(full_query_params)
    url = f"{expected_url}?{url_params}"
    if request_method == "GET":
        send_hubspot_request(
            endpoint, api_url, request_method, query_params=query_params
        )
        mock_request.assert_called_once_with(url=url)
    else:
        body = fake.pydict()
        send_hubspot_request(
            endpoint, api_url, request_method, query_params=query_params, body=body
        )
        mock_request.assert_called_once_with(url=url, json=body)


def test_make_sync_message():
    """Test make_sync_message produces a properly formatted sync-message"""
    object_id = fake.pyint()
    value = fake.word()
    properties = {"prop": value, "blank": None}
    sync_message = make_sync_message(object_id, properties)
    assert sync_message == (
        {
            "integratorObjectId": "{}-{}".format(settings.HUBSPOT_ID_PREFIX, object_id),
            "action": "UPSERT",
            "changeOccurredTimestamp": any_instance_of(int),
            "propertyNameToValues": {"prop": value, "blank": ""},
        }
    )


def test_make_contact_sync_message(user):
    """Test make_contact_sync_message serializes a user and returns a properly formatted sync message"""
    contact_sync_message = make_contact_sync_message(user.id)

    serialized_user = UserSerializer(user).data
    serialized_user.update(serialized_user.pop("legal_address") or {})
    serialized_user.update(serialized_user.pop("profile") or {})
    serialized_user["street_address"] = "\n".join(serialized_user.pop("street_address"))
    assert contact_sync_message == [
        {
            "integratorObjectId": "{}-{}".format(settings.HUBSPOT_ID_PREFIX, user.id),
            "action": "UPSERT",
            "changeOccurredTimestamp": any_instance_of(int),
            "propertyNameToValues": serialized_user,
        }
    ]


@pytest.mark.parametrize("offset", [0, 10])
def test_get_sync_errors(mock_hubspot_errors, offset):
    """Test that paging works for get_sync_errors"""
    limit = 2
    errors = list(get_sync_errors(limit, offset))
    assert len(errors) == 4
    mock_hubspot_errors.assert_any_call(limit, offset)
    mock_hubspot_errors.assert_any_call(limit, offset + limit)
    mock_hubspot_errors.assert_any_call(limit, offset + limit * 2)


@pytest.mark.django_db
def test_make_deal_sync_message(hubspot_order):
    """Test make_deal_sync_message serializes a deal and returns a properly formatted sync message"""
    deal_sync_message = make_deal_sync_message(hubspot_order.id)

    serialized_order = OrderToDealSerializer(hubspot_order).data
    serialized_order.pop("lines")
    if serialized_order["close_date"] is None:
        serialized_order["close_date"] = ""
    assert deal_sync_message == [
        {
            "integratorObjectId": "{}-{}".format(
                settings.HUBSPOT_ID_PREFIX, hubspot_order.id
            ),
            "action": "UPSERT",
            "changeOccurredTimestamp": any_instance_of(int),
            "propertyNameToValues": serialized_order,
        }
    ]


@pytest.mark.django_db
def test_make_line_item_sync_message():
    """Test make_line_item_sync_message serializes a line_item and returns a properly formatted sync message"""
    line = LineFactory()
    line_item_sync_message = make_line_item_sync_message(line.id)

    serialized_line = LineSerializer(line).data
    assert line_item_sync_message == [
        {
            "integratorObjectId": "{}-{}".format(settings.HUBSPOT_ID_PREFIX, line.id),
            "action": "UPSERT",
            "changeOccurredTimestamp": any_instance_of(int),
            "propertyNameToValues": serialized_line,
        }
    ]


@pytest.mark.django_db
def test_make_product_sync_message():
    """Test make_deal_sync_message serializes a deal and returns a properly formatted sync message"""
    product = ProductFactory()
    contact_sync_message = make_product_sync_message(product.id)

    serialized_product = ProductSerializer(product).data
    assert contact_sync_message == [
        {
            "integratorObjectId": "{}-{}".format(
                settings.HUBSPOT_ID_PREFIX, product.id
            ),
            "action": "UPSERT",
            "changeOccurredTimestamp": any_instance_of(int),
            "propertyNameToValues": serialized_product,
        }
    ]
