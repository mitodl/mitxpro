"""
Tests for hubspot serializers
"""
# pylint: disable=unused-argument, redefined-outer-name

import pytest

from courses.factories import CourseRunFactory
from ecommerce.api import round_half_up
from ecommerce.factories import (
    LineFactory,
    OrderFactory,
    CouponRedemptionFactory,
    ProductVersionFactory,
    ProductFactory,
)
from ecommerce.models import Product, Order
from hubspot.api import format_hubspot_id
from hubspot.serializers import (
    ProductSerializer,
    LineSerializer,
    OrderToDealSerializer,
    ORDER_STATUS_MAPPING,
    ORDER_TYPE_B2C,
    ORDER_TYPE_B2B,
)

pytestmark = [pytest.mark.django_db]


@pytest.mark.parametrize(
    "text_id, expected",
    [
        ["course-v1:xPRO+SysEngxNAV+R1", "Run 1"],
        ["course-v1:xPRO+SysEngxNAV+R10", "Run 10"],
        ["course-v1:xPRO+SysEngxNAV", "course-v1:xPRO+SysEngxNAV"],
    ],
)
def test_serialize_product(text_id, expected):
    """ Test that ProductSerializer has correct data """
    product_version = ProductVersionFactory.create(
        product=ProductFactory.create(
            content_object=CourseRunFactory.create(courseware_id=text_id)
        )
    )
    product = Product.objects.get(id=product_version.product.id)
    run = product.content_object
    serialized_data = ProductSerializer(instance=product).data
    assert serialized_data.get("title") == f"{run.title}: {expected}"
    assert serialized_data.get("product_type") == "courserun"
    assert serialized_data.get("id") == product.id
    assert serialized_data.get("price") == product.latest_version.price.to_eng_string()
    assert serialized_data.get("description") == product.latest_version.description


def test_serialize_line():
    """Test that LineSerializer produces the correct serialized data"""
    line = LineFactory.create()
    serialized_data = LineSerializer(instance=line).data
    assert serialized_data == {
        "id": line.id,
        "product": format_hubspot_id(line.product_version.product.id),
        "order": format_hubspot_id(line.order_id),
        "quantity": line.quantity,
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
        "purchaser": format_hubspot_id(order.purchaser.id),
        "status": ORDER_STATUS_MAPPING[status],
        "amount": line.product_version.price.to_eng_string(),
        "discount_amount": "0.00",
        "close_date": (
            int(order.updated_on.timestamp() * 1000)
            if status == Order.FULFILLED
            else None
        ),
        "coupon_code": None,
        "company": None,
        "payment_type": None,
        "payment_transaction": None,
        "discount_percent": "0",
        "order_type": ORDER_TYPE_B2C,
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
        "purchaser": format_hubspot_id(order.purchaser.id),
        "status": ORDER_STATUS_MAPPING[order.status],
        "amount": line.product_version.price.to_eng_string(),
        "discount_amount": discount.to_eng_string(),
        "close_date": (
            int(order.updated_on.timestamp() * 1000)
            if order.status == Order.FULFILLED
            else None
        ),
        "coupon_code": coupon_redemption.coupon_version.coupon.coupon_code,
        "company": coupon_redemption.coupon_version.payment_version.company.name,
        "order_type": ORDER_TYPE_B2B,
        "payment_type": coupon_redemption.coupon_version.payment_version.payment_type,
        "payment_transaction": coupon_redemption.coupon_version.payment_version.payment_transaction,
        "discount_percent": (
            coupon_redemption.coupon_version.payment_version.amount * 100
        ).to_eng_string(),
        "lines": [LineSerializer(instance=line).data],
    }
