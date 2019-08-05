"""Views for business to business ecommerce"""

import logging
from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from b2b_ecommerce.api import complete_b2b_order, generate_b2b_cybersource_sa_payload
from b2b_ecommerce.models import B2BOrder, B2BReceipt
from ecommerce.constants import CYBERSOURCE_DECISION_ACCEPT, CYBERSOURCE_DECISION_CANCEL
from ecommerce.exceptions import EcommerceException
from ecommerce.models import ProductVersion
from ecommerce.permissions import IsSignedByCyberSource


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
            per_item_price=total_price,
        )

        receipt_url = urljoin(base_url, reverse("bulk-enrollment-code-receipt"))
        if total_price == 0:
            # If price is $0, don't bother going to CyberSource, just mark as fulfilled
            order.status = B2BOrder.FULFILLED
            order.save_and_log(None)

            complete_b2b_order(order)

            # This redirects the user to our order success page
            payload = {}
            url = receipt_url
            method = "GET"
        else:
            # This generates a signed payload which is submitted as an HTML form to CyberSource
            payload = generate_b2b_cybersource_sa_payload(
                order=order, receipt_url=receipt_url, cancel_url=base_url
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
        order = B2BOrder.objects.filter_by_reference_number(reference_number).first()
        receipt.order = order
        receipt.save()

        decision = request.data["decision"]
        if order.status == B2BOrder.FAILED and decision == CYBERSOURCE_DECISION_CANCEL:
            # This is a duplicate message, ignore since it's already handled
            return Response(status=status.HTTP_200_OK)
        elif order.status != B2BOrder.CREATED:
            raise EcommerceException(
                "Order {} is expected to have status 'created'".format(order.id)
            )

        if decision != CYBERSOURCE_DECISION_ACCEPT:
            order.status = B2BOrder.FAILED
            log.warning(
                "Order fulfillment failed: received a decision that wasn't ACCEPT for order %s",
                order,
            )
            if decision != CYBERSOURCE_DECISION_CANCEL:
                # TBD: send an email about the decision?
                pass
        else:
            order.status = B2BOrder.FULFILLED

        if order.status == B2BOrder.FULFILLED:
            complete_b2b_order(order)

        # Save to log everything to an audit table including enrollments created in complete_order
        order.save_and_log(None)

        # The response does not matter to CyberSource
        return Response(status=status.HTTP_200_OK)
