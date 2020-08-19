"""
Tests for hubspot serializers
"""
# pylint: disable=unused-argument, redefined-outer-name

from decimal import Decimal
import pytest
from rest_framework import status
from django.urls import reverse
from b2b_ecommerce.factories import B2BOrderFactory, B2BCouponFactory
from b2b_ecommerce.models import B2BOrder
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
    B2BOrderToDealSerializer,
    ORDER_STATUS_MAPPING,
    ORDER_TYPE_B2C,
    ORDER_TYPE_B2B,
    B2BProductVersionToLineSerializer,
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
        "status": line.order.status,
        "product_id": line.product_version.text_id,
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
        "stage": ORDER_STATUS_MAPPING[status],
        "amount": line.product_version.price.to_eng_string(),
        "discount_amount": "0.0000",
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
        "status": order.status,
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
        "stage": ORDER_STATUS_MAPPING[order.status],
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
        "status": order.status,
    }


@pytest.mark.parametrize("status", [Order.FULFILLED, Order.CREATED])
@pytest.mark.parametrize("existing_user", [True, False])
def test_serialize_b2b_order(status, existing_user, user):
    """Test that B2BOrderToDealSerializer produces the correct serialized data"""
    order = B2BOrderFactory.create(status=status, num_seats=10)
    purchaser_id = order.email
    if existing_user:
        order.email = user.email
        purchaser_id = user.id
    serialized_data = B2BOrderToDealSerializer(instance=order).data
    assert serialized_data == {
        "id": order.id,
        "name": f"XPRO-B2BORDER-{order.id}",
        "stage": ORDER_STATUS_MAPPING[status],
        "amount": order.total_price.to_eng_string(),
        "discount_amount": None,
        "close_date": (
            int(order.updated_on.timestamp() * 1000)
            if status == Order.FULFILLED
            else None
        ),
        "coupon_code": None,
        "company": None,
        "payment_type": None,
        "payment_transaction": None,
        "discount_percent": None,
        "num_seats": 10,
        "status": order.status,
        "purchaser": format_hubspot_id(purchaser_id),
    }


def test_serialize_b2b_product_version():
    """Test that B2BProductVersionToLineSerializer produces the correct serialized data"""
    order = B2BOrderFactory.create(status=Order.FULFILLED, num_seats=10)
    serialized_data = B2BProductVersionToLineSerializer(instance=order).data
    assert serialized_data == {
        "id": format_hubspot_id(order.product_version.id),
        "product": format_hubspot_id(order.product_version.product.id),
        "order": format_hubspot_id(order.integration_id),
        "quantity": order.num_seats,
        "status": order.status,
        "product_id": order.product_version.text_id,
    }


def test_serialize_b2b_order_with_coupon(client, mocker):
    """Test that B2BOrderToDealSerializer produces the correct serialized data for an order with coupon"""

    product_version = ProductVersionFactory.create(price=10)
    payload = {"a": "payload"}
    mocker.patch(
        "b2b_ecommerce.views.generate_b2b_cybersource_sa_payload",
        autospec=True,
        return_value=payload,
    )
    coupon = B2BCouponFactory.create(
        product=product_version.product, discount_percent=Decimal(0.8)
    )
    num_seats = 10
    resp = client.post(
        reverse("b2b-checkout"),
        {
            "num_seats": num_seats,
            "email": "b@example.com",
            "product_version_id": product_version.id,
            "discount_code": coupon.coupon_code,
            "contract_number": "",
        },
    )

    assert resp.status_code == status.HTTP_200_OK
    assert B2BOrder.objects.count() == 1
    order = B2BOrder.objects.first()
    discount = round(Decimal(coupon.discount_percent) * 100, 2)
    serialized_data = B2BOrderToDealSerializer(instance=order).data
    assert serialized_data == {
        "id": order.id,
        "name": f"XPRO-B2BORDER-{order.id}",
        "stage": ORDER_STATUS_MAPPING[order.status],
        "discount_amount": discount.to_eng_string(),
        "amount": order.total_price.to_eng_string(),
        "close_date": (
            int(order.updated_on.timestamp() * 1000)
            if order.status == Order.FULFILLED
            else None
        ),
        "coupon_code": coupon.coupon_code,
        "company": coupon.company.name,
        "payment_type": None,
        "payment_transaction": None,
        "num_seats": num_seats,
        "discount_percent": round(
            Decimal(coupon.discount_percent) * 100, 2
        ).to_eng_string(),
        "status": order.status,
        "purchaser": format_hubspot_id(order.email),
    }
