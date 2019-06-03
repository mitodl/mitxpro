"""
Hubspot Ecommerce Bridge API sync utilities

https://developers.hubspot.com/docs/methods/ecomm-bridge/ecomm-bridge-overview
"""
from urllib.parse import urljoin, urlencode
import requests
from django.conf import settings

from mitxpro.utils import now_in_utc

HUBSPOT_API_BASE_URL = "https://api.hubapi.com"


def hubspot_timestamp(dt):
    """
    Convert a datetime to a Hubspot timestamp

    Args:
        dt (DateTime): the DateTime to convert

    Returns:
        int: The timestamp in milliseconds
    """
    return int(dt.timestamp() * 1000)


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
        Response: HTML response to the constructed url
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
        dict: serialized sync-message
    """
    for key in properties.keys():
        if properties[key] is None:
            properties[key] = ""
    return {
        "integratorObjectId": str(object_id),
        "action": "UPSERT",
        "changeOccurredTimestamp": hubspot_timestamp(now_in_utc()),
        "propertyNameToValues": dict(properties),
    }


def paged_sync_errors(limit=200, offset=0):
    """
    Query the Ubspot API for errors that have occurred during sync

    Args:
        limit (Int): The number of errors to be returned
        offset (Int): The index of the first error to be returned

    Returns:
        list: errors in JSON format
    """
    response = send_hubspot_request(
        "sync-errors",
        "/extensions/ecomm/v1",
        "GET",
        query_params={"limit": limit, "offset": offset},
    )
    response.raise_for_status()
    return response.json().get("results", [])


def get_sync_errors(timestamp, limit=200, offset=0):
    """
    Yield hubspot errors

    Args:
        timestamp (int): The timestamp of the last error check
        limit (int): The number of errors to be returned
        offset (int): The index of the first error to be returned

    Yields:
        dict : error in JSON format
    """
    errors = paged_sync_errors(limit, offset)
    caught_up = False
    while len(errors) > 0 and not caught_up:
        for error in errors:
            if error.get("errorTimestamp") > timestamp:
                yield error
            else:
                caught_up = True
                break
        if not caught_up:
            offset += limit
            errors = paged_sync_errors(limit, offset)


def make_contact_sync_message(user_id):
    """
    Create the body of a sync message for a contact. This will flatten the contained LegalAddress and Profile
    serialized data into one larger serializable dict

    Args:
        user_id (ObjectID): ID of user to sync contact with

    Returns:
        dict: serializable sync-message data
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
        order_id (int): Order id

    Returns:
        dict: serializable sync-message data for deals (orders)
    """
    return make_sync_message(order_id, {})


def make_line_item_sync_message(line_id):
    """
    Create the body of a sync message for a line item.

    Args:
        line_id (int): Line id

    Returns:
        dict: serializable sync-message data for lines
    """
    return make_sync_message(line_id, {})


def make_product_sync_message(product_id):
    """
    Create the body of a sync message for a product.

    Args:
        product_id (int): Product id

    Returns:
        dict: serializable sync-message data for products
    """
    return make_sync_message(product_id, {})
