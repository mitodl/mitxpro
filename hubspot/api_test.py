"""
Hubspot API tests
"""
# pylint: disable=redefined-outer-name
from urllib.parse import urlencode

import pytest
from faker import Faker
from django.conf import settings

from hubspot.api import (
    send_hubspot_request,
    HUBSPOT_API_BASE_URL,
    make_sync_message,
    make_contact_sync_message,
    get_sync_errors,
)
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
    time = sync_message["changeOccurredTimestamp"]
    assert sync_message == (
        {
            "integratorObjectId": str(object_id),
            "action": "UPSERT",
            "changeOccurredTimestamp": time,
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

    time = contact_sync_message["changeOccurredTimestamp"]
    assert contact_sync_message == (
        {
            "integratorObjectId": str(user.id),
            "action": "UPSERT",
            "changeOccurredTimestamp": time,
            "propertyNameToValues": serialized_user,
        }
    )


@pytest.mark.parametrize("offset", [0, 10])
def test_get_sync_errors(mock_hubspot_errors, offset):
    """Test that paging works for get_sync_errors"""
    limit = 2
    errors = [error for error in get_sync_errors(limit, offset)]
    assert len(errors) == 4
    mock_hubspot_errors.assert_any_call(limit, offset)
    mock_hubspot_errors.assert_any_call(limit, offset + limit)
    mock_hubspot_errors.assert_any_call(limit, offset + limit * 2)
