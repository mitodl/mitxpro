"""Tests for b2b_ecommerce functions"""
import pytest

from b2b_ecommerce.api import (
    generate_b2b_cybersource_sa_payload,
    generate_cybersource_sa_signature,
)
from b2b_ecommerce.factories import B2BOrderFactory
from b2b_ecommerce.models import B2BOrder
from ecommerce.api import ISO_8601_FORMAT
from mitxpro.utils import now_in_utc


pytestmark = pytest.mark.django_db


CYBERSOURCE_ACCESS_KEY = "access"
CYBERSOURCE_PROFILE_ID = "profile"
CYBERSOURCE_SECURITY_KEY = "security"
CYBERSOURCE_REFERENCE_PREFIX = "prefix"


@pytest.fixture(autouse=True)
def cybersource_settings(settings):
    """
    Set cybersource settings
    """
    settings.CYBERSOURCE_ACCESS_KEY = CYBERSOURCE_ACCESS_KEY
    settings.CYBERSOURCE_PROFILE_ID = CYBERSOURCE_PROFILE_ID
    settings.CYBERSOURCE_SECURITY_KEY = CYBERSOURCE_SECURITY_KEY
    settings.CYBERSOURCE_REFERENCE_PREFIX = CYBERSOURCE_REFERENCE_PREFIX


def test_get_new_b2b_order_by_reference_number():
    """
    get_new_order_by_reference_number returns an Order with status created
    """
    order = B2BOrderFactory.create(status=B2BOrder.CREATED)
    same_order = B2BOrder.objects.filter_by_reference_number(order.reference_id).first()
    assert same_order.id == order.id


def test_signed_payload(mocker):
    """
    A valid payload should be signed appropriately
    """
    order = B2BOrderFactory.create()
    transaction_uuid = "hex"

    now = now_in_utc()
    now_mock = mocker.patch(
        "b2b_ecommerce.api.now_in_utc", autospec=True, return_value=now
    )
    product_version = order.product_version
    product = product_version.product

    mocker.patch(
        "b2b_ecommerce.api.uuid.uuid4",
        autospec=True,
        return_value=mocker.MagicMock(hex=transaction_uuid),
    )
    receipt_url = "https://example.com/base_url/receipt/"
    cancel_url = "https://example.com/base_url/cancel/"
    payload = generate_b2b_cybersource_sa_payload(
        order=order, receipt_url=receipt_url, cancel_url=cancel_url
    )
    signature = payload.pop("signature")
    assert generate_cybersource_sa_signature(payload) == signature
    signed_field_names = payload["signed_field_names"].split(",")
    assert signed_field_names == sorted(payload.keys())

    total_price = order.total_price
    assert payload == {
        "access_key": CYBERSOURCE_ACCESS_KEY,
        "amount": str(total_price),
        "currency": "USD",
        "item_0_code": "enrollment_code",
        "item_0_name": f"Enrollment codes for {product_version.description}"[:254],
        "item_0_quantity": order.num_seats,
        "item_0_sku": f"enrollment_code-{str(product.content_type)}-{product.content_object.id}",
        "item_0_tax_amount": "0",
        "item_0_unit_price": str(total_price),
        "line_item_count": 1,
        "locale": "en-us",
        "reference_number": order.reference_id,
        "override_custom_receipt_page": receipt_url,
        "override_custom_cancel_page": cancel_url,
        "profile_id": CYBERSOURCE_PROFILE_ID,
        "signed_date_time": now.strftime(ISO_8601_FORMAT),
        "signed_field_names": ",".join(signed_field_names),
        "transaction_type": "sale",
        "transaction_uuid": transaction_uuid,
        "unsigned_field_names": "",
    }
    now_mock.assert_called_once_with()
