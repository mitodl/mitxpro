"""Views for ecommerce"""
import csv
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ecommerce.api import (
    create_unfulfilled_order,
    enroll_user_on_success,
    generate_cybersource_sa_payload,
    get_new_order_by_reference_number,
    get_product_version_price_with_discount,
    best_coupon_for_product,
    get_valid_coupon_versions,
    latest_product_version,
    latest_coupon_version,
)
from ecommerce.constants import CYBERSOURCE_DECISION_ACCEPT, CYBERSOURCE_DECISION_CANCEL
from ecommerce.exceptions import EcommerceException
from ecommerce.models import (
    Basket,
    CouponSelection,
    ProductVersion,
    Order,
    Receipt,
    CouponPaymentVersion,
    Product,
)
from ecommerce.permissions import IsSignedByCyberSource
from ecommerce.serializers import (
    BasketSerializer,
    SingleUseCouponSerializer,
    PromoCouponSerializer,
    ProductSerializer,
    CouponPaymentVersionSerializer,
)

log = logging.getLogger(__name__)


class ProductViewSet(ModelViewSet):
    """API view set for Products"""

    serializer_class = ProductSerializer
    queryset = Product.objects.all()


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


class BasketView(APIView):
    """ API view for viewing and updating a basket """

    permission_classes = (IsAuthenticated,)
    authentication_classes = (SessionAuthentication,)

    def get(self, request, *args, **kwargs):
        """ View a basket """
        basket, _ = Basket.objects.get_or_create(user=request.user)
        return Response(
            status=status.HTTP_200_OK, data=BasketSerializer(instance=basket).data
        )

    def patch(self, request, *args, **kwargs):
        """ Update a basket """
        basket, _ = Basket.objects.get_or_create(user=request.user)
        items = request.data.get("items")
        coupons = request.data.get("coupons")

        if items is not None or coupons is not None:
            try:
                product_version = _update_items(basket, items)
                coupon_version = _update_coupons(basket, product_version, coupons)
                if product_version:
                    # Update basket items and coupon selection
                    with transaction.atomic():
                        if items is not None:
                            basket_item = basket.basketitems.first()
                            basket_item.product = product_version.product
                            basket_item.save()
                        if coupon_version:
                            CouponSelection.objects.update_or_create(
                                basket=basket,
                                defaults={"coupon": coupon_version.coupon},
                            )
                        else:
                            basket.couponselection_set.all().delete()
                else:
                    # Remove everything from basket
                    with transaction.atomic():
                        basket.basketitems.all().delete()
                        basket.couponselection_set.all().delete()
                return Response(
                    status=status.HTTP_200_OK,
                    data=BasketSerializer(instance=basket).data,
                )
            except ValidationError as be:
                error = be.detail
        else:
            error = "Invalid request"
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data=dict(BasketSerializer(instance=basket).data, **{"errors": error}),
        )


class CouponView(APIView):
    """
    Admin view for creating coupon(s)
    """

    permission_classes = (IsAdminUser,)
    authentication_classes = (SessionAuthentication,)

    def post(self, request, *args, **kwargs):
        """ Create coupon(s) and related objects """
        # Determine what kind of coupon this is.
        if request.data.get("coupon_type") == CouponPaymentVersion.SINGLE_USE:
            coupon_serializer = SingleUseCouponSerializer(data=request.data)
        else:
            coupon_serializer = PromoCouponSerializer(data=request.data)
        if coupon_serializer.is_valid():
            payment_version = coupon_serializer.save()
            return Response(
                status=status.HTTP_200_OK,
                data=CouponPaymentVersionSerializer(instance=payment_version).data,
            )
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={
                "errors": [
                    {key: str(error[0])}
                    for (key, error) in coupon_serializer.errors.items()
                ]
            },
        )


def _update_items(basket, items):
    """
    Helper function to determine if the basket item should be updated, removed, or kept as is.

    Args:
        basket (Basket): the basket to update
        items (list of JSON objects): Basket items to update, or clear if empty list, or leave as is if None

    Returns:
        ProductVersion: ProductVersion object to assign to basket, if any.

    """
    if items:
        if len(items) > 1:
            raise ValidationError("Basket cannot contain more than one item")
        # Item updated
        product_version_id = items[0].get("id")
        if product_version_id is None:
            raise ValidationError("Invalid request")
        try:
            product_version = ProductVersion.objects.get(id=product_version_id)
        except ProductVersion.DoesNotExist:
            raise ValidationError(
                "Invalid product version id {}".format(items[0]["id"])
            )
    elif items is not None:
        # Item removed
        product_version = None
    else:
        # Item has not changed
        product_version = latest_product_version(basket.basketitems.first().product)
    return product_version


def _update_coupons(basket, product_version, coupons):
    """
    Helper function to determine if the basket coupon should be updated, removed, or kept as is.

    Args:
        basket (Basket): the basket to update
        product_version (ProductVersion): the product version coupon should apply to
        coupons (list of JSON objects): Basket coupons to update, or clear if empty list, or leave as is if None

    Returns:
        CouponVersion: CouponVersion object to assign to basket, if any.

    """
    if not product_version:
        # No product, so clear coupon too
        return None

    if coupons:
        if len(coupons) > 1:
            raise ValidationError("Basket cannot contain more than one coupon")
        coupon = coupons[0]
        if not isinstance(coupon, dict):
            raise ValidationError("Invalid request")
        coupon_code = coupon.get("code")
        if coupon_code is None:
            raise ValidationError("Invalid request")

        # Check if the coupon is valid for the product
        coupon_version = best_coupon_for_product(
            product_version.product, basket.user, code=coupon_code
        )
        if coupon_version is None:
            raise ValidationError("Coupon code {} is invalid".format(coupon_code))
    elif coupons is not None:
        # Coupon was cleared, get the best available auto coupon for the product instead
        coupon_version = best_coupon_for_product(
            product_version.product, basket.user, auto_only=True
        )
    else:
        # coupon was not changed, make sure it is still valid; if not, replace with best auto coupon if any.
        coupon_selection = basket.couponselection_set.first()
        if coupon_selection:
            coupon_version = latest_coupon_version(coupon_selection.coupon)
        else:
            coupon_version = None
        valid_coupon_versions = get_valid_coupon_versions(
            product_version.product, basket.user
        )
        if coupon_version is None or coupon_version not in valid_coupon_versions:
            coupon_version = best_coupon_for_product(
                product_version.product, basket.user, auto_only=True
            )
    return coupon_version


def coupon_code_csv_view(request, version_id):
    """View for returning a csv file of coupon codes"""
    if not (request.user and request.user.is_staff):
        raise PermissionDenied
    coupon_payment_version = get_object_or_404(CouponPaymentVersion, id=version_id)
    response = HttpResponse(content_type="text/csv")
    response[
        "Content-Disposition"
    ] = 'attachment; filename="coupon_codes_{}.csv"'.format(version_id)
    writer = csv.writer(response)
    for coupon_code in coupon_payment_version.couponversion_set.values_list(
        "coupon__coupon_code", flat=True
    ):
        writer.writerow([coupon_code])
    return response
