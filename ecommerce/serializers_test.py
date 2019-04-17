"""
Tests for ecommerce serializers
"""
# pylint: disable=unused-argument, redefined-outer-name
import pytest

from cms.factories import CoursePageFactory, ProgramPageFactory
from courses.factories import CourseFactory, ProgramFactory, CourseRunFactory
from courses.models import CourseRun
from courses.serializers import CourseRunSerializer
from courses.constants import CATALOG_COURSE_IMG_WAGTAIL_FILL
from ecommerce.api import round_half_up
from ecommerce.factories import ProductVersionFactory, ProductFactory
from ecommerce.models import CouponSelection, Product
from ecommerce.serializers import (
    ProductVersionSerializer,
    CouponSelectionSerializer,
    BasketSerializer,
    SingleUseCouponSerializer,
    PromoCouponSerializer,
    CouponPaymentVersionSerializer,
    ProductSerializer,
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
        "price": str(round_half_up(product_version.price)),
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
        "price": str(round_half_up(product_version.price)),
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
        "price": str(round_half_up(product_version.price)),
        "type": product_version.product.content_type.model,
        "course_runs": [
            CourseRunSerializer(course.first_unexpired_run).data for course in courses
        ],
        "thumbnail_url": "/static/images/mit-dome.png",
    }


def test_basket_thumbnail_courserun(basket_and_coupons):
    """Basket thumbnail should be serialized for a course run"""
    thumbnail_filename = "abcde.jpg"
    run = CourseRunFactory.create()
    course_page = CoursePageFactory.create(
        course=run.course, thumbnail_image__file__filename=thumbnail_filename
    )
    product_version = ProductVersionFactory.create(product__content_object=run)
    data = ProductVersionSerializer(product_version).data
    assert (
        data["thumbnail_url"]
        == course_page.thumbnail_image.get_rendition(
            CATALOG_COURSE_IMG_WAGTAIL_FILL
        ).url
    )


def test_basket_thumbnail_course(basket_and_coupons):
    """Basket thumbnail should be serialized for a course"""
    thumbnail_filename = "abcde.jpg"
    course_page = CoursePageFactory.create(
        thumbnail_image__file__filename=thumbnail_filename
    )
    course = course_page.course
    product_version = ProductVersionFactory.create(product__content_object=course)
    data = ProductVersionSerializer(product_version).data
    assert (
        data["thumbnail_url"]
        == course_page.thumbnail_image.get_rendition(
            CATALOG_COURSE_IMG_WAGTAIL_FILL
        ).url
    )


def test_basket_thumbnail_program(basket_and_coupons):
    """Basket thumbnail should be serialized for a program"""
    thumbnail_filename = "abcde.jpg"
    program_page = ProgramPageFactory.create(
        thumbnail_image__file__filename=thumbnail_filename
    )
    program = program_page.program
    product_version = ProductVersionFactory.create(product__content_object=program)
    data = ProductVersionSerializer(product_version).data
    assert (
        data["thumbnail_url"]
        == program_page.thumbnail_image.get_rendition(
            CATALOG_COURSE_IMG_WAGTAIL_FILL
        ).url
    )


def test_serialize_basket_coupon_selection(basket_and_coupons):
    """Test CouponSelection serialization"""
    selection = CouponSelection.objects.get(basket=basket_and_coupons.basket)
    data = CouponSelectionSerializer(selection).data
    assert data == {
        "code": selection.coupon.coupon_code,
        "amount": str(
            round_half_up(basket_and_coupons.coupongroup_best.payment_version.amount)
        ),
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


@pytest.mark.parametrize("has_products", [True, False])
@pytest.mark.parametrize("has_payment_transaction", [True, False])
def test_serialize_coupon_single_use(
    has_payment_transaction, has_products, coupon_product_ids
):
    """ Test the SingleUseCouponSerializer """
    data = {
        "name": "FAKETAG",
        "tag": None,
        "automatic": True,
        "activation_date": "2018-01-01T00:00:00Z",
        "expiration_date": "2019-12-31T00:00:00Z",
        "amount": 0.75,
        "num_coupon_codes": 2,
        "coupon_type": "single-use",
        "company": "Acme Corp.",
        "payment_type": "credit_card",
        "payment_transaction": ("fake123" if has_payment_transaction else None),
        "product_ids": (coupon_product_ids if has_products else []),
    }
    serializer = SingleUseCouponSerializer(data=data)
    assert serializer.is_valid() is (has_payment_transaction and has_products)


@pytest.mark.parametrize("has_coupon_code", [True, False])
@pytest.mark.parametrize("has_payment_transaction", [True, False])
@pytest.mark.parametrize("has_products", [True, False])
def test_serialize_coupon_promo(
    coupon_product_ids, has_payment_transaction, has_coupon_code, has_products
):
    """ Test the PromoCouponSerializer """
    data = {
        "name": "FAKETAG",
        "tag": None,
        "coupon_code": ("FAKE_CODE" if has_coupon_code else None),
        "automatic": True,
        "activation_date": "2018-01-01T00:00:00Z",
        "expiration_date": "2019-12-31T00:00:00Z",
        "amount": 0.75,
        "coupon_type": "promo",
        "company": "Acme Corp.",
        "payment_type": "credit_card",
        "payment_transaction": ("fake123" if has_payment_transaction else None),
        "product_ids": (coupon_product_ids if has_products else []),
    }
    serializer = PromoCouponSerializer(data=data)
    assert serializer.is_valid() is (has_coupon_code and has_products)


def test_serialize_coupon_payment_version_serializer(basket_and_coupons):
    """ Test that the CouponPaymentVersionSerializer has correct data """
    serializer = CouponPaymentVersionSerializer(
        instance=basket_and_coupons.coupongroup_best.payment_version
    )
    for attr in ("automatic", "coupon_type", "num_coupon_codes", "max_redemptions"):
        assert serializer.data.get(attr) == getattr(
            basket_and_coupons.coupongroup_best.payment_version, attr
        )
    for attr in ("activation_date", "expiration_date"):
        assert serializer.data.get(attr) == getattr(
            basket_and_coupons.coupongroup_best.payment_version, attr
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert serializer.data.get("amount") == "{0:.2}".format(
        basket_and_coupons.coupongroup_best.payment_version.amount
    )


def test_serialize_product(coupon_product_ids):
    """ Test that ProductSerializer has correct data """
    product = Product.objects.get(id=coupon_product_ids[0])
    course_run = CourseRun.objects.get(id=product.object_id)
    serialized_data = ProductSerializer(instance=product).data
    assert serialized_data.get("title") == course_run.title
    assert serialized_data.get("product_type") == "courserun"
    assert serialized_data.get("id") == product.id
