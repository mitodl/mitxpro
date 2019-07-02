"""
Tests for ecommerce serializers
"""
# pylint: disable=unused-argument, redefined-outer-name
from decimal import Decimal

import pytest

from mitxpro.test_utils import any_instance_of
from cms.factories import CoursePageFactory, ProgramPageFactory
from courses.factories import CourseFactory, ProgramFactory, CourseRunFactory
from courses.serializers import CourseSerializer
from courses.constants import CATALOG_COURSE_IMG_WAGTAIL_FILL
from ecommerce.api import round_half_up
from ecommerce.factories import (
    ProductVersionFactory,
    ProductFactory,
    CompanyFactory,
    DataConsentUserFactory,
    CouponFactory,
    CouponEligibilityFactory,
    CouponPaymentVersionFactory,
    CouponPaymentFactory,
)
from ecommerce.models import (
    CouponSelection,
    Product,
    CourseRunSelection,
    DataConsentUser,
)
from ecommerce.serializers import (
    ProductVersionSerializer,
    CouponSelectionSerializer,
    BasketSerializer,
    SingleUseCouponSerializer,
    PromoCouponSerializer,
    CouponPaymentVersionDetailSerializer,
    CouponPaymentVersionSerializer,
    CouponPaymentSerializer,
    CurrentCouponPaymentSerializer,
    ProductSerializer,
    CompanySerializer,
    DataConsentUserSerializer,
    CouponSerializer,
    ProductCouponSerializer,
)

pytestmark = [pytest.mark.django_db]

datetime_format = "%Y-%m-%dT%H:%M:%SZ"
datetime_millis_format = "%Y-%m-%dT%H:%M:%S.%fZ"


def test_serialize_basket_product_version_courserun(mock_context):
    """Test ProductVersion serialization for a Course"""
    courserun = CourseRunFactory.create()
    product_version = ProductVersionFactory.create(
        product=ProductFactory(content_object=courserun)
    )
    data = ProductVersionSerializer(instance=product_version, context=mock_context).data
    assert data == {
        "id": product_version.id,
        "description": product_version.description,
        "content_title": product_version.product.content_object.title,
        "price": str(round_half_up(product_version.price)),
        "type": product_version.product.content_type.model,
        "courses": [
            CourseSerializer(instance=courserun.course, context=mock_context).data
        ],
        "thumbnail_url": "/static/images/mit-dome.png",
        "object_id": product_version.product.object_id,
        "product_id": product_version.product.id,
    }


def test_serialize_basket_product_version_program(mock_context):
    """Test ProductVersion serialization for a Program"""
    program = ProgramFactory()
    courses = CourseFactory.create_batch(3, program=program)
    product_version = ProductVersionFactory.create(
        product=ProductFactory(content_object=program)
    )

    data = ProductVersionSerializer(instance=product_version, context=mock_context).data
    assert data == {
        "id": product_version.id,
        "description": product_version.description,
        "content_title": product_version.product.content_object.title,
        "price": str(round_half_up(product_version.price)),
        "type": product_version.product.content_type.model,
        "courses": [
            CourseSerializer(instance=course, context=mock_context).data
            for course in courses
        ],
        "thumbnail_url": "/static/images/mit-dome.png",
        "object_id": product_version.product.object_id,
        "product_id": product_version.product.id,
    }


def test_basket_thumbnail_courserun(basket_and_coupons, mock_context):
    """Basket thumbnail should be serialized for a courserun"""
    thumbnail_filename = "abcde.jpg"
    course_page = CoursePageFactory.create(
        thumbnail_image__file__filename=thumbnail_filename
    )
    run = CourseRunFactory.create(course=course_page.course)
    product_version = ProductVersionFactory.create(product__content_object=run)
    data = ProductVersionSerializer(instance=product_version, context=mock_context).data
    assert (
        data["thumbnail_url"]
        == course_page.thumbnail_image.get_rendition(
            CATALOG_COURSE_IMG_WAGTAIL_FILL
        ).url
    )


def test_basket_thumbnail_program(basket_and_coupons, mock_context):
    """Basket thumbnail should be serialized for a program"""
    thumbnail_filename = "abcde.jpg"
    program_page = ProgramPageFactory.create(
        thumbnail_image__file__filename=thumbnail_filename
    )
    program = program_page.program
    product_version = ProductVersionFactory.create(product__content_object=program)
    data = ProductVersionSerializer(instance=product_version, context=mock_context).data
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
        "amount": str(basket_and_coupons.coupongroup_best.payment_version.amount),
        "targets": [basket_and_coupons.product_version.id],
    }


def test_serialize_basket_data_consents(basket_and_agreement, mock_context):
    """Test DataConsentUser serialization inside basket"""
    basket = basket_and_agreement.basket
    serialized_basket = BasketSerializer(
        instance=basket_and_agreement.basket, context=mock_context
    ).data
    data_consent_user = DataConsentUser.objects.get(
        agreement=basket_and_agreement.agreement, user=basket.user
    )
    assert len(serialized_basket["data_consents"]) == 1
    serialized_data_consent = serialized_basket["data_consents"][0]
    assert serialized_data_consent == {
        "id": data_consent_user.id,
        "company": CompanySerializer(
            instance=basket_and_agreement.agreement.company
        ).data,
        "consent_date": data_consent_user.consent_date.strftime(datetime_millis_format),
        "consent_text": basket_and_agreement.agreement.content,
    }


def test_serialize_basket(basket_and_agreement, mock_context):
    """Test Basket serialization"""
    basket = basket_and_agreement.basket
    selection = CouponSelection.objects.get(basket=basket)
    run = CourseRunSelection.objects.get(basket=basket).run
    data_consent = DataConsentUser.objects.get(user=basket.user)
    data = BasketSerializer(instance=basket, context=mock_context).data
    assert data == {
        "items": [
            {
                **ProductVersionSerializer(
                    instance=basket_and_agreement.product.latest_version,
                    context=mock_context,
                ).data,
                "run_ids": [run.id],
            }
        ],
        "coupons": [CouponSelectionSerializer(selection).data],
        "data_consents": [DataConsentUserSerializer(data_consent).data],
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
    """ Test that the CouponPaymentVersionDetailSerializer has correct data """
    serializer = CouponPaymentVersionDetailSerializer(
        instance=basket_and_coupons.coupongroup_best.payment_version
    )
    for attr in ("automatic", "coupon_type", "num_coupon_codes", "max_redemptions"):
        assert serializer.data.get(attr) == getattr(
            basket_and_coupons.coupongroup_best.payment_version, attr
        )
    for attr in ("activation_date", "expiration_date"):
        assert serializer.data.get(attr) == getattr(
            basket_and_coupons.coupongroup_best.payment_version, attr
        ).strftime(datetime_format)
    assert (
        Decimal(serializer.data.get("amount"))
        == basket_and_coupons.coupongroup_best.payment_version.amount
    )


def test_coupon_payment_serializer():
    """ Test that the CouponPaymentSerializer has correct data """
    payment = CouponPaymentFactory.build()
    serialized = CouponPaymentSerializer(payment).data
    assert serialized == {
        "name": payment.name,
        "created_on": None,
        "updated_on": None,
        "id": None,
    }


def test_coupon_payment_version_serializer():
    """ Test that the CouponPaymentVersionSerializer has correct data """
    payment_version = CouponPaymentVersionFactory.create()
    serialized = CouponPaymentVersionSerializer(payment_version).data
    assert serialized == {
        "tag": payment_version.tag,
        "automatic": payment_version.automatic,
        "coupon_type": payment_version.coupon_type,
        "num_coupon_codes": payment_version.num_coupon_codes,
        "max_redemptions": payment_version.max_redemptions,
        "max_redemptions_per_user": payment_version.max_redemptions_per_user,
        "amount": str(payment_version.amount),
        "expiration_date": payment_version.expiration_date.strftime(datetime_format),
        "activation_date": payment_version.activation_date.strftime(datetime_format),
        "payment_type": payment_version.payment_type,
        "payment_transaction": payment_version.payment_transaction,
        "company": payment_version.company.id,
        "payment": payment_version.payment.id,
        "id": payment_version.id,
        "created_on": any_instance_of(str),
        "updated_on": any_instance_of(str),
    }


def test_current_coupon_payment_version_serializer():
    """ Test that the CurrentCouponPaymentSerializer has correct data """
    payment_version = CouponPaymentVersionFactory.create()
    serialized = CurrentCouponPaymentSerializer(instance=payment_version.payment).data
    assert serialized == {
        **CouponPaymentSerializer(payment_version.payment).data,
        "version": CouponPaymentVersionSerializer(payment_version).data,
    }


def test_serialize_product(coupon_product_ids):
    """ Test that ProductSerializer has correct data """
    product = Product.objects.get(id=coupon_product_ids[0])
    run = product.content_object
    serialized_data = ProductSerializer(instance=product).data
    assert serialized_data.get("title") == run.title
    assert serialized_data.get("product_type") == "courserun"
    assert serialized_data.get("id") == product.id


def test_serialize_company():
    """ Test that CompanySerializer has correct data """
    company = CompanyFactory.create()
    serialized_data = CompanySerializer(instance=company).data
    assert serialized_data == {"id": company.id, "name": company.name}


def test_serialize_data_consent_user():
    """ Test that DataConsentUserSerializer has correct data """
    consent_user = DataConsentUserFactory.create()
    serialized_data = DataConsentUserSerializer(instance=consent_user).data
    assert serialized_data == {
        "id": consent_user.id,
        "company": CompanySerializer(instance=consent_user.agreement.company).data,
        "consent_date": consent_user.consent_date.strftime(datetime_millis_format),
        "consent_text": consent_user.agreement.content,
    }


def test_serialize_coupon():
    """Test that CouponSerializer produces the correct serialized data"""
    name = "Some Coupon"
    code = "1234"
    coupon = CouponFactory.build(payment__name=name, coupon_code=code, enabled=True)
    serialized_data = CouponSerializer(instance=coupon).data
    assert serialized_data == {
        "id": None,
        "name": name,
        "coupon_code": code,
        "enabled": True,
    }


def test_serialize_product_coupon():
    """Test that ProductCouponSerializer produces the correct serialized data"""
    product_coupon = CouponEligibilityFactory.create()
    serialized_data = ProductCouponSerializer(instance=product_coupon).data
    assert serialized_data == {
        "id": product_coupon.id,
        "coupon": CouponSerializer(instance=product_coupon.coupon).data,
        "product": ProductSerializer(instance=product_coupon.product).data,
    }
