"""
Tests for hubspot_xpro serializers
"""

from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from mitol.hubspot_api.api import format_app_id
from mitol.hubspot_api.models import HubspotObject
from rest_framework import status

from b2b_ecommerce.constants import B2B_ORDER_PREFIX
from b2b_ecommerce.factories import B2BCouponFactory
from b2b_ecommerce.models import B2BOrder
from courses.factories import CourseRunFactory
from ecommerce.constants import DISCOUNT_TYPE_DOLLARS_OFF, DISCOUNT_TYPE_PERCENT_OFF
from ecommerce.factories import (
    CouponRedemptionFactory,
    ProductFactory,
    ProductVersionFactory,
)
from ecommerce.models import Order, Product
from hubspot_xpro.serializers import (
    ORDER_STATUS_MAPPING,
    ORDER_TYPE_B2B,
    ORDER_TYPE_B2C,
    B2BOrderToDealSerializer,
    B2BOrderToLineItemSerializer,
    LineSerializer,
    OrderToDealSerializer,
    ProductSerializer,
    format_product_name,
)

pytestmark = [pytest.mark.django_db]


@pytest.mark.parametrize(
    "text_id, expected",  # noqa: PT006
    [
        ["course-v1:xPRO+SysEngxNAV+R1", "Run 1"],  # noqa: PT007
        ["course-v1:xPRO+SysEngxNAV+R10", "Run 10"],  # noqa: PT007
        ["course-v1:xPRO+SysEngxNAV", "course-v1:xPRO+SysEngxNAV"],  # noqa: PT007
    ],
)
def test_serialize_product(text_id, expected):
    """Test that ProductSerializer has correct data"""
    product_version = ProductVersionFactory.create(
        product=ProductFactory.create(
            content_object=CourseRunFactory.create(courseware_id=text_id)
        )
    )
    product = Product.objects.get(id=product_version.product.id)
    run = product.content_object
    serialized_data = ProductSerializer(instance=product).data
    assert serialized_data.get("name") == f"{run.title}: {expected}"
    assert serialized_data.get("price") == product.latest_version.price.to_eng_string()
    assert serialized_data.get("description") == product.latest_version.description
    assert serialized_data.get("unique_app_id") == format_app_id(product.id)


def test_serialize_line(hubspot_order, hubspot_b2b_order_id):
    """Test that LineSerializer produces the correct serialized data"""
    line = hubspot_order.lines.first()
    serialized_data = LineSerializer(instance=line).data
    assert serialized_data == {
        "hs_product_id": HubspotObject.objects.get(
            content_type=ContentType.objects.get_for_model(Product),
            object_id=line.product_version.product.id,
        ).hubspot_id,
        "quantity": line.quantity,
        "status": line.order.status,
        "product_id": line.product_version.text_id,
        "name": format_product_name(line.product_version.product),
        "price": line.product_version.price.to_eng_string(),
        "unique_app_id": format_app_id(line.id),
    }


@pytest.mark.parametrize("status", [Order.FULFILLED, Order.CREATED])
def test_serialize_order(settings, hubspot_order, status):
    """Test that OrderToDealSerializer produces the correct serialized data"""
    hubspot_order.status = status
    line = hubspot_order.lines.first()
    serialized_data = OrderToDealSerializer(instance=hubspot_order).data
    assert serialized_data == {
        "dealname": f"XPRO-ORDER-{hubspot_order.id}",
        "dealstage": ORDER_STATUS_MAPPING[status],
        "amount": line.product_version.price.to_eng_string(),
        "discount_amount": "0.0000",
        "closedate": (
            int(hubspot_order.updated_on.timestamp() * 1000)
            if status == Order.FULFILLED
            else None
        ),
        "coupon_code": None,
        "company": None,
        "payment_type": None,
        "payment_transaction": None,
        "discount_type": None,
        "discount_percent": "0",
        "order_type": ORDER_TYPE_B2C,
        "status": hubspot_order.status,
        "pipeline": settings.HUBSPOT_PIPELINE_ID,
        "unique_app_id": format_app_id(hubspot_order.id),
    }


@pytest.mark.parametrize(
    "discount_type, amount",  # noqa: PT006
    [
        [DISCOUNT_TYPE_PERCENT_OFF, Decimal("0.75")],  # noqa: PT007
        [DISCOUNT_TYPE_DOLLARS_OFF, Decimal("75")],  # noqa: PT007
    ],
)
def test_serialize_order_with_coupon(settings, hubspot_order, discount_type, amount):
    """Test that OrderToDealSerializer produces the correct serialized data for an order with coupon"""
    line = hubspot_order.lines.first()
    coupon_redemption = CouponRedemptionFactory.create(
        order=hubspot_order,
        coupon_version__payment_version__amount=amount,
        coupon_version__payment_version__discount_type=discount_type,
    )
    discount = (
        coupon_redemption.coupon_version.payment_version.calculate_discount_amount(
            price=line.product_version.price
        )
    )
    serialized_data = OrderToDealSerializer(instance=hubspot_order).data
    assert serialized_data == {
        "dealname": f"XPRO-ORDER-{hubspot_order.id}",
        "dealstage": ORDER_STATUS_MAPPING[hubspot_order.status],
        "amount": line.product_version.price.to_eng_string(),
        "discount_amount": discount.to_eng_string(),
        "closedate": (
            int(hubspot_order.updated_on.timestamp() * 1000)
            if hubspot_order.status == Order.FULFILLED
            else None
        ),
        "coupon_code": coupon_redemption.coupon_version.coupon.coupon_code,
        "company": coupon_redemption.coupon_version.payment_version.company.name,
        "order_type": ORDER_TYPE_B2B,
        "payment_type": coupon_redemption.coupon_version.payment_version.payment_type,
        "discount_type": coupon_redemption.coupon_version.payment_version.discount_type,
        "payment_transaction": coupon_redemption.coupon_version.payment_version.payment_transaction,
        "discount_percent": coupon_redemption.coupon_version.payment_version.calculate_discount_percent(
            price=line.product_version.price
        ).to_eng_string(),
        "status": hubspot_order.status,
        "pipeline": settings.HUBSPOT_PIPELINE_ID,
        "unique_app_id": format_app_id(hubspot_order.id),
    }


@pytest.mark.parametrize("status", [Order.FULFILLED, Order.CREATED])
def test_serialize_b2b_order(settings, hubspot_b2b_order, status):
    """Test that B2BOrderToDealSerializer produces the correct serialized data"""
    hubspot_b2b_order.status = status
    serialized_data = B2BOrderToDealSerializer(instance=hubspot_b2b_order).data
    assert serialized_data == {
        "dealname": f"{B2B_ORDER_PREFIX}-{hubspot_b2b_order.id}",
        "dealstage": ORDER_STATUS_MAPPING[status],
        "amount": hubspot_b2b_order.total_price.to_eng_string(),
        "discount_amount": None,
        "closedate": (
            int(hubspot_b2b_order.updated_on.timestamp() * 1000)
            if status == Order.FULFILLED
            else None
        ),
        "coupon_code": None,
        "company": None,
        "payment_type": None,
        "payment_transaction": None,
        "discount_percent": None,
        "discount_type": None,
        "num_seats": hubspot_b2b_order.num_seats,
        "status": hubspot_b2b_order.status,
        "pipeline": settings.HUBSPOT_PIPELINE_ID,
        "order_type": ORDER_TYPE_B2B,
        "unique_app_id": f"{settings.MITOL_HUBSPOT_API_ID_PREFIX}-{B2B_ORDER_PREFIX}-{hubspot_b2b_order.id}",
    }


def test_serialize_b2b_line_item(settings, hubspot_b2b_order, hubspot_b2b_order_id):
    """Test that B2BProductVersionToLineSerializer produces the correct serialized data"""
    serialized_data = B2BOrderToLineItemSerializer(instance=hubspot_b2b_order).data
    assert serialized_data == {
        "hs_product_id": HubspotObject.objects.get(
            content_type=ContentType.objects.get_for_model(Product),
            object_id=hubspot_b2b_order.product_version.product.id,
        ).hubspot_id,
        "quantity": hubspot_b2b_order.num_seats,
        "status": hubspot_b2b_order.status,
        "product_id": hubspot_b2b_order.product_version.text_id,
        "price": hubspot_b2b_order.product_version.price.to_eng_string(),
        "name": format_product_name(hubspot_b2b_order.product_version.product),
        "unique_app_id": f"{settings.MITOL_HUBSPOT_API_ID_PREFIX}-{B2B_ORDER_PREFIX}-{hubspot_b2b_order.line.id}",
    }


def test_serialize_b2b_order_with_coupon(settings, client, mocker):
    """Test that B2BOrderToDealSerializer produces the correct serialized data for an order with coupon"""

    product_version = ProductVersionFactory.create(price=10)
    HubspotObject.objects.create(
        content_type=ContentType.objects.get_for_model(Product),
        object_id=product_version.product.id,
    )
    payload = {"a": "payload"}
    mocker.patch(
        "b2b_ecommerce.views.generate_b2b_cybersource_sa_payload",
        autospec=True,
        return_value=payload,
    )
    coupon = B2BCouponFactory.create(
        product=product_version.product, discount_percent=Decimal("0.8")
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
    assert (
        serialized_data
        == {
            "dealname": f"{B2B_ORDER_PREFIX}-{order.id}",
            "dealstage": ORDER_STATUS_MAPPING[order.status],
            "discount_amount": discount.to_eng_string(),
            "amount": order.total_price.to_eng_string(),
            "closedate": (
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
            "discount_type": DISCOUNT_TYPE_PERCENT_OFF,  # B2B Orders only support percent-off discounts
            "status": order.status,
            "order_type": ORDER_TYPE_B2B,
            "pipeline": settings.HUBSPOT_PIPELINE_ID,
            "unique_app_id": f"{settings.MITOL_HUBSPOT_API_ID_PREFIX}-{B2B_ORDER_PREFIX}-{order.id}",
        }
    )
