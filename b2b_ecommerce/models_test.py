"""models for b2b_ecommerce"""
from datetime import timedelta

from django.utils import timezone
import pytest

from b2b_ecommerce.constants import REFERENCE_NUMBER_PREFIX
from b2b_ecommerce.factories import B2BOrderFactory
from b2b_ecommerce.models import B2BCoupon, B2BOrder, B2BOrderAudit
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
    settings.ENVIRONMENT = "test"

    order = B2BOrderFactory.create()
    assert (
        f"{REFERENCE_NUMBER_PREFIX}{settings.ENVIRONMENT}-{order.id}"
        == order.reference_number
    )


@pytest.mark.parametrize(
    "activation_date, expiration_date",
    [
        [None, None],
        [timezone.now() - timedelta(days=1), timezone.now() + timedelta(days=1)],
        [None, timezone.now() + timedelta(days=1)],
        [timezone.now() - timedelta(days=1), None],
    ],
)
def test_get_unexpired_coupon(order_with_coupon, activation_date, expiration_date):
    """get_unexpired_coupon should get a coupon matching the product id and coupon code, which is also valid"""
    coupon = order_with_coupon.coupon
    coupon.activation_date = activation_date
    coupon.expiration_date = expiration_date
    coupon.save()
    assert (
        B2BCoupon.objects.get_unexpired_coupon(
            coupon_code=coupon.coupon_code, product_id=coupon.product_id
        )
        == coupon
    )


@pytest.mark.parametrize(
    "attr_name, attr_value",
    [
        ["enabled", False],
        ["activation_date", timezone.now() + timedelta(days=1)],
        ["expiration_date", timezone.now() - timedelta(days=1)],
    ],
)
def test_get_unexpired_coupon_not_found(order_with_coupon, attr_name, attr_value):
    """
    get_unexpired_coupon should raise a B2BCoupon.DoesNotExist if there is no active, enabled, and unexpired coupon
    """
    coupon = order_with_coupon.coupon
    setattr(coupon, attr_name, attr_value)
    coupon.save()
    with pytest.raises(B2BCoupon.DoesNotExist):
        B2BCoupon.objects.get_unexpired_coupon(
            coupon_code=coupon.coupon_code, product_id=coupon.product_id
        )


@pytest.mark.parametrize("reusable", [True, False])
@pytest.mark.parametrize("order_status", [B2BOrder.FULFILLED, B2BOrder.REFUNDED])
def test_get_unexpired_coupon_order_fulfilled(
    order_with_coupon, reusable, order_status
):
    """get_unexpired_coupon should raise a B2BCoupon.DoesNotExist if the coupon is already used in an order"""
    order = order_with_coupon.order
    coupon = order_with_coupon.coupon
    coupon.reusable = reusable
    coupon.save()
    order.status = order_status
    order.save()

    if not reusable:
        with pytest.raises(B2BCoupon.DoesNotExist):
            B2BCoupon.objects.get_unexpired_coupon(
                coupon_code=coupon.coupon_code, product_id=coupon.product_id
            )
    else:
        assert coupon == B2BCoupon.objects.get_unexpired_coupon(
            coupon_code=coupon.coupon_code, product_id=coupon.product_id
        )
