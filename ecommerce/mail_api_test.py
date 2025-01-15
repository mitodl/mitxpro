"""Ecommerce mail API tests"""

import datetime
from urllib.parse import quote_plus, urljoin

import factory
import pytest
from django.urls import reverse

from b2b_ecommerce.factories import B2BOrderFactory
from courses.factories import (
    CourseRunEnrollmentFactory,
    CourseRunFactory,
    ProgramFactory,
)
from ecommerce.api import get_readable_id
from ecommerce.constants import BULK_ENROLLMENT_EMAIL_TAG
from ecommerce.factories import (
    BulkCouponAssignmentFactory,
    CompanyFactory,
    CouponPaymentVersionFactory,
    LineFactory,
    ProductCouponAssignmentFactory,
    ProductFactory,
    ProductVersionFactory,
    ReceiptFactory,
)
from ecommerce.mail_api import (
    EMAIL_DATE_FORMAT,
    EMAIL_TIME_FORMAT,
    ENROLL_ERROR_EMAIL_SUBJECT,
    send_b2b_receipt_email,
    send_bulk_enroll_emails,
    send_course_run_enrollment_email,
    send_course_run_enrollment_welcome_email,
    send_ecommerce_order_receipt,
    send_enrollment_failure_message,
)
from ecommerce.models import Order
from mail.api import EmailMetadata, UserMessageProps
from mail.constants import (
    EMAIL_B2B_RECEIPT,
    EMAIL_BULK_ENROLL,
    EMAIL_COURSE_RUN_ENROLLMENT,
    EMAIL_PRODUCT_ORDER_RECEIPT,
    EMAIL_WELCOME_COURSE_RUN_ENROLLMENT,
)
from mitxpro.utils import format_price
from users.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def company():
    """Company object fixture"""
    return CompanyFactory.create(name="MIT")


def test_send_bulk_enroll_emails(mocker, settings):
    """
    send_bulk_enroll_emails should build messages for each recipient and send them
    """
    patched_send_messages = mocker.patch("ecommerce.mail_api.api.send_messages")
    patched_build_user_messages = mocker.patch(
        "ecommerce.mail_api.api.build_user_specific_messages"
    )
    settings.SITE_BASE_URL = "http://test.com/"

    num_assignments = 2
    bulk_assignment = BulkCouponAssignmentFactory.create()
    assignments = ProductCouponAssignmentFactory.create_batch(
        num_assignments, bulk_assignment=bulk_assignment
    )
    new_company = CompanyFactory.create()
    new_coupon_payment_versions = CouponPaymentVersionFactory.create_batch(
        num_assignments,
        payment=factory.Iterator(
            [assignment.product_coupon.coupon.payment for assignment in assignments]
        ),
        company=factory.Iterator([new_company, None]),
    )

    send_bulk_enroll_emails(bulk_assignment.id, assignments)

    patched_send_messages.assert_called_once()
    patched_build_user_messages.assert_called_once()
    assert patched_build_user_messages.call_args[0][0] == EMAIL_BULK_ENROLL
    recipients_and_contexts_arg = list(patched_build_user_messages.call_args[0][1])
    for i, assignment in enumerate(assignments):
        product_type_str = assignment.product_coupon.product.type_string
        user_message_props = recipients_and_contexts_arg[i]
        assert isinstance(user_message_props, UserMessageProps) is True
        assert user_message_props.recipient == assignment.email
        assert user_message_props.context == {
            "enrollable_title": assignment.product_coupon.product.content_object.title,
            "enrollment_url": f"http://test.com/checkout/?is_voucher_applied=False&product={quote_plus(assignment.product_coupon.product.content_object.text_id)}&code={assignment.product_coupon.coupon.coupon_code}",
            "company_name": (
                None
                if not new_coupon_payment_versions[i].company
                else new_coupon_payment_versions[i].company.name
            ),
            "expiration_date": new_coupon_payment_versions[i].expiration_date.strftime(
                EMAIL_DATE_FORMAT
            ),
        }
        assert user_message_props.metadata == EmailMetadata(
            tags=[BULK_ENROLLMENT_EMAIL_TAG],
            user_variables={
                "bulk_assignment": bulk_assignment.id,
                "enrollment_code": assignment.product_coupon.coupon.coupon_code,
                product_type_str: assignment.product_coupon.product.content_object.text_id,
            },
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


@pytest.mark.parametrize("enabled", [True, False])
def test_send_course_run_enrollment_welcome_email(settings, mocker, enabled):
    """send_course_run_enrollment_welcome_email should send a welcome email for the given enrollment"""
    mocker.patch("ecommerce.mail_api.is_enabled", return_value=enabled)
    mock_log = mocker.patch("ecommerce.mail_api.log")
    patched_mail_api = mocker.patch("ecommerce.mail_api.api")
    enrollment = CourseRunEnrollmentFactory.create()

    run_start_date = enrollment.run.start_date
    run_start_time = run_start_date.astimezone(datetime.UTC).strftime(EMAIL_TIME_FORMAT)
    run_end_date = enrollment.run.end_date
    date_range = (
        f"{run_start_date.strftime(EMAIL_DATE_FORMAT)} - "
        f"{run_end_date.strftime(EMAIL_DATE_FORMAT)}"
    )

    send_course_run_enrollment_welcome_email(enrollment)

    if not enabled:
        mock_log.info.assert_called_once_with(
            "Feature `enrollment_welcome_email` is disabled."
        )
    else:
        patched_mail_api.context_for_user.assert_called_once_with(
            user=enrollment.user,
            extra_context={
                "enrollment": enrollment,
                "run_start_date": run_start_date.strftime(EMAIL_DATE_FORMAT),
                "run_start_time": run_start_time,
                "run_date_range": date_range,
                "support_email": settings.EMAIL_SUPPORT,
            },
        )
        patched_mail_api.message_for_recipient.assert_called_once_with(
            enrollment.user.email,
            patched_mail_api.context_for_user.return_value,
            EMAIL_WELCOME_COURSE_RUN_ENROLLMENT,
        )
        patched_mail_api.send_message.assert_called_once_with(
            patched_mail_api.message_for_recipient.return_value
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

    run = order.product_version.product.content_object
    download_url = f"{urljoin(settings.SITE_BASE_URL, reverse('bulk-enrollment-code-receipt'))}?hash={str(order.unique_id)}"  # noqa: RUF010

    patched_mail_api.context_for_user.assert_called_once_with(
        user=None,
        extra_context={
            "purchase_date": order.updated_on.strftime(EMAIL_DATE_FORMAT),
            "total_price": format_price(order.total_price),
            "item_price": format_price(order.per_item_price),
            "discount": format_price(order.discount) if has_discount else None,
            "num_seats": str(order.num_seats),
            "contract_number": order.contract_number,
            "readable_id": get_readable_id(run),
            "run_date_range": f"{run.start_date.strftime(EMAIL_DATE_FORMAT)} - {run.end_date.strftime(EMAIL_DATE_FORMAT)}",
            "title": run.title,
            "download_url": download_url,
            "email": order.email,
            "order_reference_id": order.reference_number,
            "receipt_data": {},
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


@pytest.mark.parametrize(
    "receipt_data",
    [
        {
            "req_card_number": "1234",
            "req_card_type": "001",
            "req_payment_method": "card",
            "req_bill_to_forename": "MIT",
            "req_bill_to_surname": "Doof",
            "req_bill_to_email": "doof@mit.edu",
        }
    ],
)
def test_send_ecommerce_order_receipt(mocker, receipt_data, settings):
    """send_ecommerce_order_receipt should send a receipt email"""
    mocker.patch("ecommerce.api.is_tax_applicable", return_value=False)
    patched_mail_api = mocker.patch("ecommerce.mail_api.api")
    date = datetime.datetime(2010, 1, 1, 0, tzinfo=datetime.UTC)
    user = UserFactory.create(
        name="test",
        email="test@example.com",
        legal_address__first_name="Test",
        legal_address__last_name="User",
        legal_address__street_address_1="11 Main Street",
        legal_address__country="US",
        legal_address__state_or_territory="US-CO",
        legal_address__city="Boulder",
        legal_address__postal_code="80309",
        legal_address__vat_id="AT12349876",
    )
    line = LineFactory.create(
        order__status=Order.CREATED,
        order__id=1,
        order__created_on=date,
        order__total_price_paid=0,
        order__purchaser=user,
        product_version__price=100,
        quantity=1,
        product_version__product__content_object=CourseRunFactory.create(
            title="test_run_title"
        ),
        product_version__product__content_object__course__readable_id="course:/v7/choose-agency",
    )
    (
        ReceiptFactory.create(order=line.order, data=receipt_data)
        if receipt_data
        else None
    )
    send_ecommerce_order_receipt(line.order)
    patched_mail_api.context_for_user.assert_called_once_with(
        user=None,
        extra_context={
            "coupon": None,
            "content_title": "test_run_title",
            "lines": [
                {
                    "quantity": 1,
                    "total_paid": "100.00",
                    "tax_paid": "0.00",
                    "discount": "0.00",
                    "total_before_tax": "100.00",
                    "price": "100.00",
                    "readable_id": get_readable_id(
                        line.product_version.product.content_object
                    ),
                    "start_date": None,
                    "end_date": None,
                    "content_title": "test_run_title",
                    "CEUs": line.product_version.product.content_object.course.page.certificate_page.CEUs,
                }
            ],
            "order_total": "100.00",
            "order_total_tax": "100.00",
            "order": {
                "id": 1,
                "created_on": line.order.created_on,
                "reference_number": "xpro-b2c-dev-1",
                "tax_country_code": "",
                "tax_rate": 0,
                "tax_rate_name": "",
            },
            "receipt": {
                "card_number": "1234",
                "card_type": "Visa",
                "name": "MIT Doof",
                "payment_method": "card",
                "bill_to_email": "doof@mit.edu",
            },
            "purchaser": {
                "name": "Test User",
                "email": "test@example.com",
                "street_address": ["11 Main Street"],
                "state_code": "CO",
                "postal_code": "80309",
                "city": "Boulder",
                "country": "United States",
                "company": user.profile.company,
                "vat_id": "AT12349876",
            },
            "is_tax_applicable": False,
            "support_email": settings.EMAIL_SUPPORT,
        },
    )
    patched_mail_api.messages_for_recipients.assert_called_once_with(
        [("test@example.com", patched_mail_api.context_for_user.return_value)],
        EMAIL_PRODUCT_ORDER_RECEIPT,
    )


@pytest.mark.parametrize("is_program", [True, False])
def test_send_enrollment_failure_message(mocker, is_program):
    """Test that send_enrollment_failure_message sends a message with proper formatting"""
    patched_django_mail = mocker.patch("ecommerce.mail_api.mail")
    product_object = (
        ProgramFactory.create() if is_program else CourseRunFactory.create()
    )
    product_version = ProductVersionFactory.create(
        product=ProductFactory.create(content_object=product_object)
    )
    order = LineFactory.create(product_version=product_version).order
    details = "TestException on line 21"
    expected_message = "{name}({email}): Order #{order_id}, {error_obj} #{obj_id} ({obj_title})\n\n{details}".format(
        name=order.purchaser.username,
        email=order.purchaser.email,
        order_id=order.id,
        error_obj=("Program" if is_program else "Run"),
        obj_id=product_object.id,
        obj_title=product_object.title,
        details=details,
    )

    send_enrollment_failure_message(order, product_object, details)
    patched_django_mail.send_mail.assert_called_once()
    send_mail_args = patched_django_mail.send_mail.call_args[0]
    assert send_mail_args[0] == ENROLL_ERROR_EMAIL_SUBJECT
    assert send_mail_args[1] == expected_message
