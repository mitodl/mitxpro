"""
Tests for ecommerce serializers
"""

from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from cms.factories import CoursePageFactory, ProgramPageFactory
from courses.constants import CATALOG_COURSE_IMG_WAGTAIL_FILL
from courses.factories import (
    CourseFactory,
    CourseRunFactory,
    ProgramFactory,
    ProgramRunFactory,
)
from courses.serializers import CourseSerializer
from ecommerce.api import get_readable_id, round_half_up
from ecommerce.constants import CYBERSOURCE_CARD_TYPES, DISCOUNT_TYPE_PERCENT_OFF
from ecommerce.factories import (
    CompanyFactory,
    CouponFactory,
    CouponPaymentFactory,
    CouponPaymentVersionFactory,
    DataConsentUserFactory,
    LineFactory,
    ProductFactory,
    ProductVersionFactory,
    ReceiptFactory,
)
from ecommerce.models import CouponSelection, CourseRunSelection, DataConsentUser, Order
from ecommerce.serializers import (
    BasketSerializer,
    CompanySerializer,
    CouponPaymentSerializer,
    CouponPaymentVersionDetailSerializer,
    CouponPaymentVersionSerializer,
    CouponSelectionSerializer,
    CouponSerializer,
    DataConsentUserSerializer,
    FullProductVersionSerializer,
    OrderReceiptSerializer,
    ProgramRunSerializer,
    PromoCouponSerializer,
    SingleUseCouponSerializer,
)
from mitxpro.test_utils import any_instance_of

pytestmark = [pytest.mark.django_db]

datetime_format = "%Y-%m-%dT%H:%M:%SZ"
datetime_millis_format = "%Y-%m-%dT%H:%M:%S.%fZ"


def test_serialize_basket_product_version_courserun(mock_context):
    """Test ProductVersion serialization for a Course"""
    courserun = CourseRunFactory.create()
    product_version = ProductVersionFactory.create(
        product=ProductFactory(content_object=courserun)
    )
    data = FullProductVersionSerializer(
        instance=product_version, context=mock_context
    ).data
    assert data == {
        "id": product_version.id,
        "description": product_version.description,
        "content_title": product_version.product.content_object.title,
        "price": str(round_half_up(product_version.price)),
        "type": product_version.product.content_type.model,
        "courses": [
            CourseSerializer(instance=courserun.course, context=mock_context).data
        ],
        "thumbnail_url": courserun.course.catalog_image_url,
        "object_id": product_version.product.object_id,
        "product_id": product_version.product.id,
        "readable_id": get_readable_id(product_version.product.content_object),
        "run_tag": courserun.run_tag,
        "created_on": product_version.created_on.strftime(datetime_millis_format),
        "start_date": product_version.product.content_object.start_date.isoformat()
        if product_version.product.content_object.start_date
        else None,
    }


def test_serialize_basket_product_version_program(mock_context):
    """Test ProductVersion serialization for a Program"""
    program = ProgramFactory.create()
    courses = CourseFactory.create_batch(3, program=program)
    product_version = ProductVersionFactory.create(
        product=ProductFactory(content_object=program)
    )

    data = FullProductVersionSerializer(
        instance=product_version, context=mock_context
    ).data
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
        "thumbnail_url": program.catalog_image_url,
        "object_id": product_version.product.object_id,
        "product_id": product_version.product.id,
        "readable_id": get_readable_id(product_version.product.content_object),
        "run_tag": None,
        "created_on": product_version.created_on.strftime(datetime_millis_format),
        "start_date": product_version.product.content_object.next_run_date.isoformat()
        if product_version.product.content_object.next_run_date
        else None,
    }


def test_serialize_basket_product_version_programrun(mock_context):
    """Test ProductVersion serialization for a Program with an associated ProgramRun"""
    program_run = ProgramRunFactory()
    product_version = ProductVersionFactory.create(
        product=ProductFactory(content_object=program_run.program)
    )
    context = {**mock_context, **{"program_run": program_run}}  # noqa: PIE800

    data = FullProductVersionSerializer(instance=product_version, context=context).data
    assert data["object_id"] == program_run.program.id
    assert data["run_tag"] == program_run.run_tag


def test_basket_thumbnail_courserun(basket_and_coupons, mock_context):
    """Basket thumbnail should be serialized for a courserun"""
    from wagtail.images.views.serve import generate_image_url

    thumbnail_filename = "abcde.jpg"
    course_page = CoursePageFactory.create(
        thumbnail_image__file__filename=thumbnail_filename
    )
    run = CourseRunFactory.create(course=course_page.course)
    product_version = ProductVersionFactory.create(product__content_object=run)
    data = FullProductVersionSerializer(
        instance=product_version, context=mock_context
    ).data
    assert data["thumbnail_url"] == generate_image_url(
        course_page.thumbnail_image, CATALOG_COURSE_IMG_WAGTAIL_FILL
    )


def test_basket_thumbnail_program(basket_and_coupons, mock_context):
    """Basket thumbnail should be serialized for a program"""
    from wagtail.images.views.serve import generate_image_url

    thumbnail_filename = "abcde.jpg"
    program_page = ProgramPageFactory.create(
        thumbnail_image__file__filename=thumbnail_filename
    )
    program = program_page.program
    product_version = ProductVersionFactory.create(product__content_object=program)
    data = FullProductVersionSerializer(
        instance=product_version, context=mock_context
    ).data
    assert data["thumbnail_url"] == generate_image_url(
        program_page.thumbnail_image, CATALOG_COURSE_IMG_WAGTAIL_FILL
    )


def test_serialize_basket_coupon_selection(basket_and_coupons):
    """Test CouponSelection serialization"""
    selection = CouponSelection.objects.get(basket=basket_and_coupons.basket)
    data = CouponSelectionSerializer(selection).data
    assert data == {
        "code": selection.coupon.coupon_code,
        "amount": str(basket_and_coupons.coupongroup_best.payment_version.amount),
        "discount_type": basket_and_coupons.coupongroup_best.payment_version.discount_type,
        "targets": [basket_and_coupons.product_version.id],
    }


def test_serialize_basket_data_consents(basket_and_agreement, mock_context, mocker):
    """Test DataConsentUser serialization inside basket"""

    mocker.patch("ipware.get_client_ip", return_value="127.0.0.1")

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


@pytest.mark.parametrize("is_live", [True, False])
def test_serialize_basket(basket_and_agreement, mock_context, is_live, mocker):
    """Test Basket serialization"""
    mocker.patch("ipware.get_client_ip", return_value="127.0.0.1")
    basket = basket_and_agreement.basket
    selection = CouponSelection.objects.get(basket=basket)
    run = CourseRunSelection.objects.get(basket=basket).run
    data_consent = DataConsentUser.objects.get(user=basket.user)
    run.live = is_live
    run.save()

    data = BasketSerializer(instance=basket, context=mock_context).data
    assert data == {
        "items": [
            {
                **FullProductVersionSerializer(
                    instance=basket_and_agreement.product.latest_version,
                    context=mock_context,
                ).data,
                "run_ids": [run.id] if is_live else [],
            }
        ],
        "coupons": [CouponSelectionSerializer(selection).data],
        "data_consents": [DataConsentUserSerializer(data_consent).data],
        "tax_info": {
            "country_code": "",
            "tax_rate": 0,
            "tax_rate_name": "VAT",
            "active": True,
        },
    }


@pytest.mark.parametrize("has_products", [True, False])
@pytest.mark.parametrize("has_payment_transaction", [True, False])
def test_serialize_coupon_single_use(
    has_payment_transaction, has_products, coupon_product_ids
):
    """Test the SingleUseCouponSerializer"""
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
        "discount_type": DISCOUNT_TYPE_PERCENT_OFF,
        "payment_transaction": ("fake123" if has_payment_transaction else None),
        "product_ids": (coupon_product_ids if has_products else []),
        "include_future_runs": False,
    }
    serializer = SingleUseCouponSerializer(data=data)
    assert serializer.is_valid() is (has_payment_transaction and has_products)


@pytest.mark.parametrize(
    "too_high, expected_message",  # noqa: PT006
    [
        [  # noqa: PT007
            True,
            "The amount should be between (0 - 1) when discount type is percent-off.",
        ],
        [  # noqa: PT007
            False,
            "The amount is invalid, please specify a value greater than 0.",
        ],
    ],
)
def test_serialize_coupon_invalid_amount(
    coupon_product_ids, too_high, expected_message
):
    """The amount should be between 0 and 1"""
    data = {
        "name": "FAKETAG",
        "tag": None,
        "automatic": True,
        "activation_date": "2018-01-01T00:00:00Z",
        "expiration_date": "2019-12-31T00:00:00Z",
        "amount": 1.75 if too_high else -0.25,
        "num_coupon_codes": 2,
        "coupon_type": "single-use",
        "company": "Acme Corp.",
        "payment_type": "credit_card",
        "discount_type": DISCOUNT_TYPE_PERCENT_OFF,
        "payment_transaction": "fake123",
        "product_ids": coupon_product_ids,
        "include_future_runs": False,
    }
    serializer = SingleUseCouponSerializer(data=data)
    with pytest.raises(ValidationError) as ex:
        serializer.is_valid(raise_exception=True)
    assert ex.value.args[0] == {"discount": [expected_message]}


@pytest.mark.parametrize("has_coupon_code", [True, False])
@pytest.mark.parametrize("has_payment_transaction", [True, False])
@pytest.mark.parametrize("has_products", [True, False])
def test_serialize_coupon_promo(
    coupon_product_ids, has_payment_transaction, has_coupon_code, has_products
):
    """Test the PromoCouponSerializer"""
    data = {
        "name": "FAKETAG",
        "tag": None,
        "coupon_code": ("FAKE_CODE" if has_coupon_code else None),
        "automatic": True,
        "activation_date": "2018-01-01T00:00:00Z",
        "expiration_date": "2019-12-31T00:00:00Z",
        "amount": 0.75,
        "coupon_type": "promo",
        "discount_type": DISCOUNT_TYPE_PERCENT_OFF,
        "company": "Acme Corp.",
        "payment_type": "credit_card",
        "payment_transaction": ("fake123" if has_payment_transaction else None),
        "product_ids": (coupon_product_ids if has_products else []),
        "include_future_runs": False,
    }
    serializer = PromoCouponSerializer(data=data)
    assert serializer.is_valid() is (has_coupon_code and has_products)


@pytest.mark.parametrize(
    "too_high, expected_message",  # noqa: PT006
    [
        [  # noqa: PT007
            True,
            "The amount should be between (0 - 1) when discount type is percent-off.",
        ],
        [  # noqa: PT007
            False,
            "The amount is invalid, please specify a value greater than 0.",
        ],
    ],
)
def test_serialize_coupon_promo_invalid_amount(
    coupon_product_ids, too_high, expected_message
):
    """Test the PromoCouponSerializer"""
    data = {
        "name": "FAKETAG",
        "tag": None,
        "coupon_code": "FAKE_CODE",
        "automatic": True,
        "activation_date": "2018-01-01T00:00:00Z",
        "expiration_date": "2019-12-31T00:00:00Z",
        "amount": 1.75 if too_high else -0.25,
        "coupon_type": "promo",
        "discount_type": DISCOUNT_TYPE_PERCENT_OFF,
        "company": "Acme Corp.",
        "payment_type": "credit_card",
        "payment_transaction": None,
        "product_ids": coupon_product_ids,
        "include_future_runs": False,
    }
    serializer = PromoCouponSerializer(data=data)
    with pytest.raises(ValidationError) as ex:
        serializer.is_valid(raise_exception=True)
    assert ex.value.args[0] == {"discount": [expected_message]}


def test_serialize_coupon_payment_version_serializer(basket_and_coupons):
    """Test that the CouponPaymentVersionDetailSerializer has correct data"""
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
        ).strftime(datetime_millis_format)
    assert (
        Decimal(serializer.data.get("amount"))
        == basket_and_coupons.coupongroup_best.payment_version.amount
    )


def test_coupon_payment_serializer():
    """Test that the CouponPaymentSerializer has correct data"""
    payment = CouponPaymentFactory.build()
    assert str(payment) == f"CouponPayment {payment.name}"
    serialized = CouponPaymentSerializer(payment).data
    assert serialized == {
        "name": payment.name,
        "created_on": None,
        "updated_on": None,
        "id": None,
    }


def test_coupon_payment_version_serializer():
    """Test that the CouponPaymentVersionSerializer has correct data"""
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
        "expiration_date": payment_version.expiration_date.strftime(
            datetime_millis_format
        ),
        "activation_date": payment_version.activation_date.strftime(
            datetime_millis_format
        ),
        "payment_type": payment_version.payment_type,
        "discount_type": DISCOUNT_TYPE_PERCENT_OFF,
        "payment_transaction": payment_version.payment_transaction,
        "company": payment_version.company.id,
        "payment": payment_version.payment.id,
        "id": payment_version.id,
        "created_on": any_instance_of(str),
        "updated_on": any_instance_of(str),
    }


@pytest.mark.parametrize(
    "receipt_data",
    [
        {"req_card_number": "1234", "req_card_type": "001"},
        {"req_card_number": "5678", "req_card_type": "002"},
        {"req_card_number": "5678"},
        {
            "req_card_number": "5678",
            "req_card_type": "002",
            "req_bill_to_forename": "XYZ",
            "req_bill_to_surname": "ABC",
        },
        {},
    ],
)
def test_serialize_order_receipt(receipt_data):
    """Test that the OrderReceiptSerializer has correct data"""
    line = LineFactory.create(order__status=Order.FULFILLED)
    product_version = line.product_version
    order = line.order
    purchaser = order.purchaser.legal_address
    receipt = (
        ReceiptFactory.create(order=order, data=receipt_data) if receipt_data else None
    )
    serialized_data = OrderReceiptSerializer(instance=order).data
    assert serialized_data == {
        "coupon": None,
        "lines": [
            {
                "readable_id": get_readable_id(product_version.product.content_object),
                "content_title": product_version.product.content_object.title,
                "discount": "0.00",
                "start_date": None,
                "end_date": None,
                "price": str(product_version.price),
                "total_paid": str(line.quantity * product_version.price),
                "tax_paid": "0.00",
                "total_before_tax": str(line.quantity * product_version.price),
                "quantity": line.quantity,
                "CEUs": product_version.product.content_object.course.page.certificate_page.CEUs,
            }
        ],
        "order": {
            "id": order.id,
            "created_on": order.created_on,
            "reference_number": order.reference_number,
            "tax_country_code": "",
            "tax_rate": 0,
            "tax_rate_name": "",
        },
        "purchaser": {
            "first_name": purchaser.first_name,
            "last_name": purchaser.last_name,
            "email": order.purchaser.email,
            "country": purchaser.country,
            "state_or_territory": purchaser.state_or_territory,
            "city": purchaser.city,
            "postal_code": purchaser.postal_code,
            "vat_id": purchaser.vat_id,
            "company": order.purchaser.profile.company,
            "street_address": [
                line
                for line in [
                    purchaser.street_address_1,
                    purchaser.street_address_2,
                    purchaser.street_address_3,
                    purchaser.street_address_4,
                    purchaser.street_address_5,
                ]
                if line
            ],
        },
        "receipt": {
            "card_number": receipt_data["req_card_number"]  # noqa: SIM401
            if "req_card_number" in receipt_data
            else None,
            "card_type": CYBERSOURCE_CARD_TYPES[receipt_data["req_card_type"]]
            if "req_card_type" in receipt_data
            else None,
            "payment_method": receipt.data["req_payment_method"]  # noqa: SIM401
            if "req_payment_method" in receipt.data
            else None,
            "bill_to_email": receipt.data["req_bill_to_email"]  # noqa: SIM401
            if "req_bill_to_email" in receipt.data
            else None,
            "name": f"{receipt.data.get('req_bill_to_forename')} {receipt.data.get('req_bill_to_surname')}"
            if "req_bill_to_forename" in receipt.data
            or "req_bill_to_surname" in receipt.data
            else None,
        }
        if receipt
        else None,
    }


def test_serialize_company():
    """Test that CompanySerializer has correct data"""
    company = CompanyFactory.create()
    serialized_data = CompanySerializer(instance=company).data
    assert serialized_data == {"id": company.id, "name": company.name}


def test_serialize_data_consent_user():
    """Test that DataConsentUserSerializer has correct data"""
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
    assert str(coupon) == f"Coupon {coupon.coupon_code} for {str(coupon.payment)}"  # noqa: RUF010
    serialized_data = CouponSerializer(instance=coupon).data
    assert serialized_data == {
        "id": None,
        "name": name,
        "coupon_code": code,
        "enabled": True,
        "include_future_runs": False,
        "is_global": False,
    }


def test_serialize_global_coupon():
    """Test that CouponSerializer produces the correct serialized data for a global coupon"""
    name = "FAKE"
    code = "1111"
    coupon = CouponFactory.build(
        payment__name=name, coupon_code=code, is_global=True, enabled=True
    )
    serialized_data = CouponSerializer(instance=coupon).data
    assert serialized_data == {
        "id": None,
        "name": name,
        "coupon_code": code,
        "enabled": True,
        "include_future_runs": False,
        "is_global": True,
    }


def test_serialize_program_run():
    """ProgramRunSerializer should serializer a program run with proper format"""
    program_run = ProgramRunFactory()
    serialized_data = ProgramRunSerializer(instance=program_run).data
    assert serialized_data == {
        "id": program_run.id,
        "run_tag": program_run.run_tag,
        "start_date": program_run.start_date,
        "end_date": program_run.end_date,
    }
