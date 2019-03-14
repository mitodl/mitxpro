"""Tests for ecommerce models"""
import pytest

from courses.factories import CourseFactory, CourseRunFactory, ProgramFactory
from ecommerce.factories import CouponRedemptionFactory, LineFactory
from ecommerce.models import OrderAudit
from mitxpro.utils import serialize_model_object
from users.factories import UserFactory


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("has_user", [True, False])
def test_order_audit(has_user):
    """
    Order.save_and_log() should save the order's information to an audit model.
    """
    coupon_redemption = CouponRedemptionFactory.create()
    order = coupon_redemption.order
    contents = [
        CourseRunFactory.create(),
        CourseFactory.create(),
        ProgramFactory.create(),
    ]
    lines = [
        LineFactory.create(
            order=order, product_version__product__content_object=content
        )
        for content in contents
    ]

    assert OrderAudit.objects.count() == 0
    order.save_and_log(UserFactory.create() if has_user else None)

    assert OrderAudit.objects.count() == 1
    order_audit = OrderAudit.objects.first()
    assert order_audit.order == order

    assert order_audit.data_after == {
        **serialize_model_object(order),
        "lines": [serialize_model_object(line) for line in lines],
        "coupons": [
            serialize_model_object(coupon)
            for coupon in order.couponredemption_set.all()
        ],
    }
