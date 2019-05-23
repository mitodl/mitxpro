"""
Tests for hubspot serializers
"""
# pylint: disable=unused-argument, redefined-outer-name

import pytest

from ecommerce.api import round_half_up
from ecommerce.factories import (
    LineFactory,
    OrderFactory,
    CouponRedemptionFactory,
    ProductVersionFactory,
)
from ecommerce.models import Product, Order
from hubspot.serializers import ProductSerializer, LineSerializer, OrderToDealSerializer

pytestmark = [pytest.mark.django_db]


def test_serialize_product():
    """ Test that ProductSerializer has correct data """
    product_version = ProductVersionFactory.create()
    product = Product.objects.get(id=product_version.product.id)
    run = product.content_object
    serialized_data = ProductSerializer(instance=product).data
    assert serialized_data.get("title") == run.title
    assert serialized_data.get("product_type") == "courserun"
    assert serialized_data.get("id") == product.id
    assert serialized_data.get("price") == product.latest_version.price.to_eng_string()


def test_serialize_line():
    """Test that LineSerializer produces the correct serialized data"""
    line = LineFactory.create()
    serialized_data = LineSerializer(instance=line).data
    assert serialized_data == {
        "id": line.id,
        "product": line.product_version.product.id,
    }


@pytest.mark.parametrize("status", [Order.FULFILLED, Order.CREATED])
def test_serialize_order(status):
    """Test that OrderToDealSerializer produces the correct serialized data"""
    order = OrderFactory.create(status=status)
    line = LineFactory.create(order=order)
    serialized_data = OrderToDealSerializer(instance=order).data
    assert serialized_data == {
        "id": order.id,
        "name": f"XPRO-ORDER-{order.id}",
        "purchaser": order.purchaser.id,
        "status": status,
        "amount": line.product_version.price.to_eng_string(),
        "discount_amount": "0.00",
        "close_date": (
            int(order.updated_on.timestamp() * 1000)
            if status == Order.FULFILLED
            else None
        ),
        "coupon_code": None,
        "company": None,
        "b2b": False,
        "lines": [LineSerializer(instance=line).data],
    }


def test_serialize_order_with_coupon():
    """Test that OrderToDealSerializer produces the correct serialized data for an order with coupon"""
    line = LineFactory.create()
    order = line.order
    coupon_redemption = CouponRedemptionFactory.create(order=order)
    discount = round_half_up(
        coupon_redemption.coupon_version.payment_version.amount
        * line.product_version.price
    )
    serialized_data = OrderToDealSerializer(instance=order).data
    assert serialized_data == {
        "id": order.id,
        "name": f"XPRO-ORDER-{order.id}",
        "purchaser": order.purchaser.id,
        "status": order.status,
        "amount": line.product_version.price.to_eng_string(),
        "discount_amount": discount.to_eng_string(),
        "close_date": (
            int(order.updated_on.timestamp() * 1000)
            if order.status == Order.FULFILLED
            else None
        ),
        "coupon_code": coupon_redemption.coupon_version.coupon.coupon_code,
        "company": coupon_redemption.coupon_version.payment_version.company.id,
        "b2b": True,
        "lines": [LineSerializer(instance=line).data],
    }
