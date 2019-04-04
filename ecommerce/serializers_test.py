"""
Tests for ecommerce serializers
"""
# pylint: disable=unused-argument, redefined-outer-name
import pytest

from courses.factories import CourseFactory, ProgramFactory, CourseRunFactory
from courses.serializers import CourseRunSerializer
from ecommerce.factories import ProductVersionFactory, ProductFactory
from ecommerce.models import CouponSelection
from ecommerce.serializers import (
    ProductVersionSerializer,
    CouponSelectionSerializer,
    BasketSerializer,
)

pytestmark = [pytest.mark.django_db]


def test_serialize_basket_product_version_course_run():
    """Test ProductVersion serialization for a CourseRun"""
    course_run = CourseRunFactory.create()
    product_version = ProductVersionFactory.create(
        product=ProductFactory(content_object=course_run)
    )
    data = ProductVersionSerializer(product_version).data
    assert data == {
        "id": product_version.id,
        "description": product_version.description,
        "price": str(round(product_version.price, 2)),
        "type": product_version.product.content_type.model,
        "course_runs": [CourseRunSerializer(course_run).data],
        "thumbnail_url": "/static/images/mit-dome.png",
    }


def test_serialize_basket_product_version_course():
    """Test ProductVersion serialization for a Course"""
    course = CourseFactory.create()
    product_version = ProductVersionFactory.create(
        product=ProductFactory(content_object=course)
    )
    data = ProductVersionSerializer(product_version).data
    assert data == {
        "id": product_version.id,
        "description": product_version.description,
        "price": str(round(product_version.price, 2)),
        "type": product_version.product.content_type.model,
        "course_runs": [CourseRunSerializer(course.first_unexpired_run).data],
        "thumbnail_url": "/static/images/mit-dome.png",
    }


def test_serialize_basket_product_version_program():
    """Test ProductVersion serialization for a Program"""
    program = ProgramFactory()
    courses = CourseFactory.create_batch(3, program=program)
    product_version = ProductVersionFactory.create(
        product=ProductFactory(content_object=program)
    )

    data = ProductVersionSerializer(product_version).data
    assert data == {
        "id": product_version.id,
        "description": product_version.description,
        "price": str(round(product_version.price, 2)),
        "type": product_version.product.content_type.model,
        "course_runs": [
            CourseRunSerializer(course.first_unexpired_run).data for course in courses
        ],
        "thumbnail_url": "/static/images/mit-dome.png",
    }


def test_basket_thumbnail_courserun(basket_and_coupons):
    """Basket thumbnail should have """
    image = "abcde"
    run = CourseRunFactory.create(course__thumbnail=image)
    product_version = ProductVersionFactory.create(product__content_object=run)
    data = ProductVersionSerializer(product_version).data
    assert data["thumbnail_url"] == "/media/abcde"


def test_basket_thumbnail_course(basket_and_coupons):
    """Basket thumbnail should have """
    image = "abcde"
    run = CourseFactory.create(thumbnail=image)
    product_version = ProductVersionFactory.create(product__content_object=run)
    data = ProductVersionSerializer(product_version).data
    assert data["thumbnail_url"] == "/media/abcde"


def test_basket_thumbnail_program(basket_and_coupons):
    """Basket thumbnail should have """
    image = "abcde"
    run = ProgramFactory.create(thumbnail=image)
    product_version = ProductVersionFactory.create(product__content_object=run)
    data = ProductVersionSerializer(product_version).data
    assert data["thumbnail_url"] == "/media/abcde"


def test_serialize_basket_coupon_selection(basket_and_coupons):
    """Test CouponSelection serialization"""
    selection = CouponSelection.objects.get(basket=basket_and_coupons.basket)
    data = CouponSelectionSerializer(selection).data
    assert data == {
        "code": selection.coupon.coupon_code,
        "amount": round(basket_and_coupons.coupongroup_best.invoice_version.amount, 2),
        "targets": [basket_and_coupons.product_version.id],
    }


def test_serialize_basket(basket_and_coupons):
    """Test Basket serialization"""
    basket = basket_and_coupons.basket
    selection = CouponSelection.objects.get(basket=basket)
    data = BasketSerializer(basket).data
    assert data == {
        "items": [ProductVersionSerializer(basket_and_coupons.product_version).data],
        "coupons": [CouponSelectionSerializer(selection).data],
    }
