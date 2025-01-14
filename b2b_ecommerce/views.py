"""Views for business to business ecommerce"""

import logging
from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http.response import Http404
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from b2b_ecommerce.api import (
    complete_b2b_order,
    determine_price_and_discount,
    generate_b2b_cybersource_sa_payload,
)
from b2b_ecommerce.models import B2BCoupon, B2BCouponRedemption, B2BOrder, B2BReceipt
from courses.models import ProgramRun
from ecommerce.api import get_product_from_text_id
from ecommerce.constants import CYBERSOURCE_CARD_TYPES
from ecommerce.models import Coupon, ProductVersion
from ecommerce.serializers import FullProductVersionSerializer
from ecommerce.utils import make_checkout_url
from hubspot_xpro.task_helpers import sync_hubspot_b2b_deal
from mitxpro.utils import make_csv_http_response
from users.models import User

log = logging.getLogger(__name__)


class B2BCheckoutView(APIView):
    """
    View for checkout API. This creates an Order in our system and provides a dictionary to
    send to Cybersource
    """

    authentication_classes = ()
    permission_classes = ()

    def post(
        self,
        request,
        *args,  # noqa: ARG002
        **kwargs,  # noqa: ARG002
    ):
        """
        Create a new unfulfilled Order from the user's basket
        and return information used to submit to CyberSource.
        """
        try:
            num_seats = request.data["num_seats"]
            email = request.data["email"]
            product_version_id = request.data["product_version_id"]
            discount_code = request.data["discount_code"]
            contract_number = request.data.get("contract_number")
            run_id = request.data.get("run_id")
        except KeyError as ex:
            raise ValidationError(f"Missing parameter {ex.args[0]}")  # noqa: B904, EM102

        try:
            validate_email(email)
        except DjangoValidationError:
            raise ValidationError({"email": "Invalid email"})  # noqa: B904

        try:
            num_seats = int(num_seats)
        except ValueError:
            raise ValidationError({"num_seats": "num_seats must be a number"})  # noqa: B904

        if (
            contract_number
            and B2BOrder.objects.filter(
                contract_number__iexact=contract_number, status=B2BOrder.FULFILLED
            ).exists()
        ):
            raise ValidationError(
                {"contract_number": "This contract number has already been used"}
            )

        with transaction.atomic():
            product_version = get_object_or_404(ProductVersion, id=product_version_id)
            total_price, coupon, discount = determine_price_and_discount(
                product_version=product_version,
                discount_code=discount_code,
                num_seats=num_seats,
            )
            program_run = (
                None if not run_id else ProgramRun.objects.filter(pk=run_id).first()
            )

            order = B2BOrder.objects.create(
                num_seats=num_seats,
                email=email,
                product_version=product_version,
                total_price=total_price,
                per_item_price=product_version.price,
                discount=discount,
                coupon=coupon,
                contract_number=contract_number,
                program_run=program_run,
            )
            order.save_and_log(None)
            if coupon:
                B2BCouponRedemption.objects.create(coupon=coupon, order=order)

        base_url = request.build_absolute_uri("/")
        receipt_url = (
            f"{urljoin(base_url, reverse('bulk-enrollment-code-receipt'))}?"
            f"{urlencode({'hash': str(order.unique_id)})}"
        )
        cancel_url = urljoin(base_url, reverse("bulk-enrollment-code"))
        if total_price == 0:
            # If price is $0, don't bother going to CyberSource, just mark as fulfilled
            order.status = B2BOrder.FULFILLED
            order.save()

            complete_b2b_order(order)
            order.save_and_log(None)

            # This redirects the user to our order success page
            payload = {}
            url = receipt_url
            method = "GET"
        else:
            # This generates a signed payload which is submitted as an HTML form to CyberSource
            payload = generate_b2b_cybersource_sa_payload(
                order=order, receipt_url=receipt_url, cancel_url=cancel_url
            )
            url = settings.CYBERSOURCE_SECURE_ACCEPTANCE_URL
            method = "POST"
        if order:
            sync_hubspot_b2b_deal(order)
        return Response({"payload": payload, "url": url, "method": method})


class B2BOrderStatusView(APIView):
    """
    View to retrieve information about an order to display the receipt.
    """

    authentication_classes = ()
    permission_classes = ()

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        """Return B2B order status and other information about the order needed to display the receipt"""
        order_hash = kwargs["hash"]
        order = get_object_or_404(B2BOrder, unique_id=order_hash)

        receipt = B2BReceipt.objects.filter(order=order).order_by("-created_on").first()
        receipt_data = {"card_number": None, "card_type": None}
        customer = User.objects.filter(email=order.email).first()
        customer_name = ""
        if customer:
            customer_name = customer.name
        if receipt:
            receipt_data["card_number"] = receipt.data.get("req_card_number")
            receipt_data["card_type"] = CYBERSOURCE_CARD_TYPES.get(
                receipt.data.get("req_card_type")
            )
            if not customer_name:
                customer_name = (
                    receipt.data.get("req_bill_to_forename")
                    + " "
                    + receipt.data.get("req_bill_to_surname")
                )

        return Response(
            data={
                "status": order.status,
                "num_seats": order.num_seats,
                "total_price": str(order.total_price),
                "item_price": str(order.per_item_price),
                "discount": str(order.discount) if order.discount is not None else None,
                "product_version": FullProductVersionSerializer(
                    order.product_version, context={"all_runs": True}
                ).data,
                "email": order.email,
                "customer_name": customer_name.strip(),
                "contract_number": order.contract_number,
                "created_on": order.created_on,
                "reference_number": order.reference_number,
                "coupon_code": order.coupon.coupon_code if order.coupon else None,
                "receipt_data": receipt_data,
            }
        )


class B2BEnrollmentCodesView(APIView):
    """
    View to export a CSV of coupon codes for download
    """

    authentication_classes = ()
    permission_classes = ()

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        """Create a CSV with enrollment codes"""
        order_hash = kwargs["hash"]
        order = get_object_or_404(
            B2BOrder.objects.select_related("program_run"), unique_id=order_hash
        )

        rows = (
            {
                "url": make_checkout_url(
                    code=code,
                    product_id=order.product_version.text_id,
                    run_tag=order.program_run.run_tag if order.program_run else None,
                )
            }
            for code in Coupon.objects.filter(
                versions__payment_version__b2border=order
            ).values_list("coupon_code", flat=True)
        )

        instructions = [
            "Distribute the links below to each of your learners. Additional instructions are available at:",
            '=HYPERLINK("https://xpro.zendesk.com/hc/en-us/articles/360048166292-How-to-I-distribute-my-enrollment-codes-that-I-purchased-in-a-bulk-order-")',
        ]

        return make_csv_http_response(
            csv_rows=rows,
            filename=f"enrollmentcodes-{order_hash}.csv",
            instructions=instructions,
        )


class B2BCouponView(APIView):
    """
    View to show information about whether a coupon code would work with an order, and what discount it would provide.
    """

    authentication_classes = ()
    permission_classes = ()

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        """Get information about a coupon"""
        product = None
        try:
            coupon_code = request.GET["code"]
            product_id = request.GET["product_id"]
        except KeyError as ex:
            raise ValidationError(f"Missing parameter {ex.args[0]}")  # noqa: B904, EM102

        try:
            # product_id can be an integer e.g. 1234 or
            # a string in form of text_id e.g. program-v1:xPRO+SysEngx.
            product_id = int(product_id)
        except ValueError:
            product, _, _ = get_product_from_text_id(text_id=product_id)
        if product:
            product_id = product.id

        try:
            coupon = B2BCoupon.objects.get_unexpired_coupon(
                coupon_code=coupon_code, product_id=product_id
            )
        except B2BCoupon.DoesNotExist:
            raise Http404  # noqa: B904

        return Response(
            data={
                "code": coupon_code,
                "product_id": product_id,
                "discount_percent": str(coupon.discount_percent),
            }
        )
