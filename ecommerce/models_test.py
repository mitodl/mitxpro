"""Tests for ecommerce models"""
import pytest
from django.db.utils import IntegrityError

from courses.factories import CourseFactory, CourseRunFactory, ProgramFactory
from courses.constants import CATALOG_COURSE_IMG_WAGTAIL_FILL
from ecommerce.api import get_product_version_price_with_discount
from ecommerce.constants import REFERENCE_NUMBER_PREFIX
from ecommerce.factories import (
    CouponPaymentVersionFactory,
    CouponRedemptionFactory,
    CouponVersionFactory,
    LineFactory,
    OrderFactory,
    ProductFactory,
    ProductVersionFactory,
)
from ecommerce.models import OrderAudit
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
    assert str(
        coupon_redemption
    ) == "CouponRedemption for order {}, coupon version {}".format(
        str(coupon_redemption.order), str(coupon_redemption.coupon_version)
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
    assert str(product) == "Product for {}".format(str(product.content_object))
    assert str(versions[0]) == "ProductVersion for {}, ${}".format(
        versions[0].description, versions[0].price
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
    program = ProgramFactory.create()
    program_product = ProductFactory.create(content_object=program)
    run = CourseRunFactory.create()
    run_product = ProductFactory.create(content_object=run)

    assert (
        program_product.thumbnail_url
        == program.page.thumbnail_image.get_rendition(
            CATALOG_COURSE_IMG_WAGTAIL_FILL
        ).url
    )
    assert (
        run_product.thumbnail_url
        == run.course.page.thumbnail_image.get_rendition(
            CATALOG_COURSE_IMG_WAGTAIL_FILL
        ).url
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
    """ Test that hubspot sync tasks are called only if API key is set"""
    settings.HUBSPOT_API_KEY = hubspot_api_key
    order = OrderFactory.create()
    order.save_and_log(None)
    if hubspot_api_key is not None:
        for line in order.lines.all():
            mock_hubspot_syncs.line.assert_called_with(line.id)
            mock_hubspot_syncs.product.assert_called_with(
                line.product_version.product.id
            )
    else:
        mock_hubspot_syncs.line.assert_not_called()
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
        product=ProductFactory.create(content_object=LineFactory())
    )
    assert product_version.text_id is None
    assert mock_log.called_once_with(
        f"The content object for this ProductVersion ({product_version.id}) does not have a `text_id` property"
    )


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
