"""
Hubspot Ecommerce Bridge API sync utilities

https://developers.hubspot.com/docs/methods/ecomm-bridge/ecomm-bridge-overview
"""
import logging
import re
from urllib.parse import urljoin, urlencode

import requests
from django.conf import settings

from b2b_ecommerce.models import B2B_INTEGRATION_PREFIX
from mitxpro.utils import now_in_utc

HUBSPOT_API_BASE_URL = "https://api.hubapi.com"

log = logging.getLogger()


def hubspot_timestamp(dt):
    """
    Convert a datetime to a Hubspot timestamp

    Args:
        dt (DateTime): the DateTime to convert

    Returns:
        int: The timestamp in milliseconds
    """
    return int(dt.timestamp() * 1000)


def format_hubspot_id(object_id):
    """
    Return a formatted Hubspot ID for an object
    Args:
        object_id(int): The object id

    Returns:
        str: The hubspot id
    """
    return "{}-{}".format(settings.HUBSPOT_ID_PREFIX, object_id)


def parse_hubspot_id(hubspot_id):
    """
    Return an object ID parsed from a hubspot ID
    Args:
        hubspot_id(str): The formatted hubspot ID

    Returns:
        int: The object ID or None
    """
    match = re.compile(
        fr"{settings.HUBSPOT_ID_PREFIX}-({B2B_INTEGRATION_PREFIX})?(\d+)"
    ).match(hubspot_id)
    return int(match.group(2)) if match else None


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
    if method == "DELETE":
        return requests.delete(url=url, **kwargs)


def sanitize_properties(properties):
    """
    Ensures we don't pass any invalid values (e.g. nulls) to hubspot_timestamp

    Args:
        properties (dict):
            the dict of properties to be sanitized

    Returns:
        dict:
            the sanitized dict
    """

    return {
        key: value if value is not None else "" for key, value in properties.items()
    }


def make_sync_message(object_id, properties):
    """
    Create data for sync message

    Args:
        object_id (ObjectID): Internal ID to match with Hubspot object
        properties (dict): dict of properties to be synced

    Returns:
        dict: serialized sync-message
    """
    properties = sanitize_properties(properties)

    return {
        "integratorObjectId": format_hubspot_id(object_id),
        "action": "UPSERT",
        "changeOccurredTimestamp": hubspot_timestamp(now_in_utc()),
        "propertyNameToValues": properties,
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


def get_sync_errors(limit=200, offset=0):
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
    while len(errors) > 0:
        yield from errors
        offset += limit
        errors = paged_sync_errors(limit, offset)


def get_sync_status(object_type, object_id):
    """
    Get errors that have occurred during sync
    Args:
        object_type (STRING): "CONTACT", "DEAL", "PRODUCT", "LINE_ITEM"
        object_id (Int): The internal django ID of the object to check
    Returns:
        HTML response including sync status
    """
    response = send_hubspot_request(
        format_hubspot_id(object_id),
        f"/extensions/ecomm/v1/sync-status/{object_type.upper()}",
        "GET",
    )
    response.raise_for_status()
    return response.json()


def exists_in_hubspot(object_type, object_id):
    """
    Check if object exists in hubspot by looking for the presence of a hubspot ID

    Args:
        object_type (str): The hubspot object_type
        object_id (ID): The ID of the object to check
    Return:
        boolean: True if the object exists
    """
    try:
        sync_status = get_sync_status(object_type, object_id)
    except requests.HTTPError as sync_status_error:
        if sync_status_error.response.status_code != 400:
            log.error(sync_status_error)
        return False
    else:
        return sync_status["hubspotId"] is not None


def make_contact_sync_message(user_id):
    """
    Create the body of a sync message for a contact. This will flatten the contained LegalAddress and Profile
    serialized data into one larger serializable dict

    Args:
        user_id (int): User id

    Returns:
        list: dict containing serializable sync-message data
    """
    from users.models import User
    from users.serializers import UserSerializer

    user = User.objects.get(id=user_id)
    properties = UserSerializer(user).data
    properties.update(properties.pop("legal_address") or {})
    properties.update(properties.pop("profile") or {})
    properties.pop("unused_coupons")
    if "street_address" in properties:
        properties["street_address"] = "\n".join(properties.pop("street_address"))
    return [make_sync_message(user.id, properties)]


def make_b2b_contact_sync_message(email):
    """
    Create the body of a sync message for a b2b contact.

    Args:
        email (string): User email

    Returns:
        list: dict containing serializable sync-message data
    """
    user_id = email
    return [make_sync_message(user_id, {"email": email})]


def make_b2b_deal_sync_message(order_id):
    """
    Create the body of a sync message for a b2b deal.

    Args:
        order_id (int): B2B Order id

    Returns:
        list: dict containing serializable sync-message data for deals (orders)
    """
    from b2b_ecommerce.models import B2BOrder
    from hubspot.serializers import B2BOrderToDealSerializer
    from hubspot.serializers import ORDER_TYPE_B2B

    order = B2BOrder.objects.get(id=order_id)
    properties = B2BOrderToDealSerializer(order).data
    properties["order_type"] = ORDER_TYPE_B2B
    return [make_sync_message(order.integration_id, properties)]


def make_deal_sync_message(order_id):
    """
    Create the body of a sync message for a deal.

    Args:
        order_id (int): Order id

    Returns:
        list: dict containing serializable sync-message data for deals (orders)
    """
    from ecommerce.models import Order
    from hubspot.serializers import OrderToDealSerializer

    order = Order.objects.get(id=order_id)
    properties = OrderToDealSerializer(order).data
    properties.pop("lines")

    return [make_sync_message(order_id, properties)]


def make_line_item_sync_message(line_id):
    """
    Create the body of a sync message for a line item.

    Args:
        line_id (int): Line id

    Returns:
        list: dict containing serializable sync-message data for lines
    """
    from ecommerce.models import Line
    from hubspot.serializers import LineSerializer

    line = Line.objects.get(id=line_id)
    properties = LineSerializer(line).data
    return [make_sync_message(line_id, properties)]


def make_b2b_product_sync_message(order_id):
    """
    Create the body of a sync message for a line item.

    Args:
        line_id (int): Line id

    Returns:
        list: dict containing serializable sync-message data for lines
    """
    from b2b_ecommerce.models import B2BOrder
    from hubspot.serializers import B2BProductVersionToLineSerializer

    order = B2BOrder.objects.get(id=order_id)
    properties = B2BProductVersionToLineSerializer(order).data
    return [make_sync_message(order.integration_id, properties)]


def make_product_sync_message(product_id):
    """
    Create the body of a sync message for a product.

    Args:
        product_id (int): Product id

    Returns:
        list: dict containing serializable sync-message data for products
    """
    from ecommerce.models import Product
    from hubspot.serializers import ProductSerializer

    product = Product.objects.get(id=product_id)
    properties = ProductSerializer(product).data
    return [make_sync_message(product_id, properties)]


def make_properties_url(endpoint, object_type):
    """
    Create the url for a call to the properties api based on object type

    Args:
        endpoint (str): endpoint to follow /properties/{version}/{object_type}
        object_type (str): the type of object properties to query

    Returns:
        string: a properties url for use in send_hubspot_request
    """
    if object_type == "line_items":
        version = "v2"
    else:
        version = "v1"

    return urljoin(f"/properties/{version}/{object_type.lower()}/", endpoint)


def sync_object_property(object_type, property_dict):
    """
    Create or update a new object property


    Args:
        object_type (str): The object type of the property (ie "deals")
        property_dict (dict): The attributes of the property

    Returns:
        dict:  The new/updated property attributes
    """
    required_fields = {"name", "label", "groupName"}

    missing_fields = required_fields.difference(property_dict.keys())
    if missing_fields:
        raise KeyError(
            "The following property attributes are required: {}".format(
                ",".join(missing_fields)
            )
        )

    for key in property_dict.keys():
        if property_dict[key] is None:
            property_dict[key] = ""

    exists = object_property_exists(object_type, property_dict["name"])

    if exists:
        method = "PUT"
        endpoint = f"named/{property_dict['name']}"
    else:
        method = "POST"
        endpoint = ""

    response = send_hubspot_request(
        endpoint,
        make_properties_url("properties", object_type),
        method,
        body=property_dict,
    )
    response.raise_for_status()
    return response.json()


def get_object_property(object_type, property_name):
    """
    Get a Hubspot object property.

    Args:
        object_type (str): The object type of the property (ie "deals")
        property_name (str): The property name

    Returns:
        dict:  the property attributes
    """
    response = send_hubspot_request(
        property_name, make_properties_url("properties/named", object_type), "GET"
    )
    response.raise_for_status()
    return response.json()


def object_property_exists(object_type, property_name):
    """
    Return True if the specified property exists, False otherwise

    Args:
        object_type (str): The object type of the property (ie "deals")
        property_name (str): The property name

    Returns:
        boolean:  True if the property exists otherwise False
    """
    try:
        get_object_property(object_type, property_name)
        return True
    except requests.HTTPError:
        return False


def delete_object_property(object_type, property_name):
    """
    Delete a property from Hubspot

    Args:
        object_type (str): The object type of the property (ie "deals")
        property_name (str): The property name

    Returns:
        dict:  the result of the delete request in JSON format
    """
    response = send_hubspot_request(
        "", make_properties_url(f"named/{property_name}", object_type), "DELETE"
    )
    response.raise_for_status()
    return response.json()


def get_property_group(object_type, group_name):
    """
    Get a Hubspot property group.

    Args:
        object_type (str): The object type of the group (ie "deals")
        group_name (str): The group name

    Returns:
        dict:  The group attributes
    """
    response = send_hubspot_request(
        group_name, make_properties_url("groups/named", object_type), "GET"
    )
    response.raise_for_status()
    return response.json()


def property_group_exists(object_type, group_name):
    """
    Return True if the specified group exists (status=200), False otherwise

    Args:
        object_type (str): The object type of the group (ie "deals")
        group_name (str): The group name

    Returns:
        boolean:  True if the group exists otherwise False
    """
    try:
        get_property_group(object_type, group_name)
        return True
    except requests.HTTPError:
        return False


def sync_property_group(object_type, name, label):
    """
    Create or update a property group for an object type

    Args:
        object_type (str): The object type of the group (ie "deals")
        name (str): The group name
        label (str): The group label

    Returns:
        dict:  the new/updated group attributes

    """
    body = {"name": name, "displayName": label}

    exists = property_group_exists(object_type, name)

    if exists:
        method = "PUT"
        endpoint = f"named/{name}"
    else:
        method = "POST"
        endpoint = ""

    response = send_hubspot_request(
        endpoint, make_properties_url("groups", object_type), method, body=body
    )
    response.raise_for_status()
    return response.json()


def delete_property_group(object_type, group_name):
    """
    Delete a group from Hubspot

    Args:
        object_type (str): The object type of the group (ie "deals")
        group_name (str): The group name

    Returns:
        dict:  The result of the delete command in JSON format
    """
    response = send_hubspot_request(
        "", make_properties_url(f"groups/named/{group_name}", object_type), "DELETE"
    )
    response.raise_for_status()
    return response.json()
