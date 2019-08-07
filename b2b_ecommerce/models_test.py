"""models for b2b_ecommerce"""
import pytest

from b2b_ecommerce.constants import REFERENCE_NUMBER_PREFIX
from b2b_ecommerce.factories import B2BOrderFactory
from b2b_ecommerce.models import B2BOrderAudit
from mitxpro.utils import serialize_model_object


pytestmark = pytest.mark.django_db


def test_b2b_order_audit():
    """
    B2BOrder.save_and_log() should save the order's information to an audit model.
    """
    order = B2BOrderFactory.create()
    assert B2BOrderAudit.objects.count() == 0
    order.save_and_log(None)

    assert B2BOrderAudit.objects.count() == 1
    order_audit = B2BOrderAudit.objects.first()
    assert order_audit.order == order

    assert order_audit.data_after == {
        **serialize_model_object(order),
        "product_version_info": {
            **serialize_model_object(order.product_version),
            "product_info": {
                **serialize_model_object(order.product_version.product),
                "content_type_string": str(order.product_version.product.content_type),
                "content_object": serialize_model_object(
                    order.product_version.product.content_object
                ),
            },
        },
        "receipts": [
            serialize_model_object(receipt) for receipt in order.b2breceipt_set.all()
        ],
    }


def test_reference_number(settings):
    """
    order.reference_number should concatenate the reference prefix and the order id
    """
    cybersource_prefix = "cyb-prefix"
    settings.CYBERSOURCE_REFERENCE_PREFIX = cybersource_prefix

    order = B2BOrderFactory.create()
    assert (
        f"{REFERENCE_NUMBER_PREFIX}{cybersource_prefix}-{order.id}"
        == order.reference_number
    )
