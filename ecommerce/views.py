"""Views for ecommerce"""
import csv
import logging
from collections import defaultdict
from urllib.parse import urljoin

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework import status
from rest_framework.generics import get_object_or_404, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from b2b_ecommerce.api import fulfill_b2b_order
from b2b_ecommerce.models import B2BOrder
from courses.models import CourseRun
from courses.serializers import BaseCourseRunSerializer, BaseProgramSerializer
from ecommerce.api import (
    create_unfulfilled_order,
    fulfill_order,
    generate_cybersource_sa_payload,
    get_product_version_price_with_discount,
    get_full_price_coupon_product_set,
    get_available_bulk_product_coupons,
    get_readable_id,
    make_receipt_url,
    validate_basket_for_checkout,
    complete_order,
    bulk_assign_product_coupons,
)
from ecommerce.utils import make_checkout_url
from ecommerce.exceptions import ParseException
from ecommerce.mail_api import send_bulk_enroll_emails
from ecommerce.models import (
    Basket,
    Company,
    CouponPaymentVersion,
    Order,
    Product,
    Receipt,
    CouponPayment,
    BulkCouponAssignment,
)
from ecommerce.permissions import IsSignedByCyberSource
from ecommerce.serializers import (
    BasketSerializer,
    CouponPaymentVersionDetailSerializer,
    CompanySerializer,
    BaseProductSerializer,
    ProductDetailSerializer,
    PromoCouponSerializer,
    SingleUseCouponSerializer,
    CurrentCouponPaymentSerializer,
)
from hubspot.task_helpers import sync_hubspot_deal
from mitxpro.utils import (
    make_csv_http_response,
    first_or_none,
    format_datetime_for_filename,
)

log = logging.getLogger(__name__)


COUPON_NAME_FILENAME_LIMIT = 20


class ProductViewSet(ReadOnlyModelViewSet):
    """API view set for Products"""

    authentication_classes = ()
    permission_classes = ()

    serializer_class = ProductDetailSerializer
    queryset = Product.objects.exclude(productversions=None)


class CompanyViewSet(ReadOnlyModelViewSet):
    """API view set for Companies"""

    permission_classes = (IsAuthenticated,)
    authentication_classes = (SessionAuthentication,)

    serializer_class = CompanySerializer
    queryset = Company.objects.all().order_by("name")


class CheckoutView(APIView):
    """
    View for checkout API. This creates an Order in our system and provides a dictionary to
    send to Cybersource
    """

    authentication_classes = (SessionAuthentication, TokenAuthentication)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):  # pylint: disable=too-many-locals
        """
        Create a new unfulfilled Order from the user's basket
        and return information used to submit to CyberSource.
        """

        validate_basket_for_checkout(request.user.basket)
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

        # Should only have one line per order currently
        line = order.lines.first()

        readable_id = get_readable_id(line.product_version.product.content_object)

        if total_price == 0:
            # If price is $0, don't bother going to CyberSource, just mark as fulfilled
            order.status = Order.FULFILLED
            order.save()
            sync_hubspot_deal(order)

            complete_order(order)
            order.save_and_log(request.user)

            # This redirects the user to our order success page
            payload = {}
            url = make_receipt_url(base_url=base_url, readable_id=readable_id)
            method = "GET"
        else:
            # This generates a signed payload which is submitted as an HTML form to CyberSource
            receipt_url = make_receipt_url(base_url=base_url, readable_id=readable_id)
            cancel_url = urljoin(base_url, "checkout/")
            payload = generate_cybersource_sa_payload(
                order=order, receipt_url=receipt_url, cancel_url=cancel_url
            )
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
        try:
            reference_number = request.data.get("req_reference_number", "")
            if reference_number.startswith(B2BOrder.get_reference_number_prefix()):
                fulfill_b2b_order(request.data)
            elif reference_number.startswith(Order.get_reference_number_prefix()):
                fulfill_order(request.data)
            else:
                raise ParseException(
                    f"Unknown prefix '{reference_number}' for reference number"
                )
        except:
            # Not sure what would cause an error here but make sure we save the receipt
            Receipt.objects.create(data=request.data)
            raise

        # The response does not matter to CyberSource
        return Response(status=status.HTTP_200_OK)


class BasketView(RetrieveUpdateAPIView):
    """ API view for viewing and updating a basket """

    permission_classes = (IsAuthenticated,)
    authentication_classes = (SessionAuthentication,)
    serializer_class = BasketSerializer

    def get_object(self):
        """Get basket for user"""
        basket, _ = Basket.objects.get_or_create(user=self.request.user)
        return basket


class BulkEnrollCouponListView(APIView):
    """
    Admin view for fetching coupons that can be used for bulk enrollment
    """

    permission_classes = (IsAdminUser,)
    authentication_classes = (SessionAuthentication,)

    def get(self, request, *args, **kwargs):  # pylint: disable=missing-docstring
        """
        Handles GET requests. Response data is of this form:

        {
            "coupon_payments": [
                {
                    <serialized CouponPayment>,
                    "products": [
                        <basic serialized data for a Product that the CouponPayment applies to>,
                        ...
                    ]
                },
                ...
            ],
            "product_map": {
                "courserun": {
                    "<Product.id>": {<serialized CourseRun>},
                    ...
                },
                "program": {
                    "<Product.id>": {<serialized Program>},
                    ...
                }
            }
        """
        product_set = set()
        serialized = {"coupon_payments": []}
        for coupon_payment, products in get_full_price_coupon_product_set():
            for product in products:
                if product not in product_set:
                    product_set.add(product)
            serialized["coupon_payments"].append(
                {
                    **CurrentCouponPaymentSerializer(
                        coupon_payment,
                        context={
                            "latest_version": first_or_none(
                                coupon_payment.ordered_versions
                            )
                        },
                    ).data,
                    "products": BaseProductSerializer(
                        products, context={"has_ordered_versions": True}, many=True
                    ).data,
                }
            )
        serialized["product_map"] = defaultdict(dict)
        for product in product_set:
            product_object = product.content_object
            serialized["product_map"][product.content_type.model][str(product.id)] = (
                BaseCourseRunSerializer(product_object).data
                if isinstance(product_object, CourseRun)
                else BaseProgramSerializer(product_object).data
            )

        return Response(status=status.HTTP_200_OK, data=serialized)


class BulkEnrollmentSubmitView(APIView):
    """
    Admin view for submitting bulk enrollment requests
    """

    permission_classes = (IsAdminUser,)
    authentication_classes = (SessionAuthentication,)

    def post(self, request, *args, **kwargs):
        """View to send an enrollment email to all users in an uploaded csv file"""
        product_id = int(request.data["product_id"])
        coupon_payment_id = int(request.data["coupon_payment_id"])
        coupon_payment = CouponPayment.objects.get(pk=coupon_payment_id)

        # Extract emails of users to enroll from the uploaded user csv file
        users_file = request.data["users_file"]
        reader = csv.reader(users_file.read().decode("utf-8").splitlines())
        emails = [email_row[0] for email_row in reader]

        available_product_coupons = get_available_bulk_product_coupons(
            coupon_payment_id, product_id
        )

        coupon_limit_error = ""
        if len(emails) > coupon_payment.latest_version.num_coupon_codes:
            coupon_limit_error = "The given coupon has {} code(s) available, but {} users were submitted".format(
                coupon_payment.latest_version.num_coupon_codes, len(emails)
            )
        elif len(emails) > available_product_coupons.count():
            coupon_limit_error = "Only {} coupon(s) left that have not already been sent to users, but {} users were submitted".format(
                available_product_coupons.count(), len(emails)
            )

        if coupon_limit_error:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"errors": [{"users_file": coupon_limit_error}]},
            )

        bulk_assignment, product_coupon_assignments = bulk_assign_product_coupons(
            zip(emails, available_product_coupons.values_list("id", flat=True))
        )
        send_bulk_enroll_emails(bulk_assignment.id, product_coupon_assignments)

        return Response(
            status=status.HTTP_200_OK,
            data={"emails": emails, "bulk_assignment_id": bulk_assignment.id},
        )


class CouponListView(APIView):
    """
    Admin view for CRUD operations on coupons
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
                data=CouponPaymentVersionDetailSerializer(
                    instance=payment_version
                ).data,
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


def coupon_code_csv_view(request, version_id):
    """View for returning a csv file of coupon codes"""
    if not (request.user and request.user.is_staff):
        raise PermissionDenied
    coupon_payment_version = get_object_or_404(CouponPaymentVersion, id=version_id)

    return make_csv_http_response(
        csv_rows=(
            {"code": code}
            for code in coupon_payment_version.couponversion_set.values_list(
                "coupon__coupon_code", flat=True
            )
        ),
        filename=f"coupon_codes_{coupon_payment_version.payment.name}.csv",
    )


def bulk_assignment_csv_view(request, bulk_assignment_id):
    """View for returning a csv file of bulk assigned coupons"""
    if not (request.user and request.user.is_staff):
        raise PermissionDenied
    bulk_assignment = (
        BulkCouponAssignment.objects.filter(id=bulk_assignment_id)
        .prefetch_related(
            "assignments__product_coupon__coupon",
            "assignments__product_coupon__product",
        )
        .first()
    )
    if not bulk_assignment:
        raise Http404

    # It's assumed that the bulk assignment will have the same coupon payment for all of the individual assignments, so
    # use the name value for the first coupon payment for the filename.
    first_assignment = bulk_assignment.assignments.first()
    first_coupon_name = first_assignment.product_coupon.coupon.payment.name
    return make_csv_http_response(
        csv_rows=(
            {
                "email": product_coupon_assignment.email,
                "enrollment_url": make_checkout_url(
                    product_id=product_coupon_assignment.product_coupon.product.id,
                    code=product_coupon_assignment.product_coupon.coupon.coupon_code,
                ),
                "coupon_code": product_coupon_assignment.product_coupon.coupon.coupon_code,
            }
            for product_coupon_assignment in bulk_assignment.assignments.all()
        ),
        filename="Bulk Assign {coupon_name} {formatted_dt}.csv".format(
            coupon_name=first_coupon_name[0:COUPON_NAME_FILENAME_LIMIT],
            formatted_dt=format_datetime_for_filename(bulk_assignment.created_on),
        ),
    )
