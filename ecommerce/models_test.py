"""Tests for ecommerce models"""
import pytest

from courses.factories import CourseRunFactory, ProgramFactory
from ecommerce.factories import (
    CouponRedemptionFactory,
    LineFactory,
    ProductFactory,
    ProductVersionFactory,
)
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
    contents = [CourseRunFactory.create(), ProgramFactory.create()]
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


def test_latest_version():
    """
    The latest_version property should return the latest product version
    """
    versions_to_create = 4
    product = ProductFactory.create()
    versions = ProductVersionFactory.create_batch(versions_to_create, product=product)
    # Latest version should be the most recently created
    assert product.latest_version == versions[versions_to_create - 1]


@pytest.mark.parametrize("is_program", [True, False])
def test_run_queryset(is_program):
    """
    run_queryset should return all runs related to the product
    """
    program = ProgramFactory.create()
    runs = [CourseRunFactory.create(course__program=program) for _ in range(4)]
    run = runs[2]
    obj = program if is_program else run
    product = ProductFactory.create(content_object=obj)

    def key_func(_run):
        return _run.id

    assert sorted(product.run_queryset, key=key_func) == sorted(
        runs if is_program else [run], key=key_func
    )
