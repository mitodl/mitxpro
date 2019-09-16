"""Ecommerce mail API tests"""
from urllib.parse import urljoin

from django.urls import reverse
import pytest

from b2b_ecommerce.factories import B2BOrderFactory
from courses.factories import CourseRunEnrollmentFactory
from ecommerce.api import get_readable_id
from ecommerce.factories import (
    CouponPaymentVersionFactory,
    CouponEligibilityFactory,
    ProductVersionFactory,
    CompanyFactory,
)
from ecommerce.mail_api import (
    send_b2b_receipt_email,
    send_bulk_enroll_emails,
    send_course_run_enrollment_email,
)
from mail.constants import (
    EMAIL_BULK_ENROLL,
    EMAIL_COURSE_RUN_ENROLLMENT,
    EMAIL_B2B_RECEIPT,
)
from mitxpro.utils import format_price

lazy = pytest.lazy_fixture

pytestmark = pytest.mark.django_db


@pytest.fixture()
def company():
    """Company object fixture"""
    return CompanyFactory.create(name="MIT")


@pytest.mark.parametrize("test_company", [lazy("company"), None])
def test_send_bulk_enroll_emails(mocker, settings, test_company):
    """
    send_bulk_enroll_emails should build messages for each recipient and send them
    """
    patched_mail_api = mocker.patch("ecommerce.mail_api.api")

    settings.SITE_BASE_URL = "http://test.com/"
    email = "a@b.com"
    payment_version = CouponPaymentVersionFactory.create(company=test_company)
    product_version = ProductVersionFactory.create()
    product_coupon = CouponEligibilityFactory.create(
        coupon__payment=payment_version.payment, product=product_version.product
    )

    expected_qs = "product={}&code={}".format(
        product_version.product.id, product_coupon.coupon.coupon_code
    )
    expected_context = {
        "enrollable_title": product_coupon.product.content_object.title,
        "enrollment_url": "http://test.com/checkout/?{}".format(expected_qs),
        "company_name": test_company.name if test_company else None,
    }

    send_bulk_enroll_emails([email], [product_coupon])

    patched_mail_api.build_user_specific_messages.assert_called_once()
    assert (
        patched_mail_api.build_user_specific_messages.call_args[0][0]
        == EMAIL_BULK_ENROLL
    )
    assert list(patched_mail_api.build_user_specific_messages.call_args[0][1]) == [
        (email, expected_context)
    ]

    patched_mail_api.send_messages.assert_called_once_with(
        patched_mail_api.build_user_specific_messages.return_value
    )


def test_send_course_run_enrollment_email(mocker):
    """send_course_run_enrollment_email should send an email for the given enrollment"""
    patched_mail_api = mocker.patch("ecommerce.mail_api.api")
    enrollment = CourseRunEnrollmentFactory.create()

    send_course_run_enrollment_email(enrollment)

    patched_mail_api.context_for_user.assert_called_once_with(
        user=enrollment.user, extra_context={"enrollment": enrollment}
    )
    patched_mail_api.message_for_recipient.assert_called_once_with(
        enrollment.user.email,
        patched_mail_api.context_for_user.return_value,
        EMAIL_COURSE_RUN_ENROLLMENT,
    )
    patched_mail_api.send_message.assert_called_once_with(
        patched_mail_api.message_for_recipient.return_value
    )


def test_send_course_run_enrollment_email_error(mocker):
    """send_course_run_enrollment_email handle and log errors"""
    patched_mail_api = mocker.patch("ecommerce.mail_api.api")
    patched_log = mocker.patch("ecommerce.mail_api.log")
    patched_mail_api.send_message.side_effect = Exception("error")
    enrollment = CourseRunEnrollmentFactory.create()

    send_course_run_enrollment_email(enrollment)

    patched_log.exception.assert_called_once_with(
        "Error sending enrollment success email"
    )


@pytest.mark.parametrize("has_discount", [True, False])
def test_send_b2b_receipt_email(mocker, settings, has_discount):
    """send_b2b_receipt_email should send a receipt email"""
    patched_mail_api = mocker.patch("ecommerce.mail_api.api")
    order = B2BOrderFactory.create()
    if has_discount:
        discount = order.total_price / 3
        order.discount = discount
        order.total_price -= discount
        order.save()

    send_b2b_receipt_email(order)

    format_string = "%b %-d, %Y"
    run = order.product_version.product.content_object
    download_url = f'{urljoin(settings.SITE_BASE_URL, reverse("bulk-enrollment-code-receipt"))}?hash={str(order.unique_id)}'

    patched_mail_api.context_for_user.assert_called_once_with(
        user=None,
        extra_context={
            "purchase_date": order.updated_on.strftime(format_string),
            "total_price": format_price(order.total_price),
            "item_price": format_price(order.per_item_price),
            "discount": format_price(order.discount) if has_discount else None,
            "num_seats": str(order.num_seats),
            "readable_id": get_readable_id(run),
            "run_date_range": f"{run.start_date.strftime(format_string)} - {run.end_date.strftime(format_string)}",
            "title": run.title,
            "download_url": download_url,
            "email": order.email,
            "order_reference_id": order.reference_number,
        },
    )
    patched_mail_api.message_for_recipient.assert_called_once_with(
        order.email, patched_mail_api.context_for_user.return_value, EMAIL_B2B_RECEIPT
    )
    patched_mail_api.send_message.assert_called_once_with(
        patched_mail_api.message_for_recipient.return_value
    )


def test_send_b2b_receipt_email_error(mocker):
    """send_b2b_receipt_email should log an error and silence the exception if sending mail fails"""
    order = B2BOrderFactory.create()
    patched_mail_api = mocker.patch("ecommerce.mail_api.api")
    patched_log = mocker.patch("ecommerce.mail_api.log")
    patched_mail_api.send_message.side_effect = Exception("error")

    send_b2b_receipt_email(order)

    patched_log.exception.assert_called_once_with("Error sending receipt email")
