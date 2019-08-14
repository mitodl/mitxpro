"""Views for business to business ecommerce"""

import csv
import logging
from urllib.parse import urljoin, urlencode

from django.conf import settings
from django.http.response import HttpResponse
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from b2b_ecommerce.api import complete_b2b_order, generate_b2b_cybersource_sa_payload
from b2b_ecommerce.models import B2BOrder, B2BReceipt
from ecommerce.api import determine_order_status_change
from ecommerce.models import ProductVersion, Coupon
from ecommerce.permissions import IsSignedByCyberSource
from ecommerce.serializers import ProductVersionSerializer


log = logging.getLogger(__name__)


class B2BCheckoutView(APIView):
    """
    View for checkout API. This creates an Order in our system and provides a dictionary to
    send to Cybersource
    """

    authentication_classes = ()
    permission_classes = ()

    def post(self, request, *args, **kwargs):  # pylint: disable=too-many-locals
        """
        Create a new unfulfilled Order from the user's basket
        and return information used to submit to CyberSource.
        """
        try:
            num_seats = request.data["num_seats"]
            email = request.data["email"]
            product_version_id = request.data["product_version_id"]
        except KeyError as ex:
            raise ValidationError(f"Missing parameter {ex.args[0]}")

        try:
            num_seats = int(num_seats)
        except ValueError:
            raise ValidationError("num_seats must be a number")

        product_version = get_object_or_404(ProductVersion, id=product_version_id)
        total_price = product_version.price * num_seats

        base_url = request.build_absolute_uri("/")
        order = B2BOrder.objects.create(
            num_seats=num_seats,
            email=email,
            product_version=product_version,
            total_price=total_price,
            per_item_price=product_version.price,
        )

        receipt_url = (
            f'{urljoin(base_url, reverse("bulk-enrollment-code-receipt"))}?'
            f'{urlencode({"hash": str(order.unique_id)})}'
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

        return Response({"payload": payload, "url": url, "method": method})


class B2BOrderFulfillmentView(APIView):
    """
    View for order fulfillment API. This API is special in that only CyberSource should talk to it.
    Instead of authenticating with OAuth or via session this looks at the signature of the message
    to verify authenticity.
    """

    authentication_classes = ()
    permission_classes = (IsSignedByCyberSource,)

    def post(self, request, *args, **kwargs):
        """
        Confirmation from CyberSource which fulfills an existing Order.
        """
        # First, save this information in a receipt
        receipt = B2BReceipt.objects.create(data=request.data)

        # Link the order with the receipt if we can parse it
        reference_number = request.data["req_reference_number"]
        order = B2BOrder.objects.get_by_reference_number(reference_number)
        receipt.order = order
        receipt.save()

        new_order_status = determine_order_status_change(
            order, request.data["decision"]
        )
        if new_order_status is None:
            # This is a duplicate message, ignore since it's already handled
            return Response(status=status.HTTP_200_OK)

        order.status = new_order_status
        if new_order_status == B2BOrder.FULFILLED:
            complete_b2b_order(order)

        # Save to log everything to an audit table including enrollments created in complete_order
        order.save_and_log(None)

        # The response does not matter to CyberSource
        return Response(status=status.HTTP_200_OK)


class B2BOrderStatusView(APIView):
    """
    View to retrieve information about an order to display the receipt.
    """

    authentication_classes = ()
    permission_classes = ()

    def get(self, request, *args, **kwargs):
        """Return B2B order status and other information about the order needed to display the receipt"""
        order_hash = kwargs["hash"]
        order = get_object_or_404(B2BOrder, unique_id=order_hash)

        return Response(
            data={
                "status": order.status,
                "num_seats": order.num_seats,
                "total_price": str(order.total_price),
                "item_price": str(order.per_item_price),
                "product_version": ProductVersionSerializer(
                    order.product_version, context={"all_runs": True}
                ).data,
                "email": order.email,
            }
        )


class B2BEnrollmentCodesView(APIView):
    """
    View to export a CSV of coupon codes for download
    """

    authentication_classes = ()
    permission_classes = ()

    def get(self, request, *args, **kwargs):
        """Create a CSV with enrollment codes"""
        order_hash = kwargs["hash"]
        order = get_object_or_404(B2BOrder, unique_id=order_hash)

        response = HttpResponse(content_type="text/csv")
        response[
            "Content-Disposition"
        ] = f'attachment; filename="enrollmentcodes-{order_hash}.csv"'

        writer = csv.writer(response)

        for code in Coupon.objects.filter(
            versions__payment_version__b2border=order
        ).values_list("coupon_code", flat=True):
            writer.writerow([code])

        return response
