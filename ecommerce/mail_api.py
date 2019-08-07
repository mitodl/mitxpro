"""Ecommerce mail API"""
from urllib.parse import urljoin, urlencode
import itertools
import logging

from django.conf import settings
from django.urls import reverse

from mail import api
from mail.constants import (
    EMAIL_BULK_ENROLL,
    EMAIL_COURSE_RUN_ENROLLMENT,
    EMAIL_COURSE_RUN_UNENROLLMENT,
)
from ecommerce.models import ProductCouponAssignment

log = logging.getLogger()


def get_bulk_enroll_email_context(product_coupon):
    """Gets the bulk enrollment email template context for one CouponEligibility object"""
    enrollment_url = "?".join(
        [
            urljoin(settings.SITE_BASE_URL, reverse("checkout-page")),
            urlencode(
                {
                    "product": product_coupon.product.id,
                    "code": product_coupon.coupon.coupon_code,
                }
            ),
        ]
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


def send_bulk_enroll_emails(recipients, product_coupon_iter):
    """
    Sends an email for recipients to enroll in a courseware offering via coupon

    Args:
        recipients (iterable of str): An iterable of user email addresses
        product_coupon_iter (iterable of CouponEligibility): An iterable of product coupons that will be given
            one-by-one to the given recipients

    Returns:
        list of ProductCouponAssignment: Created ProductCouponAssignment objects that represent a bulk enrollment email
            sent to a recipient
    """
    # We will loop over pairs of recipients and product coupons twice, so create 2 generators
    recipient_product_coupon_iter1, recipient_product_coupon_iter2 = itertools.tee(
        zip(recipients, product_coupon_iter)
    )

    api.send_messages(
        api.build_user_specific_messages(
            EMAIL_BULK_ENROLL,
            (
                (recipient, get_bulk_enroll_email_context(product_coupon))
                for recipient, product_coupon in recipient_product_coupon_iter1
            ),
        )
    )
    return [
        ProductCouponAssignment.objects.create(
            email=recipient, product_coupon=product_coupon
        )
        for recipient, product_coupon in recipient_product_coupon_iter2
    ]


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
