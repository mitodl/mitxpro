"""Views for ecommerce"""
import logging

from django.conf import settings
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView

from ecommerce.api import (
    create_unfulfilled_order,
    enroll_user_on_success,
    generate_cybersource_sa_payload,
    get_new_order_by_reference_number,
    get_product_version_price_with_discount,
)
from ecommerce.constants import CYBERSOURCE_DECISION_ACCEPT, CYBERSOURCE_DECISION_CANCEL
from ecommerce.exceptions import EcommerceException
from ecommerce.models import Order, Receipt
from ecommerce.permissions import IsSignedByCyberSource


log = logging.getLogger(__name__)


class CheckoutView(APIView):
    """
    View for checkout API. This creates an Order in our system and provides a dictionary to
    send to Cybersource
    """

    authentication_classes = (SessionAuthentication, TokenAuthentication)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Create a new unfulfilled Order from the user's basket
        and return information used to submit to CyberSource.
        """

        base_url = request.build_absolute_uri("/")
        order = create_unfulfilled_order(request.user)
        coupon_redemption = order.couponredemption_set.first()
        coupon_version = coupon_redemption.coupon_version if coupon_redemption else None
        total_price = sum(
            get_product_version_price_with_discount(
                coupon_version=coupon_version, product_version=line.product_version
            )
            for line in order.lines.all()
        )

        if total_price == 0:
            # If price is $0, don't bother going to CyberSource, just mark as fulfilled
            order.status = Order.FULFILLED
            order.save_and_log(request.user)

            try:
                enroll_user_on_success(order)
            except:  # pylint: disable=bare-except
                log.exception(
                    "Error occurred when enrolling user in one or more courses for order %s. "
                    "See other errors above for more info.",
                    order,
                )
                # TBD: in micromasters we send email in this case. Do we need to here too?

            # This redirects the user to our order success page
            payload = {}
            url = base_url
            method = "GET"
        else:
            # This generates a signed payload which is submitted as an HTML form to CyberSource
            payload = generate_cybersource_sa_payload(order, base_url)
            url = settings.CYBERSOURCE_SECURE_ACCEPTANCE_URL
            method = "POST"

        return Response({"payload": payload, "url": url, "method": method})


class OrderFulfillmentView(APIView):
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
        receipt = Receipt.objects.create(data=request.data)

        # Link the order with the receipt if we can parse it
        reference_number = request.data["req_reference_number"]
        order = get_new_order_by_reference_number(reference_number)
        receipt.order = order
        receipt.save()

        decision = request.data["decision"]
        if order.status == Order.FAILED and decision == CYBERSOURCE_DECISION_CANCEL:
            # This is a duplicate message, ignore since it's already handled
            return Response(status=HTTP_200_OK)
        elif order.status != Order.CREATED:
            raise EcommerceException(
                "Order {} is expected to have status 'created'".format(order.id)
            )

        if decision != CYBERSOURCE_DECISION_ACCEPT:
            order.status = Order.FAILED
            log.warning(
                "Order fulfillment failed: received a decision that wasn't ACCEPT for order %s",
                order,
            )
            if decision != CYBERSOURCE_DECISION_CANCEL:
                # TBD: send an email about the decision?
                pass
        else:
            order.status = Order.FULFILLED
        order.save_and_log(None)

        if order.status == Order.FULFILLED:
            try:
                enroll_user_on_success(order)
            except:  # pylint: disable=bare-except
                log.exception(
                    "Error occurred when enrolling user in one or more courses for order %s. "
                    "See other errors above for more info.",
                    order,
                )
                # TBD: send an email for the error?
        # The response does not matter to CyberSource
        return Response(status=HTTP_200_OK)
