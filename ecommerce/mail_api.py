"""Ecommerce mail API"""
import logging
from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.urls import reverse

from courses.models import CourseRun
from mail import api
from mail.constants import (
    EMAIL_B2B_RECEIPT,
    EMAIL_BULK_ENROLL,
    EMAIL_COURSE_RUN_ENROLLMENT,
    EMAIL_COURSE_RUN_UNENROLLMENT,
)
from mitxpro.utils import format_price

log = logging.getLogger()


def get_bulk_enroll_email_context(product_coupon):
    """Gets the bulk enrollment email template context for one CouponEligibility object"""
    from ecommerce.api import make_checkout_url

    enrollment_url = make_checkout_url(
        product_id=product_coupon.product.id, code=product_coupon.coupon.coupon_code
    )
    company_name = (
        product_coupon.coupon.payment.versions.values_list("company__name", flat=True)
        .order_by("-created_on")
        .first()
    )
    return {
        "enrollable_title": product_coupon.product.content_object.title,
        "enrollment_url": enrollment_url,
        "company_name": company_name,
    }


def send_bulk_enroll_emails(recipient_product_coupon_iter):
    """
    Sends an email for recipients to enroll in a courseware offering via coupon

    Args:
        recipient_product_coupon_iter (iterable of (str, CouponEligibility)): An iterable of tuples, where each one
            is an email paired with the product coupon assigned to that email.
    """
    api.send_messages(
        api.build_user_specific_messages(
            EMAIL_BULK_ENROLL,
            (
                (recipient, get_bulk_enroll_email_context(product_coupon))
                for recipient, product_coupon in recipient_product_coupon_iter
            ),
        )
    )


def send_course_run_enrollment_email(enrollment):
    """
    Notify the user of successful enrollment for a course run

    Args:
        enrollment (CourseRunEnrollment): the enrollment for which to send the email
    """
    try:
        user = enrollment.user
        api.send_message(
            api.message_for_recipient(
                user.email,
                api.context_for_user(
                    user=user, extra_context={"enrollment": enrollment}
                ),
                EMAIL_COURSE_RUN_ENROLLMENT,
            )
        )
    except:  # pylint: disable=bare-except
        log.exception("Error sending enrollment success email")


def send_course_run_unenrollment_email(enrollment):
    """
    Notify the user of successful unenrollment for a course run

    Args:
        enrollment (CourseRunEnrollment): the enrollment for which to send the email
    """
    try:
        user = enrollment.user
        api.send_message(
            api.message_for_recipient(
                user.email,
                api.context_for_user(
                    user=user, extra_context={"enrollment": enrollment}
                ),
                EMAIL_COURSE_RUN_UNENROLLMENT,
            )
        )
    except Exception as exp:  # pylint: disable=broad-except
        log.exception("Error sending unenrollment success email: %s", exp)


def send_b2b_receipt_email(order):
    """
    Send an email summarizing the enrollment codes purchased by a user

    Args:
        order (b2b_ecommerce.models.B2BOrder):
            An order
    """
    from ecommerce.api import get_readable_id

    format_string = "%b %-d, %Y"

    course_run_or_program = order.product_version.product.content_object
    title = course_run_or_program.title

    if (
        isinstance(course_run_or_program, CourseRun)
        and course_run_or_program.start_date is not None
        and course_run_or_program.end_date is not None
    ):
        run = course_run_or_program
        date_range = f"{run.start_date.strftime(format_string)} - {run.end_date.strftime(format_string)}"
    else:
        date_range = ""

    download_url = (
        f'{urljoin(settings.SITE_BASE_URL, reverse("bulk-enrollment-code-receipt"))}?'
        f'{urlencode({"hash": str(order.unique_id)})}'
    )
    try:
        api.send_message(
            api.message_for_recipient(
                order.email,
                api.context_for_user(
                    user=None,
                    extra_context={
                        "purchase_date": order.updated_on.strftime(format_string),
                        "total_price": format_price(order.total_price),
                        "item_price": format_price(order.per_item_price),
                        "discount": format_price(order.discount)
                        if order.discount is not None
                        else None,
                        "num_seats": str(order.num_seats),
                        "readable_id": get_readable_id(
                            order.product_version.product.content_object
                        ),
                        "run_date_range": date_range,
                        "title": title,
                        "download_url": download_url,
                        "email": order.email,
                        "order_reference_id": order.reference_number,
                    },
                ),
                EMAIL_B2B_RECEIPT,
            )
        )
    except:  # pylint: disable=bare-except
        log.exception("Error sending receipt email")
