"""Views for business to business ecommerce"""

import logging
from urllib.parse import urljoin, urlencode

from django.conf import settings
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from b2b_ecommerce.api import complete_b2b_order, generate_b2b_cybersource_sa_payload
from b2b_ecommerce.models import B2BOrder
from ecommerce.api import make_checkout_url
from ecommerce.models import ProductVersion, Coupon
from ecommerce.serializers import ProductVersionSerializer
from mitxpro.utils import make_csv_http_response


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

        rows = (
            {
                "code": code,
                "url": make_checkout_url(
                    code=code, product_id=order.product_version.product_id
                ),
            }
            for code in Coupon.objects.filter(
                versions__payment_version__b2border=order
            ).values_list("coupon_code", flat=True)
        )

        return make_csv_http_response(
            csv_rows=rows, filename=f"enrollmentcodes-{order_hash}.csv"
        )
