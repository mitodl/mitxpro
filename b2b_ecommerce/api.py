"""Functions for b2b_ecommerce"""
from decimal import Decimal
import uuid

from django.conf import settings
from django.db import transaction
from rest_framework.validators import ValidationError

from b2b_ecommerce.models import B2BCoupon, B2BOrder, B2BReceipt
from ecommerce.api import (
    create_coupons,
    determine_order_status_change,
    ISO_8601_FORMAT,
    sign_cybersource_payload,
)
from ecommerce.mail_api import send_b2b_receipt_email
from ecommerce.models import CouponPaymentVersion
from hubspot.task_helpers import sync_hubspot_b2b_deal
from mitxpro.utils import now_in_utc


def complete_b2b_order(order):
    """
    Create the enrollment codes which were paid for and link them to the purchaser.

    Args:
        order (B2BOrder): A fulfilled order for enrollment codes
    """

    if order.coupon and order.contract_number:
        name = f"order_{order.id} {order.contract_number} {order.coupon.coupon_code}"
    elif order.contract_number:
        name = order.contract_number
    elif order.coupon:
        name = order.coupon.coupon_code
    else:
        name = f"CouponPayment for order #{order.id}"

    with transaction.atomic():
        product_id = order.product_version.product.id
        payment_version = create_coupons(
            name=name,
            product_ids=[product_id],
            amount=Decimal("1"),
            num_coupon_codes=order.num_seats,
            coupon_type=CouponPaymentVersion.SINGLE_USE,
            payment_type=CouponPaymentVersion.PAYMENT_SALE,
            payment_transaction=order.contract_number or order.reference_number,
        )
        order.coupon_payment_version = payment_version
        order.save()

    send_b2b_receipt_email(order)


def _generate_b2b_cybersource_sa_payload(*, order, receipt_url, cancel_url):
    """
    Generates a payload dict to send to CyberSource for Secure Acceptance for a B2BOrder
    Args:
        order (B2BOrder): An order for purchasing enrollment codes
        receipt_url (str): The URL to be used by Cybersource to redirect the user after completion of the purchase
        cancel_url (str): The URL to be used by Cybersource to redirect the user after they click cancel
    Returns:
        dict: the payload to send to CyberSource via Secure Acceptance
    """
    # http://apps.cybersource.com/library/documentation/dev_guides/Secure_Acceptance_WM/Secure_Acceptance_WM.pdf
    # Section: API Fields

    # NOTE: be careful about max length here, many (all?) string fields have a max
    # length of 255. At the moment none of these fields should go over that, due to database
    # constraints or other reasons

    product_version = order.product_version
    content_object = product_version.product.content_object
    content_type = str(product_version.product.content_type)
    price = order.total_price

    return {
        "access_key": settings.CYBERSOURCE_ACCESS_KEY,
        "amount": str(price),
        "currency": "USD",
        "locale": "en-us",
        "item_0_code": "enrollment_code",
        "item_0_name": f"Enrollment codes for {product_version.description}"[:254],
        "item_0_quantity": order.num_seats,
        "item_0_sku": f"enrollment_code-{content_type}-{content_object.id}"[:254],
        "item_0_tax_amount": "0",
        "item_0_unit_price": str(price),
        "line_item_count": 1,
        "reference_number": order.reference_number,
        "profile_id": settings.CYBERSOURCE_PROFILE_ID,
        "signed_date_time": now_in_utc().strftime(ISO_8601_FORMAT),
        "override_custom_receipt_page": receipt_url,
        "override_custom_cancel_page": cancel_url,
        "transaction_type": "sale",
        "transaction_uuid": uuid.uuid4().hex,
        "unsigned_field_names": "",
        "merchant_defined_data1": order.contract_number or "",
    }


def generate_b2b_cybersource_sa_payload(*, order, receipt_url, cancel_url):
    """
    Generates a payload dict to send to CyberSource for Secure Acceptance for a B2BOrder
    Args:
        order (B2BOrder): An order for purchasing enrollment codes
        receipt_url (str): The URL to be used by Cybersource to redirect the user after completion of the purchase
        cancel_url (str): The URL to be used by Cybersource to redirect the user after they click cancel
    Returns:
        dict: the payload to send to CyberSource via Secure Acceptance
    """
    return sign_cybersource_payload(
        _generate_b2b_cybersource_sa_payload(
            order=order, receipt_url=receipt_url, cancel_url=cancel_url
        )
    )


def fulfill_b2b_order(request_data):
    """
    Fulfill an order for enrollment code purchase by B2B entities.

    Args:
        request_data (dict): Request data from CyberSource
    """
    # First, save this information in a receipt
    receipt = B2BReceipt.objects.create(data=request_data)

    # Link the order with the receipt if we can parse it
    reference_number = request_data["req_reference_number"]
    order = B2BOrder.objects.get_by_reference_number(reference_number)
    receipt.order = order
    receipt.save()

    new_order_status = determine_order_status_change(order, request_data["decision"])
    if new_order_status is None:
        # This is a duplicate message, ignore since it's already handled
        return

    order.status = new_order_status
    if new_order_status == B2BOrder.FULFILLED:
        complete_b2b_order(order)

    # Save to log everything to an audit table including enrollments created in complete_order
    order.save_and_log(None)

    sync_hubspot_b2b_deal(order)


def determine_price_and_discount(*, product_version, discount_code, num_seats):
    """
    Calculate the total price and discount given the product and a code

    Args:
        product_version (ProductVersion): The product
        discount_code (str): The discount code
        num_seats (int): The number of seats to be purchased

    Returns:
        tuple: total_price, coupon, discount
    """
    if discount_code:
        try:
            coupon = B2BCoupon.objects.get_unexpired_coupon(
                coupon_code=discount_code, product_id=product_version.product.id
            )
        except B2BCoupon.DoesNotExist as exc:
            raise ValidationError("Invalid coupon code") from exc
    else:
        coupon = None

    total_price = product_version.price * num_seats
    if coupon:
        discount = round(coupon.discount_percent * total_price, 2)
        total_price -= discount
    else:
        discount = None

    return total_price, coupon, discount
