"""
Functions for ecommerce
"""
from base64 import b64encode
import hashlib
import hmac
import logging
import uuid

from django.conf import settings

from mitxpro.utils import now_in_utc

ISO_8601_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
log = logging.getLogger(__name__)

_REFERENCE_NUMBER_PREFIX = "MITXPRO-"


def generate_cybersource_sa_signature(payload):
    """
    Generate an HMAC SHA256 signature for the CyberSource Secure Acceptance payload
    Args:
        payload (dict): The payload to be sent to CyberSource
    Returns:
        str: The signature
    """
    # This is documented in certain CyberSource sample applications:
    # http://apps.cybersource.com/library/documentation/dev_guides/Secure_Acceptance_SOP/html/wwhelp/wwhimpl/js/html/wwhelp.htm#href=creating_profile.05.6.html
    keys = payload["signed_field_names"].split(",")
    message = ",".join(f"{key}={payload[key]}" for key in keys)

    digest = hmac.new(
        settings.CYBERSOURCE_SECURITY_KEY.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    return b64encode(digest).decode("utf-8")


def generate_cybersource_sa_payload(order):
    """
    Generates a payload dict to send to CyberSource for Secure Acceptance
    Args:
        order (Order): An order
    Returns:
        dict: the payload to send to CyberSource via Secure Acceptance
    """
    # http://apps.cybersource.com/library/documentation/dev_guides/Secure_Acceptance_WM/Secure_Acceptance_WM.pdf
    # Section: API Fields

    # NOTE: be careful about max length here, many (all?) string fields have a max
    # length of 255. At the moment none of these fields should go over that, due to database
    # constraints or other reasons

    line_items = {}
    total = 0
    for i, line in enumerate(order.lines.all()):
        product_version = line.product_version
        line_items[f"item_{i}_code"] = str(product_version.product.content_type)
        line_items[f"item_{i}_name"] = str(product_version.description)[:254]
        line_items[f"item_{i}_quantity"] = line.quantity
        line_items[f"item_{i}_sku"] = product_version.product.content_object.id
        line_items[f"item_{i}_tax_amount"] = "0"
        line_items[f"item_{i}_unit_price"] = str(product_version.price)

        total += product_version.price

    payload = {
        "access_key": settings.CYBERSOURCE_ACCESS_KEY,
        "amount": str(total),
        "consumer_id": order.purchaser.username,
        "currency": "USD",
        "locale": "en-us",
        **line_items,
        "line_item_count": order.lines.count(),
        "reference_number": make_reference_id(order),
        "profile_id": settings.CYBERSOURCE_PROFILE_ID,
        "signed_date_time": now_in_utc().strftime(ISO_8601_FORMAT),
        "transaction_type": "sale",
        "transaction_uuid": uuid.uuid4().hex,
        "unsigned_field_names": "",
    }

    field_names = sorted(list(payload.keys()) + ["signed_field_names"])
    payload["signed_field_names"] = ",".join(field_names)
    payload["signature"] = generate_cybersource_sa_signature(payload)

    return payload


def make_reference_id(order):
    """
    Make a reference id
    Args:
        order (Order):
            An order
    Returns:
        str:
            A reference number for use with CyberSource to keep track of orders
    """
    return (
        f"{_REFERENCE_NUMBER_PREFIX}{settings.CYBERSOURCE_REFERENCE_PREFIX}-{order.id}"
    )
