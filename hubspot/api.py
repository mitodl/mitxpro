"""
Hubspot Ecommerce Bridge API sync utilities

https://developers.hubspot.com/docs/methods/ecomm-bridge/ecomm-bridge-overview
"""
import time
from urllib.parse import urljoin, urlencode
import requests
from django.conf import settings


HUBSPOT_API_BASE_URL = "https://api.hubapi.com"


def send_hubspot_request(
    endpoint, api_url, method, body=None, query_params=None, **kwargs
):
    """
    Send a request to Hubspot using the given params, body and api key specified in settings

    Args:
        endpoint (String): Specific endpoint to hit. Can be the empty string
        api_url (String): The url path to append endpoint to
        method (String): GET, POST, or PUT
        body (serializable data): Data to be JSON serialized and sent with a PUT or POST request
        query_params (Dict): Params to be added to the query string
        kwargs: keyword arguments to add to the request method
    Returns:
        HTML response to the constructed url
    """

    base_url = urljoin(f"{HUBSPOT_API_BASE_URL}/", api_url)
    if endpoint:
        base_url = urljoin(f"{base_url}/", endpoint)
    if query_params is None:
        query_params = {}
    if "hapikey" not in query_params:
        query_params["hapikey"] = settings.HUBSPOT_API_KEY
    params = urlencode(query_params)
    url = f"{base_url}?{params}"
    if method == "GET":
        return requests.get(url=url, **kwargs)
    if method == "PUT":
        return requests.put(url=url, json=body, **kwargs)
    if method == "POST":
        return requests.post(url=url, json=body, **kwargs)


def make_sync_message(object_id, properties):
    """
    Create data for sync message
    Args:
        object_id (ObjectID): Internal ID to match with Hubspot object
        properties (dict): dict of properties to be synced
    Returns:
        dict to be serialized as body in sync-message
    """
    for key in properties.keys():
        if properties[key] is None:
            properties[key] = ""
    return {
        "integratorObjectId": str(object_id),
        "action": "UPSERT",
        "changeOccurredTimestamp": int(time.time() * 1000),
        "propertyNameToValues": dict(properties),
    }


def get_sync_errors(limit=200, offset=0):
    """
    Get errors that have occurred during sync
    Args:
        limit (Int): The number of errors to be returned
        offset (Int): The index of the first error to be returned
    Returns:
        HTML response including error data
    """
    response = send_hubspot_request(
        "sync-errors",
        "/extensions/ecomm/v1",
        "GET",
        query_params={"limit": limit, "offset": offset},
    )
    response.raise_for_status()
    return response


def make_contact_sync_message(user_id):
    """
    Create the body of a sync message for a contact. This will flatten the contained LegalAddress and Profile
    serialized data into one larger serializable dict
    Args:
        user_id (ObjectID): ID of user to sync contact with
    Returns:
        dict containing serializable sync-message data
    """
    from users.models import User
    from users.serializers import UserSerializer

    user = User.objects.get(id=user_id)
    properties = UserSerializer(user).data
    properties.update(properties.pop("legal_address") or {})
    properties.update(properties.pop("profile") or {})
    properties["street_address"] = "\n".join(properties.pop("street_address"))
    return make_sync_message(user.id, properties)


def make_deal_sync_message(order_id):
    """
    Create the body of a sync message for a deal.
    Args:
    Returns:
        dict containing serializable sync-message data
    """
    return make_sync_message(order_id, {})


def make_line_item_sync_message(line_id):
    """
    Create the body of a sync message for a line item.
    Args:
    Returns:
        dict containing serializable sync-message data
    """
    return make_sync_message(line_id, {})


def make_product_sync_message(product_id):
    """
    Create the body of a sync message for a product.
    Args:
    Returns:
        dict containing serializable sync-message data
    """
    return make_sync_message(product_id, {})
