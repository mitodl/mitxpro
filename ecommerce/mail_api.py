"""Ecommerce mail API"""
from urllib.parse import urljoin, urlencode
import itertools

from django.conf import settings
from django.urls import reverse

from mail import api
from mail.constants import EMAIL_BULK_ENROLL
from ecommerce.models import BulkEnrollmentDelivery


def get_bulk_enroll_email_context(product_coupon):
    """Gets the bulk enrollment email template context for one CouponEligibility object"""
    enrollment_url = "?".join(
        [
            urljoin(settings.SITE_BASE_URL, reverse("anon-enrollment")),
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
        list of BulkEnrollmentDelivery: Created BulkEnrollmentDelivery objects that represent a bulk enrollment email
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
        BulkEnrollmentDelivery.objects.create(
            email=recipient, product_coupon=product_coupon
        )
        for recipient, product_coupon in recipient_product_coupon_iter2
    ]
