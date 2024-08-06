"""Tests for ecommerce models"""

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from b2b_ecommerce.factories import B2BCouponFactory
from courses.constants import CATALOG_COURSE_IMG_WAGTAIL_FILL
from courses.factories import CourseFactory, CourseRunFactory, ProgramFactory
from ecommerce.api import (
    get_product_version_price_with_discount,
    get_product_version_price_with_discount_tax,
)
from ecommerce.constants import REFERENCE_NUMBER_PREFIX
from ecommerce.factories import (
    CouponFactory,
    CouponPaymentVersionFactory,
    CouponRedemptionFactory,
    CouponVersionFactory,
    LineFactory,
    OrderFactory,
    ProductFactory,
    ProductVersionFactory,
)
from ecommerce.models import Coupon, OrderAudit
from mitxpro.utils import serialize_model_object
from users.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("has_user", [True, False])
@pytest.mark.parametrize("has_lines", [True, False])
def test_order_audit(has_user, has_lines):
    """
    Order.save_and_log() should save the order's information to an audit model.
    """
    coupon_redemption = CouponRedemptionFactory.create()
    assert (
        str(coupon_redemption)
        == f"CouponRedemption for order {coupon_redemption.order!s}, coupon version {coupon_redemption.coupon_version!s}"
    )
    order = coupon_redemption.order
    contents = [CourseRunFactory.create(), ProgramFactory.create()]
    lines = (
        [
            LineFactory.create(
                order=order, product_version__product__content_object=content
            )
            for content in contents
        ]
        if has_lines
        else []
    )

    assert OrderAudit.objects.count() == 0
    order.save_and_log(UserFactory.create() if has_user else None)

    assert OrderAudit.objects.count() == 1
    order_audit = OrderAudit.objects.first()
    assert order_audit.order == order

    assert order_audit.data_after == {
        **serialize_model_object(order),
        "purchaser_email": order.purchaser.email,
        "lines": [
            {
                **serialize_model_object(line),
                "product_version_info": {
                    **serialize_model_object(line.product_version),
                    "product_info": {
                        **serialize_model_object(line.product_version.product),
                        "content_type_string": str(
                            line.product_version.product.content_type
                        ),
                        "content_object": serialize_model_object(
                            line.product_version.product.content_object
                        ),
                    },
                },
            }
            for line in lines
        ],
        "coupons": [
            {
                **serialize_model_object(coupon_redemption.coupon_version.coupon),
                "coupon_version_info": {
                    **serialize_model_object(coupon_redemption.coupon_version),
                    "payment_version_info": serialize_model_object(
                        coupon_redemption.coupon_version.payment_version
                    ),
                },
            }
            for coupon_redemption in order.couponredemption_set.all()
        ],
        "run_enrollments": [
            enrollment.run.courseware_id
            for enrollment in order.courserunenrollment_set.all()
        ],
        "total_price": str(
            get_product_version_price_with_discount(
                product_version=lines[0].product_version,
                coupon_version=order.couponredemption_set.first().coupon_version,
            )
        )
        if has_lines
        else "",
        "total_tax": str(
            get_product_version_price_with_discount_tax(
                product_version=lines[0].product_version,
                coupon_version=order.couponredemption_set.first().coupon_version,
                tax_rate=order.tax_rate,
            )["tax_assessed"]
        )
        if has_lines
        else "",
        "tax_rate": str(order.tax_rate),
        "tax_name": order.tax_rate_name,
        "receipts": [
            serialize_model_object(receipt) for receipt in order.receipt_set.all()
        ],
    }


def test_latest_version():
    """
    The latest_version property should return the latest product version
    """
    versions_to_create = 4
    product = ProductFactory.create()
    versions = ProductVersionFactory.create_batch(versions_to_create, product=product)
    assert str(product) == f"Product for {str(product.content_object)}"  # noqa: RUF010
    assert (
        str(versions[0])
        == f"ProductVersion for {versions[0].description}, ${versions[0].price}"
    )
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


def test_type_string():
    """
    type_string should return a string representation of the Product type
    """
    program = ProgramFactory.create()
    run = CourseRunFactory.create()
    program_product = ProductFactory.create(content_object=program)
    assert program_product.type_string == "program"
    run_product = ProductFactory.create(content_object=run)
    assert run_product.type_string == "courserun"


def test_title():
    """
    title should return a string representation of the Product's title
    """
    program = ProgramFactory.create(title="test title of the program")
    course = CourseFactory.create(title="test title of the course")
    run = CourseRunFactory.create(course=course)

    program_product = ProductFactory.create(content_object=program)
    assert program_product.title == "test title of the program"
    run_product = ProductFactory.create(content_object=run)
    assert run_product.title == "test title of the course"


def test_thumbnail_url():
    """
    thumbnail_url should return a url of the Product's thumbnail
    """
    from wagtail.images.views.serve import generate_image_url

    program = ProgramFactory.create()
    program_product = ProductFactory.create(content_object=program)
    run = CourseRunFactory.create()
    run_product = ProductFactory.create(content_object=run)

    assert program_product.thumbnail_url == generate_image_url(
        program.page.thumbnail_image, CATALOG_COURSE_IMG_WAGTAIL_FILL
    )
    assert run_product.thumbnail_url == generate_image_url(
        run.course.page.thumbnail_image, CATALOG_COURSE_IMG_WAGTAIL_FILL
    )


def test_start_date():
    """
    start_date should return a start next_run_date of the Product
    """
    program = ProgramFactory.create()
    course = CourseFactory.create()
    run = CourseRunFactory.create(course=course)

    program_product = ProductFactory.create(content_object=program)
    assert program_product.start_date == program.next_run_date
    run_product = ProductFactory.create(content_object=run)
    assert run_product.start_date == course.next_run_date


@pytest.mark.parametrize("hubspot_api_key", [None, "fake-key"])
def test_hubspot_syncs(mock_hubspot_syncs, settings, hubspot_api_key):
    """Test that hubspot sync tasks are called only if API key is set"""
    settings.MITOL_HUBSPOT_API_PRIVATE_TOKEN = hubspot_api_key
    order = OrderFactory.create()
    order.save_and_log(None)
    if hubspot_api_key is not None:
        for line in order.lines.all():
            mock_hubspot_syncs.product.assert_called_with(
                line.product_version.product.id
            )
    else:
        mock_hubspot_syncs.product.assert_not_called()


def test_product_version_save_text_id_courserun():
    """ProductVersion.text_id should be set to CourseRun.courseware_id on save"""
    run = CourseRunFactory.create()
    product_version = ProductVersionFactory.create(
        product=ProductFactory.create(content_object=run)
    )
    assert product_version.text_id == run.courseware_id


def test_product_version_save_text_id_program():
    """ProductVersion.text_id should be set to Program.readable_id on save"""
    program = ProgramFactory.create()
    product_version = ProductVersionFactory.create(
        product=ProductFactory.create(content_object=program)
    )
    assert product_version.text_id == program.readable_id


def test_product_version_save_text_id_badproduct(mocker):
    """ProductVersion.text_id should None if ProductVersion.product is invalid"""
    mock_log = mocker.patch("ecommerce.models.log")
    product_version = ProductVersionFactory.create(
        product=ProductFactory.create(content_object=LineFactory()), id=1
    )
    assert product_version.text_id is None
    mock_log.error.assert_called_once_with(
        "The content object for this ProductVersion (%s) does not have a `text_id` property",
        str(product_version.id),
    )


def test_product_version_save_empty_description(mocker):
    """ProductVersion should raise ValidationError if ProductVersion.description is empty"""
    product_version = ProductVersionFactory.create(
        product=ProductFactory.create(content_object=LineFactory())
    )
    product_version.description = ""
    with pytest.raises(ValidationError) as exc:
        product_version.save()
    assert exc.value.message == "Description is a required field."


@pytest.mark.parametrize(
    "factory",
    [ProductVersionFactory, CouponVersionFactory, CouponPaymentVersionFactory],
)
def test_prevent_update(factory):
    """Check that we prevent updating certain version models"""
    obj = factory.create()
    with pytest.raises(IntegrityError):
        obj.save()


@pytest.mark.parametrize(
    "factory",
    [ProductVersionFactory, CouponVersionFactory, CouponPaymentVersionFactory],
)
def test_prevent_delete(factory):
    """Check that we prevent deleting certain version models"""
    obj = factory.create()
    obj_id = obj.id
    obj.delete()
    assert type(obj).objects.filter(id=obj_id).count() == 1


def test_reference_number(settings):
    """
    order.reference_number should concatenate the reference prefix and the order id
    """
    settings.ENVIRONMENT = "test"

    order = OrderFactory.create()
    assert (
        f"{REFERENCE_NUMBER_PREFIX}{settings.ENVIRONMENT}-{order.id}"
        == order.reference_number
    )


@pytest.mark.parametrize("factory", [CouponFactory, B2BCouponFactory])
def test_duplicate_coupon_not_allowed(factory):
    """Verify that duplicate coupons are not allowed."""
    coupon = factory.create()

    with pytest.raises(ValidationError) as cm:  # noqa: PT012
        new_coupon = CouponFactory.build(coupon_code=coupon.coupon_code)
        new_coupon.clean()
    assert (
        cm.value.message_dict["coupon_code"][0]
        == "Coupon code already exists in the platform."
    )


def test_edit_coupon():
    """Verify that a coupon can be successfully edited"""
    coupon = CouponFactory.create()
    coupon.coupon_code = "new_coupon"
    coupon.enabled = False
    coupon.save()

    updated_coupon = Coupon.objects.get(pk=coupon.pk)
    assert updated_coupon.coupon_code == "new_coupon"
    assert not updated_coupon.enabled
