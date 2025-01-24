"""Ecommerce mail API"""

import logging
from urllib.parse import urlencode, urljoin

import pycountry
from django.conf import settings
from django.core import mail
from django.urls import reverse
from mitol.olposthog.features import is_enabled

from courses.models import CourseRun
from ecommerce.constants import BULK_ENROLLMENT_EMAIL_TAG, CYBERSOURCE_CARD_TYPES
from ecommerce.utils import format_run_date, make_checkout_url
from mail import api
from mail.constants import (
    EMAIL_B2B_RECEIPT,
    EMAIL_BULK_ENROLL,
    EMAIL_COURSE_RUN_ENROLLMENT,
    EMAIL_COURSE_RUN_UNENROLLMENT,
    EMAIL_PRODUCT_ORDER_RECEIPT,
    EMAIL_WELCOME_COURSE_RUN_ENROLLMENT,
)
from mitxpro import features
from mitxpro.utils import format_price

log = logging.getLogger()
ENROLL_ERROR_EMAIL_SUBJECT = "MIT xPRO enrollment error"
EMAIL_DATE_FORMAT = "%b %-d, %Y"
EMAIL_TIME_FORMAT = "%I:%M %p %Z"


def get_b2b_receipt_data(order):
    """
    Get receipt information if it exists

    Args:
        Order (object): An order instance.

    Returns:
        A dict of receipt data, in case of Cybersource purchase.
    """
    receipt = order.b2breceipt_set.order_by("-created_on").first()
    receipt_data = {}
    if receipt:
        country = pycountry.countries.get(
            alpha_2=receipt.data.get("req_bill_to_address_country")
        )
        receipt_data = {
            "card_number": receipt.data.get("req_card_number"),
            "card_type": CYBERSOURCE_CARD_TYPES.get(receipt.data.get("req_card_type")),
            "payment_method": receipt.data.get("req_payment_method")
            if "req_payment_method" in receipt.data
            else None,
            "purchaser": {
                "name": " ".join(
                    [
                        receipt.data.get("req_bill_to_forename"),
                        receipt.data.get("req_bill_to_surname"),
                    ]
                ),
                "email": receipt.data.get("req_bill_to_email"),
                "street_address_1": receipt.data.get("req_bill_to_address_line1", ""),
                "street_address_2": receipt.data.get("req_bill_to_address_line2", ""),
                "state": receipt.data.get("req_bill_to_address_state", ""),
                "postal_code": receipt.data.get("req_bill_to_address_postal_code", ""),
                "city": receipt.data.get("req_bill_to_address_city", ""),
                "country": country.name if country else "",
            },
        }

    coupon_redemption = order.b2bcouponredemption_set.first()
    if coupon_redemption:
        receipt_data["coupon_code"] = coupon_redemption.coupon.coupon_code

    return receipt_data


def get_bulk_enroll_message_data(bulk_assignment_id, recipient, product_coupon):
    """
    Builds the tuple of data required for each recipient's bulk enrollment email

    Args:
        bulk_assignment_id (int): The id for the BulkCouponAssignment that this assignment belongs to
        recipient (str): The recipient email address
        product_coupon (CouponEligibility): The product coupon that was assigned to the given recipient

    Returns:
        ecommerce.api.UserMessageProps: An object containing user-specific message data
    """
    product_object = product_coupon.product.content_object
    if product_coupon.program_run:
        email_product_id = product_coupon.program_run.full_readable_id
    else:
        email_product_id = product_object.text_id
    enrollment_url = make_checkout_url(
        product_id=email_product_id, code=product_coupon.coupon.coupon_code
    )
    payment_version_data = (
        product_coupon.coupon.payment.versions.values(
            "company__name", "expiration_date"
        )
        .order_by("-created_on")
        .first()
    )
    company_name = payment_version_data.get("company__name")
    expiration_date = payment_version_data.get("expiration_date")
    context = {
        "enrollable_title": product_object.title,
        "enrollment_url": enrollment_url,
        "company_name": company_name,
        "expiration_date": (
            expiration_date.strftime(EMAIL_DATE_FORMAT) if expiration_date else None
        ),
    }
    return api.UserMessageProps(
        recipient=recipient,
        context=context,
        metadata=api.EmailMetadata(
            tags=[BULK_ENROLLMENT_EMAIL_TAG],
            user_variables={
                "bulk_assignment": bulk_assignment_id,
                "enrollment_code": product_coupon.coupon.coupon_code,
                product_coupon.product.type_string: product_object.text_id,
            },
        ),
    )


def send_bulk_enroll_emails(bulk_assignment_id, product_coupon_assignments):
    """
    Sends an email for recipients to enroll in a courseware offering via coupon

    Args:
        bulk_assignment_id (int): The id for the BulkCouponAssignment that the assignments belong to
        product_coupon_assignments (iterable of ProductCouponAssignments):
            Product coupon assignments about which we want to notify the recipients
    """
    api.send_messages(
        api.build_user_specific_messages(
            EMAIL_BULK_ENROLL,
            (
                get_bulk_enroll_message_data(
                    bulk_assignment_id,
                    product_coupon_assignment.email,
                    product_coupon_assignment.product_coupon,
                )
                for product_coupon_assignment in product_coupon_assignments
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
    except:  # noqa: E722
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
    except Exception as exp:
        log.exception("Error sending unenrollment success email: %s", exp)  # noqa: TRY401


def send_course_run_enrollment_welcome_email(enrollment):
    """
    Send welcome email to the user on successful enrollment

    Args:
        enrollment (CourseRunEnrollment): the enrollment for which to send the welcome email
    """
    if not is_enabled(features.ENROLLMENT_WELCOME_EMAIL, default=False):
        log.info("Feature `enrollment_welcome_email` is disabled.")
        return
    run_start_date, run_start_time = format_run_date(enrollment.run.start_date)
    run_end_date, _ = format_run_date(enrollment.run.end_date)
    run_duration = (
        f"{run_start_date} - {run_end_date}" if run_start_date and run_end_date else ""
    )
    try:
        user = enrollment.user
        api.send_message(
            api.message_for_recipient(
                user.email,
                api.context_for_user(
                    user=user,
                    extra_context={
                        "enrollment": enrollment,
                        "run_start_date": run_start_date,
                        "run_start_time": run_start_time,
                        "run_date_range": run_duration,
                        "support_email": settings.EMAIL_SUPPORT,
                    },
                ),
                EMAIL_WELCOME_COURSE_RUN_ENROLLMENT,
            )
        )
    except:  # noqa: E722
        log.exception("Error sending welcome email")


def send_b2b_receipt_email(order):
    """
    Send an email summarizing the enrollment codes purchased by a user

    Args:
        order (b2b_ecommerce.models.B2BOrder):
            An order
    """
    from ecommerce.api import get_readable_id

    course_run_or_program = order.product_version.product.content_object
    title = course_run_or_program.title

    if (
        isinstance(course_run_or_program, CourseRun)
        and course_run_or_program.start_date is not None
        and course_run_or_program.end_date is not None
    ):
        run = course_run_or_program
        date_range = f"{run.start_date.strftime(EMAIL_DATE_FORMAT)} - {run.end_date.strftime(EMAIL_DATE_FORMAT)}"
    else:
        date_range = ""

    download_url = (
        f"{urljoin(settings.SITE_BASE_URL, reverse('bulk-enrollment-code-receipt'))}?"
        f"{urlencode({'hash': str(order.unique_id)})}"
    )
    try:
        api.send_message(
            api.message_for_recipient(
                order.email,
                api.context_for_user(
                    user=None,
                    extra_context={
                        "purchase_date": order.updated_on.strftime(EMAIL_DATE_FORMAT),
                        "total_price": format_price(order.total_price),
                        "item_price": format_price(order.per_item_price),
                        "discount": format_price(order.discount)
                        if order.discount is not None
                        else None,
                        "contract_number": order.contract_number,
                        "num_seats": str(order.num_seats),
                        "readable_id": get_readable_id(
                            order.product_version.product.content_object
                        ),
                        "run_date_range": date_range,
                        "title": title,
                        "download_url": download_url,
                        "email": order.email,
                        "order_reference_id": order.reference_number,
                        "receipt_data": get_b2b_receipt_data(order),
                    },
                ),
                EMAIL_B2B_RECEIPT,
            )
        )
    except:  # noqa: E722
        log.exception("Error sending receipt email")


def send_ecommerce_order_receipt(order, cyber_source_provided_email=None):
    """
    Send emails receipt summarizing the user purchase detail.

    Args:
        cyber_source_provided_email: Include the email address if user provide though CyberSource payment process.
        order: An order.
    """
    from ecommerce.serializers import OrderReceiptSerializer

    data = OrderReceiptSerializer(instance=order).data
    purchaser = data.get("purchaser")
    coupon = data.get("coupon")
    lines = data.get("lines")
    order = data.get("order")
    receipt = data.get("receipt")
    country = pycountry.countries.get(alpha_2=purchaser.get("country"))
    recipients = [purchaser.get("email")]
    if cyber_source_provided_email and cyber_source_provided_email not in recipients:
        recipients.append(cyber_source_provided_email)

    try:
        messages = list(
            api.messages_for_recipients(
                [
                    (
                        recipient,
                        api.context_for_user(
                            user=None,
                            extra_context={
                                "coupon": coupon,
                                "content_title": lines[0].get("content_title")
                                if lines
                                else None,
                                "lines": lines,
                                "order_total": format(
                                    sum(float(line["total_paid"]) for line in lines),
                                    ".2f",
                                ),
                                "order_total_tax": format(
                                    sum(float(line["total_paid"]) for line in lines)
                                    + (
                                        sum(float(line["total_paid"]) for line in lines)
                                        * float(order["tax_rate"] / 100)
                                    ),
                                    ".2f",
                                ),
                                "order": order,
                                "receipt": receipt,
                                "purchaser": {
                                    "name": " ".join(
                                        [
                                            purchaser.get("first_name"),
                                            purchaser.get("last_name"),
                                        ]
                                    ),
                                    "email": purchaser.get("email"),
                                    "street_address": purchaser.get("street_address"),
                                    "state_code": purchaser.get(
                                        "state_or_territory"
                                    ).split("-")[-1],
                                    "postal_code": purchaser.get("postal_code"),
                                    "city": purchaser.get("city"),
                                    "country": country.name if country else None,
                                    "company": purchaser.get("company"),
                                    "vat_id": purchaser.get("vat_id"),
                                },
                                "is_tax_applicable": bool(order["tax_rate"]),
                                "support_email": settings.EMAIL_SUPPORT,
                            },
                        ),
                    )
                    for recipient in recipients
                ],
                EMAIL_PRODUCT_ORDER_RECEIPT,
            )
        )
        api.send_messages(messages)

    except:  # noqa: E722
        log.exception("Error sending order receipt email.")


def send_support_email(subject, message):
    """
    Send an email to support.

    Args:
        subject (str): The email subject.
        message (str): The email message.
    """
    try:
        with mail.get_connection(settings.NOTIFICATION_EMAIL_BACKEND) as connection:
            mail.send_mail(
                subject,
                message,
                settings.ADMIN_EMAIL,
                [settings.EMAIL_SUPPORT],
                connection=connection,
            )
    except:  # noqa: E722
        log.exception("Exception sending email to admins")


def send_enrollment_failure_message(order, obj, details):
    """
    Args:
        order (Order): the order with a failed enrollment
        obj (Program or CourseRun): the object that failed enrollment
        details (str): Details of the error (typically a stack trace)

    Returns:
        str: The formatted error message
    """
    message = "{name}({email}): Order #{order_id}, {error_obj} #{obj_id} ({obj_title})\n\n{details}".format(
        name=order.purchaser.username,
        email=order.purchaser.email,
        order_id=order.id,
        error_obj=("Run" if isinstance(obj, CourseRun) else "Program"),
        obj_id=obj.id,
        obj_title=obj.title,
        details=details,
    )
    send_support_email(ENROLL_ERROR_EMAIL_SUBJECT, message)
